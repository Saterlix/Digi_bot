
import logging
import os
from datetime import datetime
from typing import Optional, Any, Dict

import asyncpg

from config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages asynchronous PostgreSQL database interactions using asyncpg.
    Handles user balances and transaction history.
    """
    
    def __init__(self):
        """
        Initialize the database manager.
        """
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self) -> None:
        """Establish connection pool to the database."""
        if not self.pool:
            try:
                # SSL mode is required for Neon/Supabase
                self.pool = await asyncpg.create_pool(
                    dsn=config.DATABASE_URL,
                    min_size=1,
                    max_size=10, # Adjustable based on Vercel limits
                    ssl='require' 
                )
                logger.info("Connected to PostgreSQL database")
                await self.init_db()
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
            
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection closed")
            
    async def init_db(self) -> None:
        """Initialize database tables."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            # Users Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    balance BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transactions Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    ref_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    sku TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    provider_ref TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Active Deposits Table (for locking logic)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_deposits (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    amount BIGINT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        logger.info("Database tables initialized")
        
    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user_id))
            return dict(row) if row else None
            
    async def create_user(self, user_id: str, username: str = None) -> dict:
        """Create a new user or return existing."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            # Postgres: ON CONFLICT DO NOTHING
            await conn.execute(
                """
                INSERT INTO users (id, username) VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username
                """,
                str(user_id), username
            )
            return await self.get_user(user_id)
            
    async def update_balance(self, user_id: str, amount: int) -> int:
        """Update user balance (credit or debit)."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Lock row for update
                row = await conn.fetchrow("SELECT balance FROM users WHERE id = $1 FOR UPDATE", str(user_id))
                
                if not row:
                    # Auto-create if not exists (should rarely happen in this flow)
                    await self.create_user(user_id)
                    current_balance = 0
                else:
                    current_balance = row["balance"]
                    
                new_balance = current_balance + amount
                
                if new_balance < 0:
                    raise ValueError("Insufficient funds")
                    
                await conn.execute(
                    """
                    UPDATE users 
                    SET balance = $1, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = $2
                    """,
                    new_balance, str(user_id)
                )
                return new_balance
        
    async def create_transaction(
        self,
        ref_id: str,
        user_id: str,
        sku: str,
        player_id: str,
        amount: int,
        status: str = "pending"
    ) -> dict:
        """Create a new transaction record."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO transactions 
                (ref_id, user_id, sku, player_id, amount, status) 
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                ref_id, str(user_id), sku, player_id, amount, status
            )
        
        return {
            "ref_id": ref_id,
            "user_id": user_id,
            "sku": sku,
            "amount": amount,
            "status": status
        }
    
    async def update_transaction_status(
        self,
        ref_id: str,
        status: str,
        provider_ref: str = None
    ) -> None:
        """Update transaction status."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            if provider_ref:
                await conn.execute(
                    "UPDATE transactions SET status = $1, provider_ref = $2, updated_at = CURRENT_TIMESTAMP WHERE ref_id = $3",
                    status, provider_ref, ref_id
                )
            else:
                await conn.execute(
                    "UPDATE transactions SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE ref_id = $2",
                    status, ref_id
                )

    async def create_deposit(self, user_id: str, amount: int, expires_at: datetime) -> int:
        """Creates a pending deposit record."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            # RETURN id to get the inserted serial
            val = await conn.fetchval(
                "INSERT INTO active_deposits (user_id, amount, expires_at) VALUES ($1, $2, $3) RETURNING id",
                str(user_id), amount, expires_at
            )
            return val

    async def is_amount_active(self, amount: int) -> bool:
        """Checks if an amount is currently locked in active_deposits."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT 1 FROM active_deposits WHERE amount = $1 AND expires_at > CURRENT_TIMESTAMP", 
                amount
            )
            return val is not None

    async def cleanup_expired_deposits(self) -> None:
        """Removes expired deposits."""
        if not self.pool:
            raise RuntimeError("Database not connected")
            
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM active_deposits WHERE expires_at <= CURRENT_TIMESTAMP"
            )


# Singleton instance
db = DatabaseManager()
