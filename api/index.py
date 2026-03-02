
import logging
import os
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import types, Dispatcher, Bot
from aiogram.types import Update

from backend.bot import bot, dp
from backend.config import config
from backend.services.database import db
from backend.services.digiflazz_mock import MockDigiflazzClient
from backend.services.pricing import pricing_engine
from backend.services.payment_manager import payment_manager

# Initialize FastAPI
app = FastAPI()

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Services
# Note: On Vercel, this runs on every request effectively for serverless functions,
# but we rely on the global instances in modules.
digiflazz_client = MockDigiflazzClient()

@app.on_event("startup")
async def on_startup():
    await db.connect()
    # Set webhook on startup (optional, better to do manually or via script)
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != config.WEBAPP_URL + "/api/webhook":
         await bot.set_webhook(config.WEBAPP_URL + "/api/webhook")

@app.on_event("shutdown")
async def on_shutdown():
    await db.close()

# --- Telegram Webhook ---
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """
    Handle incoming Telegram updates.
    """
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# --- Frontend API Endpoints ---

@app.get("/api/user")
async def get_user(user_id: str):
    """Get user profile and balance."""
    user = await db.get_user(user_id)
    if not user:
        # Create user if not exists (frontend might call this first)
        user = await db.create_user(user_id, "Guest")
    return user

@app.get("/api/catalog")
async def get_catalog(category: Optional[str] = None):
    """Get processed catalog items (Mock Digiflazz)."""
    # Get raw mock data
    response = await digiflazz_client.get_price_list(category=category)
    raw_items = response.get("data", [])
    
    # Process with pricing engine (margin + IDR->UZS)
    processed_items = pricing_engine.process_price_list(raw_items)
    
    return processed_items

@app.post("/api/deposit")
async def create_deposit(data: dict):
    """
    Initiate a deposit request.
    Wraps the 'Amount Locking' logic.
    """
    user_id = data.get("user_id")
    amount = data.get("amount")
    
    if not user_id or not amount:
        raise HTTPException(status_code=400, detail="Missing user_id or amount")
        
    try:
        amount = int(amount)
        if amount <= 0:
             raise HTTPException(status_code=400, detail="Amount must be positive")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        result = await payment_manager.create_deposit_request(str(user_id), amount)
        return result
    except ValueError as e:
        # If locking fails (e.g. system busy)
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/")
async def root():
    return {"status": "Antigravity Bot API Running"}
