"""
ThunderPay — Minimal Telegram Bot
Только /start и /help + кнопка Web App.
Вся бизнес-логика — в Web App.
"""
import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://thunderpay-huhhuku-7744s-projects.vercel.app")

dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ Открыть ThunderPay", web_app=WebAppInfo(url=WEBAPP_URL))]
    ], resize_keyboard=True)
    
    await message.answer(
        f"⚡ <b>Добро пожаловать в ThunderPay!</b>\n\n"
        f"Привет, {message.from_user.first_name}! 🎮\n"
        f"Здесь можно купить игровую валюту для 10+ игр.\n\n"
        f"Нажми кнопку внизу чтобы открыть магазин 👇",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "⚡ <b>ThunderPay — Помощь</b>\n\n"
        "🎮 <b>Как купить?</b>\n"
        "1. Нажми «Открыть ThunderPay»\n"
        "2. Выбери игру → товар\n"
        "3. Введи свой Player ID\n"
        "4. Оплати и получи доставку!\n\n"
        "💳 <b>Как пополнить?</b>\n"
        "В приложении нажми «Пополнить» → введи сумму → переведи на карту.\n\n"
        "❓ По всем вопросам: @ThunderPaySupport",
        parse_mode="HTML"
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("⚡ ThunderPay Bot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
