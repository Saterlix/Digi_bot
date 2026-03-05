import json
import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# Конфигурация
DB_PATH = "shop_base.db"
# Замените на реальный URL вашего Web App (например, после деплоя на Vercel/GitHub Pages или через ngrok/localtunnel)
WEB_APP_URL = "https://your.webapp.url/here"

# 1. Работа с базой данных (aiosqlite)
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица users
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                name TEXT,
                balance INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица pending_payments
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                base_amount INTEGER,
                locked_amount INTEGER,
                expires_at INTEGER
            )
        ''')
        
        # Таблица settings
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_shop_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Инициализация дефолтных настроек (если таблица пустая)
        await db.execute('''
            INSERT INTO settings (id, is_shop_active)
            SELECT 1, 1 WHERE NOT EXISTS (SELECT 1 FROM settings WHERE id = 1)
        ''')
        
        await db.commit()

async def add_user(tg_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, name) VALUES (?, ?)",
            (tg_id, name)
        )
        await db.commit()

async def get_user_balance(tg_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# 2. Обработчики Aiogram 3.x
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Регистрируем юзера в БД при старте
    await add_user(message.from_user.id, message.from_user.first_name)
    
    # Создаем кнопку для Web App
    web_app_btn = KeyboardButton(
        text="Откройте магазин",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[web_app_btn]],
        resize_keyboard=True
    )
    
    await message.answer(
        "👋 Добро пожаловать! Нажмите кнопку ниже, чтобы открыть магазин:",
        reply_markup=keyboard
    )

@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    """
    Обработчик данных, которые приходят из Web App через tg.sendData()
    """
    try:
        # Парсим JSON данные от клиента
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка обработки данных.")
        return

    if data.get("action") == "buy":
        product_id = data.get("product_id")
        player_id = data.get("player_id")
        
        # Проверяем баланс пользователя в БД
        balance = await get_user_balance(message.from_user.id)
        
        # В этой базовой версии считаем, что если баланс 0 - средств не хватает.
        # В будущем здесь будет проверка стоимости товара: if balance < TARGET_PRICE
        if balance <= 0:
            await message.answer(
                f"Товар: {product_id} | Ваш ID: {player_id}\n\n"
                "❌ Недостаточно средств."
            )
        else:
            await message.answer("✅ В разработке: покупка принята.")

# Заглушка для запуска, если решите запустить этот файл напрямую (не забудьте токен)
"""
async def main():
    await init_db()
    bot = Bot(token="YOUR_BOT_TOKEN")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
"""
