import hashlib
import asyncio
import aiosqlite
import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
import time

app = FastAPI(title="Mock Digiflazz API")

DB_PATH = "mock_df.db"

# Секретные данные для проверки подписи (MD5)
EXPECTED_USERNAME = "saterlix_user"
EXPECTED_API_KEY = "dummy_api_key_123"

def verify_sign(username: str, provided_sign: str, sign_type: str, ref_id: str = "") -> bool:
    """
    Проверка MD5 подписи.
    sign_type: 'depo' (баланс), 'pricelist' (каталог), 'transaction' (покупка)
    Для покупки добавляется ref_id.
    """
    if username != EXPECTED_USERNAME:
        return False
        
    if sign_type == "depo":
        text_to_hash = f"{EXPECTED_USERNAME}{EXPECTED_API_KEY}depo"
    elif sign_type == "pricelist":
        text_to_hash = f"{EXPECTED_USERNAME}{EXPECTED_API_KEY}pricelist"
    elif sign_type == "transaction":
        text_to_hash = f"{EXPECTED_USERNAME}{EXPECTED_API_KEY}{ref_id}"
    else:
        return False
        
    calculated_sign = hashlib.md5(text_to_hash.encode()).hexdigest()
    return provided_sign == calculated_sign

@app.on_event("startup")
async def startup():
    # Инициализация тестовой БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mock_balance (
                id INTEGER PRIMARY KEY,
                deposit INTEGER
            )
        ''')
        # Изначальный баланс 1 500 000
        await db.execute('INSERT OR IGNORE INTO mock_balance (id, deposit) VALUES (1, 1500000)')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mock_catalog (
                buyer_sku_code TEXT PRIMARY KEY,
                product_name TEXT,
                price INTEGER,
                buyer_product_status BOOLEAN
            )
        ''')
        await db.execute('DELETE FROM mock_catalog') # Очистка
        catalog = [
            ("mlbb_86", "86 Diamonds MLBB", 14000, True),
            ("pubg_60", "60 UC PUBG", 13500, True),
            ("ff_100", "100 Diamonds Free Fire", 12000, True),
            ("genshin_60", "60 Crystals Genshin", 13800, False), # Отключен для теста
        ]
        await db.executemany(
            'INSERT INTO mock_catalog (buyer_sku_code, product_name, price, buyer_product_status) VALUES (?, ?, ?, ?)',
            catalog
        )
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mock_transactions (
                ref_id TEXT PRIMARY KEY,
                buyer_sku_code TEXT,
                customer_no TEXT,
                status TEXT
            )
        ''')
        await db.commit()

class BalanceRequest(BaseModel):
    username: str
    sign: str
    cmd: str = "deposit"

@app.post("/cek-saldo")
async def cek_saldo(req: BalanceRequest):
    if not verify_sign(req.username, req.sign, "depo"):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT deposit FROM mock_balance WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return {"data": {"deposit": row[0]}}

class CatalogRequest(BaseModel):
    username: str
    sign: str
    cmd: str = "prepaid"

@app.post("/price-list")
async def price_list(req: CatalogRequest):
    if not verify_sign(req.username, req.sign, "pricelist"):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT buyer_sku_code, product_name, price, buyer_product_status FROM mock_catalog") as cursor:
            rows = await cursor.fetchall()
            
    data = []
    for row in rows:
        data.append({
            "buyer_sku_code": row[0],
            "product_name": row[1],
            "price": row[2],
            "buyer_product_status": bool(row[3])
        })
    return {"data": data}

class TransactionRequest(BaseModel):
    username: str
    buyer_sku_code: str
    customer_no: str
    ref_id: str
    sign: str

# Фоновая задача для отправки Webhook
async def process_transaction_and_webhook(req: TransactionRequest, price: int):
    # Имитируем задержку сервиса (Mobile Legends думает)
    await asyncio.sleep(5) 
    
    # Меняем статус в БД
    status = "Success"
    # Для теста: если customer_no = "ERROR", делаем ошибку
    if req.customer_no == "ERROR":
        status = "Failed"
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE mock_transactions SET status = ? WHERE ref_id = ?", (status, req.ref_id))
        if status == "Failed":
             # Возвращаем деньги на баланс
             await db.execute("UPDATE mock_balance SET deposit = deposit + ? WHERE id = 1", (price,))
        await db.commit()
    
    # Отправляем webhook боту (бот будет слушать порт 8080)
    webhook_url = "http://localhost:8080/digiflazz/webhook"
    webhook_data = {
        "status": status,
        "ref_id": req.ref_id,
        "buyer_sku_code": req.buyer_sku_code,
        "customer_no": req.customer_no
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=webhook_data)
        print(f"[Digiflazz MOCK] Webhook отправлен для {req.ref_id}: {status}")
    except Exception as e:
        print(f"[Digiflazz MOCK] Ошибка отправки Webhook: {e}")


@app.post("/transaction")
async def transaction(req: TransactionRequest):
    # Проверка подписи с ref_id
    if not verify_sign(req.username, req.sign, "transaction", req.ref_id):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем товар и цену
        async with db.execute("SELECT price, buyer_product_status FROM mock_catalog WHERE buyer_sku_code = ?", (req.buyer_sku_code,)) as cursor:
            product = await cursor.fetchone()
            
        if not product or not product[1]:
            return {"data": {"status": "Failed", "message": "Product not found or offline"}}
            
        price = product[0]
        
        # Проверяем баланс
        async with db.execute("SELECT deposit FROM mock_balance WHERE id = 1") as cursor:
            balance = (await cursor.fetchone())[0]
            
        if balance < price:
             return {"data": {"status": "Failed", "message": "Insufficient balance"}}
             
        # Списываем баланс
        await db.execute("UPDATE mock_balance SET deposit = deposit - ? WHERE id = 1", (price,))
        
        # Добавляем транзакцию (Pending)
        await db.execute(
            "INSERT INTO mock_transactions (ref_id, buyer_sku_code, customer_no, status) VALUES (?, ?, ?, ?)",
            (req.ref_id, req.buyer_sku_code, req.customer_no, "Pending")
        )
        await db.commit()
        
    # Запускаем фоновый процесс (webhook)
    asyncio.create_task(process_transaction_and_webhook(req, price))
    
    return {
        "data": {
            "ref_id": req.ref_id,
            "status": "Pending",
            "message": "Transaction is being processed"
        }
    }

if __name__ == "__main__":
    uvicorn.run("mock_digiflazz:app", host="0.0.0.0", port=8000, reload=True)
