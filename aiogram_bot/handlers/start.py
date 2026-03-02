from aiogram import Router, types, F
from aiogram.filters import CommandStart
import database as db
from keyboards.builder import get_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handles the /start command, registers the user and sends the main menu."""
    user = message.from_user
    username = user.username or user.first_name
    
    # Save user to database
    await db.add_user(user.id, username)
    
    welcome_text = (
        "👋 <b>Добро пожаловать в магазин доната!</b>\n\n"
        "Выберите действие ниже, чтобы начать покупки или управлять профилем:"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "💬 Поддержка")
async def support_handler(message: types.Message):
    """Stub for the support button."""
    await message.answer("💬 Если у вас возникли проблемы, напишите нашему администратору: @admin")
