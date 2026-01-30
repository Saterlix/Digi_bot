"""
Digiflazz API integration client.
Handles communication with Digiflazz API for balance checks and price lists.
"""

import hashlib
import logging
from typing import Any, Optional

import aiohttp

from config import config

logger = logging.getLogger(__name__)


class DigiflazzClient:
    """
    Async client for interacting with the Digiflazz API.
    
    Implements signature-based authentication and provides methods
    for checking balance and retrieving price lists.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the Digiflazz client.
        
        Args:
            session: Optional aiohttp ClientSession. If not provided,
                     a new session will be created for each request.
        """
        self._session = session
        self._base_url = config.DIGIFLAZZ_BASE_URL
        self._username = config.DIGIFLAZZ_USER
        self._api_key = config.DIGIFLAZZ_KEY
    
    def _generate_signature(self, ref_id: Optional[str] = None) -> str:
        """
        Generate MD5 signature for API authentication.
        
        For balance check: md5(username + key + "depo")
        For transactions: md5(username + key + ref_id)
        
        Args:
            ref_id: Reference ID for transactions. If None, generates
                   signature for balance check using "depo".
        
        Returns:
            MD5 hash string of the signature.
        """
        suffix = ref_id if ref_id else "depo"
        raw_signature = f"{self._username}{self._api_key}{suffix}"
        return hashlib.md5(raw_signature.encode()).hexdigest()
    
    async def _make_request(
        self,
        endpoint: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Make an authenticated POST request to the Digiflazz API.
        
        Args:
            endpoint: API endpoint path (e.g., "/cek-saldo").
            payload: Request payload dictionary.
        
        Returns:
            JSON response from the API.
        
        Raises:
            aiohttp.ClientError: If the request fails.
        """
        url = f"{self._base_url}{endpoint}"
        
        # Use provided session or create a new one
        if self._session:
            async with self._session.post(url, json=payload) as response:
                response.raise_for_status()
                return await response.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
    
    async def get_balance(self) -> dict[str, Any]:
        """
        Check the current Digiflazz deposit balance.
        
        Returns:
            API response containing balance information.
            Example: {"data": {"deposit": 1000000}}
        """
        signature = self._generate_signature()
        
        payload = {
            "cmd": "deposit",
            "username": self._username,
            "sign": signature
        }
        
        logger.info("Checking Digiflazz balance")
        
        try:
            response = await self._make_request("/cek-saldo", payload)
            logger.info(f"Balance check successful: {response}")
            return response
        except aiohttp.ClientError as e:
            logger.error(f"Failed to check balance: {e}")
            raise
    
    async def get_price_list(
        self,
        cmd: str = "prepaid",
        category: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Retrieve the price list from Digiflazz.
        
        Args:
            cmd: Command type - "prepaid" or "pasca" (postpaid).
            category: Optional category filter (e.g., "Pulsa", "PLN").
        
        Returns:
            API response containing list of products with prices.
            Example: {"data": [{"product_name": "...", "price": 10000, ...}]}
        """
        """
        Retrieve the price list.
        MOCKED: Returns hardcoded data for Mobile Legends, Free Fire, and PUBG.
        """
        # Static Mock Data
        mock_items = [
            # Mobile Legends
            {"product_name": "Weekly Diamond Pass", "category": "Games", "brand": "Mobile Legends", "price": 24000, "buyer_sku_code": "mlbb_wdp", "desc": "Fast Delivery"},
            {"product_name": "86 Diamonds", "category": "Games", "brand": "Mobile Legends", "price": 12500, "buyer_sku_code": "mlbb_86", "desc": "Instant"},
            {"product_name": "172 Diamonds", "category": "Games", "brand": "Mobile Legends", "price": 25000, "buyer_sku_code": "mlbb_172", "desc": "Bonus +10"},
            
            # Free Fire
            {"product_name": "100 Diamonds", "category": "Games", "brand": "Free Fire", "price": 11000, "buyer_sku_code": "ff_100", "desc": "ID Only"},
            {"product_name": "310 Diamonds", "category": "Games", "brand": "Free Fire", "price": 32000, "buyer_sku_code": "ff_310", "desc": "Fast"},

            # PUBG Mobile
            {"product_name": "60 UC", "category": "Games", "brand": "PUBG Mobile", "price": 11500, "buyer_sku_code": "pubg_60", "desc": "Global"},
            {"product_name": "325 UC", "category": "Games", "brand": "PUBG Mobile", "price": 58000, "buyer_sku_code": "pubg_325", "desc": "Global"},
        ]

        logger.info(f"Returning {len(mock_items)} mock items")
        return {"data": mock_items}
    
    async def create_transaction(
        self,
        buyer_sku_code: str,
        customer_no: str,
        ref_id: str
    ) -> dict[str, Any]:
        """
        Create a new transaction (purchase) on Digiflazz.
        
        Args:
            buyer_sku_code: Product SKU code.
            customer_no: Customer number/ID (e.g., phone number, game ID).
            ref_id: Unique reference ID for this transaction.
        
        Returns:
            API response containing transaction status.
        """
        signature = self._generate_signature(ref_id)
        
        payload = {
            "username": self._username,
            "buyer_sku_code": buyer_sku_code,
            "customer_no": customer_no,
            "ref_id": ref_id,
            "sign": signature
        }
        
        logger.info(f"Creating transaction: sku={buyer_sku_code}, ref={ref_id}")
        
        try:
            response = await self._make_request("/transaction", payload)
            logger.info(f"Transaction created: {response}")
            return response
        except aiohttp.ClientError as e:
            logger.error(f"Failed to create transaction: {e}")
            raise
