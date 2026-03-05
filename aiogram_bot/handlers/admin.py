from aiogram import Router, types
from aiogram.filters import Command, CommandObject
import os
import database as db
from dotenv import load_dotenv

load_dotenv()
router = Router()

ADMIN_ID = os.getenv("ADMIN_ID", "7165323599")

@router.message(Command("approve_pay"))
async def cmd_approve_pay(message: types.Message, command: CommandObject):
    """Admin command to approve a pending payment: /approve_pay <amount>"""
    # Check if the user is an admin
    if str(message.from_user.id) != str(ADMIN_ID):
        return
        
    if command.args is None or not command.args.isdigit():
        await message.answer("❌ Использование: /approve_pay <сумма>")
        return
        
    locked_amount = int(command.args)
    pending_payment = await db.get_pending_payment(locked_amount)
    
    if pending_payment:
        user_id = pending_payment["user_id"]
        base_amount = pending_payment["base_amount"]
        
        # Add base_amount to user's balance
        await db.update_balance(user_id, base_amount)
        
        # Delete pending payment
        await db.delete_pending_payment(locked_amount)
        
        # Notify user (bot.send_message might be needed if user is not the one executing the command)
        # Assuming the Bot instance is available or using the message bot object
        try:
            await message.bot.send_message(
                chat_id=user_id, 
                text=f"✅ Ваш баланс успешно пополнен на {base_amount} UZS!"
            )
        except Exception as e:
            await message.answer(f"⚠️ Платеж обработан, но не удалось уведомить пользователя.\nОшибка: {e}")

        # Reply to admin
        await message.answer(f"✅ Платеж найден. Баланс пользователя {user_id} пополнен.")
    else:
        await message.answer("❌ Ожидающий платеж с такой суммой не найден.")
