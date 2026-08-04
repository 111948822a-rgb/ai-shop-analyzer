"""测试旧版 API 端点和不同的查询参数组合。"""
import sys
import os
import time
import json
from datetime import datetime

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

# 获取 shop_cipher
from app.adapters.tiktok_shop import TikTokShopPartnerAPI
api = TikTokShopPartnerAPI()
shop_cipher = api._get_shop_cipher()
print(f"shop_cipher: {shop_cipher}")

def sign_v2(path, params, body_str=""):
    """旧版 v2 API 用 MD5 签名。"""
    filtered = {k: v for k, v in params.items() if k != "sign" and k != "access_token"}
    sign_string = path
    for key in sorted(filtered):
        sign_string += f"{key}{filtered[key]}"
    if body_str:
        sign_string += body_str
    sign_string = app_secret + sign_string + app_secret
    return hashlib.md5(sign_string.encode()).hexdigest().upper()

# 测试 1: 202309 API 带按 status 过滤 (只查 IN_TRANSIT 等近期状态)
print("\n=== 测试1: 202309 API 按订单状态过滤 (PARTIAL_CANCELING / IN_TRANSIT) ===")
for status in ["IN_TRANSIT", "DELIVERED", "COMPLETED", "AWAITING_SHIPMENT", "AWAITING_COLLECTION"]:
    data = {"page_no": 1, "page_size": 10, "order_status": status}
    result = api._make_request("POST", "/order/202309/orders/search", data)
    orders = result.get("orders", []) if result else []
    print(f"  status={status}: {len(orders)} 单")

# 测试 2: 尝试 202401 版本 API
print("\n=== 测试2: 尝试 /order/202401/orders/search ===")
data = {"page_no": 1, "page_size": 10}
result = api._make_request("POST", "/order/202401/orders/search", data)
if result:
    orders = result.get("orders", [])
    print(f"  返回订单数: {len(orders)}")
else:
    print(f"  无返回 (可能版本不存在)")

# 测试 3: 用旧版 v2 API
print("\n=== 测试3: 旧版 /api/v2/orders/search ===")
api_path = "/api/v2/orders/search"
params = {
    "app_key": app_key,
    "timestamp": str(int(time.time())),
    "shop_id": shop_id,
    "sign_method": "md5",
    "access_token": access_token,
}
# v2 旧版用 create_time 字符串格式
data_params = {
    "page_no": 1,
    "page_size": 10,
    "create_time_from": "2026-07-01 00:00:00",
    "create_time_to": "2026-07-31 23:59:59",
}
for k, v in data_params.items():
    params[k] = str(v)
params["sign"] = sign_v2(api_path, params)

headers = {
    "x-tts-access-token": access_token,
    "Content-Type": "application/json",
}
try:
    resp = requests.get(f"{BASE}{api_path}", params=params, headers=headers, timeout=30)
    print(f"  状态码: {resp.status_code}")
    print(f"  返回: {resp.text[:500]}")
except Exception as e:
    print(f"  异常: {e}")

# 测试 4: 检查订单的 update_time 范围(看是否有近期更新的订单)
print("\n=== 测试4: 检查已拉取订单的 update_time 范围 ===")
from collections import Counter
data = {"page_no": 1, "page_size": 100}
result = api._make_request("POST", "/order/202309/orders/search", data)
if result:
    orders = result.get("orders", [])
    update_months = Counter()
    for o in orders:
        ut = o.get("update_time")
        if ut:
            ts = int(ut) // 1000 if int(ut) > 1e12 else int(ut)
            update_months[datetime.fromtimestamp(ts).strftime("%Y-%m")] += 1
    print(f"  update_time 按月分布: {dict(update_months)}")
    # 看看 update_time 最晚的订单
    max_ut = max((o.get("update_time", 0) for o in orders), default=0)
    if max_ut:
        ts = int(max_ut) // 1000 if int(max_ut) > 1e12 else int(max_ut)
        print(f"  最晚 update_time: {datetime.fromtimestamp(ts)}")
