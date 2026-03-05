import asyncio
import json
import logging
import time
import os
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from aiohttp import web
from services.digiflazz import check_supplier_balance, make_transaction

# Тексты (Локализация)
TEXTS = {
    "uz": {
        "start": "👋 Xush kelibsiz, {name}!\n💰 Balansingiz: {balance} UZS\n\nPastdagi tugmalar orqali xizmatlardan foydalaning.",
        "open_store": "🛒 Do'konni ochish",
        "support": "💬 Qo'llab-quvvatlash",
        "instruction": "📖 Qo'llanma",
        "lang_switch": "🇷🇺 Rus tiliga o'tish",
        "support_text": "👨‍💻 Qo'llab-quvvatlash xizmati bilan bog'lanish uchun, iltimos @ThunderPaySupport ga yozing.",
        "instruction_text": "❓ <b>Qanday qilib sotib olish mumkin?</b>\n1. Do'konni oching\n2. O'yinni tanlang\n3. ID raqamingizni kiriting\n4. To'lov qiling va tasdiqlang!\n\n<i>To'lovlar avtomatlashtirilgan.</i>",
        "lang_changed": "✅ Til o'zbek tiliga o'zgartirildi!",
        "deposit_info": "Balansni to'ldirish uchun do'kon ichidagi Hamyon bo'limidan foydalaning.",
        "not_enough": "❌ <b>Mablag' yetarli emas.</b> Iltimos, balansingizni to'ldiring.",
        "pending": "✅ <b>Qayta ishlashga yuborildi (Pending)</b>\n💳 Buyurtma: <code>{ref_id}</code>\nMahsulot: {product} | ID: {player}\n\n<i>Serverdan tasdiqlash kutilmoqda...</i>",
        "error_create": "❌ Buyurtma yaratishda xatolik: {msg}",
        "gateway_closed": "⚙️ Hozirgi vaqtda to'lov shlyuzi profilaktika sababli yopiq. Iltimos keyinroq urinib ko'ring.",
        "deposit_enter": "💰 UZS hisobida to'lov summasini kiriting (masalan, 50000):",
        "deposit_not_num": "❌ Summa raqam bo'lishi kerak. Qayta urinib ko'ring.",
        "deposit_min": "❌ Eng kam to'lov summasi: 1000 UZS.",
        "deposit_too_many": "❌ Ushbu summaga juda ko'p arizalar tushgan. Boshqacharoq summa kiriting (masalan, 50005).",
        "deposit_pay": "⚠️ Karta raqamiga ROPPA-ROSA <b>{amount} UZS</b> o'tkazing:\n💳 <code>{card}</code>\n\n⏳ Tolov uchun 15 daqiqa vaqtingiz bor.\n❗ <i>Boshqa summa o'tkazsangiz - tolov avtomatik qabul qilinmaydi!</i>"
    },
    "ru": {
        "start": "👋 Добро пожаловать, {name}!\n💰 Ваш баланс: {balance} UZS\n\nИспользуйте кнопки ниже для навигации.",
        "open_store": "🛒 Открыть магазин",
        "support": "💬 Поддержка",
        "instruction": "📖 Инструкция",
        "lang_switch": "🇺🇿 O'zbek tiliga o'tish",
        "support_text": "👨‍💻 Для связи с поддержкой напишите @ThunderPaySupport.",
        "instruction_text": "❓ <b>Как купить?</b>\n1. Откройте магазин\n2. Выберите игру\n3. Введите ваш игровой ID\n4. Оплатите и подтвердите!\n\n<i>Все платежи автоматизированы.</i>",
        "lang_changed": "✅ Язык изменен на русский!",
        "deposit_info": "Для пополнения баланса перейдите в раздел Кошелек внутри магазина.",
        "not_enough": "❌ <b>Недостаточно средств.</b> Пожалуйста, пополните баланс.",
        "pending": "✅ <b>Отправлено в обработку (Pending)</b>\n💳 Заказ: <code>{ref_id}</code>\nТовар: {product} | ID: {player}\n\n<i>Ожидаем подтверждения от сервера...</i>",
        "error_create": "❌ Ошибка создания заказа: {msg}",
        "gateway_closed": "⚙️ В данный момент шлюз пополнения закрыт на техническое обслуживание. Попробуйте позже.",
        "deposit_enter": "💰 Введите сумму пополнения в UZS (например, 50000):",
        "deposit_not_num": "❌ Сумма должна быть числом. Попробуйте еще раз.",
        "deposit_min": "❌ Минимальная сумма пополнения: 1000 UZS.",
        "deposit_too_many": "❌ Слишком много заявок на эту сумму. Попробуйте ввести немного другую (например, 50005).",
        "deposit_pay": "⚠️ Переведите РОВНО <b>{amount} UZS</b> на карту:\n💳 <code>{card}</code>\n\n⏳ У вас есть 15 минут на оплату.\n❗ <i>Если переведете другую сумму - платеж не зачислится автоматически!</i>"
    }
}

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
DB_PATH = "shop_base.db"
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID", "7165323599")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR and ADMIN_ID_STR.isdigit() else 7165323599

# Для локального теста используем localhost.run или ngrok, 
# Но пока возьмем из .env, если его нет - замокоем
WEB_APP_URL = os.getenv("WEBAPP_URL", "https://thunderpay-huhhuku-7744s-projects.vercel.app") 

CARD_NUMBER = "8600 0000 0000 0000"

# ==========================================
# 1. Работа с базой данных (aiosqlite)
# ==========================================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                name TEXT,
                balance INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'uz'
            )''')
        # В случае, если таблица была создана ранее, добавим столбец lang (игнорируем ошибку если он есть)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'uz'")
        except:
            pass
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                base_amount INTEGER,
                locked_amount INTEGER,
                expires_at INTEGER
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_shop_active BOOLEAN DEFAULT 1
            )''')
        await db.execute('''
            INSERT INTO settings (id, is_shop_active)
            SELECT 1, 1 WHERE NOT EXISTS (SELECT 1 FROM settings WHERE id = 1)
        ''')
        await db.commit()

async def add_user(tg_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (tg_id, name) VALUES (?, ?)", (tg_id, name))
        await db.commit()

async def get_user_balance_and_lang(tg_id: int) -> tuple:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance, lang FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return (row[0], row[1]) if row else (0, 'uz')

async def set_user_lang(tg_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang = ? WHERE tg_id = ?", (lang, tg_id))
        await db.commit()

async def add_balance(tg_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()

async def get_unique_locked_amount(base_amount: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        current_time = int(time.time())
        async with db.execute(
            "SELECT locked_amount FROM pending_payments WHERE base_amount = ? AND expires_at > ?",
            (base_amount, current_time)
        ) as cursor:
            rows = await cursor.fetchall()
            locked_amounts = {row[0] for row in rows}
            for i in range(101):
                candidate = base_amount + i
                if candidate not in locked_amounts:
                    return candidate
            return None

async def create_pending_payment(tg_id: int, base_amount: int, locked_amount: int, expires_at: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO pending_payments (tg_id, base_amount, locked_amount, expires_at) VALUES (?, ?, ?, ?)",
            (tg_id, base_amount, locked_amount, expires_at)
        )
        await db.commit()

async def fetch_and_delete_payment(locked_amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        current_time = int(time.time())
        async with db.execute(
            "SELECT tg_id, base_amount FROM pending_payments WHERE locked_amount = ? AND expires_at > ?",
            (locked_amount, current_time)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                await db.execute("DELETE FROM pending_payments WHERE locked_amount = ?", (locked_amount,))
                await db.commit()
                return {"tg_id": row[0], "base_amount": row[1]}
            return None

# ==========================================
# 2. Обработчики Aiogram 3.x
# ==========================================

dp = Dispatcher()

class DepositState(StatesGroup):
    waiting_for_amount = State()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.first_name)
    balance, lang = await get_user_balance_and_lang(message.from_user.id)
    
    text = TEXTS[lang]["start"].format(name=message.from_user.first_name, balance=balance)
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]["instruction"]), KeyboardButton(text=TEXTS[lang]["support"])],
        [KeyboardButton(text=TEXTS[lang]["lang_switch"])]
    ], resize_keyboard=True)
    
    await message.answer(text, reply_markup=kb)

@dp.message(F.text.in_([TEXTS["uz"]["instruction"], TEXTS["ru"]["instruction"]]))
async def handle_instruction(message: Message):
    _, lang = await get_user_balance_and_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["instruction_text"], parse_mode="HTML")

@dp.message(F.text.in_([TEXTS["uz"]["support"], TEXTS["ru"]["support"]]))
async def handle_support(message: Message):
    _, lang = await get_user_balance_and_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["support_text"], parse_mode="HTML")

@dp.message(F.text.in_([TEXTS["uz"]["lang_switch"], TEXTS["ru"]["lang_switch"]]))
async def handle_lang_switch(message: Message):
    balance, lang = await get_user_balance_and_lang(message.from_user.id)
    new_lang = "ru" if lang == "uz" else "uz"
    await set_user_lang(message.from_user.id, new_lang)
    
    text = TEXTS[new_lang]["start"].format(name=message.from_user.first_name, balance=balance)
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[new_lang]["instruction"]), KeyboardButton(text=TEXTS[new_lang]["support"])],
        [KeyboardButton(text=TEXTS[new_lang]["lang_switch"])]
    ], resize_keyboard=True)
    
    await message.answer(TEXTS[new_lang]["lang_changed"], reply_markup=kb)

@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        return

    if data.get("action") == "buy":
        product_id = data.get("product_id")
        player_id = data.get("player_id")
        
        balance, lang = await get_user_balance_and_lang(message.from_user.id)
        
        if balance <= 0:
            await message.answer(TEXTS[lang]["not_enough"], parse_mode="HTML")
        else:
            # Вызов API Digiflazz
            ref_id = f"order_{int(time.time())}_{message.from_user.id}"
            res = await make_transaction(product_id, player_id, ref_id)
            
            status = res.get("data", {}).get("status", "Failed")
            msg = res.get("data", {}).get("message", "Unknown error")
            
            if status == "Pending":
                text = TEXTS[lang]["pending"].format(ref_id=ref_id, product=product_id, player=player_id)
                await message.answer(text, parse_mode="HTML")
            else:
                text = TEXTS[lang]["error_create"].format(msg=msg)
                await message.answer(text)

@dp.message(Command("deposit"))
async def cmd_deposit(message: Message, state: FSMContext, bot: Bot):
    balance, lang = await get_user_balance_and_lang(message.from_user.id)
    # --- АВТОМАТИЧЕСКАЯ ЗАЩИТА ---
    supplier_balance = await check_supplier_balance()
    MIN_SUPPLIER_BALANCE = 50000
    if supplier_balance < MIN_SUPPLIER_BALANCE:
        await message.answer(TEXTS[lang]["gateway_closed"])
        try:
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ <b>Внимание! Автоматическая защита активирована!</b>\n"
                f"На балансе Digiflazz осталось: <code>{supplier_balance}</code> UZS.\n"
                f"Пополнения временно отключены для пользователей.",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить алерт админу: {e}")
        return
        
    await message.answer(TEXTS[lang]["deposit_enter"])
    await state.set_state(DepositState.waiting_for_amount)

@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    balance, lang = await get_user_balance_and_lang(message.from_user.id)
    
    if not message.text.isdigit():
        await message.answer(TEXTS[lang]["deposit_not_num"])
        return
        
    base_amount = int(message.text)
    if base_amount < 1000:
        await message.answer(TEXTS[lang]["deposit_min"])
        return
        
    unique_amount = await get_unique_locked_amount(base_amount)
    if unique_amount is None:
        await message.answer(TEXTS[lang]["deposit_too_many"])
        await state.clear()
        return
        
    expires_at = int(time.time()) + (15 * 60)
    await create_pending_payment(message.from_user.id, base_amount, unique_amount, expires_at)
    
    text = TEXTS[lang]["deposit_pay"].format(amount=unique_amount, card=CARD_NUMBER)
    await message.answer(text, parse_mode="HTML")
    await state.clear()

@dp.message(Command("approve_pay"))
async def cmd_approve_pay(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
        
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("❌ Формат: /approve_pay <сумма>\nПример: /approve_pay 50001")
        return
        
    locked_amount = int(args[1])
    payment_data = await fetch_and_delete_payment(locked_amount)
    if not payment_data:
        await message.answer(f"❌ Платеж на сумму {locked_amount} не найден или просрочен.")
        return
        
    tg_id = payment_data["tg_id"]
    base_amount = payment_data["base_amount"]
    await add_balance(tg_id, base_amount)
    await message.answer(f"✅ Успешно! Пользователю {tg_id} начислено {base_amount} UZS.")
    
    try:
        await bot.send_message(tg_id, f"✅ Ваш платеж подтвержден! Баланс пополнен на {base_amount} UZS.")
    except Exception as e:
        await message.answer(f"⚠️ Баланс начислен, но юзер заблокировал бота: {e}")

# ==========================================
# 4. Фоновая очистка (Background Task)
# ==========================================

async def cleanup_pending_payments():
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                current_time = int(time.time())
                cursor = await db.execute("DELETE FROM pending_payments WHERE expires_at <= ?", (current_time,))
                deleted_count = cursor.rowcount
                await db.commit()
                if deleted_count > 0:
                    logging.info(f"[🧹ОЧИСТКА] Удалено {deleted_count} просроченных платежных заявок.")
        except Exception as e:
            logging.error(f"[❌ОШИБКА ОЧИСТКИ] {e}")
        await asyncio.sleep(60)

# ==========================================
# 5. Webhook сервер для Digiflazz
# ==========================================

async def digiflazz_webhook(request: web.Request):
    data = await request.json()
    status = data.get("status")
    ref_id = data.get("ref_id")
    buyer_sku_code = data.get("buyer_sku_code")
    customer_no = data.get("customer_no")
    
    try:
        # Извлекаем tg_id из ref_id, который мы сгенерировали
        tg_id = int(ref_id.split("_")[2])
        bot: Bot = request.app['bot']
        
        if status == "Success":
            text = (f"🎉 <b>Успешно!</b>\n"
                    f"Ваш заказ <code>{ref_id}</code> ({buyer_sku_code}) успешно доставлен на аккаунт <code>{customer_no}</code>!")
            # Для теста: спишем какую-то сумму. На бою мы бы сначала искали цену в каталоге
            await add_balance(tg_id, -14000)
        else:
            text = (f"❌ <b>Ошибка!</b>\n"
                    f"Ваш заказ <code>{ref_id}</code> отменен. Введен неверный ID или техническая ошибка.")
            
        await bot.send_message(tg_id, text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        
    return web.json_response({"status": "ok"})

async def run_webhook_server(bot: Bot):
    app = web.Application()
    app['bot'] = bot
    app.router.add_post('/digiflazz/webhook', digiflazz_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    logging.info("Webhook server started on http://localhost:8080")

# ==========================================
# Запуск бота
# ==========================================

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Фоновую задачу очистки просроченных оплат
    asyncio.create_task(cleanup_pending_payments())
    
    # Запускаем локальный веб-сервер для Webhooks (Digiflazz)
    await run_webhook_server(bot)
    
    print("Бот успешно запущен! Напишите ему /start")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
