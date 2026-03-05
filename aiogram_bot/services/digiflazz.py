import hashlib
import aiohttp
import json

USERNAME = "saterlix_user"
API_KEY = "dummy_api_key_123"
BASE_URL = "http://localhost:8000"

def _generate_sign(cmd: str, ref_id: str = "") -> str:
    if cmd == "deposit":
        text = f"{USERNAME}{API_KEY}depo"
    elif cmd == "prepaid":
        text = f"{USERNAME}{API_KEY}pricelist"
    elif cmd == "transaction":
        text = f"{USERNAME}{API_KEY}{ref_id}"
    else:
        text = ""
    return hashlib.md5(text.encode()).hexdigest()

async def get_catalog():
    sign = _generate_sign("prepaid")
    payload = {
        "username": USERNAME,
        "sign": sign,
        "cmd": "prepaid"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BASE_URL}/price-list", json=payload) as resp:
                data = await resp.json()
                return data.get("data", [])
        except Exception as e:
            print("Error get_catalog:", e)
            return []

async def check_supplier_balance() -> int:
    sign = _generate_sign("deposit")
    payload = {
        "username": USERNAME,
        "sign": sign,
        "cmd": "deposit"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BASE_URL}/cek-saldo", json=payload) as resp:
                data = await resp.json()
                return data.get("data", {}).get("deposit", 0)
        except Exception as e:
            print("Error check_supplier_balance:", e)
            return 0

async def make_transaction(buyer_sku_code: str, customer_no: str, ref_id: str):
    sign = _generate_sign("transaction", ref_id)
    payload = {
        "username": USERNAME,
        "buyer_sku_code": buyer_sku_code,
        "customer_no": customer_no,
        "ref_id": ref_id,
        "sign": sign
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BASE_URL}/transaction", json=payload) as resp:
                return await resp.json()
        except Exception as e:
            print("Error transaction:", e)
            return {"data": {"status": "Failed", "message": "Connection error"}}
