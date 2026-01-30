"""
Antigravity Telegram Bot
Handles user interaction and Mini App entry point.
"""

import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import config
from services.database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# URL where the frontend is hosted (Must be HTTPS)
# User must deploy frontend to GitHub Pages or use ngrok.
WEBAPP_URL = getenv("WEBAPP_URL", "https://Saterlix.github.io/Digi_bot")

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    user = message.from_user
    await db.create_user(str(user.id), user.username)
    
    # Add timestamp to force cache refresh
    import time
    webapp_url_with_cache = f"{WEBAPP_URL}?v={int(time.time())}"
    
    # Create Menu Button
    builder = ReplyKeyboardBuilder()
    builder.button(text="🌌 Open Store (Updated)", web_app=WebAppInfo(url=webapp_url_with_cache))
    builder.add(KeyboardButton(text="ℹ️ Help"))
    builder.add(KeyboardButton(text="🔄 Reload"))
    builder.adjust(1, 2)
    
    await message.answer(
        f"🌌 <b>Welcome back, {html.bold(user.full_name)}!</b>\n\n"
        "Antigravity Store is live with the new <b>BuyPin</b> design.\n"
        "Tap the button below to check out the new experience.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(lambda message: message.text == "ℹ️ Help")
async def command_help_btn(message: Message) -> None:
    await message.answer(
        "🛠 **Bot Help**\n\n"
        "1. Tap **Open Store** to buy items.\n"
        "2. Use `/balance` to check your funds.\n"
        "3. If the update is not visible, try **Reload** or clear your cache."
    )

@dp.message(lambda message: message.text == "🔄 Reload")
async def command_reload_btn(message: Message) -> None:
    await message.answer("♻️ Reloading menu...", reply_markup=None)
    await command_start_handler(message)

@dp.message(Command("balance"))
async def command_balance(message: Message) -> None:
    user_id = str(message.from_user.id)
    user = await db.get_user(user_id)
    
    if user:
        await message.answer(f"💰 Your balance: {user['balance']} UZS")
    else:
        await message.answer("User not found.")

@dp.message(Command("test_deposit"))
async def command_test_deposit(message: Message, command: CommandObject) -> None:
    """
    Usage: /test_deposit 5000
    """
    if command.args is None:
        await message.answer("Usage: /test_deposit <amount>")
        return
        
    try:
        amount = int(command.args)
        user_id = str(message.from_user.id)
        
        # Security Note: In production, restrict this to admins!
        
        new_balance = await db.update_balance(user_id, amount)
        await message.answer(f"✅ Added {amount} UZS.\nNew Balance: {new_balance} UZS")
        
    except ValueError:
        await message.answer("Error: Invalid amount.")

async def main() -> None:
    # Initialize DB connection for the bot process
    await db.connect()
    
    logger.info("Starting Bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped!")
