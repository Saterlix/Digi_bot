from aiogram import Router, types, F
import database as db
from keyboards.builder import get_profile_keyboard

router = Router()

@router.message(F.text == "👤 Профиль")
async def show_profile(message: types.Message):
    """Fetches user data and displays the profile info."""
    user_data = await db.get_user(message.from_user.id)
    
    if not user_data:
        await message.answer("❌ Профиль не найден. Нажмите /start для регистрации.")
        return
        
    profile_text = (
        "👤 <b>Ваш профиль:</b>\n\n"
        f"<b>ID:</b> <code>{user_data['tg_id']}</code>\n"
        f"<b>Баланс:</b> {user_data['balance']:,} UZS"
    )
    
    await message.answer(
        profile_text,
        reply_markup=get_profile_keyboard(),
        parse_mode="HTML"
    )
