import sys
import os
import requests
import hashlib
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.services.tk_token_manager import get_access_token

TIKTOK_PARTNER_API_BASE_URL = "https://open-api.tiktokglobalshop.com"

app_key = settings.TK_PARTNER_APP_KEY
app_secret = settings.TK_PARTNER_APP_SECRET
shop_id = settings.TK_AUTH_SHOP_ID

def generate_signature(params):
    sorted_params = sorted(params.items())
    sign_string = ""
    for key, value in sorted_params:
        if key != "sign" and key != "access_token":
            sign_string += f"{key}{value}"
    sign_string = app_secret + sign_string + app_secret
    return hashlib.md5(sign_string.encode()).hexdigest().upper()

def test_auth_method_1():
    access_token = get_access_token()
    print(f"\n=== 测试方式1: Header x-tts-access-token ===")
    print(f"access_token: {access_token[:30]}...")

    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "md5",
        "page_no": 1,
        "page_size": 10,
    }
    params["sign"] = generate_signature(params)

    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, params=params, json={"page_no": 1, "page_size": 10}, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
    except Exception as e:
        print(f"失败: {e}")

def test_auth_method_2():
    access_token = get_access_token()
    print(f"\n=== 测试方式2: Query 参数 access_token ===")

    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "md5",
        "access_token": access_token,
        "page_no": 1,
        "page_size": 10,
    }
    params["sign"] = generate_signature(params)

    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, params=params, json={"page_no": 1, "page_size": 10}, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
    except Exception as e:
        print(f"失败: {e}")

def test_auth_method_3():
    access_token = get_access_token()
    print(f"\n=== 测试方式3: Shop Cipher 格式 ===")

    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_cipher": shop_id,
        "sign_method": "md5",
        "page_no": 1,
        "page_size": 10,
    }
    params["sign"] = generate_signature(params)

    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, params=params, json={"page_no": 1, "page_size": 10}, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
    except Exception as e:
        print(f"失败: {e}")

def test_product_endpoint():
    access_token = get_access_token()
    print(f"\n=== 测试商品API ===")

    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "md5",
        "page_no": 1,
        "page_size": 10,
    }
    params["sign"] = generate_signature(params)

    url = f"{TIKTOK_PARTNER_API_BASE_URL}/product/202309/products"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, params=params, json={"page_no": 1, "page_size": 10}, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
    except Exception as e:
        print(f"失败: {e}")

def main():
    print("=" * 80)
    print("TikTok API 认证方式调试")
    print("=" * 80)

    test_auth_method_1()
    test_auth_method_2()
    test_auth_method_3()
    test_product_endpoint()

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
