
import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict

from services.database import db

logger = logging.getLogger(__name__)

# Hardcoded Admin Cards (as requested)
ADMIN_CARDS = [
    "9860176621555463",
    "5614684903147088",
    "4916990333210208",
    "4023060504089615",
    "5614682203527918"
]
ADMIN_NAME = "Normatov Shahriyor"

# Lock duration in minutes
LOCK_DURATION_MINUTES = 15

class PaymentManager:
    """
    Manages deposit requests and ensures unique exact amounts for active deposits.
    """

    async def create_deposit_request(self, user_id: str, desired_amount: int) -> Dict:
        """
        Attempts to reserve an amount close to the desired amount.
        If desired_amount is taken, finds the nearest free amount.
        """
        # 1. Clean up expired deposits first
        await db.cleanup_expired_deposits()

        # 2. Try to reserve the exact amount
        if await self._is_amount_free(desired_amount):
            return await self._reserve_amount(user_id, desired_amount)

        # 3. If taken, search for nearest available amount (+- 500, +- 1000, etc.)
        # We step by 100 sums (or 500 as requested, but 100 is safer for collisions)
        # The user example said "30.500 or 31.000", so let's try steps of 100 to be flexible but keep it clean.
        # Let's try steps of 100 up to +/- 5000
        step = 100
        for i in range(1, 51): # 1 to 50
            offset = i * step
            
            # Check +offset
            candidate_up = desired_amount + offset
            if await self._is_amount_free(candidate_up):
                return await self._reserve_amount(user_id, candidate_up)
            
            # Check -offset (if valid > 0)
            candidate_down = desired_amount - offset
            if candidate_down > 0 and await self._is_amount_free(candidate_down):
                return await self._reserve_amount(user_id, candidate_down)
        
        # If we excessively fail (unlikely), just return None or error
        raise ValueError("System busy: Cannot reserve a unique amount at this time.")

    async def _is_amount_free(self, amount: int) -> bool:
        """Checks if a specific amount is currently locked by someone else."""
        return not await db.is_amount_active(amount)

    async def _reserve_amount(self, user_id: str, amount: int) -> Dict:
        """Locks the amount for the user and returns payment details."""
        expires_at = datetime.now() + timedelta(minutes=LOCK_DURATION_MINUTES)
        
        # Save to DB
        deposit_id = await db.create_deposit(user_id, amount, expires_at)
        
        return {
            "deposit_id": deposit_id,
            "amount": amount,
            "currency": "UZS",
            "expires_at": expires_at.isoformat(),
            "admin_name": ADMIN_NAME,
            "card": random.choice(ADMIN_CARDS), # Show one random card or all? User said "these are my cards". Let's return all or one. Let's return one for UI simplicity but maybe list all in description.
            "all_cards": ADMIN_CARDS
        }

payment_manager = PaymentManager()
