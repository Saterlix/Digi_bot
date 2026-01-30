"""
Mock Digiflazz API client for testing and development.
Simulates API responses without making actual network requests.
"""

import logging
import uuid
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MockDigiflazzClient:
    """
    Mock client that simulates Digiflazz behavior.
    """
    
    async def get_balance(self) -> dict[str, Any]:
        """Simulate getting user balance."""
        logger.info("[MOCK] Checking balance")
        return {
            "data": {
                "deposit": 10000000,  # 10 Million IDR
                "currency": "IDR"
            }
        }
    
    async def get_price_list(
        self,
        cmd: str = "prepaid",
        category: Optional[str] = None
    ) -> dict[str, Any]:
        """Simulate getting price list."""
        logger.info(f"[MOCK] Fetching price list: category={category}")
        
        # Mock data based on user requirements (Mobile Legends, PUBG)
        # Prices in IDR
        products = [
            {
                "product_name": "Mobile Legends 11 Diamonds",
                "buyer_sku_code": "MLBB_11",
                "category": "Games",
                "brand": "Mobile Legends",
                "price": 3000,
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "Instant"
            },
            {
                "product_name": "Mobile Legends 53 Diamonds",
                "buyer_sku_code": "MLBB_53",
                "category": "Games",
                "brand": "Mobile Legends",
                "price": 14000,
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "Instant"
            },
            {
                "product_name": "Mobile Legends 100 Diamonds",
                "buyer_sku_code": "MLBB_100",
                "category": "Games",
                "brand": "Mobile Legends",
                "price": 28000,
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "Instant"
            },
            {
                "product_name": "PUBG Mobile 60 UC",
                "buyer_sku_code": "PUBG_60",
                "category": "Games",
                "brand": "PUBG Mobile",
                "price": 14500,
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "Global"
            },
            {
                "product_name": "Free Fire 100 Diamonds",
                "buyer_sku_code": "FF_100",
                "category": "Games",
                "brand": "Free Fire",
                "price": 18000,
                "buyer_product_status": True,
                "seller_product_status": True,
                "desc": "ID Only"
            }
        ]
        
        if category:
            products = [p for p in products if p["category"] == category]
            
        return {"data": products}
    
    async def create_transaction(
        self,
        buyer_sku_code: str,
        customer_no: str,
        ref_id: str
    ) -> dict[str, Any]:
        """Simulate creating a transaction."""
        logger.info(f"[MOCK] Creating transaction: sku={buyer_sku_code}, ref={ref_id}")
        
        # Simulate success
        return {
            "data": {
                "ref_id": ref_id,
                "status": "Success",  # Mocking immediate success
                "message": "Transaction Successful",
                "sn": f"SN{random.randint(1000000000, 9999999999)}",
                "price": 10000,  # Dummy deduction
                "balance": 9990000
            }
        }
