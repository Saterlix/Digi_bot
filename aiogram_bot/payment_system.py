import asyncio
import time
import os
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
DB_PATH = "shop_base.db"
# Получаем ADMIN_ID из .env и преобразуем в int (если указан)
ADMIN_ID_STR = os.getenv("ADMIN_ID", "7165323599")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR and ADMIN_ID_STR.isdigit() else 7165323599
CARD_NUMBER = "8600 0000 0000 0000"

# ==========================================
# 1. Работа с базой данных (доп. функции)
# ==========================================

async def get_unique_locked_amount(base_amount: int) -> int | None:
    """Генерирует уникальную сумму (base_amount + randint до 100), которой нет в активных ожиданиях"""
    async with aiosqlite.connect(DB_PATH) as db:
        current_time = int(time.time())
        # Получаем все занятые суммы для этой базы
        async with db.execute(
            "SELECT locked_amount FROM pending_payments WHERE base_amount = ? AND expires_at > ?",
            (base_amount, current_time)
        ) as cursor:
            rows = await cursor.fetchall()
            locked_amounts = {row[0] for row in rows}
            
            # Ищем свободную сумму (+0 до +100 сум)
            for i in range(101):
                candidate = base_amount + i
                if candidate not in locked_amounts:
                    return candidate
            return None # Если все 100 вариантов заняты (редко)

async def create_pending_payment(tg_id: int, base_amount: int, locked_amount: int, expires_at: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO pending_payments (tg_id, base_amount, locked_amount, expires_at) VALUES (?, ?, ?, ?)",
            (tg_id, base_amount, locked_amount, expires_at)
        )
        await db.commit()

async def fetch_and_delete_payment(locked_amount: int):
    """Ищет активный платеж по точной сумме, возвращает его данные и удаляет запись"""
    async with aiosqlite.connect(DB_PATH) as db:
        current_time = int(time.time())
        # Находим платеж
        async with db.execute(
            "SELECT tg_id, base_amount FROM pending_payments WHERE locked_amount = ? AND expires_at > ?",
            (locked_amount, current_time)
        ) as cursor:
            row = await cursor.fetchone()
            
            if row:
                # Удаляем запись, так как она оплачена
                await db.execute("DELETE FROM pending_payments WHERE locked_amount = ?", (locked_amount,))
                await db.commit()
                return {"tg_id": row[0], "base_amount": row[1]}
            return None

async def add_balance(tg_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()

# ==========================================
# 2. FSM для пополнения баланса
# ==========================================

class DepositState(StatesGroup):
    waiting_for_amount = State()

dp = Dispatcher()
# bot = Bot(token=os.getenv("BOT_TOKEN")) # Нужно инициализировать при запуске

from services.digiflazz import check_supplier_balance

# Допустим, бот передан в State, или мы можем импортировать бота, либо использовать message.bot
@dp.message(Command("deposit"))
async def cmd_deposit(message: Message, state: FSMContext, bot: Bot):
    # --- АВТОМАТИЧЕСКАЯ ЗАЩИТА (AUTO-KILL SWITCH) ---
    supplier_balance = await check_supplier_balance()
    MIN_SUPPLIER_BALANCE = 50000
    
    if supplier_balance < MIN_SUPPLIER_BALANCE:
        await message.answer("⚙️ В данный момент шлюз пополнения закрыт на техническое обслуживание. Попробуйте позже.")
        
        # Отправляем алерт админу
        try:
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ <b>Внимание! Автоматическая защита активирована!</b>\n"
                f"На балансе Digiflazz осталось мало средств: <code>{supplier_balance}</code> UZS.\n"
                f"Пополнения временно отключены для пользователей.",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить алерт админу: {e}")
            
        return # Прерываем операцию
    # ------------------------------------------------
    
    await message.answer("💰 Введите сумму пополнения в UZS (например, 50000):")
    await state.set_state(DepositState.waiting_for_amount)

@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Сумма должна быть числом. Попробуйте еще раз.")
        return
        
    base_amount = int(message.text)
    
    if base_amount < 1000:
        await message.answer("❌ Минимальная сумма пополнения: 1000 UZS.")
        return
        
    unique_amount = await get_unique_locked_amount(base_amount)
    
    if unique_amount is None:
        await message.answer("❌ Слишком много заявок на эту сумму сейчас. Попробуйте ввести немного другую сумму (например, 50005).")
        await state.clear()
        return
        
    # Замораживаем на 15 минут
    expires_at = int(time.time()) + (15 * 60)
    await create_pending_payment(message.from_user.id, base_amount, unique_amount, expires_at)
    
    await message.answer(
        f"⚠️ Переведите РОВНО <b>{unique_amount} UZS</b> на карту:\n"
        f"💳 <code>{CARD_NUMBER}</code>\n\n"
        f"⏳ У вас есть 15 минут на оплату.\n"
        f"❗ <i>Если переведете другую сумму - платеж не зачислится автоматически!</i>",
        parse_mode="HTML"
    )
    await state.clear()


# ==========================================
# 3. Панель Администратора (/approve_pay)
# ==========================================

@dp.message(Command("approve_pay"))
async def cmd_approve_pay(message: Message, bot: Bot):
    # Проверка на админа
    if message.from_user.id != ADMIN_ID:
        # Игнорируем или отвечаем "нет прав"
        return
        
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("❌ Формат: /approve_pay <сумма>")
        return
        
    locked_amount = int(args[1])
    
    # Ищем платеж в базе
    payment_data = await fetch_and_delete_payment(locked_amount)
    
    if not payment_data:
        await message.answer(f"❌ Платеж на сумму {locked_amount} не найден или просрочен.")
        return
        
    tg_id = payment_data["tg_id"]
    base_amount = payment_data["base_amount"]
    
    # Начисляем баланс
    await add_balance(tg_id, base_amount)
    
    await message.answer(f"✅ Успешно! Пользователю {tg_id} начислено {base_amount} UZS.")
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            tg_id, 
            f"✅ Ваш баланс успешно пополнен на {base_amount} UZS!"
        )
    except Exception as e:
        await message.answer(f"⚠️ Баланс начислен, но не удалось уведомить пользователя: {e}")


# ==========================================
# 4. Фоновая задача: Очистка просроченных
# ==========================================

async def cleanup_pending_payments():
    """Фоновая задача для удаления просроченных платежей"""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                current_time = int(time.time())
                # Удаляем все записи старше текущего времени
                cursor = await db.execute("DELETE FROM pending_payments WHERE expires_at <= ?", (current_time,))
                deleted_count = cursor.rowcount
                await db.commit()
                if deleted_count > 0:
                    logging.info(f"Удалено {deleted_count} просроченных платежей.")
        except Exception as e:
            logging.error(f"Ошибка при очистке БД: {e}")
            
        # Спим 1 минуту (60 секунд)
        await asyncio.sleep(60)

# Заглушка для добавления в основной файл
'''
async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    
    # Запуск фоновой задачи
    asyncio.create_task(cleanup_pending_payments())
    
    await dp.start_polling(bot)
'''
