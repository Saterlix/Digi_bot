"""
Database manager for Antigravity backend.
Handles SQLite connections and operations using aiosqlite.
"""

import logging
from datetime import datetime
from typing import Optional, Any

import aiosqlite

from config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages asynchronous SQLite database interactions.
    Handles user balances and transaction history.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._conn: Optional[aiosqlite.Connection] = None
        
    async def connect(self) -> None:
        """Establish connection to the database."""
        if not self._conn:
            self._conn = await aiosqlite.connect(self.db_path)
            # Enable row factory to get dict-like access
            self._conn.row_factory = aiosqlite.Row
            logger.info(f"Connected to database at {self.db_path}")
            await self.init_db()
            
    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")
            
    async def init_db(self) -> None:
        """Initialize database tables."""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                ref_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                player_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                provider_ref TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        await self._conn.commit()
        logger.info("Database tables initialized")
        
    async def get_user(self, user_id: str) -> Optional[dict]:
        """
        Get user by ID.
        
        Args:
            user_id: Telegram user ID.
            
        Returns:
            User record as dictionary or None if not found.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        async with self._conn.execute(
            "SELECT * FROM users WHERE id = ?", (str(user_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
            
    async def create_user(self, user_id: str, username: str = None) -> dict:
        """
        Create a new user.
        
        Args:
            user_id: Telegram user ID.
            username: Telegram username.
            
        Returns:
            Created user record.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        try:
            await self._conn.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (str(user_id), username)
            )
            await self._conn.commit()
            return await self.get_user(user_id)
        except aiosqlite.IntegrityError:
            return await self.get_user(user_id)
            
    async def update_balance(self, user_id: str, amount: int) -> int:
        """
        Update user balance (credit or debit).
        
        Args:
            user_id: Telegram user ID.
            amount: Amount to add (positive) or subtract (negative).
            
        Returns:
            New balance.
            
        Raises:
            ValueError: If insufficient funds for debit.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        # Use transaction for atomicity
        async with self._conn.execute("BEGIN"):
            cursor = await self._conn.execute(
                "SELECT balance FROM users WHERE id = ?", (str(user_id),)
            )
            row = await cursor.fetchone()
            
            if not row:
                # Auto-create user if not exists
                await self.create_user(user_id)
                current_balance = 0
            else:
                current_balance = row["balance"]
                
            new_balance = current_balance + amount
            
            if new_balance < 0:
                await self._conn.execute("ROLLBACK")
                raise ValueError("Insufficient funds")
                
            await self._conn.execute(
                """
                UPDATE users 
                SET balance = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (new_balance, str(user_id))
            )
            await self._conn.commit()
            
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
        """
        Create a new transaction record.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        await self._conn.execute(
            """
            INSERT INTO transactions 
            (ref_id, user_id, sku, player_id, amount, status) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ref_id, str(user_id), sku, player_id, amount, status)
        )
        await self._conn.commit()
        
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
        """
        Update transaction status.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if provider_ref:
            updates.append("provider_ref = ?")
            params.append(provider_ref)
            
        params.append(ref_id)
        
        await self._conn.execute(
            f"UPDATE transactions SET {', '.join(updates)} WHERE ref_id = ?",
            params
        )
        await self._conn.commit()


# Singleton instance
db = DatabaseManager()
