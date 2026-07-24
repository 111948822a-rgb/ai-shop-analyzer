"""抖店（Douyin / 抖店开放平台）适配器 ETL 骨架。

职责：把抖店开放平台的原始数据清洗为内部 Standard* DTO，并写入 ORM。
本文件覆盖需求要求的四块能力：

1. OAuth 2.0 授权流：构造授权 URL、处理回调 code、换取 access/refresh token。
2. Token 自动刷新：TokenStore 在「即将过期」或「401」时自动用 refresh_token 换新。
3. 数据拉取 + 字段映射：模拟调用 /order/searchList，把抖店复杂 JSON 精准映射到
   StandardOrderDTO（pay_amount→gmv、sku_id→product_id、order_status→status 等）。
4. 容错与重试：遇到 HTTP 429 自动指数退避重试；401 触发 token 刷新后重试。

说明：真实抖店 API 还需 md5 签名（sign）与 access-token 头，生产环境需补全签名计算；
本骨架聚焦「映射 / 刷新 / 重试」三条主线，并保留 demo 模式供无凭证时单测映射。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app.adapters.base import AdapterRegistry, BaseAdapter
from app.models.standard import (
    OrderStatus,
    Platform,
    StandardInfluencerDTO,
    StandardOrder,
    StandardOrderDTO,
    StandardProductDTO,
)

# ----------------------------- 抖店开放平台端点 -----------------------------
AUTH_BASE = "https://open.douyin.com"
API_BASE = "https://openapi-fxg.jinritemai.com"  # 抖店开放平台 API 网关
AUTHORIZE_URL = f"{AUTH_BASE}/platform/oauth/connect/"
TOKEN_URL = f"{AUTH_BASE}/oauth/access_token/"
REFRESH_URL = f"{AUTH_BASE}/oauth/refresh_token/"
ORDER_SEARCH_URL = f"{API_BASE}/order/searchList"

# 抖店 order_status 原始值 → 我们统一的 OrderStatus
DOUYIN_STATUS_MAP: dict[str, OrderStatus] = {
    "PAID": OrderStatus.PAID,                 # 已支付
    "DELIVERING": OrderStatus.SHIPPED,        # 发货中
    "DELIVERED": OrderStatus.SHIPPED,         # 已发货
    "COMPLETED": OrderStatus.COMPLETED,       # 已完成
    "SETTLEMENT": OrderStatus.COMPLETED,      # 已结算
    "REFUND": OrderStatus.REFUNDED,           # 退款
    "PART_REFUND": OrderStatus.REFUNDED,      # 部分退款
    "CANCEL": OrderStatus.REFUNDED,           # 取消（视为退款关闭）
}

# 429 重试参数
MAX_RETRIES = 5
BACKOFF_BASE = 2.0  # 秒，指数退避基数


class TokenExpired(Exception):
    """访问令牌失效，需要刷新。"""


@dataclass
class DouyinToken:
    """一次授权拿到的令牌信息。"""

    access_token: str
    refresh_token: str
    expires_in: int
    open_id: str | None = None
    scope: str | None = None
    obtained_at: float = field(default_factory=time.time)

    @property
    def expires_at(self) -> float:
        return self.obtained_at + self.expires_in

    def is_expiring_soon(self, slack: int = 300) -> bool:
        """是否将在 slack 秒内过期（默认提前 5 分钟刷新）。"""
        return time.time() >= (self.expires_at - slack)


class DouyinTokenStore:
    """Access Token 存储 + 自动刷新。

    生产环境应把令牌落库（按 shop_id / open_id 维度），这里用内存字典做骨架。
    """

    def __init__(self, client_key: str, client_secret: str) -> None:
        self.client_key = client_key
        self.client_secret = client_secret
        self._tokens: dict[str, DouyinToken] = {}  # key: open_id 或 shop_id

    # ---------------- OAuth 2.0 授权流 ----------------
    def build_authorize_url(self, redirect_uri: str, state: str, scope: str = "shop.order") -> str:
        """构造让用户授权的 URL（前端/后端跳转到此地址）。"""
        from urllib.parse import urlencode

        params = {
            "client_key": self.client_key,
            "response_type": "code",
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "prompt": "consent",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def handle_callback(self, code: str) -> DouyinToken:
        """处理授权回调：用 code 换取 access_token / refresh_token。

        抖店返回结构：{"data": {"access_token", "expires_in", "refresh_token",
        "open_id", "scope"}, "err_no": 0, "message": "success"}
        """
        body = self._post_json(
            TOKEN_URL,
            {
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            auth=False,
        )
        token = self._parse_token(body)
        self._tokens[token.open_id or "default"] = token
        return token

    # ---------------- Token 自动刷新 ----------------
    def refresh(self, key: str) -> DouyinToken:
        """用 refresh_token 换新 access_token。"""
        old = self._tokens.get(key)
        if old is None:
            raise KeyError(f"未找到令牌: {key}，请先完成授权")
        body = self._post_json(
            REFRESH_URL,
            {
                "client_key": self.client_key,
                "refresh_token": old.refresh_token,
                "grant_type": "refresh_token",
            },
            auth=False,
        )
        new = self._parse_token(body)
        # 抖店刷新后通常返回新的 refresh_token，需覆盖；否则沿用旧的
        if not new.refresh_token:
            new.refresh_token = old.refresh_token
        self._tokens[key] = new
        return new

    def ensure_valid(self, key: str) -> str:
        """返回可用的 access_token；若即将过期则自动刷新。"""
        tok = self._tokens.get(key)
        if tok is None:
            raise KeyError(f"未找到令牌: {key}，请先完成授权")
        if tok.is_expiring_soon():
            tok = self.refresh(key)
        return tok.access_token

    @staticmethod
    def _parse_token(body: dict) -> DouyinToken:
        data = body.get("data", body)
        if not data.get("access_token"):
            raise RuntimeError(f"换取令牌失败: {body}")
        return DouyinToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_in=int(data.get("expires_in", 86400 * 7)),
            open_id=data.get("open_id"),
            scope=data.get("scope"),
        )

    # ---------------- 定时刷新检查（可接入 Celery beat）----------------
    def refresh_expiring_tokens(self) -> list[str]:
        """检查所有存储的令牌，过期的自动刷新。返回被刷新的 key 列表。

        可在 Celery beat 中每小时调用一次，保证定时任务拉数时 token 始终有效。
        """
        refreshed: list[str] = []
        for key, tok in list(self._tokens.items()):
            if tok.is_expiring_soon():
                self.refresh(key)
                refreshed.append(key)
        return refreshed


class DouyinClient:
    """携带令牌的抖店 API 客户端，封装签名头、429 重试、401 自动刷新。"""

    def __init__(self, store: DouyinTokenStore, token_key: str) -> None:
        self.store = store
        self.token_key = token_key

    def search_orders(self, page: int = 0, size: int = 100, **extra: Any) -> list[dict]:
        """调用 /order/searchList 拉取原始订单列表（含 429 重试 + 401 刷新）。

        真实环境需在 params 中计算 sign=md5(sorted(params)+app_secret) 并带上
        access-token 头；此处以 access-token 头示意，sign 计算留作生产补全点。
        """
        params: dict[str, Any] = {"page": page, "size": size, "order_by": "create_time", **extra}
        return self._request(ORDER_SEARCH_URL, params).get("data", {}).get("orders", [])

    # ---------------- 底层 HTTP（重试 / 刷新）----------------
    def _request(self, url: str, params: dict[str, Any]) -> dict:
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return self._do_http(url, params)
            except TokenExpired:
                # 401：刷新令牌后重试一次（不计入退避）
                self.store.ensure_valid(self.token_key)
                try:
                    return self._do_http(url, params)
                except TokenExpired as e:  # 刷新后仍失效
                    raise RuntimeError("令牌刷新后仍无效，请重新授权") from e
            except _RateLimited as e:
                last_err = e
                wait = min(BACKOFF_BASE**attempt, 30) + (attempt * 0.3)
                time.sleep(wait)  # 限流：指数退避
                continue
        raise RuntimeError(f"请求失败（限流重试耗尽）: {last_err}")

    def _do_http(self, url: str, params: dict[str, Any]) -> dict:
        access_token = self.store.ensure_valid(self.token_key)
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(params).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise TokenExpired() from e
            if e.code == 429:
                raise _RateLimited(f"429 rate limited: {e}") from e
            body = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

    @staticmethod
    def _post_json(url: str, payload: dict, auth: bool = True) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e


class _RateLimited(Exception):
    """内部信号：HTTP 429。"""


# =========================================================================
# 字段映射：抖店原始订单 → StandardOrderDTO
# =========================================================================
def _fen_to_yuan(fen: float | str | None) -> float:
    """抖店金额单位为分，转为元。空值返回 0.0。"""
    if fen is None:
        return 0.0
    return round(float(fen) / 100.0, 2)


def _str_or_none(value: Any) -> str | None:
    """真值转字符串，假值（None / 空串）返回 None。避免 str(None) 变成 'None'。"""
    return str(value) if value else None


def _epoch_to_dt(value: int | str | None) -> datetime | None:
    """时间戳（秒或毫秒）→ datetime(UTC)。空值返回 None。"""
    if value is None:
        return None
    val = int(value)
    if val > 10**12:  # 毫秒
        val = val / 1000.0
    return datetime.fromtimestamp(val, tz=timezone.utc).replace(tzinfo=None)


def map_douyin_order(raw: dict) -> StandardOrderDTO:
    """核心映射：把一条抖店原始订单精准清洗为 StandardOrderDTO。

    字段对应（节选）：
      - order_id              → order_id
      - pay_amount(分)        → gmv(元)         # 抖店 pay_amount 映射为金额，并做 fen→yuan
      - sku_order_list[0].sku_id       → product_id   # 抖店 sku_id 映射为 product_id
      - sku_order_list[0].product_name→ product_name
      - sku_order_list[0].item_num     → quantity
      - province_name        → province
      - author_info.open_id  → creator_id     # 带货达人
      - shop_id              → shop_id
      - order_status         → status（枚举归一）
      - post_pay_time        → paid_at（时间戳解析）
    """
    sku = (raw.get("sku_order_list") or [{}])[0]
    author = raw.get("author_info") or {}
    status_raw = raw.get("order_status", "PAID")
    return StandardOrderDTO(
        platform=Platform.DOUYIN,
        order_id=str(raw.get("order_id")),
        product_id=str(sku.get("sku_id") or sku.get("product_id") or ""),
        product_name=str(sku.get("product_name") or raw.get("product_name") or ""),
        gmv=_fen_to_yuan(raw.get("pay_amount") or sku.get("sku_pay_amount")),
        quantity=int(sku.get("item_num") or 1),
        customer_id=_str_or_none(raw.get("buyer_id") or raw.get("user_id")),
        creator_id=_str_or_none(author.get("open_id") or author.get("author_id")),
        status=DOUYIN_STATUS_MAP.get(status_raw, OrderStatus.PAID),
        paid_at=_epoch_to_dt(raw.get("post_pay_time") or raw.get("pay_time")),
        province=raw.get("province_name") or raw.get("province"),
        shop_id=str(raw.get("shop_id") or ""),
    )


def to_orm_order(dto: StandardOrderDTO) -> StandardOrder:
    """DTO → ORM（供 ETL 批量写入 standard_orders）。"""
    return StandardOrder(**dto.model_dump())


# =========================================================================
# 适配器实现
# =========================================================================
class DouyinAdapter(BaseAdapter):
    platform = Platform.DOUYIN

    def __init__(self, store: DouyinTokenStore | None = None, token_key: str = "default") -> None:
        self.store = store
        self.token_key = token_key

    def pull_orders(self, demo: bool = False, **kwargs) -> Iterable[StandardOrderDTO]:
        """拉取抖店订单并归一化。demo=True 时用内置样例，免去真实凭证。

        生产路径：client = DouyinClient(self.store, self.token_key);
                  for page in range(...):
                      for raw in client.search_orders(page):
                          yield map_douyin_order(raw)
        """
        if demo or self.store is None:
            for raw in _demo_raw_orders():
                yield map_douyin_order(raw)
            return

        client = DouyinClient(self.store, self.token_key)
        page = 0
        while True:
            raws = client.search_orders(page=page, **kwargs)
            if not raws:
                break
            for raw in raws:
                yield map_douyin_order(raw)
            page += 1

    def pull_products(self, **kwargs) -> Iterable[StandardProductDTO]:
        # 商品映射骨架：真实环境需调用 /product/list 并映射；此处返回空。
        return []


def _demo_raw_orders() -> list[dict]:
    """内置样例：模拟抖店 /order/searchList 返回的真实风格 JSON。"""
    return [
        {
            "order_id": "6930000000000001001",
            "order_status": "COMPLETED",
            "pay_amount": 129900,                    # 1299.00 元
            "post_pay_time": 1719300000,            # 秒级时间戳
            "province_name": "广东",
            "shop_id": "123456",
            "buyer_id": "b_8821",
            "author_info": {"open_id": "ou_abc123", "author_name": "美妆小美"},
            "sku_order_list": [
                {
                    "sku_id": "S123456",
                    "product_id": "P654321",
                    "product_name": "美妆套装-爆款",
                    "item_num": 2,
                    "sku_pay_amount": 129900,
                }
            ],
        },
        {
            "order_id": "6930000000000001002",
            "order_status": "REFUND",
            "pay_amount": 39900,
            "post_pay_time": 1719386400,
            "province_name": "浙江",
            "shop_id": "123456",
            "buyer_id": "b_7732",
            "author_info": {"open_id": "ou_def456", "author_name": "水军A"},  # 高互动低转化达人
            "sku_order_list": [
                {
                    "sku_id": "S999000",
                    "product_id": "P111222",
                    "product_name": "9.9 福利品-引流",
                    "item_num": 1,
                    "sku_pay_amount": 39900,
                }
            ],
        },
        {
            "order_id": "6930000000000001003",
            "order_status": "DELIVERING",
            "pay_amount": 25900,
            "post_pay_time": 1719472800,
            "province_name": "四川",
            "shop_id": "123456",
            "buyer_id": "b_5510",
            "sku_order_list": [               # 自然流量订单（无 author_info）
                {
                    "sku_id": "S555001",
                    "product_id": "P333444",
                    "product_name": "日用百货-常规",
                    "item_num": 3,
                    "sku_pay_amount": 25900,
                }
            ],
        },
    ]


if __name__ == "__main__":
    # 无凭证快速验证映射是否正确
    print("===== 抖店适配器 字段映射 demo =====")
    for dto in DouyinAdapter().pull_orders(demo=True):
        print(dto.model_dump_json(indent=2))
else:
    # 模块加载即注册到全局适配器表（导入 app.adapters 包时触发）
    AdapterRegistry.register(DouyinAdapter())
