import asyncio
from typing import List, Dict

async def get_catalog() -> List[Dict]:
    """
    Fetches the catalog from Digiflazz.
    MOCK IMPLEMENTATION: Returns 4 mock products as requested.
    """
    # Simulate network delay
    await asyncio.sleep(0.5)
    
    mock_catalog = [
        {
            "id": "mock_mlbb_100",
            "category": "Mobile Legends",
            "name": "TEST 100 Diamonds",
            "price": 15000,
            "currency": "UZS",
            "icon": "💎",
            "badge": "-10%"
        },
        {
            "id": "mock_pubg_60",
            "category": "PUBG Mobile",
            "name": "TEST 60 UC",
            "price": 14000,
            "currency": "UZS",
            "icon": "💥",
            "badge": "Hot"
        },
        {
            "id": "mock_ff_100",
            "category": "Free Fire",
            "name": "TEST 100 Diamonds",
            "price": 12000,
            "currency": "UZS",
            "icon": "🔥",
            "badge": ""
        },
        {
            "id": "mock_roblox_80",
            "category": "Roblox",
            "name": "TEST 80 Robux",
            "price": 18000,
            "currency": "UZS",
            "icon": "🎮",
            "badge": "Bonus"
        }
    ]
    
    return mock_catalog
