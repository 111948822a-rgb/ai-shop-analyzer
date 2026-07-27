import logging
import sys
import os
import requests
import hashlib
import hmac
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.tk_token_manager import get_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_shop_cipher(access_token):
    url = "https://open-api.tiktokglobalshop.com/authorization/202309/shops"
    timestamp = str(int(time.time()))
    
    params = {
        "app_key": settings.TK_PARTNER_APP_KEY,
        "timestamp": timestamp,
        "sign_method": "sha256",
    }
    
    sign_string = "/authorization/202309/shops"
    for key, value in sorted(params.items()):
        if key != "sign" and key != "access_token":
            sign_string += f"{key}{value}"
    sign_string = settings.TK_PARTNER_APP_SECRET + sign_string + settings.TK_PARTNER_APP_SECRET
    
    signature = hmac.new(
        settings.TK_PARTNER_APP_SECRET.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["sign"] = signature
    
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                shops = result.get("data", {}).get("shops", [])
                if shops:
                    return shops[0].get("cipher")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    return None


def test_api_get(access_token, shop_cipher, api_path, query_params):
    url = f"https://open-api.tiktokglobalshop.com{api_path}"
    timestamp = str(int(time.time()))
    
    params = {
        "app_key": settings.TK_PARTNER_APP_KEY,
        "timestamp": timestamp,
        "shop_id": settings.TK_AUTH_SHOP_ID,
        "shop_cipher": shop_cipher,
        "sign_method": "sha256",
    }
    
    for key, value in query_params.items():
        params[key] = str(value)
    
    sign_string = api_path
    for key, value in sorted(params.items()):
        if key != "sign":
            sign_string += f"{key}{value}"
    sign_string = settings.TK_PARTNER_APP_SECRET + sign_string + settings.TK_PARTNER_APP_SECRET
    
    signature = hmac.new(
        settings.TK_PARTNER_APP_SECRET.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["sign"] = signature
    
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    logger.info(f"\nTesting GET {api_path}")
    logger.info(f"URL: {url}")
    logger.info(f"Query params: {query_params}")
    logger.info(f"Sign string length: {len(sign_string)}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Content: {response.text[:1500]}")
        
        try:
            result = response.json()
            if result.get("code") == 0:
                products = result.get("data", {}).get("products", [])
                items = result.get("data", {}).get("items", [])
                count = len(products) if products else len(items)
                logger.info(f"✅ SUCCESS! Found {count} items")
                return True, result
        except:
            pass
            
    except Exception as e:
        logger.error(f"Request Error: {e}")
    
    return False, None


def test_api_post(access_token, shop_cipher, api_path, body):
    url = f"https://open-api.tiktokglobalshop.com{api_path}"
    timestamp = str(int(time.time()))
    
    params = {
        "app_key": settings.TK_PARTNER_APP_KEY,
        "timestamp": timestamp,
        "shop_id": settings.TK_AUTH_SHOP_ID,
        "shop_cipher": shop_cipher,
        "sign_method": "sha256",
    }
    
    body_str = json.dumps(body, separators=(',', ':'))
    
    sign_string = api_path
    for key, value in sorted(params.items()):
        if key != "sign":
            sign_string += f"{key}{value}"
    sign_string += body_str
    sign_string = settings.TK_PARTNER_APP_SECRET + sign_string + settings.TK_PARTNER_APP_SECRET
    
    signature = hmac.new(
        settings.TK_PARTNER_APP_SECRET.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["sign"] = signature
    
    headers = {
        "x-tts-access-token": access_token,
        "Content-Type": "application/json",
    }
    
    logger.info(f"\nTesting POST {api_path} with body")
    logger.info(f"URL: {url}")
    logger.info(f"Body: {body_str}")
    logger.info(f"Sign string length: {len(sign_string)}")
    
    try:
        response = requests.post(url, params=params, json=body, headers=headers, timeout=30)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Content: {response.text[:1500]}")
        
        try:
            result = response.json()
            if result.get("code") == 0:
                products = result.get("data", {}).get("products", [])
                items = result.get("data", {}).get("items", [])
                count = len(products) if products else len(items)
                logger.info(f"✅ SUCCESS! Found {count} items")
                return True, result
        except:
            pass
            
    except Exception as e:
        logger.error(f"Request Error: {e}")
    
    return False, None


def main():
    logger.info("=" * 60)
    logger.info("TikTok Shop Partner API Debug - Product API v2")
    logger.info("=" * 60)
    
    access_token = get_access_token()
    if not access_token:
        logger.error("No access token available")
        sys.exit(1)
    
    shop_cipher = get_shop_cipher(access_token)
    logger.info(f"Shop Cipher: {shop_cipher}")
    
    if shop_cipher:
        query_params = {"page_no": 1, "page_size": 10}
        body = {"page_no": 1, "page_size": 10}
        
        test_api_get(access_token, shop_cipher, "/product/202309/products/query", query_params)
        test_api_post(access_token, shop_cipher, "/product/202309/products/query", body)
        
        test_api_get(access_token, shop_cipher, "/product/202309/products/list", query_params)
        test_api_post(access_token, shop_cipher, "/product/202309/products/list", body)
        
        test_api_get(access_token, shop_cipher, "/api/v2/product/list", query_params)
        test_api_post(access_token, shop_cipher, "/api/v2/product/list", body)
        
        test_api_get(access_token, shop_cipher, "/product/202309/product/list", query_params)
        test_api_post(access_token, shop_cipher, "/product/202309/product/list", body)
    
    logger.info("\n" + "=" * 60)
    logger.info("Debug complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
