"""Telegram mini-app style demo bot for SKYBOOST."""

import random
import string

import telebot
from telebot import types


BOT_TOKEN = "8222737803:AAGR9g3GirR5F-zJBYUizU7uWD1Q-EUUtgM"
DEFAULT_BALANCE = 75_000

STATE_NONE = "none"
STATE_WAITING_PLAYER = "waiting_player"
STATE_WAITING_CONFIRM = "waiting_confirm"
STATE_WAITING_TOPUP = "waiting_topup"

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}
user_states = {}

DEMO_CARDS = [
    {"bank": "Sky Bank", "number": "8600 1111 2222 3333", "holder": "SKYBOOST"},
    {"bank": "Orbit Pay", "number": "9860 4444 5555 6666", "holder": "SKYBOOST"},
]

CATALOG = {
    "mlbb": {
        "name": "Mobile Legends",
        "tagline": "Mashhur | 5v5",
        "items": [
            {"name": "💎 86 Алмазов", "price": 8_000},
            {"name": "💎 172 Алмаза", "price": 16_000},
            {"name": "💎 257 Алмазов", "price": 24_000},
            {"name": "💎 344 Алмаза", "price": 32_000},
            {"name": "💎 514 Алмазов", "price": 48_000},
            {"name": "💎 706 Алмазов", "price": 65_500},
            {"name": "💎 878 Алмазов", "price": 81_000},
            {"name": "💎 1000 Алмазов", "price": 92_000},
            {"name": "🎫 Twilight Pass", "price": 28_000},
            {"name": "🌟 Starlight Member", "price": 45_000},
        ],
    },
    "pubg": {
        "name": "PUBG Mobile",
        "tagline": "Global | UC",
        "items": [
            {"name": "💰 60 UC", "price": 11_000},
            {"name": "💰 120 UC", "price": 21_000},
            {"name": "💰 180 UC", "price": 30_000},
            {"name": "💰 325 UC", "price": 55_000},
            {"name": "💰 500 UC", "price": 83_000},
            {"name": "💰 660 UC", "price": 110_000},
            {"name": "💰 720 UC", "price": 118_000},
            {"name": "💰 810 UC", "price": 132_000},
            {"name": "💰 1020 UC", "price": 164_000},
            {"name": "💰 1800 UC", "price": 285_000},
        ],
    },
    "freefire": {
        "name": "Free Fire",
        "tagline": "Mashhour | Diamonds",
        "items": [
            {"name": "💎 100 Diamonds", "price": 12_000},
            {"name": "💎 210 Diamonds", "price": 23_000},
            {"name": "💎 310 Diamonds", "price": 35_000},
            {"name": "💎 520 Diamonds", "price": 56_000},
            {"name": "💎 620 Diamonds", "price": 66_000},
            {"name": "💎 1080 Diamonds", "price": 112_000},
            {"name": "💎 1440 Diamonds", "price": 148_000},
            {"name": "💎 2000 Diamonds", "price": 200_000},
            {"name": "🎫 Weekly Membership", "price": 26_000},
            {"name": "🪙 Monthly Membership", "price": 75_000},
        ],
    },
    "steam": {
        "name": "Steam Wallet",
        "tagline": "PC | Gift Code",
        "items": [
            {"name": "💳 5$ Gift Card", "price": 57_000},
            {"name": "💳 10$ Gift Card", "price": 110_000},
            {"name": "💳 20$ Gift Card", "price": 215_000},
            {"name": "💳 50$ Gift Card", "price": 520_000},
            {"name": "💳 100$ Gift Card", "price": 1_020_000},
        ],
    },
}


TEXTS = {
    "ru": {
        "language_prompt": "👋 Привет! Выберите язык:",
        "language_selected": "Русский язык активирован. Добро пожаловать в демо-магазин!",
        "main_menu_intro": "🏠 Главное меню. Что делаем?",
        "btn_catalog": "💎 Каталог",
        "btn_wallet": "👛 Кошелёк",
        "btn_history": "📜 История",
        "btn_help": "🆘 Помощь",
        "btn_cancel": "⬅️ Назад",
        "select_game": "🎮 Выберите игру:",
        "select_item": "🛍 Выберите товар:",
        "enter_player_id": "✍️ Введите ID игрового аккаунта (или отправьте имя):",
        "invoice_header": "🧾 Счёт (демо режим)",
        "invoice_footer": "Сделайте вид, что оплатили, и нажмите кнопку ниже. Реальных платежей нет!",
        "cards_title": "Тестовые карты:",
        "confirm_button": "✅ Подтвердить (демо)",
        "cancel_purchase": "❌ Отмена",
        "payment_hint": "💡 Используйте демо-карты только для тренировок.",
        "purchase_success": "✅ Заказ оформлен! Код {code}. Остаток: {balance} сум.",
        "purchase_cancelled": "⛔ Покупка отменена.",
        "no_balance": "⚠️ Недостаточно средств. Пополните баланс через 'Кошелёк'.",
        "wallet_header": "👛 Ваш демо-баланс: {balance} сум",
        "wallet_cards_title": "Реквизиты для тренировки:",
        "wallet_topup_button": "➕ Пополнить баланс",
        "topup_prompt": "Введите сумму пополнения (только цифры):",
        "topup_success": "Баланс пополнен на {amount} сум. Теперь: {balance} сум.",
        "topup_cancelled": "Пополнение отменено.",
        "invalid_amount": "Введите корректную сумму числом.",
        "history_empty": "История заказов пустая. Самое время сделать первую покупку!",
        "history_title": "📜 Ваши демо-заказы:",
        "history_line": "{code} · {item} ({player}) — {price} сум",
        "help_text": "Этот бот — демо-витрина SKYBOOST. Выбирайте игру в каталоге, пополняйте демо-баланс и оформляйте заказы без реальных платежей.",
        "cancelled": "Действие отменено.",
        "history_hint": "Статус можно посмотреть в разделе 'История'.",
        "lang_button_ru": "🇷🇺 Русский",
        "lang_button_uz": "🇺🇿 O'zbekcha",
        "language_switched": "Язык переключён на русский.",
    },
    "uz": {
        "language_prompt": "👋 Salom! Tilni tanlang:",
        "language_selected": "O'zbek tili yoqildi. Demo-do'konimizga xush kelibsiz!",
        "main_menu_intro": "🏠 Asosiy menyu. Qaysi bo'limga o'tamiz?",
        "btn_catalog": "💎 Katalog",
        "btn_wallet": "👛 Hamyon",
        "btn_history": "📜 Tarix",
        "btn_help": "🆘 Yordam",
        "btn_cancel": "⬅️ Orqaga",
        "select_game": "🎮 O'yinni tanlang:",
        "select_item": "🛍 Mahsulotni tanlang:",
        "enter_player_id": "✍️ O'yinchi ID sini yuboring (yoki nickname):",
        "invoice_header": "🧾 Hisob (demo rejim)",
        "invoice_footer": "To'lovni tasavvur qiling va pastdagi tugmani bosing. Haqiqiy to'lov yo'q!",
        "cards_title": "Test kartalar:",
        "confirm_button": "✅ Tasdiqlash (demo)",
        "cancel_purchase": "❌ Bekor qilish",
        "payment_hint": "💡 Bu kartalar faqat mashq uchun.",
        "purchase_success": "✅ Buyurtma qabul qilindi! Kod {code}. Qolgan balans: {balance} so'm.",
        "purchase_cancelled": "⛔ Buyurtma bekor qilindi.",
        "no_balance": "⚠️ Mablag' yetarli emas. 'Hamyon' bo'limidan to'ldiring.",
        "wallet_header": "👛 Demo balansingiz: {balance} so'm",
        "wallet_cards_title": "Mashq uchun rekvizitlar:",
        "wallet_topup_button": "➕ Balansni to'ldirish",
        "topup_prompt": "To'ldirish summasini kiriting (faqat raqamlar):",
        "topup_success": "Balans {amount} so'mga oshdi. Endi: {balance} so'm.",
        "topup_cancelled": "To'ldirish bekor qilindi.",
        "invalid_amount": "Faqat son kiriting, iltimos.",
        "history_empty": "Tarix bo'sh. Demo buyurtma qilish vaqti keldi!",
        "history_title": "📜 Demo-buyurtmalar ro'yxati:",
        "history_line": "{code} · {item} ({player}) — {price} so'm",
        "help_text": "Bu bot SKYBOOST vitrinasining demo versiyasi. Katalogdan o'yin tanlang, demo balansni to'ldirib, xavfsiz buyurtma qiling.",
        "cancelled": "Amal bekor qilindi.",
        "history_hint": "Holatni 'Tarix' bo'limida ko'rishingiz mumkin.",
        "lang_button_ru": "🇷🇺 Rus tili",
        "lang_button_uz": "🇺🇿 O'zbek tili",
        "language_switched": "Til o'zbekchaga o'zgartirildi.",
    },
}


def format_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def get_profile(user_id: int) -> dict:
    profile = user_data.setdefault(
        user_id,
        {
            "lang": "ru",
            "balance": DEFAULT_BALANCE,
            "orders": [],
            "order_counter": 1,
        },
    )
    profile.setdefault("orders", [])
    profile.setdefault("balance", DEFAULT_BALANCE)
    profile.setdefault("order_counter", 1)
    return profile


def get_lang(user_id: int) -> str:
    return get_profile(user_id).get("lang", "ru")


def text(user_id: int, key: str, **kwargs) -> str:
    lang = get_lang(user_id)
    template = TEXTS[lang][key]
    formatted_kwargs = {
        k: format_price(v) if isinstance(v, int) else v for k, v in kwargs.items()
    }
    return template.format(**formatted_kwargs)


def generate_order_code(profile: dict) -> str:
    random_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=2))
    code = f"#{profile['order_counter']:03d}{random_part}"
    profile["order_counter"] += 1
    return code


def cancel_keyboard(user_id: int) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(text(user_id, "btn_cancel"))
    return markup


def remove_reply_keyboard() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()


def send_main_menu(user_id: int) -> None:
    user_states[user_id] = STATE_NONE
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        text(user_id, "btn_catalog"),
        text(user_id, "btn_wallet"),
    )
    markup.add(
        text(user_id, "btn_history"),
        text(user_id, "btn_help"),
    )
    bot.send_message(user_id, text(user_id, "main_menu_intro"), reply_markup=markup)


def send_catalog(user_id: int) -> None:
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, game in CATALOG.items():
        label = f"{game['name']} · {game['tagline']}"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"game_{key}"))
    bot.send_message(user_id, text(user_id, "select_game"), reply_markup=markup)


def send_items(user_id: int, game_key: str, call_message: types.Message) -> None:
    game = CATALOG[game_key]
    items = game["items"]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, item in enumerate(items):
        label = f"{item['name']} — {format_price(item['price'])}"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"item_{game_key}_{idx}"))
    markup.add(types.InlineKeyboardButton(text(user_id, "btn_cancel"), callback_data="back_catalog"))
    try:
        bot.edit_message_text(
            chat_id=call_message.chat.id,
            message_id=call_message.message_id,
            text=text(user_id, "select_item"),
            reply_markup=markup,
        )
    except Exception:
        bot.send_message(call_message.chat.id, text(user_id, "select_item"), reply_markup=markup)


@bot.message_handler(commands=["start"])
def start_command(message: types.Message) -> None:
    user_id = message.chat.id
    profile = get_profile(user_id)
    profile.setdefault("username", message.from_user.first_name or "guest")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(TEXTS["ru"]["lang_button_ru"], callback_data="lang_ru"),
        types.InlineKeyboardButton(TEXTS["uz"]["lang_button_uz"], callback_data="lang_uz"),
    )
    bot.send_message(user_id, TEXTS["ru"]["language_prompt"], reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in {"lang_ru", "lang_uz"})
def set_language(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    profile = get_profile(user_id)
    lang = call.data.split("_")[1]
    profile["lang"] = lang
    user_states[user_id] = STATE_NONE
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(user_id, TEXTS[lang]["language_selected"], reply_markup=remove_reply_keyboard())
    send_main_menu(user_id)


@bot.message_handler(func=lambda m: m.text in [TEXTS["ru"]["btn_cancel"], TEXTS["uz"]["btn_cancel"]])
def handle_cancel(message: types.Message) -> None:
    user_id = message.chat.id
    get_profile(user_id)  # ensure initialized
    user_states[user_id] = STATE_NONE
    bot.send_message(user_id, text(user_id, "cancelled"), reply_markup=remove_reply_keyboard())
    send_main_menu(user_id)


@bot.message_handler(func=lambda m: m.text in [TEXTS["ru"]["btn_catalog"], TEXTS["uz"]["btn_catalog"]])
def handle_catalog(message: types.Message) -> None:
    send_catalog(message.chat.id)


@bot.message_handler(func=lambda m: m.text in [TEXTS["ru"]["btn_wallet"], TEXTS["uz"]["btn_wallet"]])
def handle_wallet(message: types.Message) -> None:
    user_id = message.chat.id
    profile = get_profile(user_id)
    cards_lines = "\n".join(
        f"{idx}. {card['bank']} — {card['number']} ({card['holder']})" for idx, card in enumerate(DEMO_CARDS, start=1)
    )
    wallet_text = (
        text(user_id, "wallet_header", balance=profile["balance"]) +
        "\n\n" +
        text(user_id, "wallet_cards_title") +
        "\n" +
        cards_lines +
        "\n\n" +
        text(user_id, "payment_hint")
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text(user_id, "wallet_topup_button"), callback_data="wallet_topup"))
    bot.send_message(user_id, wallet_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "wallet_topup")
def start_topup(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    user_states[user_id] = STATE_WAITING_TOPUP
    bot.send_message(user_id, text(user_id, "topup_prompt"), reply_markup=cancel_keyboard(user_id))


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == STATE_WAITING_TOPUP)
def process_topup(message: types.Message) -> None:
    user_id = message.chat.id
    content = message.text.strip()
    if content == text(user_id, "btn_cancel"):
        handle_cancel(message)
        return
    if not content.isdigit():
        bot.send_message(user_id, text(user_id, "invalid_amount"))
        return
    amount = int(content)
    if amount <= 0:
        bot.send_message(user_id, text(user_id, "invalid_amount"))
        return
    profile = get_profile(user_id)
    profile["balance"] += amount
    user_states[user_id] = STATE_NONE
    bot.send_message(
        user_id,
        text(user_id, "topup_success", amount=amount, balance=profile["balance"]),
        reply_markup=remove_reply_keyboard(),
    )
    send_main_menu(user_id)


@bot.message_handler(func=lambda m: m.text in [TEXTS["ru"]["btn_history"], TEXTS["uz"]["btn_history"]])
def handle_history(message: types.Message) -> None:
    user_id = message.chat.id
    profile = get_profile(user_id)
    if not profile["orders"]:
        bot.send_message(user_id, text(user_id, "history_empty"))
        return
    history_lines = "\n".join(
        text(
            user_id,
            "history_line",
            code=order["code"],
            item=order["item"],
            player=order["player_id"],
            price=order["price"],
        )
        for order in profile["orders"]
    )
    bot.send_message(user_id, text(user_id, "history_title") + "\n" + history_lines)


@bot.message_handler(func=lambda m: m.text in [TEXTS["ru"]["btn_help"], TEXTS["uz"]["btn_help"]])
def handle_help(message: types.Message) -> None:
    bot.send_message(message.chat.id, text(message.chat.id, "help_text"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def handle_game_selection(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    game_key = call.data.split("_", 1)[1]
    bot.answer_callback_query(call.id)
    profile = get_profile(user_id)
    profile["temp_game"] = game_key
    send_items(user_id, game_key, call.message)


@bot.callback_query_handler(func=lambda call: call.data == "back_catalog")
def back_to_catalog(call: types.CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    send_catalog(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("item_"))
def handle_item_selection(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    _, game_key, index = call.data.split("_", 2)
    bot.answer_callback_query(call.id)
    profile = get_profile(user_id)
    item = CATALOG[game_key]["items"][int(index)]
    profile["temp_item"] = item
    profile["temp_game_key"] = game_key
    bot.send_message(user_id, text(user_id, "enter_player_id"), reply_markup=cancel_keyboard(user_id))
    user_states[user_id] = STATE_WAITING_PLAYER


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == STATE_WAITING_PLAYER)
def process_player_id(message: types.Message) -> None:
    user_id = message.chat.id
    content = message.text.strip()
    if content == text(user_id, "btn_cancel"):
        handle_cancel(message)
        return
    profile = get_profile(user_id)
    item = profile.get("temp_item")
    if not item:
        user_states[user_id] = STATE_NONE
        send_main_menu(user_id)
        return
    profile["temp_player_id"] = content
    cards_lines = "\n".join(
        f"{idx}. {card['bank']} — {card['number']} ({card['holder']})" for idx, card in enumerate(DEMO_CARDS, start=1)
    )
    invoice = (
        f"{text(user_id, 'invoice_header')}\n\n"
        f"🎮 {CATALOG[profile['temp_game_key']]['name']}\n"
        f"📦 {item['name']}\n"
        f"🆔 {content}\n"
        f"💰 {format_price(item['price'])} сум\n\n"
        f"{text(user_id, 'cards_title')}\n{cards_lines}\n\n"
        f"{text(user_id, 'invoice_footer')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text(user_id, "confirm_button"), callback_data="pay_confirm"))
    markup.add(types.InlineKeyboardButton(text(user_id, "cancel_purchase"), callback_data="pay_cancel"))
    bot.send_message(user_id, invoice, reply_markup=markup)
    user_states[user_id] = STATE_WAITING_CONFIRM


@bot.callback_query_handler(func=lambda call: call.data == "pay_confirm")
def confirm_payment(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    profile = get_profile(user_id)
    item = profile.get("temp_item")
    player_id = profile.get("temp_player_id", "-")
    bot.answer_callback_query(call.id)
    if user_states.get(user_id) != STATE_WAITING_CONFIRM or not item:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        return
    price = item["price"]
    if profile["balance"] < price:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
        bot.send_message(user_id, text(user_id, "no_balance"))
        user_states[user_id] = STATE_NONE
        send_main_menu(user_id)
        return
    profile["balance"] -= price
    code = generate_order_code(profile)
    order = {
        "code": code,
        "item": item["name"],
        "price": price,
        "player_id": player_id,
    }
    profile["orders"].insert(0, order)
    profile.pop("temp_item", None)
    profile.pop("temp_player_id", None)
    profile.pop("temp_game_key", None)
    try:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(user_id, text(user_id, "purchase_success", code=code, balance=profile["balance"]))
    bot.send_message(user_id, text(user_id, "history_hint"))
    user_states[user_id] = STATE_NONE
    send_main_menu(user_id)


@bot.callback_query_handler(func=lambda call: call.data == "pay_cancel")
def cancel_payment(call: types.CallbackQuery) -> None:
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    profile = get_profile(user_id)
    profile.pop("temp_item", None)
    profile.pop("temp_player_id", None)
    profile.pop("temp_game_key", None)
    try:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(user_id, text(user_id, "purchase_cancelled"))
    user_states[user_id] = STATE_NONE
    send_main_menu(user_id)


@bot.message_handler(func=lambda _: True)
def fallback_handler(message: types.Message) -> None:
    user_id = message.chat.id
    if user_states.get(user_id) == STATE_NONE:
        bot.send_message(user_id, text(user_id, "main_menu_intro"))
        send_main_menu(user_id)


if __name__ == "__main__":
    bot.infinity_polling()
