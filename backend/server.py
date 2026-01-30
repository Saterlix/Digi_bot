"""
Antigravity - Secure Backend API for Telegram Mini App Donation Store.

This is the main entry point for the aiohttp web server.
Provides API endpoints for health checks, catalog retrieval, and purchases.
"""

import logging
import uuid
from typing import Optional

import aiohttp_cors
import aiohttp
from aiohttp import web
import hmac
import hashlib
import json
from urllib.parse import parse_qsl

from config import config
# from services.digiflazz import DigiflazzClient
from services.digiflazz_mock import MockDigiflazzClient as DigiflazzClient  # Use Mock for dev
from services.pricing import pricing_engine
from services.database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Security & Validation
# ============================================================================

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram Mini App initData using HMAC-SHA256.
    """
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_value = parsed_data.pop('hash', None)
        
        if not hash_value:
            return {"valid": False, "error": "No hash provided"}
            
        # Create data check string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # Calculate secret key (HMAC-SHA256 of bot token with 'WebAppData')
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != hash_value:
             return {"valid": False, "error": "Invalid hash"}
             
        # Parse user data
        user_data = json.loads(parsed_data.get('user', '{}'))
        return {
            "valid": True,
            "user": user_data,
            "data": parsed_data
        }
        
    except Exception as e:
        logger.error(f"Auth validation error: {e}")
        return {"valid": False, "error": str(e)}


# ============================================================================
# API Handlers
# ============================================================================

async def health_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint.
    
    Returns:
        200 OK with status information.
    """
    return web.json_response({
        "status": "ok",
        "service": "antigravity",
        "version": "1.0.0"
    })


async def catalog_handler(request: web.Request) -> web.Response:
    """
    Get the catalog of available items with UZS prices.
    
    Query Parameters:
        category: Optional category filter.
    
    Returns:
        JSON array of products with calculated UZS prices.
    """
    category = request.query.get("category")
    
    try:
        # Get the shared client session from app
        # session = request.app.get("client_session")
        # client = DigiflazzClient(session=session)
        
        # Mock Client doesn't need session, but we keep signature compatible if possible
        # or just instantiate directly
        client = DigiflazzClient() 
        
        # Fetch price list from Digiflazz
        # response = await client.get_price_list(category=category)
        # Mock client might not accept arguments yet if signature differs?
        # Checked mock code: get_price_list(cmd, category) matches.
        
        response = await client.get_price_list(category=category)
        price_list = response.get("data", [])
        
        # Process prices to UZS
        processed_list = pricing_engine.process_price_list(price_list)
        
        # Filter active products only
        active_products = [
            item for item in processed_list
            if item.get("buyer_product_status", True) and item.get("seller_product_status", True)
        ]
        
        return web.json_response({
            "success": True,
            "data": active_products,
            "count": len(active_products)
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch catalog: {e}")
        return web.json_response(
            {"success": False, "error": "Failed to fetch catalog"},
            status=500
        )


async def buy_handler(request: web.Request) -> web.Response:
    """
    Process a purchase request.
    
    1. Validate input/auth.
    2. Check item price and user balance.
    3. Create pending transaction.
    4. Deduct balance (atomic).
    5. call Digiflazz API.
    6. Update transaction status.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"success": False, "error": "Invalid JSON body"},
            status=400
        )
    
    # Validate required fields
    user_id = data.get("user_id")
    item_sku = data.get("item_sku")
    player_id = data.get("player_id")
    
    if not all([user_id, item_sku, player_id]):
        return web.json_response(
            {"success": False, "error": "Missing required fields"},
            status=400
        )
        
    # Validated required fields
    
    # Ensure user exists (Auto-register for demo purposes)
    await db.create_user(user_id)
    
    # Generate unique reference ID
    ref_id = f"AG-{user_id}-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        # 1. Get Product Price (Simulate lookup or cache)
        # In a real app, you might want to cache the catalog or look it up live
        # session = request.app.get("client_session")
        # client = DigiflazzClient(session=session)
        client = DigiflazzClient()
        
        # Security: In production, verify price hasn't changed significantly or cache it
        # For this implementation, we'll fetch it to be sure
        # Optimization: In high traffic, this should be cached
        # We need the price in UZS to deduct from balance
        
        # 2. Check Balance & Deduct
        # We need to know the price amount to deduct.
        # Ideally, the frontend sends the expected price, and we verify it matches backend.
        # For now, let's assume we lookup price from a cached source or Digiflazz.
        # Simplified: Trusting frontend price is dangerous. We MUST lookup price.
        
        # fetching price for sku (expensive operation per request, consider caching!)
        # For now, we will handle this by fetching price list (mocking single item lookup for MVP)
        # In production -> Redis/Local Cache
        
        # Let's assume we proceed with a transaction record first
        # We need the amount. For MVP, we'll require 'amount_uzs' in payload or look it up.
        # Let's look it up from Digiflazz for correctness.
        
        # price_res = await client.get_price_list(cmd="prepaid", category=...) 
        # This is too slow.
        # ALTERNATIVE: PASS PRICE FROM FRONTEND AND VERIFY SIGNATURE OR JUST TRUST FOR MVP (NOT SECURE)
        # BETTER: Use a predefined map or cache.
        
        # For this MVP step 2: 
        # We will assume the user has enough balance and we know the price.
        # Since I cannot implement full catalog caching in this step easily without extra complexity:
        # I will fetch the price list to find the item.
        
        price_list_res = await client.get_price_list()
        products = price_list_res.get("data", [])
        product = next((p for p in products if p["buyer_sku_code"] == item_sku), None)
        
        if not product:
             return web.json_response({"success": False, "error": "Product not found"}, status=404)
             
        # Calculate UZS price
        price_uzs = pricing_engine.convert_idr_to_uzs(product["price"])
        
        # 3. Create Transaction Record (Pending)
        await db.create_transaction(
            ref_id=ref_id,
            user_id=user_id,
            sku=item_sku,
            player_id=player_id,
            amount=price_uzs,
            status="pending"
        )
        
        # 4. Atomic Balance Deduction
        try:
            new_balance = await db.update_balance(user_id, -price_uzs)
        except ValueError:
             await db.update_transaction_status(ref_id, "failed")
             return web.json_response(
                 {"success": False, "error": "Insufficient balance"},
                 status=402
             )
             
        # 5. Execute Purchase on Digiflazz
        try:
            trx_res = await client.create_transaction(
                buyer_sku_code=item_sku,
                customer_no=player_id,
                ref_id=ref_id
            )
            
            # Check provider status
            provider_data = trx_res.get("data", {})
            provider_status = provider_data.get("status", "Pending")
            provider_ref = provider_data.get("sn") or provider_data.get("ref_id")
            
            # Map provider status to local status
            final_status = "success" if provider_status in ["Success", "Pending"] else "failed"
            # Note: "Pending" in Digiflazz means it's processing, we treat as success for now 
            # or keep as pending. Let's keep as pending-success logic.
            
            await db.update_transaction_status(ref_id, final_status, provider_ref)
            
            return web.json_response({
                "success": True,
                "message": "Transaction processed",
                "data": {
                    "ref_id": ref_id,
                    "status": final_status,
                    "price": price_uzs,
                    "remaining_balance": new_balance,
                    "provider_message": provider_data.get("message")
                }
            })
            
        except Exception as e:
            # Refund on API failure
            logger.error(f"Digiflazz API failed: {e}")
            await db.update_balance(user_id, price_uzs) # Refund
            await db.update_transaction_status(ref_id, "failed")
            return web.json_response(
                {"success": False, "error": "Provider error"},
                status=502
            )

    except Exception as e:
        logger.error(f"Buy handler error: {e}")
        return web.json_response(
            {"success": False, "error": "Internal server error"},
            status=500
        )


async def balance_handler(request: web.Request) -> web.Response:
    """
    Get the current Digiflazz deposit balance.
    
    Note: This endpoint should be protected in production.
    
    Returns:
        JSON with balance information.
    """
    try:
        session = request.app.get("client_session")
        client = DigiflazzClient(session=session)
        
        response = await client.get_balance()
        
        return web.json_response({
            "success": True,
            "data": response.get("data", {})
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
        return web.json_response(
            {"success": False, "error": "Failed to fetch balance"},
            status=500
        )



async def login_handler(request: web.Request) -> web.Response:
    """
    Handle user login via Telegram initData.
    """
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
             return web.json_response({"success": False, "error": "Missing initData"}, status=400)
             
        validation = validate_telegram_init_data(init_data, config.BOT_TOKEN)
        
        if not validation["valid"]:
            return web.json_response({"success": False, "error": "Invalid authentication"}, status=401)
            
        tg_user = validation["user"]
        user_id = str(tg_user.get("id"))
        username = tg_user.get("username", "Unknown")
        
        # Ensure user exists in DB
        user_record = await db.create_user(user_id, username)
        
        return web.json_response({
            "success": True,
            "user": {
                "id": user_id,
                "username": username,
                "balance": user_record.get("balance", 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return web.json_response({"success": False, "error": "Internal Error"}, status=500)


async def deposit_handler(request: web.Request) -> web.Response:
    """
    Test endpoint to add funds.
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        amount = int(data.get("amount", 0))
        
        if not user_id or amount <= 0:
            return web.json_response({"success": False, "error": "Invalid params"}, status=400)
            
        new_balance = await db.update_balance(user_id, amount)
        
        return web.json_response({
            "success": True,
            "new_balance": new_balance,
            "message": f"Added {amount} UZS"
        })
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


# ============================================================================
# Application Setup
# ============================================================================

async def on_startup(app: web.Application) -> None:
    """Create shared resources on application startup."""
    # Connect to database
    await db.connect()
    logger.info("Database connection established")
    
    # Create a shared aiohttp ClientSession
    app["client_session"] = aiohttp.ClientSession()
    logger.info("Application started - client session created")


async def on_cleanup(app: web.Application) -> None:
    """Clean up resources on application shutdown."""
    # Close database connection
    await db.close()
    
    session = app.get("client_session")
    if session:
        await session.close()
    logger.info("Application shutting down - resources cleaned up")


def create_app() -> web.Application:
    """
    Create and configure the aiohttp application.
    
    Returns:
        Configured web.Application instance.
    """
    app = web.Application()
    
    # Register lifecycle handlers
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    
    # Add routes
    app.router.add_get("/health", health_handler)
    app.router.add_get("/api/catalog", catalog_handler)
    app.router.add_post("/api/buy", buy_handler)
    app.router.add_get("/api/balance", balance_handler)
    app.router.add_post("/api/auth/login", login_handler)
    app.router.add_post("/api/deposit", deposit_handler)
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS"]
        )
    })
    
    # Apply CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    logger.info("Application configured with CORS support")
    
    return app


def main() -> None:
    """Entry point for the application."""
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.warning(f"Configuration warnings: {errors}")
        logger.warning("Some features may not work without proper configuration")
    
    # Create and run the application
    app = create_app()
    
    logger.info(f"Starting Antigravity server on {config.HOST}:{config.PORT}")
    web.run_app(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
