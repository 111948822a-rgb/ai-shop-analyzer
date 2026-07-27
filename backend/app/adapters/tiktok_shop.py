import logging
import hashlib
import hmac
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import requests

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.standard import StandardOrder, StandardProduct, StandardInfluencer
from app.services.tk_token_manager import get_access_token

logger = logging.getLogger(__name__)

TIKTOK_PARTNER_API_BASE_URL = "https://open-api.tiktokglobalshop.com"


class TikTokShopPartnerAPI:
    def __init__(self):
        self.app_key = settings.TK_PARTNER_APP_KEY
        self.app_secret = settings.TK_PARTNER_APP_SECRET
        self.auth_shop_id = settings.TK_AUTH_SHOP_ID
        self._shop_cipher = None

    def _get_shop_cipher(self) -> Optional[str]:
        if self._shop_cipher:
            return self._shop_cipher

        access_token = get_access_token()
        if not access_token:
            return None

        timestamp = str(int(time.time()))
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
        }

        sign_string = "/authorization/202309/shops"
        for key, value in sorted(params.items()):
            if key != "sign" and key != "access_token":
                sign_string += f"{key}{value}"
        sign_string = self.app_secret + sign_string + self.app_secret

        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        params["sign"] = signature

        url = f"{TIKTOK_PARTNER_API_BASE_URL}/authorization/202309/shops"
        headers = {
            "x-tts-access-token": access_token,
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                shops = result.get("data", {}).get("shops", [])
                if shops:
                    self._shop_cipher = shops[0].get("cipher")
                    return self._shop_cipher
        except Exception as e:
            logger.error(f"Failed to fetch shop cipher: {e}")

        return None

    def _generate_signature(self, api_path: str, params: Dict[str, str], body_str: str = "") -> str:
        filtered_params = {k: v for k, v in params.items() if k != "sign"}
        sorted_params = sorted(filtered_params.items())

        sign_string = api_path
        for key, value in sorted_params:
            sign_string += f"{key}{value}"
        
        if body_str:
            sign_string += body_str

        sign_string = self.app_secret + sign_string + self.app_secret

        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _make_request(self, method: str, api_path: str, data: Optional[Dict] = None, send_as_body: bool = False) -> Dict:
        if not self.app_key or not self.app_secret or not self.auth_shop_id:
            logger.error("TikTok Shop Partner API credentials are not configured")
            return {}

        access_token = get_access_token()
        if not access_token:
            logger.error("No valid TikTok access token available")
            return {}

        shop_cipher = self._get_shop_cipher()
        if not shop_cipher:
            logger.error("Failed to get shop cipher")
            return {}

        timestamp = str(int(time.time()))
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.auth_shop_id,
            "shop_cipher": shop_cipher,
            "sign_method": "sha256",
        }

        body_str = ""
        if data and send_as_body:
            body_str = json.dumps(data, separators=(',', ':'))
        elif data:
            for key, value in data.items():
                params[key] = str(value)

        params["sign"] = self._generate_signature(api_path, params, body_str)

        url = f"{TIKTOK_PARTNER_API_BASE_URL}{api_path}"
        headers = {
            "x-tts-access-token": access_token,
            "Content-Type": "application/json",
        }

        try:
            logger.info(f"Calling TikTok Partner API: {method} {api_path}")
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            else:
                if send_as_body and body_str:
                    response = requests.post(url, params=params, json=data, headers=headers, timeout=30)
                else:
                    response = requests.post(url, params=params, data="", headers=headers, timeout=30)

            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                logger.error(f"TikTok Partner API error: code={result.get('code')}, message={result.get('message')}")
                return {}

            return result.get("data", {})

        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok Partner API request failed: {e}")
            try:
                if response:
                    logger.error(f"Response content: {response.text[:500]}")
            except:
                pass
            return {}

    def fetch_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        all_orders = []
        page_no = 1
        page_size = 100

        while True:
            data = {
                "page_no": page_no,
                "page_size": page_size,
                "create_time_from": f"{start_date} 00:00:00",
                "create_time_to": f"{end_date} 23:59:59",
            }

            result = self._make_request("POST", "/order/202309/orders/search", data)

            if not result:
                break

            orders = result.get("orders", [])
            total = result.get("total", 0)

            logger.info(f"Fetched page {page_no}: {len(orders)} orders, total {total}")
            all_orders.extend(orders)

            if len(all_orders) >= total:
                break

            if not orders:
                break

            page_no += 1

        return all_orders

    def fetch_order_details(self, order_id: str) -> Dict:
        data = {"order_id": order_id}
        return self._make_request("GET", "/api/v2/order/detail", data)

    def fetch_products(self) -> List[Dict]:
        all_products = []
        page_no = 1
        page_size = 100

        while True:
            data = {
                "page_no": page_no,
                "page_size": page_size,
            }

            result = self._make_request("POST", "/product/202309/products/query", data)

            if not result:
                break

            products = result.get("products", [])
            total = result.get("total", 0)

            logger.info(f"Fetched page {page_no}: {len(products)} products, total {total}")
            all_products.extend(products)

            if len(all_products) >= total:
                break

            if not products:
                break

            page_no += 1

        return all_products

    def fetch_product_detail(self, product_id: str) -> Dict:
        data = {"product_id": product_id}
        return self._make_request("GET", "/api/v2/product/detail", data)



    def fetch_affiliate_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        all_orders = []
        page_no = 1
        page_size = 100

        while True:
            data = {
                "page_no": page_no,
                "page_size": page_size,
                "start_date": start_date,
                "end_date": end_date,
            }

            result = self._make_request("GET", "/api/v2/affiliate/order/list", data)

            if not result:
                break

            orders = result.get("orders", []) or result.get("items", [])
            total = result.get("total", 0)

            logger.info(f"Fetched page {page_no}: {len(orders)} affiliate orders, total {total}")
            all_orders.extend(orders)

            if len(all_orders) >= total:
                break

            if not orders:
                break

            page_no += 1

        return all_orders

    def fetch_shop_performance(self, start_date: str, end_date: str) -> Dict:
        data = {
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._make_request("GET", "/api/v2/shop/performance", data)


def map_tiktok_order(raw_order: Dict[str, Any]) -> Dict[str, Any]:
    items = raw_order.get("line_items", raw_order.get("items", []))
    first_item = items[0] if items else {}

    return {
        "order_id": str(raw_order.get("order_id") or raw_order.get("id") or ""),
        "site_code": raw_order.get("region") or raw_order.get("site") or raw_order.get("region_code") or "TH",
        "currency": raw_order.get("currency") or raw_order.get("currency_code") or "THB",
        "product_id": str(first_item.get("product_id") or raw_order.get("product_id") or ""),
        "influencer_id": raw_order.get("creator_id") or raw_order.get("influencer_id") or "",
        "order_amount": float(raw_order.get("order_amount") or raw_order.get("amount") or raw_order.get("total_amount") or first_item.get("sale_price") or 0),
        "order_amount_local": float(raw_order.get("order_amount_local") or raw_order.get("local_amount") or 0),
        "quantity": int(raw_order.get("quantity") or first_item.get("quantity") or 1),
        "order_status": raw_order.get("status") or raw_order.get("order_status") or "pending",
        "order_date": _parse_tiktok_datetime(raw_order.get("create_time") or raw_order.get("order_create_time")) or datetime.now(),
        "customer_id": raw_order.get("customer_id") or raw_order.get("buyer_id") or "",
    }


def map_tiktok_product(raw_product: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_id": str(raw_product.get("product_id") or raw_product.get("id") or ""),
        "site_code": raw_product.get("region") or raw_product.get("site") or raw_product.get("region_code") or "TH",
        "currency": raw_product.get("currency") or raw_product.get("currency_code") or "THB",
        "product_name": raw_product.get("product_name") or raw_product.get("name") or "",
        "product_category": raw_product.get("category") or raw_product.get("category_name") or raw_product.get("product_category") or "",
        "product_price": float(raw_product.get("price") or raw_product.get("original_price") or raw_product.get("product_price") or 0),
        "product_price_local": float(raw_product.get("price_local") or raw_product.get("local_price") or 0),
        "stock_quantity": int(raw_product.get("stock") or raw_product.get("stock_quantity") or 0),
        "sales_volume": int(raw_product.get("sales_volume") or raw_product.get("sales") or raw_product.get("sold_count") or 0),
        "rating": float(raw_product.get("rating") or raw_product.get("product_rating") or 0),
        "review_count": int(raw_product.get("review_count") or raw_product.get("reviews") or 0),
        "image_url": raw_product.get("image_url") or raw_product.get("cover_image") or raw_product.get("main_image_url") or "",
        "brand": raw_product.get("brand") or "",
    }


def _parse_tiktok_datetime(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None

    date_str = str(date_str).strip()

    if date_str.isdigit():
        try:
            timestamp = int(date_str)
            if timestamp > 1000000000000:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp)
        except ValueError:
            pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def sync_tiktok_orders(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, int]:
    api = TikTokShopPartnerAPI()
    db = SessionLocal()

    try:
        orders = api.fetch_orders(start_date, end_date)

        if not orders:
            logger.warning("No orders fetched from TikTok Shop Partner API")
            return {"total_fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

        inserted = 0
        updated = 0
        skipped = 0

        for raw_order in orders:
            mapped_data = map_tiktok_order(raw_order)
            order_id = mapped_data.get("order_id")

            if not order_id:
                skipped += 1
                continue

            existing = db.query(StandardOrder).filter(
                StandardOrder.order_id == order_id
            ).first()

            if existing:
                for key, value in mapped_data.items():
                    if key != "order_id":
                        setattr(existing, key, value)
                updated += 1
            else:
                order = StandardOrder(**mapped_data)
                db.add(order)
                inserted += 1

            if (inserted + updated) % 50 == 0:
                db.commit()
                logger.info(f"Committed {inserted + updated} order records...")

        db.commit()

        logger.info(f"Order sync completed: fetched={len(orders)}, inserted={inserted}, updated={updated}, skipped={skipped}")

        return {
            "total_fetched": len(orders),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Order sync failed: {e}")
        raise
    finally:
        db.close()


def sync_tiktok_products() -> Dict[str, int]:
    api = TikTokShopPartnerAPI()
    db = SessionLocal()

    try:
        products = api.fetch_products()

        if not products:
            logger.warning("No products fetched from TikTok Shop Partner API")
            return {"total_fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

        inserted = 0
        updated = 0
        skipped = 0

        for raw_product in products:
            mapped_data = map_tiktok_product(raw_product)
            product_id = mapped_data.get("product_id")

            if not product_id:
                skipped += 1
                continue

            existing = db.query(StandardProduct).filter(
                StandardProduct.product_id == product_id
            ).first()

            if existing:
                for key, value in mapped_data.items():
                    if key != "product_id":
                        setattr(existing, key, value)
                updated += 1
            else:
                product = StandardProduct(**mapped_data)
                db.add(product)
                inserted += 1

            if (inserted + updated) % 50 == 0:
                db.commit()
                logger.info(f"Committed {inserted + updated} product records...")

        db.commit()

        logger.info(f"Product sync completed: fetched={len(products)}, inserted={inserted}, updated={updated}, skipped={skipped}")

        return {
            "total_fetched": len(products),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Product sync failed: {e}")
        raise
    finally:
        db.close()


def sync_tiktok_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Dict]:
    logger.info("Starting TikTok Shop Partner API data sync...")

    order_result = sync_tiktok_orders(start_date, end_date)
    product_result = sync_tiktok_products()

    return {
        "orders": order_result,
        "products": product_result,
    }


def get_tiktok_order_count() -> int:
    db = SessionLocal()
    try:
        return db.query(StandardOrder).count()
    finally:
        db.close()


def get_tiktok_product_count() -> int:
    db = SessionLocal()
    try:
        return db.query(StandardProduct).count()
    finally:
        db.close()
