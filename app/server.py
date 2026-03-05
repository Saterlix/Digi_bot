"""
ThunderPay — Main Backend API Server
Порт: 5000
Раздаёт статику, обрабатывает API, принимает вебхуки.
"""
import hashlib
import asyncio
import aiosqlite
import httpx
import json
import time
import os
import hmac
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ─── Config ───
DB_PATH = "data.db"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7165323599"))
DF_USERNAME = os.getenv("DIGIFLAZZ_USERNAME", "thunderpay")
DF_API_KEY = os.getenv("DIGIFLAZZ_API_KEY", "dev-key-thunderpay-2026")
DF_BASE = os.getenv("DIGIFLAZZ_BASE_URL", "http://localhost:8000/v1")
MARKUP = int(os.getenv("MARKUP_PERCENT", "25"))
MIN_SUPPLIER = int(os.getenv("MIN_SUPPLIER_BALANCE", "50000"))
FREEZE_SECONDS = 5 * 60  # 5 минут

logging.basicConfig(level=logging.INFO)

# ─── DB helpers ───
async def get_db():
    return aiosqlite.connect(DB_PATH)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                name TEXT,
                username TEXT,
                balance INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                ref_id TEXT UNIQUE,
                buyer_sku_code TEXT,
                product_name TEXT,
                customer_no TEXT,
                cost INTEGER,
                sell_price INTEGER,
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                base_amount INTEGER,
                locked_amount INTEGER,
                status TEXT DEFAULT 'waiting',
                created_at INTEGER,
                expires_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Default settings
        defaults = {
            "card_number": os.getenv("CARD_NUMBER", "8600 0000 0000 0000"),
            "card_holder": os.getenv("CARD_HOLDER", "ThunderPay Admin"),
            "markup_percent": str(MARKUP),
            "min_supplier_balance": str(MIN_SUPPLIER),
            "shop_active": "1",
            "df_username": DF_USERNAME,
            "df_api_key": DF_API_KEY,
            "df_base_url": DF_BASE,
        }
        for k, v in defaults.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v))
        await db.commit()

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else ""

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()

# ─── Digiflazz Client ───
def df_sign(extra: str) -> str:
    return hashlib.md5(f"{DF_USERNAME}{DF_API_KEY}{extra}".encode()).hexdigest()

async def df_check_balance() -> int:
    try:
        base = await get_setting("df_base_url") or DF_BASE
        un = await get_setting("df_username") or DF_USERNAME
        ak = await get_setting("df_api_key") or DF_API_KEY
        sign = hashlib.md5(f"{un}{ak}depo".encode()).hexdigest()
        async with httpx.AsyncClient(timeout=5) as cl:
            r = await cl.post(f"{base}/cek-saldo", json={"username": un, "sign": sign})
            return r.json().get("data", {}).get("deposit", 0)
    except:
        return 0

async def df_get_catalog() -> list:
    try:
        base = await get_setting("df_base_url") or DF_BASE
        un = await get_setting("df_username") or DF_USERNAME
        ak = await get_setting("df_api_key") or DF_API_KEY
        sign = hashlib.md5(f"{un}{ak}pricelist".encode()).hexdigest()
        async with httpx.AsyncClient(timeout=10) as cl:
            r = await cl.post(f"{base}/price-list", json={"username": un, "sign": sign, "cmd": "prepaid"})
            return r.json().get("data", [])
    except:
        return []

async def df_transaction(sku: str, customer_no: str, ref_id: str) -> dict:
    try:
        base = await get_setting("df_base_url") or DF_BASE
        un = await get_setting("df_username") or DF_USERNAME
        ak = await get_setting("df_api_key") or DF_API_KEY
        sign = hashlib.md5(f"{un}{ak}{ref_id}".encode()).hexdigest()
        async with httpx.AsyncClient(timeout=10) as cl:
            r = await cl.post(f"{base}/transaction", json={
                "username": un, "buyer_sku_code": sku,
                "customer_no": customer_no, "ref_id": ref_id, "sign": sign})
            return r.json()
    except Exception as e:
        return {"data": {"status": "Failed", "message": str(e)}}

# ─── Background tasks ───
async def cleanup_expired():
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                now = int(time.time())
                await db.execute("UPDATE pending_payments SET status='expired' WHERE expires_at<=? AND status='waiting'", (now,))
                await db.commit()
        except:
            pass
        await asyncio.sleep(30)

# ─── App ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(cleanup_expired())
    yield

app = FastAPI(title="ThunderPay API", lifespan=lifespan)
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

# ─── API Routes ───

@app.post("/api/auth")
async def auth(req: AuthReq):
    """Авто-регистрация по Telegram initData"""
    try:
        # Parse initData (simplified — on production validate hash)
        params = dict(x.split("=", 1) for x in req.initData.split("&") if "=" in x)
        import urllib.parse
        user_json = urllib.parse.unquote(params.get("user", "{}"))
        user = json.loads(user_json)
        tg_id = user.get("id", 0)
        name = user.get("first_name", "User")
        username = user.get("username", "")
    except:
        # Fallback for testing without Telegram
        tg_id = 999999
        name = "Test User"
        username = "testuser"
    
    if not tg_id:
        raise HTTPException(400, "Invalid initData")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, name, username, created_at) VALUES (?,?,?,?)",
            (tg_id, name, username, int(time.time())))
        # Update admin flag
        if tg_id == ADMIN_ID:
            await db.execute("UPDATE users SET is_admin=1 WHERE tg_id=?", (tg_id,))
        await db.commit()
        async with db.execute("SELECT balance, is_admin FROM users WHERE tg_id=?", (tg_id,)) as c:
            row = await c.fetchone()
    
    return {"ok": True, "tg_id": tg_id, "name": name,
            "balance": row[0] if row else 0,
            "is_admin": bool(row[1]) if row else False}

@app.get("/api/catalog")
async def catalog():
    """Каталог товаров из Digiflazz с наценкой"""
    items = await df_get_catalog()
    markup = int(await get_setting("markup_percent") or MARKUP)
    for item in items:
        item["sell_price"] = int(item["price"] * (1 + markup / 100))
    return {"ok": True, "data": items}

@app.get("/api/user/{tg_id}/balance")
async def user_balance(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id=?", (tg_id,)) as c:
            row = await c.fetchone()
    return {"ok": True, "balance": row[0] if row else 0}

# ── Deposit (P2P) ──
@app.post("/api/deposit/create")
async def deposit_create(req: DepositReq):
    """Создание заявки на пополнение с заморозкой суммы"""
    if req.amount < 1000:
        return {"ok": False, "error": "Минимум 1000 UZS"}
    
    # Kill switch
    supplier_bal = await df_check_balance()
    min_bal = int(await get_setting("min_supplier_balance") or MIN_SUPPLIER)
    if supplier_bal < min_bal:
        return {"ok": False, "error": "⚙️ Шлюз пополнения временно закрыт. Попробуйте позже."}
    
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        # Find unique amount
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
        pid = db.last_insert_rowid()  
        # Get the payment id
        async with db.execute("SELECT last_insert_rowid()") as c2:
            pid = (await c2.fetchone())[0]
        await db.commit()
    
    card = await get_setting("card_number")
    holder = await get_setting("card_holder")
    
    return {"ok": True, "payment_id": pid, "locked_amount": locked,
            "card_number": card, "card_holder": holder,
            "expires_in": FREEZE_SECONDS,
            "message": f"Переведите РОВНО {locked} UZS"}

@app.post("/api/deposit/check")
async def deposit_check(req: DepositCheckReq):
    """Кнопка «Оплатил» — помечает платёж как ожидающий подтверждения"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT status, expires_at FROM pending_payments WHERE id=? AND tg_id=?",
            (req.payment_id, req.tg_id)) as c:
            row = await c.fetchone()
        
        if not row:
            return {"ok": False, "error": "Платёж не найден"}
        if row[0] == "confirmed":
            return {"ok": True, "status": "confirmed", "message": "Уже зачислено!"}
        if row[0] == "expired":
            return {"ok": False, "error": "Время платежа истекло"}
        
        now = int(time.time())
        if now > row[1]:
            await db.execute("UPDATE pending_payments SET status='expired' WHERE id=?", (req.payment_id,))
            await db.commit()
            return {"ok": False, "error": "Время платежа истекло"}
        
        await db.execute("UPDATE pending_payments SET status='checking' WHERE id=?", (req.payment_id,))
        await db.commit()
    
    return {"ok": True, "status": "checking",
            "message": "Заявка отправлена. Ожидайте подтверждения администратора."}

# ── Buy ──
@app.post("/api/buy")
async def buy(req: BuyReq):
    """Покупка товара через Digiflazz"""
    # Check balance
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE tg_id=?", (req.tg_id,)) as c:
            row = await c.fetchone()
    if not row:
        return {"ok": False, "error": "Пользователь не найден"}
    balance = row[0]
    
    # Get price from catalog
    items = await df_get_catalog()
    markup = int(await get_setting("markup_percent") or MARKUP)
    product = None
    for item in items:
        if item["buyer_sku_code"] == req.buyer_sku_code:
            product = item
            break
    if not product:
        return {"ok": False, "error": "Товар не найден"}
    
    sell_price = int(product["price"] * (1 + markup / 100))
    if balance < sell_price:
        return {"ok": False, "error": f"Недостаточно средств. Нужно {sell_price} UZS, у вас {balance} UZS."}
    
    # Deduct
    ref_id = f"tp_{int(time.time())}_{req.tg_id}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance-? WHERE tg_id=?", (sell_price, req.tg_id))
        await db.execute(
            "INSERT INTO orders (tg_id, ref_id, buyer_sku_code, product_name, customer_no, cost, sell_price, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (req.tg_id, ref_id, req.buyer_sku_code, product["product_name"],
             req.customer_no, product["price"], sell_price, "pending", int(time.time())))
        await db.commit()
    
    # Call Digiflazz
    result = await df_transaction(req.buyer_sku_code, req.customer_no, ref_id)
    status = result.get("data", {}).get("status", "Failed")
    
    if status == "Failed":
        # Refund
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (sell_price, req.tg_id))
            await db.execute("UPDATE orders SET status='failed' WHERE ref_id=?", (ref_id,))
            await db.commit()
        return {"ok": False, "error": result.get("data", {}).get("message", "Transaction failed")}
    
    return {"ok": True, "ref_id": ref_id, "status": "pending",
            "message": "Заказ отправлен! Ожидайте доставку."}

# ── Webhook from Digiflazz ──
@app.post("/api/webhook/digiflazz")
async def webhook_digiflazz(request: Request):
    body = await request.json()
    data = body.get("data", {})
    ref_id = data.get("ref_id", "")
    status = data.get("status", "")
    
    final_status = "success" if status == "Sukses" else "failed"
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id, sell_price FROM orders WHERE ref_id=?", (ref_id,)) as c:
            order = await c.fetchone()
        if order:
            await db.execute("UPDATE orders SET status=? WHERE ref_id=?", (final_status, ref_id))
            if final_status == "failed":
                await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (order[1], order[0]))
            await db.commit()
    
    logging.info(f"[Webhook] {ref_id} → {final_status}")
    return {"ok": True}

# ── Admin ──
@app.get("/api/admin/payments")
async def admin_payments():
    """Список ожидающих платежей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT p.id, p.tg_id, u.name, p.base_amount, p.locked_amount, p.status, p.created_at, p.expires_at
            FROM pending_payments p LEFT JOIN users u ON p.tg_id=u.tg_id
            WHERE p.status IN ('waiting','checking')
            ORDER BY p.created_at DESC""") as c:
            rows = await c.fetchall()
    return {"ok": True, "data": [
        {"id": r[0], "tg_id": r[1], "name": r[2], "base_amount": r[3],
         "locked_amount": r[4], "status": r[5], "created_at": r[6], "expires_at": r[7]}
        for r in rows]}

@app.post("/api/admin/approve")
async def admin_approve(req: ApproveReq):
    """Подтверждение платежа"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id, base_amount, status FROM pending_payments WHERE id=?",
                              (req.payment_id,)) as c:
            row = await c.fetchone()
        if not row:
            return {"ok": False, "error": "Платёж не найден"}
        if row[2] == "confirmed":
            return {"ok": False, "error": "Уже подтверждён"}
        
        tg_id, base_amount = row[0], row[1]
        await db.execute("UPDATE pending_payments SET status='confirmed' WHERE id=?", (req.payment_id,))
        await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (base_amount, tg_id))
        await db.commit()
    
    return {"ok": True, "message": f"Начислено {base_amount} UZS пользователю {tg_id}"}

@app.get("/api/admin/settings")
async def admin_get_settings():
    keys = ["card_number", "card_holder", "markup_percent", "min_supplier_balance",
            "shop_active", "df_username", "df_api_key", "df_base_url"]
    result = {}
    for k in keys:
        result[k] = await get_setting(k)
    return {"ok": True, "data": result}

@app.post("/api/admin/settings")
async def admin_set_settings(req: SettingReq):
    await set_setting(req.key, req.value)
    return {"ok": True}

@app.get("/api/admin/stats")
async def admin_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*), COALESCE(SUM(sell_price),0) FROM orders WHERE status='success'") as c:
            r = await c.fetchone()
            orders, revenue = r[0], r[1]
        async with db.execute("SELECT COALESCE(SUM(base_amount),0) FROM pending_payments WHERE status='confirmed'") as c:
            deposits = (await c.fetchone())[0]
    supplier = await df_check_balance()
    return {"ok": True, "users": users, "orders": orders, "revenue": revenue,
            "deposits": deposits, "supplier_balance": supplier}

@app.get("/api/orders/{tg_id}")
async def user_orders(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ref_id, product_name, customer_no, sell_price, status, created_at FROM orders WHERE tg_id=? ORDER BY created_at DESC LIMIT 20",
            (tg_id,)) as c:
            rows = await c.fetchall()
    return {"ok": True, "data": [
        {"ref_id": r[0], "product_name": r[1], "customer_no": r[2],
         "sell_price": r[3], "status": r[4], "created_at": r[5]}
        for r in rows]}

# ── Static files ──
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)
