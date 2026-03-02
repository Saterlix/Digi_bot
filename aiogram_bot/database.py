import aiosqlite
import datetime

DB_NAME = "database.sqlite"

async def init_db():
    """Initialize the database and create tables if they do not exist."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                balance INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                base_amount INTEGER NOT NULL,
                locked_amount INTEGER UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        await db.commit()

async def add_user(tg_id: int, username: str):
    """Add a new user to the database if they don't already exist."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (tg_id, username)
            VALUES (?, ?)
        ''', (tg_id, username))
        await db.commit()

async def get_user(tg_id: int) -> dict:
    """Retrieve user data by Telegram ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_balance(tg_id: int, amount: int):
    """Update a user's balance (can be positive or negative)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE users SET balance = balance + ? WHERE tg_id = ?
        ''', (amount, tg_id))
        await db.commit()

async def lock_amount(user_id: int, base_amount: int, locked_amount: int, expires_in_minutes: int = 15):
    """Save a unique locked amount for a user with an expiration time."""
    expires_at = datetime.datetime.now() + datetime.timedelta(minutes=expires_in_minutes)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO pending_payments (user_id, base_amount, locked_amount, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, base_amount, locked_amount, expires_at))
        await db.commit()

async def get_pending_payment(locked_amount: int) -> dict:
    """Retrieve a pending payment by its unique locked amount."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM pending_payments WHERE locked_amount = ?', (locked_amount,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_pending_payment(locked_amount: int):
    """Delete a pending payment record after successful top-up or cancellation."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM pending_payments WHERE locked_amount = ?', (locked_amount,))
        await db.commit()

async def check_amount_exists(locked_amount: int) -> bool:
    """Check if a specific locked amount is already assigned to an active pending payment."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT 1 FROM pending_payments WHERE locked_amount = ? AND expires_at > CURRENT_TIMESTAMP', (locked_amount,)) as cursor:
            return await cursor.fetchone() is not None

async def cleanup_expired_payments():
    """Delete all pending payments where the expiration time has passed."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM pending_payments WHERE expires_at < ?', (datetime.datetime.now(),))
        await db.commit()
