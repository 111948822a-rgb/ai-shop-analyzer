import sys
import os
import requests
import hashlib
import hmac
import time
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.services.tk_token_manager import get_access_token

TIKTOK_PARTNER_API_BASE_URL = "https://open-api.tiktokglobalshop.com"

app_key = settings.TK_PARTNER_APP_KEY
app_secret = settings.TK_PARTNER_APP_SECRET
shop_id = settings.TK_AUTH_SHOP_ID

def generate_signature(api_path, params, body=""):
    filtered_params = {k: v for k, v in params.items() if k != "sign" and k != "access_token"}
    sorted_params = sorted(filtered_params.items())
    
    sign_string = api_path
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    
    if body:
        sign_string += body
    
    sign_string = app_secret + sign_string + app_secret
    
    signature = hmac.new(
        app_secret.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def test_order_search_v1():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V1 (POST + 查询串参数 + data参数 驼峰) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
    }
    
    body_data = {
        "PageNo": 1,
        "PageSize": 10,
        "CreateTimeFrom": "2026-07-20 00:00:00",
        "CreateTimeTo": "2026-07-27 23:59:59",
    }
    body_string = json.dumps(body_data, separators=(',', ':'))
    print(f"请求体: {body_string}")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"实际URL: {response.url}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_order_search_v5():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V5 (POST + 只认证参数放查询串 + 业务参数只放请求体) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
    }
    
    body_data = {
        "PageNo": 1,
        "PageSize": 10,
        "CreateTimeFrom": "2026-07-20 00:00:00",
        "CreateTimeTo": "2026-07-27 23:59:59",
    }
    body_string = json.dumps(body_data, separators=(',', ':'))
    print(f"请求体: {body_string}")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"实际URL: {response.url}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_order_search_v6():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V6 (POST + URL手动拼接) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
    }
    
    body_data = {
        "PageNo": 1,
        "PageSize": 10,
    }
    body_string = json.dumps(body_data, separators=(',', ':'))
    print(f"请求体: {body_string}")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    query_params = "&".join([f"{k}={v}" for k, v in params.items()])
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search?{query_params}"
    print(f"完整URL: {url}")
    
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_order_search_v3():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V3 (POST + 参数放查询串) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
        "PageNo": 1,
        "PageSize": 10,
    }
    
    body_string = ""
    print(f"请求体: (空)")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"实际URL: {response.url}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_order_search_v4():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V4 (POST + URL编码参数 + 表单格式) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
        "PageNo": 1,
        "PageSize": 10,
    }
    
    body_data = {
        "PageNo": 1,
        "PageSize": 10,
    }
    body_string = json.dumps(body_data, separators=(',', ':'))
    print(f"请求体: {body_string}")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, json=body_data, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"实际URL: {response.url}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_order_search_v2():
    access_token = get_access_token()
    print("\n=== 测试订单搜索 V2 (POST + 查询串参数 + data参数 下划线) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
    }
    
    body_data = {
        "page_no": 1,
        "page_size": 10,
    }
    body_string = json.dumps(body_data, separators=(',', ':'))
    print(f"请求体: {body_string}")
    print(f"请求体长度: {len(body_string)}")
    
    params["sign"] = generate_signature("/order/202309/orders/search", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/order/202309/orders/search"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_shop_api():
    access_token = get_access_token()
    print("\n=== 测试店铺API ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": "sha256",
    }
    
    body_string = ""
    params["sign"] = generate_signature("/authorization/202309/shops", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/authorization/202309/shops"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_product_api():
    access_token = get_access_token()
    print("\n=== 测试商品API (POST + 查询串参数) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
        "PageNo": 1,
        "PageSize": 10,
    }
    
    body_string = ""
    print(f"请求体: (空)")
    
    params["sign"] = generate_signature("/product/202309/products", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/product/202309/products"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(url, params=params, data=body_string, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def test_product_api_v2():
    access_token = get_access_token()
    print("\n=== 测试商品API (列表) ===")
    
    timestamp = str(int(time.time()))
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "shop_id": shop_id,
        "sign_method": "sha256",
        "page_no": 1,
        "page_size": 10,
    }
    
    body_string = ""
    params["sign"] = generate_signature("/product/202309/products", params, body_string)
    
    url = f"{TIKTOK_PARTNER_API_BASE_URL}/product/202309/products"
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

def main():
    print("=" * 80)
    print("TikTok API 详细调试")
    print("=" * 80)
    
    test_order_search_v6()
    test_order_search_v5()
    test_shop_api()
    
    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
