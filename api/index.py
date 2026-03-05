"""
ThunderPay — Vercel Serverless API
Объединённый backend: App API + Mock Digiflazz API + Webhook
"""
import hashlib
import asyncio
import aiosqlite
import httpx
import json
import time
import os
import logging
import urllib.parse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# ─── Config ───
DB_PATH = "/tmp/thunderpay.db"
MOCK_DB = "/tmp/mock_digiflazz.db"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7165323599"))
DF_USERNAME = os.getenv("DIGIFLAZZ_USERNAME", "thunderpay")
DF_API_KEY = os.getenv("DIGIFLAZZ_API_KEY", "dev-key-thunderpay-2026")
MARKUP = int(os.getenv("MARKUP_PERCENT", "25"))
MIN_SUPPLIER = int(os.getenv("MIN_SUPPLIER_BALANCE", "50000"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000")
CARD_HOLDER = os.getenv("CARD_HOLDER", "ThunderPay Admin")
FREEZE_SECONDS = 5 * 60

logging.basicConfig(level=logging.INFO)

# ═══════════════════════════════════════
# MOCK DIGIFLAZZ SEED DATA
# ═══════════════════════════════════════
SEED_CATALOG = [
    ("mlbb_86","MLBB","86 Diamonds",14000,True),("mlbb_172","MLBB","172 Diamonds",27000,True),
    ("mlbb_257","MLBB","257 Diamonds",40000,True),("mlbb_344","MLBB","344 Diamonds",53000,True),
    ("mlbb_514","MLBB","514 Diamonds",79000,True),("mlbb_706","MLBB","706 Diamonds",108000,True),
    ("mlbb_wp","MLBB","Weekly Diamond Pass",18000,True),("mlbb_tp","MLBB","Twilight Pass",95000,True),
    ("pubg_60","PUBG","60 UC",13500,True),("pubg_325","PUBG","325 UC",65000,True),
    ("pubg_660","PUBG","660 UC",130000,True),("pubg_1800","PUBG","1800 UC",340000,True),
    ("pubg_rp","PUBG","Royale Pass",95000,True),
    ("ff_100","FREEFIRE","100 Diamonds",12000,True),("ff_210","FREEFIRE","210 Diamonds",24000,True),
    ("ff_530","FREEFIRE","530 Diamonds",56000,True),("ff_1060","FREEFIRE","1060 Diamonds",108000,True),
    ("ff_wm","FREEFIRE","Weekly Membership",18000,True),
    ("gi_60","GENSHIN","60 Genesis Crystals",15000,True),("gi_300","GENSHIN","300 Genesis Crystals",68000,True),
    ("gi_980","GENSHIN","980 Genesis Crystals",210000,True),("gi_1980","GENSHIN","1980 Genesis Crystals",415000,True),
    ("gi_welkin","GENSHIN","Welkin Moon (30 дней)",55000,True),("gi_bp","GENSHIN","Battle Pass Gnostic Hymn",100000,True),
    ("so2_150","STANDOFF2","150 Gold",15000,True),("so2_500","STANDOFF2","500 Gold",45000,True),
    ("so2_1500","STANDOFF2","1500 Gold",125000,True),("so2_5000","STANDOFF2","5000 Gold",380000,True),
    ("cr_80","CLASHROYALE","80 Gems",12000,True),("cr_500","CLASHROYALE","500 Gems",55000,True),
    ("cr_1200","CLASHROYALE","1200 Gems",115000,True),("cr_2500","CLASHROYALE","2500 Gems",225000,True),
    ("cr_pass","CLASHROYALE","Pass Royale",55000,True),
    ("hok_60","HOK","60 Tokens",13000,True),("hok_300","HOK","300 Tokens",58000,True),
    ("hok_600","HOK","600 Tokens",110000,True),("hok_1500","HOK","1500 Tokens",260000,True),
    ("codm_80","CODM","80 CP",12000,True),("codm_400","CODM","400 CP",52000,True),
    ("codm_800","CODM","800 CP",98000,True),("codm_2400","CODM","2400 CP",280000,True),
    ("codm_bp","CODM","Battle Pass",95000,True),
    ("bs_30","BRAWLSTARS","30 Gems",10000,True),("bs_80","BRAWLSTARS","80 Gems",22000,True),
    ("bs_170","BRAWLSTARS","170 Gems",45000,True),("bs_360","BRAWLSTARS","360 Gems",88000,True),
    ("bs_pass","BRAWLSTARS","Brawl Pass",85000,True),
    ("rbx_400","ROBLOX","400 Robux",52000,True),("rbx_800","ROBLOX","800 Robux",98000,True),
    ("rbx_1700","ROBLOX","1700 Robux",195000,True),("rbx_4500","ROBLOX","4500 Robux",490000,True),
    ("tg_50","TGSTARS","50 Stars",5500,True),("tg_100","TGSTARS","100 Stars",10500,True),
    ("tg_250","TGSTARS","250 Stars",25000,True),("tg_1000","TGSTARS","1000 Stars",95000,True),
    ("tg_prem1","TGSTARS","Telegram Premium 1 мес",35000,True),("tg_prem6","TGSTARS","Telegram Premium 6 мес",175000,True),
]

# ═══════════════════════════════════════
# DB INIT
# ═══════════════════════════════════════
async def init_app_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER UNIQUE,
                name TEXT, username TEXT, balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0, created_at INTEGER);
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER,
                ref_id TEXT UNIQUE, buyer_sku_code TEXT, product_name TEXT,
                customer_no TEXT, cost INTEGER, sell_price INTEGER,
                status TEXT DEFAULT 'pending', created_at INTEGER);
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER,
                base_amount INTEGER, locked_amount INTEGER,
                status TEXT DEFAULT 'waiting', created_at INTEGER, expires_at INTEGER);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """)
        defaults = {
            "card_number": CARD_NUMBER, "card_holder": CARD_HOLDER,
            "markup_percent": str(MARKUP), "min_supplier_balance": str(MIN_SUPPLIER),
            "shop_active": "1",
        }
        for k, v in defaults.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v))
        await db.commit()

async def init_mock_db():
    async with aiosqlite.connect(MOCK_DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS balance (id INTEGER PRIMARY KEY, deposit INTEGER)")
        await db.execute("INSERT OR IGNORE INTO balance (id, deposit) VALUES (1, 5000000)")
        await db.execute("""CREATE TABLE IF NOT EXISTS catalog (
            buyer_sku_code TEXT PRIMARY KEY, category TEXT, product_name TEXT,
            price INTEGER, buyer_product_status BOOLEAN)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS transactions (
            ref_id TEXT PRIMARY KEY, buyer_sku_code TEXT, customer_no TEXT,
            status TEXT, price INTEGER, created_at INTEGER)""")
        # Reseed catalog
        await db.execute("DELETE FROM catalog")
        await db.executemany("INSERT INTO catalog VALUES (?,?,?,?,?)", SEED_CATALOG)
        await db.commit()

_db_ready = False
async def ensure_db():
    global _db_ready
    if not _db_ready:
        await init_app_db()
        await init_mock_db()
        _db_ready = True

# ─── Settings helpers ───
async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else ""

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()

# ═══════════════════════════════════════
# MOCK DIGIFLAZZ (internal functions)
# ═══════════════════════════════════════
def mock_verify(username: str, sign: str, extra: str) -> bool:
    if username != DF_USERNAME:
        return False
    return sign == hashlib.md5(f"{username}{DF_API_KEY}{extra}".encode()).hexdigest()

async def mock_cek_saldo():
    async with aiosqlite.connect(MOCK_DB) as db:
        async with db.execute("SELECT deposit FROM balance WHERE id=1") as c:
            row = await c.fetchone()
    return row[0] if row else 0

async def mock_price_list():
    async with aiosqlite.connect(MOCK_DB) as db:
        async with db.execute("SELECT * FROM catalog") as c:
            rows = await c.fetchall()
    return [{"buyer_sku_code": r[0], "category": r[1], "product_name": r[2],
             "price": r[3], "buyer_product_status": bool(r[4])} for r in rows]

async def mock_transaction(sku: str, customer_no: str, ref_id: str):
    async with aiosqlite.connect(MOCK_DB) as db:
        async with db.execute("SELECT ref_id FROM transactions WHERE ref_id=?", (ref_id,)) as c:
            if await c.fetchone():
                return {"status": "Failed", "message": "Duplicate ref_id"}
        async with db.execute("SELECT price, buyer_product_status FROM catalog WHERE buyer_sku_code=?", (sku,)) as c:
            prod = await c.fetchone()
        if not prod or not prod[1]:
            return {"status": "Failed", "message": "Product not found"}
        price = prod[0]
        async with db.execute("SELECT deposit FROM balance WHERE id=1") as c:
            bal = (await c.fetchone())[0]
        if bal < price:
            return {"status": "Failed", "message": "Insufficient supplier balance"}
        await db.execute("UPDATE balance SET deposit=deposit-? WHERE id=1", (price,))
        await db.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?)",
                         (ref_id, sku, customer_no, "Pending", price, int(time.time())))
        await db.commit()

    # Schedule webhook (simulates delayed callback)
    asyncio.ensure_future(_mock_process(ref_id, sku, customer_no, price))
    return {"status": "Pending", "ref_id": ref_id, "buyer_sku_code": sku,
            "customer_no": customer_no, "price": price, "message": "Processing"}

async def _mock_process(ref_id, sku, customer_no, price):
    await asyncio.sleep(4)
    status = "Failed" if customer_no == "ERROR" else "Sukses"
    async with aiosqlite.connect(MOCK_DB) as db:
        await db.execute("UPDATE transactions SET status=? WHERE ref_id=?", (status, ref_id))
        if status == "Failed":
            await db.execute("UPDATE balance SET deposit=deposit+? WHERE id=1", (price,))
        await db.commit()
    # Internal webhook — call our own endpoint
    final = "success" if status == "Sukses" else "failed"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id, sell_price FROM orders WHERE ref_id=?", (ref_id,)) as c:
            order = await c.fetchone()
        if order:
            await db.execute("UPDATE orders SET status=? WHERE ref_id=?", (final, ref_id))
            if final == "failed":
                await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (order[1], order[0]))
            await db.commit()
            # Notify user via Telegram Bot API
            if BOT_TOKEN:
                tg_id = order[0]
                if final == "success":
                    text = f"🎉 <b>Успешно!</b>\nЗаказ <code>{ref_id}</code> доставлен!"
                else:
                    text = f"❌ <b>Ошибка!</b>\nЗаказ <code>{ref_id}</code> отменён. Средства возвращены."
                try:
                    async with httpx.AsyncClient() as cl:
                        await cl.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                      json={"chat_id": tg_id, "text": text, "parse_mode": "HTML"})
                except:
                    pass
    logging.info(f"[Mock] Transaction {ref_id} → {final}")

# ═══════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════
app = FastAPI(title="ThunderPay API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── Pydantic Models ───
class AuthReq(BaseModel):
    initData: str
class DepositReq(BaseModel):
    tg_id: int
    amount: int
class DepositCheckReq(BaseModel):
    tg_id: int
    payment_id: int
class BuyReq(BaseModel):
    tg_id: int
    buyer_sku_code: str
    customer_no: str
class SettingReq(BaseModel):
    key: str
    value: str
class ApproveReq(BaseModel):
    payment_id: int

# ─── Auth ───
@app.post("/api/auth")
async def auth(req: AuthReq):
    await ensure_db()
    try:
        params = dict(x.split("=", 1) for x in req.initData.split("&") if "=" in x)
        user_json = urllib.parse.unquote(params.get("user", "{}"))
        user = json.loads(user_json)
        tg_id = user.get("id", 0)
        name = user.get("first_name", "User")
        username = user.get("username", "")
    except:
        tg_id = 999999
        name = "Test User"
        username = "testuser"
    if not tg_id:
        raise HTTPException(400, "Invalid initData")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (tg_id, name, username, created_at) VALUES (?,?,?,?)",
                         (tg_id, name, username, int(time.time())))
        if tg_id == ADMIN_ID:
            await db.execute("UPDATE users SET is_admin=1 WHERE tg_id=?", (tg_id,))
        await db.commit()
        async with db.execute("SELECT balance, is_admin FROM users WHERE tg_id=?", (tg_id,)) as c:
            row = await c.fetchone()
    return {"ok": True, "tg_id": tg_id, "name": name,
            "balance": row[0] if row else 0, "is_admin": bool(row[1]) if row else False}

# ─── Catalog ───
@app.get("/api/catalog")
async def catalog():
    await ensure_db()
    items = await mock_price_list()
    markup = int(await get_setting("markup_percent") or MARKUP)
    for item in items:
        item["sell_price"] = int(item["price"] * (1 + markup / 100))
    return {"ok": True, "data": items}

# ─── Balance ───
@app.get("/api/user/{tg_id}/balance")
async def user_balance(tg_id: int):
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id=?", (tg_id,)) as c:
            row = await c.fetchone()
    return {"ok": True, "balance": row[0] if row else 0}

# ─── Deposit ───
@app.post("/api/deposit/create")
async def deposit_create(req: DepositReq):
    await ensure_db()
    if req.amount < 1000:
        return {"ok": False, "error": "Минимум 1000 UZS"}
    supplier_bal = await mock_cek_saldo()
    min_bal = int(await get_setting("min_supplier_balance") or MIN_SUPPLIER)
    if supplier_bal < min_bal:
        return {"ok": False, "error": "⚙️ Шлюз временно закрыт. Попробуйте позже."}
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT locked_amount FROM pending_payments WHERE base_amount=? AND status='waiting' AND expires_at>?",
            (req.amount, now)) as c:
            taken = {r[0] for r in await c.fetchall()}
        locked = None
        for i in range(101):
            candidate = req.amount + i
            if candidate not in taken:
                locked = candidate
                break
        if locked is None:
            return {"ok": False, "error": "Слишком много заявок. Попробуйте другую сумму."}
        expires = now + FREEZE_SECONDS
        await db.execute(
            "INSERT INTO pending_payments (tg_id, base_amount, locked_amount, status, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (req.tg_id, req.amount, locked, "waiting", now, expires))
        async with db.execute("SELECT last_insert_rowid()") as c2:
            pid = (await c2.fetchone())[0]
        await db.commit()
    card = await get_setting("card_number") or CARD_NUMBER
    holder = await get_setting("card_holder") or CARD_HOLDER
    return {"ok": True, "payment_id": pid, "locked_amount": locked,
            "card_number": card, "card_holder": holder,
            "expires_in": FREEZE_SECONDS, "message": f"Переведите РОВНО {locked} UZS"}

@app.post("/api/deposit/check")
async def deposit_check(req: DepositCheckReq):
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status, expires_at FROM pending_payments WHERE id=? AND tg_id=?",
                              (req.payment_id, req.tg_id)) as c:
            row = await c.fetchone()
        if not row:
            return {"ok": False, "error": "Платёж не найден"}
        if row[0] == "confirmed":
            return {"ok": True, "status": "confirmed", "message": "Уже зачислено!"}
        if row[0] == "expired" or int(time.time()) > row[1]:
            await db.execute("UPDATE pending_payments SET status='expired' WHERE id=?", (req.payment_id,))
            await db.commit()
            return {"ok": False, "error": "Время платежа истекло"}
        await db.execute("UPDATE pending_payments SET status='checking' WHERE id=?", (req.payment_id,))
        await db.commit()
    return {"ok": True, "status": "checking", "message": "Заявка отправлена. Ожидайте подтверждения."}

# ─── Buy ───
@app.post("/api/buy")
async def buy(req: BuyReq):
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id=?", (req.tg_id,)) as c:
            row = await c.fetchone()
    if not row:
        return {"ok": False, "error": "Пользователь не найден"}
    balance = row[0]
    items = await mock_price_list()
    markup = int(await get_setting("markup_percent") or MARKUP)
    product = next((i for i in items if i["buyer_sku_code"] == req.buyer_sku_code), None)
    if not product:
        return {"ok": False, "error": "Товар не найден"}
    sell_price = int(product["price"] * (1 + markup / 100))
    if balance < sell_price:
        return {"ok": False, "error": f"Недостаточно средств. Нужно {sell_price}, у вас {balance} UZS"}
    ref_id = f"tp_{int(time.time())}_{req.tg_id}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance-? WHERE tg_id=?", (sell_price, req.tg_id))
        await db.execute(
            "INSERT INTO orders (tg_id, ref_id, buyer_sku_code, product_name, customer_no, cost, sell_price, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (req.tg_id, ref_id, req.buyer_sku_code, product["product_name"],
             req.customer_no, product["price"], sell_price, "pending", int(time.time())))
        await db.commit()
    result = await mock_transaction(req.buyer_sku_code, req.customer_no, ref_id)
    if result.get("status") == "Failed":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (sell_price, req.tg_id))
            await db.execute("UPDATE orders SET status='failed' WHERE ref_id=?", (ref_id,))
            await db.commit()
        return {"ok": False, "error": result.get("message", "Failed")}
    return {"ok": True, "ref_id": ref_id, "status": "pending", "message": "Заказ отправлен!"}

# ─── Orders ───
@app.get("/api/orders/{tg_id}")
async def user_orders(tg_id: int):
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ref_id, product_name, customer_no, sell_price, status, created_at FROM orders WHERE tg_id=? ORDER BY created_at DESC LIMIT 20",
            (tg_id,)) as c:
            rows = await c.fetchall()
    return {"ok": True, "data": [
        {"ref_id": r[0], "product_name": r[1], "customer_no": r[2],
         "sell_price": r[3], "status": r[4], "created_at": r[5]} for r in rows]}

# ─── Admin ───
@app.get("/api/admin/payments")
async def admin_payments():
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT p.id, p.tg_id, u.name, p.base_amount, p.locked_amount, p.status, p.created_at, p.expires_at
            FROM pending_payments p LEFT JOIN users u ON p.tg_id=u.tg_id
            WHERE p.status IN ('waiting','checking') ORDER BY p.created_at DESC""") as c:
            rows = await c.fetchall()
    return {"ok": True, "data": [
        {"id": r[0], "tg_id": r[1], "name": r[2], "base_amount": r[3],
         "locked_amount": r[4], "status": r[5], "created_at": r[6], "expires_at": r[7]} for r in rows]}

@app.post("/api/admin/approve")
async def admin_approve(req: ApproveReq):
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id, base_amount, status FROM pending_payments WHERE id=?",
                              (req.payment_id,)) as c:
            row = await c.fetchone()
        if not row:
            return {"ok": False, "error": "Не найден"}
        if row[2] == "confirmed":
            return {"ok": False, "error": "Уже подтверждён"}
        tg_id, base_amount = row[0], row[1]
        await db.execute("UPDATE pending_payments SET status='confirmed' WHERE id=?", (req.payment_id,))
        await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (base_amount, tg_id))
        await db.commit()
    return {"ok": True, "message": f"Начислено {base_amount} UZS пользователю {tg_id}"}

@app.get("/api/admin/settings")
async def admin_get_settings():
    await ensure_db()
    keys = ["card_number", "card_holder", "markup_percent", "min_supplier_balance", "shop_active"]
    result = {}
    for k in keys:
        result[k] = await get_setting(k)
    return {"ok": True, "data": result}

@app.post("/api/admin/settings")
async def admin_set_settings(req: SettingReq):
    await ensure_db()
    await set_setting(req.key, req.value)
    return {"ok": True}

@app.get("/api/admin/stats")
async def admin_stats():
    await ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*), COALESCE(SUM(sell_price),0) FROM orders WHERE status='success'") as c:
            r = await c.fetchone()
            orders, revenue = r[0], r[1]
        async with db.execute("SELECT COALESCE(SUM(base_amount),0) FROM pending_payments WHERE status='confirmed'") as c:
            deposits = (await c.fetchone())[0]
    supplier = await mock_cek_saldo()
    return {"ok": True, "users": users, "orders": orders, "revenue": revenue,
            "deposits": deposits, "supplier_balance": supplier}

# ─── Health ───
@app.get("/api/health")
async def health():
    await ensure_db()
    return {"ok": True, "status": "ThunderPay is running ⚡"}
