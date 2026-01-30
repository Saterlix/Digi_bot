import requests
import hashlib
import json

USERNAME = ""
API_KEY = ""

def get_digiflazz_balance():
    sign_str = USERNAME + API_KEY + "depo"
    signature = hashlib.md5(sign_str.encode()).hexdigest()

    payload = {
        "username": USERNAME,
        "sign": signature
    }

    print("")
    response = requests.post("https://api.digiflazz.com/v1/cek-saldo", json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        return f"Ошибка: {response.status_code}"

if __name__ == "__main__":
    balance_data = get_digiflazz_balance()
    print(json.dumps(balance_data, indent=4))