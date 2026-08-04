"""检查授权的店铺列表,确认 shop_cipher 对应的店铺是否正确。"""
import sys
import os
import time
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

import requests
from app.services.tk_token_manager import get_access_token
from app.core.config import settings
import hashlib
import hmac

BASE = "https://open-api.tiktokglobalshop.com"
app_key = settings.tk_partner_app_key
app_secret = settings.tk_partner_app_secret
shop_id = settings.tk_auth_shop_id

access_token = get_access_token()
print(f"app_key: {app_key}")
print(f"配置的 shop_id: {shop_id}")
print(f"access_token: {access_token[:20]}...")

# 获取授权的店铺列表
api_path = "/authorization/202309/shops"
params = {
    "app_key": app_key,
    "timestamp": str(int(time.time())),
    "sign_method": "sha256",
}

# 签名
filtered = {k: v for k, v in params.items() if k != "sign"}
sign_string = api_path
for key in sorted(filtered):
    sign_string += f"{key}{filtered[key]}"
sign_string = app_secret + sign_string + app_secret
sign = hmac.new(app_secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
params["sign"] = sign

headers = {
    "x-tts-access-token": access_token,
    "Content-Type": "application/json",
}

print(f"\n--- 调用 {api_path} 获取授权店铺列表 ---")
resp = requests.get(f"{BASE}{api_path}", params=params, headers=headers, timeout=30)
print(f"状态码: {resp.status_code}")
result = resp.json()
print(f"返回: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

# 分析返回的店铺
if result.get("code") == 0:
    shops = result.get("data", {}).get("shops", [])
    print(f"\n授权的店铺数量: {len(shops)}")
    for i, shop in enumerate(shops):
        print(f"\n店铺 {i+1}:")
        print(f"  id: {shop.get('id')}")
        print(f"  cipher: {shop.get('cipher')}")
        print(f"  name: {shop.get('name')}")
        print(f"  region: {shop.get('region')}")
        print(f"  seller_type: {shop.get('seller_type')}")
        print(f"  status: {shop.get('status')}")
        print(f"  create_time: {shop.get('create_time')}")
        if shop.get('create_time'):
            ts = int(shop['create_time'])
            if ts > 1e12:
                ts //= 1000
            from datetime import datetime
            print(f"  create_time (格式化): {datetime.fromtimestamp(ts)}")
