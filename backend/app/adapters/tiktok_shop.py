"""TikTok Shop 全球店铺 Partner API 适配器。

职责：从 TikTok Shop 开放平台拉取订单/商品，归一化为 StandardOrder / StandardProduct
ORM 落库，供 Dashboard 看板与 AI 工具聚合查询。

依赖：app_key / app_secret / 已授权的 shop_id / access_token（见 tk_token_manager）。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal
from app.models.standard import (
    OrderStatus,
    Platform,
    StandardOrder,
    StandardProduct,
)
from app.services.tk_token_manager import get_access_token

logger = logging.getLogger(__name__)

TIKTOK_PARTNER_API_BASE_URL = "https://open-api.tiktokglobalshop.com"


# ----------------------------- 签名 & 请求 -----------------------------
class TikTokShopPartnerAPI:
    """封装 TikTok Shop Partner API 的签名、分页、调用。"""

    def __init__(self) -> None:
        self.app_key = settings.tk_partner_app_key
        self.app_secret = settings.tk_partner_app_secret
        self.auth_shop_id = settings.tk_auth_shop_id
        self._shop_cipher: Optional[str] = None

    # ---- shop_cipher 缓存 ----
    def _get_shop_cipher(self) -> Optional[str]:
        if self._shop_cipher:
            return self._shop_cipher
        access_token = get_access_token()
        if not access_token:
            return None

        api_path = "/authorization/202309/shops"
        params: Dict[str, str] = {
            "app_key": self.app_key,
            "timestamp": str(int(time.time())),
            "sign_method": "sha256",
        }
        params["sign"] = self._sign(api_path, params, "")

        try:
            resp = requests.get(
                f"{TIKTOK_PARTNER_API_BASE_URL}{api_path}",
                params=params,
                headers=self._headers(access_token),
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                shops = result.get("data", {}).get("shops", [])
                if shops:
                    self._shop_cipher = shops[0].get("cipher")
                    return self._shop_cipher
            logger.error(f"Get shop cipher failed: {result.get('code')} {result.get('message')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Get shop cipher request failed: {e}")
        return None

    def _headers(self, access_token: str) -> Dict[str, str]:
        return {
            "x-tts-access-token": access_token,
            "Content-Type": "application/json",
        }

    def _sign(self, api_path: str, params: Dict[str, str], body_str: str = "") -> str:
        """TikTok Partner API 签名：app_secret + path + sorted(params) + body + app_secret"""
        filtered = {k: v for k, v in params.items() if k != "sign"}
        sign_string = api_path
        for key in sorted(filtered):
            sign_string += f"{key}{filtered[key]}"
        if body_str:
            sign_string += body_str
        sign_string = self.app_secret + sign_string + self.app_secret
        return hmac.new(
            self.app_secret.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _make_request(
        self,
        method: str,
        api_path: str,
        data: Optional[Dict] = None,
        send_as_body: bool = False,
    ) -> Dict:
        if not self.app_key or not self.app_secret or not self.auth_shop_id:
            logger.error("TikTok Shop Partner API credentials not configured")
            return {}
        access_token = get_access_token()
        if not access_token:
            logger.error("No valid TikTok access token")
            return {}
        shop_cipher = self._get_shop_cipher()
        if not shop_cipher:
            logger.error("Failed to get shop cipher")
            return {}

        params: Dict[str, str] = {
            "app_key": self.app_key,
            "timestamp": str(int(time.time())),
            "shop_id": self.auth_shop_id,
            "shop_cipher": shop_cipher,
            "sign_method": "sha256",
        }

        body_str = ""
        if data and send_as_body:
            # 签名用的 body 串必须与实际发送的字节完全一致
            body_str = json.dumps(data, separators=(",", ":"))
        elif data:
            for k, v in data.items():
                params[k] = str(v)

        params["sign"] = self._sign(api_path, params, body_str)
        url = f"{TIKTOK_PARTNER_API_BASE_URL}{api_path}"

        try:
            logger.info(f"Calling TikTok Partner API: {method} {api_path}")
            if method.upper() == "GET":
                resp = requests.get(url, params=params, headers=self._headers(access_token), timeout=30)
            else:
                if send_as_body and body_str:
                    # 用 data= 发送原始字符串，保证与签名一致
                    resp = requests.post(
                        url,
                        params=params,
                        data=body_str,
                        headers=self._headers(access_token),
                        timeout=30,
                    )
                else:
                    resp = requests.post(
                        url, params=params, data="", headers=self._headers(access_token), timeout=30
                    )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                logger.error(
                    f"TikTok Partner API error: code={result.get('code')}, message={result.get('message')}"
                )
                return {}
            return result.get("data", {}) or {}
        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok Partner API request failed: {e}")
            return {}

    # ----------------------------- 业务拉取 -----------------------------
    def fetch_orders(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict]:
        """拉取订单列表。

        关键：TikTok 202309 orders/search 接口分页必须用 **page_token** 参数
        （不是 next_page_token）。API 返回的翻页游标字段名叫 next_page_token，
        但请求时传给 API 的参数名是 page_token。用 next_page_token 请求会被
        API 静默忽略，每次都返回第一页。

        另外，create_time_from/to 时间过滤参数对该接口也不生效（API 会忽略
        时间条件，按 create_time 升序返回全部订单），所以这里不再传时间参数，
        而是拉全量后在 Python 侧按 start_date/end_date 过滤。
        """
        if start_date is None:
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # 关键：start_date/end_date 按 UTC 解释，与 TikTok 后台口径一致
        t_from = int(
            datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        )
        t_to = int(
            datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        ) + 86399

        all_orders: List[Dict] = []
        page_size = 100
        page_token: Optional[str] = None
        page_no = 1
        max_pages = 500  # 安全上限：500 页 = 50000 单
        while page_no <= max_pages:
            data: Dict[str, Any] = {"page_size": page_size}
            if page_token:
                # 关键：用 page_token 而非 next_page_token
                data["page_token"] = page_token
            else:
                data["page_no"] = 1
            result = self._make_request("POST", "/order/202309/orders/search", data)
            if not result:
                break
            orders = result.get("orders", [])
            # API 返回的游标字段名是 next_page_token
            page_token = result.get("next_page_token")
            logger.info(
                f"Fetched page {page_no}: {len(orders)} orders, page_token={'yes' if page_token else 'no'}"
            )
            # 本地按时间过滤（API 时间过滤不生效）
            for o in orders:
                ct = o.get("create_time") or o.get("paid_time")
                if ct:
                    ts = int(ct)
                    if ts > 1_000_000_000_000:
                        ts //= 1000
                    if t_from <= ts <= t_to:
                        all_orders.append(o)
                else:
                    all_orders.append(o)
            # 停止条件：无下一页 token 或本页为空
            if not page_token or not orders:
                break
            page_no += 1
        logger.info(
            f"fetch_orders done: pages={page_no}, matched={len(all_orders)} "
            f"(filter {start_date} ~ {end_date})"
        )
        return all_orders

    def fetch_order_detail(self, order_id: str) -> Dict:
        """拉取单笔订单详情（含商品行项目）。"""
        data = {"order_id": order_id}
        return self._make_request("POST", "/order/202309/orders/detail", data)

    def fetch_products(self) -> List[Dict]:
        """拉取商品列表。与 fetch_orders 同理，分页用 page_token。"""
        all_products: List[Dict] = []
        page_size = 100
        page_token: Optional[str] = None
        page_no = 1
        max_pages = 500
        while page_no <= max_pages:
            data: Dict[str, Any] = {"page_size": page_size}
            if page_token:
                data["page_token"] = page_token
            else:
                data["page_no"] = 1
            result = self._make_request("POST", "/product/202309/products/search", data)
            if not result:
                break
            products = result.get("products", [])
            page_token = result.get("next_page_token")
            logger.info(
                f"Fetched products page {page_no}: {len(products)} items, token={'yes' if page_token else 'no'}"
            )
            all_products.extend(products)
            if not page_token or not products:
                break
            page_no += 1
        return all_products


# ----------------------------- 字段映射 -----------------------------
def _parse_tiktok_datetime(value: Any) -> Optional[datetime]:
    """把 TikTok 返回的时间值解析为 naive datetime（统一按 UTC 存，与 TK 后台对齐）。

    TikTok API 的 create_time / paid_time 等都是 UTC 秒级时间戳。
    旧代码用 datetime.fromtimestamp(ts) 在本地时区机器上会得到本地墙钟时间，
    导致数据库里存的时间比 UTC 早 8 小时，与 TikTok 后台口径错位。
    现统一存 UTC naive datetime，看板统计也按 UTC 算窗口。
    """
    if not value:
        return None
    s = str(value).strip()
    if s.isdigit():
        try:
            ts = int(s)
            if ts > 1_000_000_000_000:  # 毫秒
                ts //= 1000
            # 用 UTC 解释时间戳，去掉 tzinfo 存为 naive（DB 无时区）
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        except (ValueError, OSError):
            return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _norm_status(raw: Any) -> OrderStatus:
    """TikTok 订单状态枚举归一到内部 OrderStatus。"""
    s = str(raw or "").lower()
    mapping = {
        "unpaid": OrderStatus.PAID,
        "on_hold": OrderStatus.PAID,
        "awaiting_shipment": OrderStatus.PAID,
        "awaiting_collection": OrderStatus.PAID,
        "in_transit": OrderStatus.SHIPPED,
        "delivered": OrderStatus.COMPLETED,
        "completed": OrderStatus.COMPLETED,
        "cancelled": OrderStatus.REFUNDED,
        "refund": OrderStatus.REFUNDED,
        "refunded": OrderStatus.REFUNDED,
    }
    return mapping.get(s, OrderStatus.PAID)


def map_tiktok_order(raw_order: Dict[str, Any]) -> Dict[str, Any]:
    """把 TikTok 原始订单映射为 StandardOrder 字段。

    TikTok 202309 orders/search 返回的 order 含 line_items / status / create_time 等。
    """
    line_items = raw_order.get("line_items") or raw_order.get("items") or []
    first = line_items[0] if line_items else {}

    order_id = str(raw_order.get("id") or raw_order.get("order_id") or "")
    product_id = str(first.get("product_id") or raw_order.get("product_id") or "")
    product_name = (
        first.get("product_name")
        or raw_order.get("product_name")
        or first.get("sku_name")
        or product_id
        or "未知商品"
    )

    # GMV：优先 payment.total_amount，其次 line_items 汇总 sale_price*quantity
    payment = raw_order.get("payment") or {}
    gmv = float(
        payment.get("total_amount")
        or payment.get("original_total_product_price")
        or raw_order.get("total_amount")
        or raw_order.get("order_amount")
        or 0
    )
    if gmv == 0 and line_items:
        gmv = sum(
            float(it.get("sale_price") or 0) * int(it.get("quantity") or 1)
            for it in line_items
        )

    quantity = int(
        sum(int(it.get("quantity") or 1) for it in line_items)
        if line_items
        else (raw_order.get("quantity") or first.get("quantity") or 1)
    )

    # 状态：line_items[0].display_status 优先，其次 order 级 status
    raw_status = (
        first.get("display_status")
        or raw_order.get("status")
        or raw_order.get("order_status")
    )
    norm_status = _norm_status(raw_status)

    # 已取消/已退款的订单不计入 GMV（TikTok API 返回的 payment.total_amount 仍含金额）
    if norm_status == OrderStatus.REFUNDED:
        gmv = 0.0

    return {
        "order_id": order_id,
        "shop_id": settings.tk_auth_shop_id or None,
        "platform": Platform.TIKTOK,
        "product_id": product_id,
        "product_name": str(product_name)[:255],
        "gmv": round(gmv, 2),
        "quantity": quantity,
        "customer_id": str(raw_order.get("buyer_email") or raw_order.get("user_id") or raw_order.get("customer_id") or "") or None,
        "creator_id": str(
            raw_order.get("creator_id") or raw_order.get("influencer_id") or ""
        ) or None,
        "status": norm_status,
        "paid_at": _parse_tiktok_datetime(
            raw_order.get("paid_time") or raw_order.get("create_time") or raw_order.get("order_create_time")
        ),
        "province": _extract_province(raw_order),
        # —— 扩展字段：充分利用 API 返回数据 ——
        "sku_id": str(first.get("sku_id") or "") or None,
        "seller_sku": str(first.get("seller_sku") or "") or None,
        "sku_name": str(first.get("sku_name") or "")[:255] or None,
        "currency": str(payment.get("currency") or first.get("currency") or "") or None,
        "original_price": float(first.get("original_price") or payment.get("original_total_product_price") or 0) or None,
        "platform_discount": float(payment.get("platform_discount") or 0) or None,
        "seller_discount": float(payment.get("seller_discount") or 0) or None,
        "shipping_fee": float(payment.get("shipping_fee") or payment.get("original_shipping_fee") or 0) or None,
        "is_cod": bool(raw_order.get("is_cod") or False),
        "is_sample_order": bool(raw_order.get("is_sample_order") or False),
        "delivery_type": str(raw_order.get("delivery_type") or "") or None,
        "shipping_provider": str(raw_order.get("shipping_provider") or "") or None,
        "tracking_number": str(raw_order.get("tracking_number") or first.get("tracking_number") or "") or None,
        "rts_time": _parse_tiktok_datetime(raw_order.get("rts_time")),
        "delivery_time": _parse_tiktok_datetime(raw_order.get("delivery_time")),
        "update_time": _parse_tiktok_datetime(raw_order.get("update_time")),
    }


def _extract_province(raw_order: Dict[str, Any]) -> Optional[str]:
    """从 recipient_address.district_info 提取省份（TK 202309 字段结构）。"""
    addr = raw_order.get("recipient_address") or raw_order.get("shipping_address") or {}
    # 优先从 district_info 找 province level
    district_info = addr.get("district_info") or []
    for d in district_info:
        if d.get("address_level_name") == "province":
            return str(d.get("address_name") or "")[:32] or None
    # fallback
    return str(addr.get("region") or addr.get("province") or "")[:32] or None


def map_tiktok_product(raw_product: Dict[str, Any]) -> Dict[str, Any]:
    """把 TikTok 原始商品映射为 StandardProduct 字段。"""
    cats = raw_product.get("categories") or raw_product.get("recommended_categories") or []
    category_name = cats[-1].get("name") if cats and isinstance(cats[-1], dict) else (
        raw_product.get("category") or raw_product.get("category_name")
    )
    # price 在 skus[0].price.tax_exclusive_price（TK 202309 products 结构）
    price = 0.0
    skus = raw_product.get("skus") or []
    if skus and isinstance(skus[0], dict):
        sku_price = skus[0].get("price") or {}
        try:
            price = float(
                sku_price.get("tax_exclusive_price")
                or sku_price.get("original_price")
                or sku_price.get("price")
                or 0
            )
        except (ValueError, TypeError):
            price = 0.0
    if price == 0:
        try:
            price = float(raw_product.get("price") or raw_product.get("original_price") or 0)
        except (ValueError, TypeError):
            price = 0.0

    return {
        "product_id": str(raw_product.get("product_id") or raw_product.get("id") or ""),
        "platform": Platform.TIKTOK,
        "name": str(
            raw_product.get("product_name")
            or raw_product.get("title")
            or raw_product.get("name")
            or ""
        )[:255],
        "category": str(category_name or "")[:64] or None,
        "price": price,
        "total_gmv": 0.0,
        "total_sold": int(
            raw_product.get("sales_volume")
            or raw_product.get("sold_count")
            or raw_product.get("sales")
            or 0
        ),
    }


# ----------------------------- 落库 -----------------------------
def _upsert_order(db: Session, data: Dict[str, Any]) -> str:
    """订单 upsert：按 (order_id, platform) 唯一键。返回 inserted/updated/skipped 之一。"""
    order_id = data.get("order_id")
    if not order_id:
        return "skipped"
    existing = (
        db.query(StandardOrder)
        .filter(StandardOrder.order_id == order_id, StandardOrder.platform == Platform.TIKTOK)
        .first()
    )
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        return "updated"
    db.add(StandardOrder(**data))
    return "inserted"


def _upsert_product(db: Session, data: Dict[str, Any]) -> str:
    product_id = data.get("product_id")
    if not product_id:
        return "skipped"
    existing = (
        db.query(StandardProduct)
        .filter(StandardProduct.product_id == product_id, StandardProduct.platform == Platform.TIKTOK)
        .first()
    )
    if existing:
        for k, v in data.items():
            if k != "total_gmv":  # GMV 由订单聚合，不覆盖
                setattr(existing, k, v)
        return "updated"
    db.add(StandardProduct(**data))
    return "inserted"


def _aggregate_product_gmv(db: Session) -> int:
    """按 product_id 聚合 TikTok 订单的 total_gmv / total_sold，回写到 StandardProduct。

    聚合规则：platform='tiktok' 且 status != REFUNDED 的订单参与汇总。
    回写时只更新已存在的 StandardProduct 记录，找不到则跳过（不自动创建）。
    返回成功更新的记录数。
    """
    stmt = (
        select(
            StandardOrder.product_id.label("product_id"),
            func.coalesce(func.sum(StandardOrder.gmv), 0.0).label("total_gmv"),
            func.coalesce(func.sum(StandardOrder.quantity), 0).label("total_sold"),
        )
        .where(
            StandardOrder.platform == Platform.TIKTOK,
            StandardOrder.status != OrderStatus.REFUNDED,
        )
        .group_by(StandardOrder.product_id)
    )
    rows = db.execute(stmt).all()
    updated = 0
    for r in rows:
        product = (
            db.query(StandardProduct)
            .filter(
                StandardProduct.product_id == r.product_id,
                StandardProduct.platform == Platform.TIKTOK,
            )
            .first()
        )
        if not product:
            continue
        product.total_gmv = round(float(r.total_gmv), 2)
        product.total_sold = int(r.total_sold)
        updated += 1
    db.commit()
    return updated


def sync_tiktok_orders(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, int]:
    api = TikTokShopPartnerAPI()
    db = SessionLocal()
    try:
        orders = api.fetch_orders(start_date, end_date)
        if not orders:
            logger.warning("No orders fetched from TikTok Shop Partner API")
            return {"total_fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

        inserted = updated = skipped = 0
        for raw in orders:
            result = _upsert_order(db, map_tiktok_order(raw))
            if result == "inserted":
                inserted += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1
            if (inserted + updated) % 50 == 0:
                db.commit()
        db.commit()
        logger.info(
            f"Order sync done: fetched={len(orders)}, inserted={inserted}, updated={updated}, skipped={skipped}"
        )
        # 订单同步完成后，按 product_id 聚合 GMV/销量 回写到 StandardProduct
        agg_updated = _aggregate_product_gmv(db)
        logger.info(f"Product GMV aggregation done: updated={agg_updated}")
        return {"total_fetched": len(orders), "inserted": inserted, "updated": updated, "skipped": skipped}
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

        inserted = updated = skipped = 0
        for raw in products:
            result = _upsert_product(db, map_tiktok_product(raw))
            if result == "inserted":
                inserted += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1
            if (inserted + updated) % 50 == 0:
                db.commit()
        db.commit()
        logger.info(
            f"Product sync done: fetched={len(products)}, inserted={inserted}, updated={updated}, skipped={skipped}"
        )
        return {"total_fetched": len(products), "inserted": inserted, "updated": updated, "skipped": skipped}
    except Exception as e:
        db.rollback()
        logger.error(f"Product sync failed: {e}")
        raise
    finally:
        db.close()


def sync_tiktok_data(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Dict[str, int]]:
    """同步订单 + 商品。"""
    logger.info("Starting TikTok Shop Partner API data sync...")
    return {
        "orders": sync_tiktok_orders(start_date, end_date),
        "products": sync_tiktok_products(),
    }
