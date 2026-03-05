import os
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """Builds the main menu with a WebApp button."""
    webapp_url = os.getenv("WEBAPP_URL", "https://thunderpay-huhhuku-7744s-projects.vercel.app")
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Магазин", web_app=WebAppInfo(url=webapp_url))],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Builds the profile inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="top_up")]
        ]
    )

def get_payment_methods_keyboard(amount: int) -> InlineKeyboardMarkup:
    """Builds the mock payment method selection keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="[Click]", callback_data=f"pay_click_{amount}"),
                InlineKeyboardButton(text="[Payme]", callback_data=f"pay_payme_{amount}")
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ]
    )
