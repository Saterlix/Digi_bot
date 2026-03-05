"""
ThunderPay — Mock Digiflazz API Server
Полный эмулятор API Digiflazz для тестирования.
Порт: 8000
"""
import hashlib
import asyncio
import aiosqlite
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import time
import json

app = FastAPI(title="ThunderPay Mock Digiflazz API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "mock_data.db"
USERNAME = "thunderpay"
API_KEY = "dev-key-thunderpay-2026"
WEBHOOK_URL = "http://localhost:5000/api/webhook/digiflazz"

# ─── Helpers ───
def make_sign(username: str, api_key: str, extra: str) -> str:
    return hashlib.md5(f"{username}{api_key}{extra}".encode()).hexdigest()

def verify(username: str, sign: str, extra: str) -> bool:
    if username != USERNAME:
        return False
    return sign == make_sign(USERNAME, API_KEY, extra)

# ─── Seed Data ───
SEED_CATALOG = [
    # MLBB
    ("mlbb_86",   "MLBB",  "86 Diamonds",   14000, True),
    ("mlbb_172",  "MLBB",  "172 Diamonds",  27000, True),
    ("mlbb_257",  "MLBB",  "257 Diamonds",  40000, True),
    ("mlbb_344",  "MLBB",  "344 Diamonds",  53000, True),
    ("mlbb_514",  "MLBB",  "514 Diamonds",  79000, True),
    ("mlbb_706",  "MLBB",  "706 Diamonds",  108000, True),
    ("mlbb_wp",   "MLBB",  "Weekly Diamond Pass", 18000, True),
    ("mlbb_tp",   "MLBB",  "Twilight Pass",  95000, True),
    # PUBG
    ("pubg_60",   "PUBG",  "60 UC",         13500, True),
    ("pubg_325",  "PUBG",  "325 UC",        65000, True),
    ("pubg_660",  "PUBG",  "660 UC",        130000, True),
    ("pubg_1800", "PUBG",  "1800 UC",       340000, True),
    ("pubg_rp",   "PUBG",  "Royale Pass",   95000, True),
    # Free Fire
    ("ff_100",    "FREEFIRE", "100 Diamonds",  12000, True),
    ("ff_210",    "FREEFIRE", "210 Diamonds",  24000, True),
    ("ff_530",    "FREEFIRE", "530 Diamonds",  56000, True),
    ("ff_1060",   "FREEFIRE", "1060 Diamonds", 108000, True),
    ("ff_wm",     "FREEFIRE", "Weekly Membership", 18000, True),
    # Genshin Impact
    ("gi_60",     "GENSHIN", "60 Genesis Crystals",  15000, True),
    ("gi_300",    "GENSHIN", "300 Genesis Crystals", 68000, True),
    ("gi_980",    "GENSHIN", "980 Genesis Crystals", 210000, True),
    ("gi_1980",   "GENSHIN", "1980 Genesis Crystals", 415000, True),
    ("gi_welkin", "GENSHIN", "Welkin Moon (30 дней)", 55000, True),
    ("gi_bp",     "GENSHIN", "Battle Pass Gnostic Hymn", 100000, True),
    # Standoff 2
    ("so2_150",   "STANDOFF2", "150 Gold",   15000, True),
    ("so2_500",   "STANDOFF2", "500 Gold",   45000, True),
    ("so2_1500",  "STANDOFF2", "1500 Gold",  125000, True),
    ("so2_5000",  "STANDOFF2", "5000 Gold",  380000, True),
    # Clash Royale
    ("cr_80",     "CLASHROYALE", "80 Gems",     12000, True),
    ("cr_500",    "CLASHROYALE", "500 Gems",    55000, True),
    ("cr_1200",   "CLASHROYALE", "1200 Gems",   115000, True),
    ("cr_2500",   "CLASHROYALE", "2500 Gems",   225000, True),
    ("cr_pass",   "CLASHROYALE", "Pass Royale", 55000, True),
    # Honor of Kings
    ("hok_60",    "HOK",   "60 Tokens",     13000, True),
    ("hok_300",   "HOK",   "300 Tokens",    58000, True),
    ("hok_600",   "HOK",   "600 Tokens",    110000, True),
    ("hok_1500",  "HOK",   "1500 Tokens",   260000, True),
    # Call of Duty Mobile
    ("codm_80",   "CODM",  "80 CP",         12000, True),
    ("codm_400",  "CODM",  "400 CP",        52000, True),
    ("codm_800",  "CODM",  "800 CP",        98000, True),
    ("codm_2400", "CODM",  "2400 CP",       280000, True),
    ("codm_bp",   "CODM",  "Battle Pass",   95000, True),
    # Brawl Stars
    ("bs_30",     "BRAWLSTARS", "30 Gems",    10000, True),
    ("bs_80",     "BRAWLSTARS", "80 Gems",    22000, True),
    ("bs_170",    "BRAWLSTARS", "170 Gems",   45000, True),
    ("bs_360",    "BRAWLSTARS", "360 Gems",   88000, True),
    ("bs_pass",   "BRAWLSTARS", "Brawl Pass", 85000, True),
    # Roblox
    ("rbx_400",   "ROBLOX", "400 Robux",     52000, True),
    ("rbx_800",   "ROBLOX", "800 Robux",     98000, True),
    ("rbx_1700",  "ROBLOX", "1700 Robux",    195000, True),
    ("rbx_4500",  "ROBLOX", "4500 Robux",    490000, True),
    # Telegram Stars
    ("tg_50",     "TGSTARS", "50 Stars",     5500, True),
    ("tg_100",    "TGSTARS", "100 Stars",    10500, True),
    ("tg_250",    "TGSTARS", "250 Stars",    25000, True),
    ("tg_1000",   "TGSTARS", "1000 Stars",   95000, True),
    ("tg_prem1",  "TGSTARS", "Telegram Premium 1 мес", 35000, True),
    ("tg_prem6",  "TGSTARS", "Telegram Premium 6 мес", 175000, True),
]

# ─── DB Init ───
@app.on_event("startup")
async def startup():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS balance (id INTEGER PRIMARY KEY, deposit INTEGER)")
        await db.execute("INSERT OR IGNORE INTO balance (id, deposit) VALUES (1, 5000000)")
        await db.execute("""CREATE TABLE IF NOT EXISTS catalog (
            buyer_sku_code TEXT PRIMARY KEY, category TEXT, product_name TEXT,
            price INTEGER, buyer_product_status BOOLEAN)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS transactions (
            ref_id TEXT PRIMARY KEY, buyer_sku_code TEXT, customer_no TEXT,
            status TEXT, price INTEGER, created_at INTEGER)""")
        await db.execute("DELETE FROM catalog")
        await db.executemany(
            "INSERT INTO catalog VALUES (?,?,?,?,?)", SEED_CATALOG)
        await db.commit()

# ─── Models ───
class BalanceReq(BaseModel):
    username: str
    sign: str

class CatalogReq(BaseModel):
    username: str
    sign: str
    cmd: str = "prepaid"

class TransactionReq(BaseModel):
    username: str
    buyer_sku_code: str
    customer_no: str
    ref_id: str
    sign: str

# ─── Endpoints ───
@app.post("/v1/cek-saldo")
async def cek_saldo(req: BalanceReq):
    if not verify(req.username, req.sign, "depo"):
        return {"data": {"rc": "401", "message": "Invalid signature"}}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT deposit FROM balance WHERE id=1") as c:
            row = await c.fetchone()
    return {"data": {"deposit": row[0]}}

@app.post("/v1/price-list")
async def price_list(req: CatalogReq):
    if not verify(req.username, req.sign, "pricelist"):
        return {"data": {"rc": "401", "message": "Invalid signature"}}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM catalog") as c:
            rows = await c.fetchall()
    return {"data": [{"buyer_sku_code": r[0], "category": r[1],
                      "product_name": r[2], "price": r[3],
                      "buyer_product_status": bool(r[4])} for r in rows]}

@app.post("/v1/transaction")
async def transaction(req: TransactionReq):
    if not verify(req.username, req.sign, req.ref_id):
        return {"data": {"status": "Failed", "rc": "401", "message": "Invalid signature"}}
    async with aiosqlite.connect(DB_PATH) as db:
        # Check duplicate
        async with db.execute("SELECT ref_id FROM transactions WHERE ref_id=?", (req.ref_id,)) as c:
            if await c.fetchone():
                return {"data": {"status": "Failed", "rc": "400", "message": "Duplicate ref_id"}}
        # Check product
        async with db.execute("SELECT price, buyer_product_status FROM catalog WHERE buyer_sku_code=?",
                              (req.buyer_sku_code,)) as c:
            prod = await c.fetchone()
        if not prod or not prod[1]:
            return {"data": {"status": "Failed", "rc": "404", "message": "Product not found or offline"}}
        price = prod[0]
        # Check balance
        async with db.execute("SELECT deposit FROM balance WHERE id=1") as c:
            bal = (await c.fetchone())[0]
        if bal < price:
            return {"data": {"status": "Failed", "rc": "402", "message": "Insufficient supplier balance"}}
        # Deduct & save
        await db.execute("UPDATE balance SET deposit=deposit-? WHERE id=1", (price,))
        await db.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?)",
                         (req.ref_id, req.buyer_sku_code, req.customer_no, "Pending", price, int(time.time())))
        await db.commit()

    asyncio.create_task(_process_webhook(req, price))
    return {"data": {"ref_id": req.ref_id, "status": "Pending",
                     "buyer_sku_code": req.buyer_sku_code, "customer_no": req.customer_no,
                     "price": price, "message": "Transaction is being processed"}}

async def _process_webhook(req: TransactionReq, price: int):
    await asyncio.sleep(4)
    status = "Failed" if req.customer_no == "ERROR" else "Sukses"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE transactions SET status=? WHERE ref_id=?", (status, req.ref_id))
        if status == "Failed":
            await db.execute("UPDATE balance SET deposit=deposit+? WHERE id=1", (price,))
        await db.commit()
    payload = {"data": {"ref_id": req.ref_id, "status": status,
               "buyer_sku_code": req.buyer_sku_code, "customer_no": req.customer_no, "price": price}}
    try:
        async with httpx.AsyncClient() as cl:
            await cl.post(WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[MOCK] Webhook send failed: {e}")

if __name__ == "__main__":
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True)
