import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import database as db
from aiohttp import web
import json

import database as db
from handlers import start, profile, payments, admin
from services.digiflazz import get_catalog

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def background_cleanup():
    """Background task to periodically clean up expired pending payments."""
    while True:
        try:
            await db.cleanup_expired_payments()
            logging.info("Cleaned up expired payments.")
        except Exception as e:
            logging.error(f"Error cleaning up expired payments: {e}")
        # Run every 60 seconds
        await asyncio.sleep(60)

async def api_catalog_handler(request: web.Request):
    """API endpoint to get the product catalog."""
    catalog = await get_catalog()
    
    # Return JSON with permissive CORS for the WebApp
    return web.json_response(
        {"status": "success", "data": catalog},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

async def options_handler(request: web.Request):
    """Handle CORS preflight requests."""
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

async def start_web_server():
    """Starts the aiohttp web server for the frontend API."""
    app = web.Application()
    app.router.add_get('/api/catalog', api_catalog_handler)
    app.router.add_options('/api/catalog', options_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("API server running on http://0.0.0.0:8080")

async def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize DB
    await db.init_db()
    
    # Initialize bot and dispatcher
    # Using DefaultBotProperties for the required parse_mode
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    
    # Register routers to Dispatcher
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(payments.router)
    dp.include_router(admin.router)
    
    # Start background cleanup task
    asyncio.create_task(background_cleanup())
    
    # Start the API server
    asyncio.create_task(start_web_server())
    
    # Delete webhook (to ensure long-polling works) and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
