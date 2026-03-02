from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from states.payment import PaymentState
from keyboards.builder import get_payment_methods_keyboard
import database as db

router = Router()

@router.callback_query(F.data == "top_up")
async def start_top_up(callback: types.CallbackQuery, state: FSMContext):
    """Triggered when the user clicks 'Пополнить баланс'."""
    await callback.message.answer("💸 Введите сумму пополнения в UZS (только цифры):")
    await state.set_state(PaymentState.waiting_for_amount)
    await callback.answer()

@router.message(PaymentState.waiting_for_amount)
async def process_top_up_amount(message: types.Message, state: FSMContext):
    """Receives the amount from the user."""
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите корректную сумму (только цифры).")
        return
        
    amount = int(message.text)
    
    if amount < 1000:
        await message.answer("❌ Минимальная сумма пополнения: 1,000 UZS.")
        return

    # Clear state as we successfully got the amount
    await state.clear()
    
    # Logic: find a unique locked_amount starting from the requested amount
    locked_amount = amount
    max_search = amount + 100
    found_unique = False
    
    while locked_amount <= max_search:
        if not await db.check_amount_exists(locked_amount):
            found_unique = True
            break
        locked_amount += 1
        
    if not found_unique:
        await message.answer("❌ В данный момент слишком много платежей с такой суммой. Попробуйте еще раз немного позже или введите другую сумму.")
        return
        
    # Save the locked amount to pending payments with a 15 min expiry
    await db.lock_amount(message.from_user.id, amount, locked_amount, expires_in_minutes=15)

    await message.answer(
        f"⚠️ Для пополнения переведите РОВНО <b>{locked_amount} UZS</b> на карту <code>8600 0000 0000 0000</code>.\n\n"
        f"Важно: отправьте копейка в копейку, иначе система не распознает платеж! У вас есть 15 минут.",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery):
    """Cancels the payment process."""
    await callback.message.edit_text("❌ Пополнение отменено.")
    await callback.answer()

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery):
    """Cancels the payment process."""
    await callback.message.edit_text("❌ Пополнение отменено.")
    await callback.answer()

import json

@router.message(F.web_app_data)
async def web_app_data_handler(message: types.Message, state: FSMContext):
    """Handles data sent from the Telegram Mini App via tg.sendData()"""
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        user_id = message.from_user.id
        
        if action == "topup":
            # Start the same top-up flow
            await message.answer("💸 Введите сумму пополнения в UZS (только цифры):")
            await state.set_state(PaymentState.waiting_for_amount)
            
        elif action == "buy":
            product_id = data.get("product_id")
            player_id = data.get("player_id")
            
            # Here you would typically fetch real price from DB/Catalog. We'll simulate it based on product_id
            # Mock catalog prices:
            prices = {
                "mlbb_86": 16000,
                "mlbb_172": 32000,
                "pubg_60": 15000,
                "pubg_325": 65000
            }
            
            price = prices.get(product_id, 0)
            
            if price == 0:
                await message.answer("❌ Ошибка: товар не найден.")
                return
                
            user = await db.get_user(user_id)
            if not user:
                await message.answer("❌ Профиль не найден. Нажмите /start для регистрации.")
                return
                
            balance = user["balance"]
            
            if balance < price:
                await message.answer("❌ Недостаточно средств. Пожалуйста, пополните баланс.")
                return
                
            # Deduct balance
            await db.update_balance(user_id, -price)
            
            # Send success message
            await message.answer(f"✅ Заказ принят! Сумма {price:,} UZS была списана с баланса.\nОжидайте пополнения на ID: <code>{player_id}</code>.", parse_mode="HTML")
            
        else:
            await message.answer("⚠️ Получена неизвестная команда от веб-приложения.")
            
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка при обработке данных из веб-приложения.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {e}")
