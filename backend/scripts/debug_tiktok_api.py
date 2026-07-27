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

def test_api(method, api_path, data=None):
    access_token = get_access_token()
    if not access_token:
        print(f"❌ 无法获取 access_token")
        return

    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "md5",
    }

    if method.upper() == "GET" and data:
        for key, value in data.items():
            params[key] = str(value)

    params["sign"] = generate_signature(params)

    url = f"{TIKTOK_PARTNER_API_BASE_URL}{api_path}"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }

    print(f"\n测试: {method} {api_path}")
    print(f"URL: {url}")

    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=30)
        else:
            response = requests.post(url, params=params, json=data, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.text:
            print(f"响应内容: {response.text[:1000]}")
        
        return response
    
    except Exception as e:
        print(f"请求失败: {e}")
        return None

def main():
    print("=" * 80)
    print("TikTok API 路径调试")
    print("=" * 80)

    test_paths = [
        ("POST", "/api/v2/orders/search", {"page_no": 1, "page_size": 10, "create_time_from": "2026-07-20 00:00:00", "create_time_to": "2026-07-27 23:59:59"}),
        ("POST", "/api/v2/order/search", {"page_no": 1, "page_size": 10, "create_time_from": "2026-07-20 00:00:00", "create_time_to": "2026-07-27 23:59:59"}),
        ("POST", "/partner/api/v2/order/search", {"page_no": 1, "page_size": 10, "create_time_from": "2026-07-20 00:00:00", "create_time_to": "2026-07-27 23:59:59"}),
        ("GET", "/api/v2/products", {"page_no": 1, "page_size": 10}),
        ("GET", "/api/v2/product/list", {"page_no": 1, "page_size": 10}),
        ("GET", "/partner/api/v2/products", {"page_no": 1, "page_size": 10}),
        ("GET", "/api/v2/creators", {"page_no": 1, "page_size": 10}),
        ("GET", "/api/v2/creator/list", {"page_no": 1, "page_size": 10}),
        ("GET", "/partner/api/v2/creators", {"page_no": 1, "page_size": 10}),
        ("GET", "/api/v2/shop/get", {}),
        ("GET", "/api/v2/shop/info", {}),
    ]

    for method, path, data in test_paths:
        test_api(method, path, data)

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
