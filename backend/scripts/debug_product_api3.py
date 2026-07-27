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
from app.core.database import SessionLocal
from app.models.standard import StandardOrder

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


def get_product_ids_from_db():
    db = SessionLocal()
    try:
        product_ids = db.query(StandardOrder.product_id).filter(
            StandardOrder.product_id.isnot(None),
            StandardOrder.product_id != ""
        ).distinct().limit(10).all()
        return [p[0] for p in product_ids]
    finally:
        db.close()


def main():
    logger.info("=" * 60)
    logger.info("TikTok Shop Partner API Debug - Product API v3")
    logger.info("=" * 60)
    
    access_token = get_access_token()
    if not access_token:
        logger.error("No access token available")
        sys.exit(1)
    
    shop_cipher = get_shop_cipher(access_token)
    logger.info(f"Shop Cipher: {shop_cipher}")
    
    if shop_cipher:
        product_ids = get_product_ids_from_db()
        logger.info(f"\nFound {len(product_ids)} unique product IDs in database")
        
        for product_id in product_ids[:5]:
            logger.info(f"\n--- Testing product detail for ID: {product_id} ---")
            
            test_api_get(access_token, shop_cipher, "/product/202309/product/detail", {"product_id": product_id})
            test_api_get(access_token, shop_cipher, "/api/v2/product/detail", {"product_id": product_id})
        
        test_api_get(access_token, shop_cipher, "/product/202309/products/query", {"page_no": 1, "page_size": 10, "product_status": "on_sale"})
        test_api_post(access_token, shop_cipher, "/product/202309/products/query", {"page_no": 1, "page_size": 10, "product_status": "on_sale"})
        
        test_api_get(access_token, shop_cipher, "/product/202309/products/list", {"page_no": 1, "page_size": 10, "product_status": "on_sale"})
        test_api_post(access_token, shop_cipher, "/product/202309/products/list", {"page_no": 1, "page_size": 10, "product_status": "on_sale"})
    
    logger.info("\n" + "=" * 60)
    logger.info("Debug complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
