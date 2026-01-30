"""
Demo script to show the Antigravity system in action.
Simulates the full flow: User Creation -> Balance Top-up -> Catalog Check -> Purchase.
Mocks external API calls to Digiflazz.
"""

import asyncio
import os
import uuid
import logging
from unittest.mock import AsyncMock, patch
from typing import Any

from services.database import db
from services.pricing import pricing_engine
from services.digiflazz import DigiflazzClient

# Configure Logging to show what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("DEMO")

async def demo_scenario():
    print("\n🚀 Starting Antigravity System Demo\n" + "="*40)
    
    # Setup DB
    db_path = "antigravity.db"
    # Reset DB for demo
    if os.path.exists(db_path):
        os.remove(db_path)
    
    await db.connect()
    print("✅ Database System Initialized")

    # 1. Create User
    user_id = "12345678"
    username = "demo_user"
    await db.create_user(user_id, username)
    print(f"👤 User Created: {username} (ID: {user_id})")
    
    # 2. Add Balance
    initial_balance = 500000
    await db.update_balance(user_id, initial_balance)
    print(f"💰 Balance Credited: +{initial_balance} UZS")
    
    # 3. Simulate Catalog Check (Mocking Digiflazz)
    print("\n📋 Fetching Catalog (Mocked)...")
    
    # Mock data from Digiflazz
    mock_price_list = {
        "data": [
            {
                "product_name": "Mobile Legends 100 Diamonds",
                "buyer_sku_code": "MLBB_100",
                "category": "Games",
                "price": 28000,  # IDR
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "Instant Delivery"
            }
        ]
    }
    
    # Mock the API client
    with patch('services.digiflazz.DigiflazzClient._make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_price_list
        
        client = DigiflazzClient()
        response = await client.get_price_list()
        
        # Process prices
        products = response.get("data", [])
        processed = pricing_engine.process_price_list(products)
        item = processed[0]
        
        print(f"   Found Item: {item['product_name']}")
        print(f"   Base Price (IDR): {item['price_idr']}")
        print(f"   Final Price (UZS): {item['price_uzs']} (Calculated with margin)")
        
    # 4. Simulate Purchase
    print("\n🛒 Simulating Purchase Request...")
    target_sku = "MLBB_100"
    target_player = "9999911111"
    
    # Mock Transaction Response
    mock_trx_response = {
        "data": {
            "ref_id": f"TRX-{uuid.uuid4().hex[:8]}",
            "status": "Pending",
            "message": "Transaction processing",
            "sn": "SN1234567890"
        }
    }
    
    with patch('services.digiflazz.DigiflazzClient._make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_trx_response
        
        # LOGIC FROM buy_handler (Simulated)
        print(f"   User {user_id} buying {target_sku} for player {target_player}")
        
        # Check Price
        # (Re-using item calculated above)
        price_uzs = item['price_uzs']
        
        # Check Balance & Create Transaction
        ref_id = f"AG-DEMO-{uuid.uuid4().hex[:6]}"
        
        await db.create_transaction(
            ref_id=ref_id,
            user_id=user_id,
            sku=target_sku,
            player_id=target_player,
            amount=price_uzs,
            status="pending"
        )
        print(f"   📝 Transaction Record Created: {ref_id} (Pending)")
        
        # Deduct Balance
        new_balance = await db.update_balance(user_id, -price_uzs)
        print(f"   💸 Balance Deducted: -{price_uzs} UZS (Remaining: {new_balance})")
        
        # Call API
        api_res = await client.create_transaction(target_sku, target_player, ref_id)
        print("   📡 Digiflazz API Called")
        
        # Update Status
        provider_data = api_res.get("data", {})
        prov_status = "success" # mocking "Pending" -> success logic
        prov_ref = provider_data.get("sn")
        
        await db.update_transaction_status(ref_id, prov_status, prov_ref)
        print(f"   ✅ Transaction Finalized: {prov_status.upper()} (Provider Ref: {prov_ref})\n")
        
    # 5. Final State Check
    user = await db.get_user(user_id)
    print("📊 Final User State:")
    print(f"   Balance: {user['balance']} UZS")
    
    await db.close()
    print("\n✨ Demo Completed Successfully")

if __name__ == "__main__":
    asyncio.run(demo_scenario())
