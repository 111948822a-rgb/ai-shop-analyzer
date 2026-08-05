"""Dashboard 数据看板 API：从 SQLite 读取聚合数据，供前端 Recharts 渲染。

全部聚合在数据库层用 SQLAlchemy select / func.sum / func.count / group_by 完成，
不把订单明细拉进 Python 内存（与 ai_tools 同一原则）。
提供 4 个端点：
  - GET /api/dashboard/overview      核心 KPI（GMV/订单/客单价/退款率）+ 环比(delta_pct)
  - GET /api/dashboard/gmv-trend     近 N 天每日 GMV 折线数据
  - GET /api/dashboard/top-products  商品销量 Top N 横向柱状数据
  - GET /api/dashboard/influencers   达人散点（互动率 x 转化率，气泡=GMV，含 is_suspicious）
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, case, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.standard import OrderStatus, StandardInfluencer, StandardOrder, StandardProduct

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ----------------------------- 内部聚合工具 -----------------------------
def _window(days: int) -> tuple[datetime, datetime, datetime, datetime]:
    """返回 (当前窗口起, 当前窗口止=含今, 上一窗口起, 上一窗口止)。

    当前窗口 = [now-days, now+1天)，上一窗口等长左移。
    """
    now = datetime.now()
    end_exclusive = now + timedelta(days=1)          # 含今天一整天
    start = end_exclusive - timedelta(days=days)
    prev_end_exclusive = start
    prev_start = prev_end_exclusive - timedelta(days=days)
    return start, end_exclusive, prev_start, prev_end_exclusive


def _actual_data_range(db: Session, shop_conds: list | None = None) -> tuple[datetime | None, datetime | None]:
    """查询数据库中实际订单的最早/最晚 paid_at。

    TK API 时间过滤不生效，同步下来的订单可能是几个月前的，
    看板按"近N天"窗口过滤会显示空。此时需要知道数据实际范围。
    """
    where = []
    if shop_conds:
        where.extend(shop_conds)
    where.append(StandardOrder.paid_at.isnot(None))
    stmt = select(
        func.min(StandardOrder.paid_at).label("earliest"),
        func.max(StandardOrder.paid_at).label("latest"),
    ).where(*where)
    row = db.execute(stmt).one()
    return row.earliest, row.latest


def _shop_filter_conditions(shop_ids: list[str] | None) -> list:
    """把前端传来的店铺ID列表转成 SQLAlchemy 过滤条件。

    - 空列表/None：不加过滤（看全部店铺）
    - 含空串 ""：代表「默认店铺」(shop_id IS NULL)
    - 其余：shop_id IN (...)
    """
    if not shop_ids:
        return []
    non_empty = [s for s in shop_ids if s not in ("", None)]
    conds = []
    if "" in shop_ids:
        conds.append(StandardOrder.shop_id.is_(None))
    if non_empty:
        conds.append(StandardOrder.shop_id.in_(non_empty))
    if not conds:
        return []
    return [or_(*conds)]


def _period_agg(
    db: Session, start: datetime, end_exclusive: datetime, shop_conds: list | None = None
) -> dict:
    """数据库层聚合一个时间窗口的 GMV / 订单数 / 客单价 / 退款率。

    GMV 统计排除已取消/已退款订单（status=REFUNDED），这些订单不应计入成交额。
    订单数仍统计全部（含退款），退款率 = 退款单 / 总单。
    """
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_exclusive]
    if shop_conds:
        where_clauses.extend(shop_conds)
    stmt = select(
        # GMV 只算非退款订单
        func.coalesce(
            func.sum(
                func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
            ),
            0.0,
        ).label("gmv"),
        func.count(StandardOrder.id).label("orders"),
        func.coalesce(
            func.sum(
                func.cast(StandardOrder.status == OrderStatus.REFUNDED, Integer)
            ),
            0,
        ).label("refunds"),
    ).where(*where_clauses)
    row = db.execute(stmt).one()
    gmv = float(row.gmv)
    orders = int(row.orders)
    refunds = int(row.refunds)
    # 有效订单数（非退款），用于算真实客单价
    valid_orders = orders - refunds
    return {
        "gmv": gmv,
        "orders": orders,
        "aov": (gmv / valid_orders) if valid_orders else 0.0,
        "refund_rate": (refunds / orders * 100) if orders else 0.0,
    }


def _delta_pct(cur: float, prev: float) -> float | None:
    if prev == 0:
        return None
    return round((cur - prev) / prev * 100, 1)


# ----------------------------- 端点 1：KPI + 环比 -----------------------------
@router.get("/overview")
def dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID，空串代表默认店铺"),
    db: Session = Depends(get_db),
) -> dict:
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, prev_start, prev_end_ex = _window(days)
    cur = _period_agg(db, start, end_ex, shop_conds)
    prev = _period_agg(db, prev_start, prev_end_ex, shop_conds)

    # 查数据实际范围，前端据此提示用户
    earliest, latest = _actual_data_range(db, shop_conds)

    def kpi(label: str, key: str, higher_is_better: bool, fmt: str) -> dict:
        return {
            "key": key,
            "label": label,
            "value": round(cur[key], 2),
            "delta_pct": _delta_pct(cur[key], prev[key]),
            "higher_is_better": higher_is_better,
            "format": fmt,
        }

    return {
        "period": {
            "start": start.strftime("%Y-%m-%d"),
            "end": (end_ex - timedelta(seconds=1)).strftime("%Y-%m-%d"),
            "days": days,
        },
        "previous_period": {
            "start": prev_start.strftime("%Y-%m-%d"),
            "end": (prev_end_ex - timedelta(seconds=1)).strftime("%Y-%m-%d"),
        },
        "data_range": {
            "earliest": earliest.strftime("%Y-%m-%d") if earliest else None,
            "latest": latest.strftime("%Y-%m-%d") if latest else None,
        },
        "kpis": [
            kpi("GMV", "gmv", True, "currency"),
            kpi("订单数", "orders", True, "int"),
            kpi("客单价", "aov", True, "currency"),
            kpi("退款率", "refund_rate", False, "percent"),
        ],
    }


# ----------------------------- 端点 2：GMV 趋势 -----------------------------
@router.get("/gmv-trend")
def gmv_trend(
    days: int = Query(30, ge=1, le=365),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID"),
    db: Session = Depends(get_db),
) -> dict:
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, _, _ = _window(days)
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_ex]
    if shop_conds:
        where_clauses.extend(shop_conds)
    stmt = (
        select(
            func.date(StandardOrder.paid_at).label("day"),
            func.coalesce(
                func.sum(
                    func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
                ),
                0.0,
            ).label("gmv"),
        )
        .where(*where_clauses)
        .group_by(func.date(StandardOrder.paid_at))
        .order_by("day")
    )
    rows = db.execute(stmt).all()
    gmv_by_day = {str(r.day): round(float(r.gmv), 2) for r in rows}

    # 补齐缺失日期，保证折线图横轴连续
    series = []
    d = start.date()
    end = (end_ex - timedelta(seconds=1)).date()
    while d <= end:
        key = d.strftime("%Y-%m-%d")
        series.append({"date": key, "gmv": gmv_by_day.get(key, 0.0)})
        d += timedelta(days=1)

    return {"series": series}


# ----------------------------- 端点 3：商品 Top N -----------------------------
@router.get("/top-products")
def top_products(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID"),
    db: Session = Depends(get_db),
) -> dict:
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, _, _ = _window(days)
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_ex]
    if shop_conds:
        where_clauses.extend(shop_conds)
    stmt = (
        select(
            StandardOrder.product_name.label("product"),
            func.coalesce(
                func.sum(
                    func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
                ),
                0.0,
            ).label("gmv"),
            func.count(StandardOrder.id).label("orders"),
            # LEFT JOIN StandardProduct 补充 category / price（按 product_id + platform 关联，
            # 用 MAX 聚合以兼容按 product_name 分组）
            func.max(StandardProduct.category).label("category"),
            func.max(StandardProduct.price).label("price"),
        )
        .outerjoin(
            StandardProduct,
            (StandardOrder.product_id == StandardProduct.product_id)
            & (StandardOrder.platform == StandardProduct.platform),
        )
        .where(*where_clauses)
        .group_by(StandardOrder.product_name)
        .order_by(
            func.sum(
                func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
            ).desc()
        )
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    # 用 Python 反转成「从下往上」的好看顺序（横向柱状图底部放第一名）
    items = [
        {
            "product": r.product,
            "gmv": round(float(r.gmv), 2),
            "orders": int(r.orders),
            "category": r.category,
            "price": float(r.price) if r.price is not None else None,
        }
        for r in rows
    ]
    return {"items": list(reversed(items))}


# ----------------------------- 端点 4：达人散点 -----------------------------
@router.get("/influencers")
def influencers_scatter(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(StandardInfluencer)).scalars().all()
    points = [
        {
            "creator_id": r.creator_id,
            "name": r.name,
            "category": r.category,
            "engagement_rate": r.engagement_rate,
            "conversion_rate": r.conversion_rate,
            "gmv": round(float(r.gmv), 2),
            "roi": round(float(r.roi), 2) if r.roi is not None else None,
            "followers": int(r.followers),
            "is_suspicious": bool(r.is_suspicious),
        }
        for r in rows
    ]
    return {"points": points, "suspicious_count": sum(1 for p in points if p["is_suspicious"])}


# ----------------------------- 端点 5：店铺列表（供前端多选）-----------------------------
@router.get("/shops")
def list_shops(db: Session = Depends(get_db)) -> dict:
    """返回去重后的店铺列表及各自订单数 / GMV，供首页「销售数据分析」先选店铺。

    shop_id 为 NULL 的订单统一归入「默认店铺」(shop_id="")。
    """
    rows = db.execute(
        select(
            StandardOrder.shop_id,
            func.count(StandardOrder.id).label("orders"),
            func.coalesce(func.sum(StandardOrder.gmv), 0.0).label("gmv"),
        ).group_by(StandardOrder.shop_id)
    ).all()
    shops = []
    for r in rows:
        sid = r.shop_id or ""
        shops.append(
            {
                "shop_id": sid,
                "name": r.shop_id or "默认店铺",
                "order_count": int(r.orders),
                "gmv": round(float(r.gmv), 2),
            }
        )
    if not shops:
        shops.append({"shop_id": "", "name": "默认店铺", "order_count": 0, "gmv": 0.0})
    return {"shops": shops}


# ----------------------------- 端点 6：地域分布 -----------------------------
@router.get("/geo-distribution")
def geo_distribution(
    days: int = Query(30, ge=1, le=365),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID"),
    db: Session = Depends(get_db),
) -> dict:
    """按省份聚合订单数与 GMV，排除 province 为 NULL 的订单，按 GMV 降序取 Top 20。"""
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, _, _ = _window(days)
    where_clauses = [
        StandardOrder.paid_at >= start,
        StandardOrder.paid_at < end_ex,
        StandardOrder.province.isnot(None),
    ]
    if shop_conds:
        where_clauses.extend(shop_conds)
    stmt = (
        select(
            StandardOrder.province.label("province"),
            func.count(StandardOrder.id).label("orders"),
            func.coalesce(
                func.sum(
                    func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
                ),
                0.0,
            ).label("gmv"),
        )
        .where(*where_clauses)
        .group_by(StandardOrder.province)
        .order_by(
            func.sum(
                func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
            ).desc()
        )
        .limit(20)
    )
    rows = db.execute(stmt).all()
    items = [
        {
            "province": r.province,
            "orders": int(r.orders),
            "gmv": round(float(r.gmv), 2),
        }
        for r in rows
    ]
    return {"items": items}


# ----------------------------- 端点 7：订单状态分布 -----------------------------
@router.get("/order-status")
def order_status(
    days: int = Query(30, ge=1, le=365),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID"),
    db: Session = Depends(get_db),
) -> dict:
    """按订单状态分组统计订单数、GMV 及占比百分比。"""
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, _, _ = _window(days)
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_ex]
    if shop_conds:
        where_clauses.extend(shop_conds)
    stmt = (
        select(
            StandardOrder.status.label("status"),
            func.count(StandardOrder.id).label("orders"),
            func.coalesce(
                func.sum(
                    func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
                ),
                0.0,
            ).label("gmv"),
        )
        .where(*where_clauses)
        .group_by(StandardOrder.status)
    )
    rows = db.execute(stmt).all()
    total_orders = sum(int(r.orders) for r in rows) or 1
    label_map = {
        "completed": "已完成",
        "shipped": "已发货",
        "paid": "已付款",
        "refunded": "已退款/取消",
    }
    items = []
    for r in rows:
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        orders = int(r.orders)
        items.append(
            {
                "status": status_val,
                "label": label_map.get(status_val, status_val),
                "orders": orders,
                "gmv": round(float(r.gmv), 2),
                "pct": round(orders / total_orders * 100, 1),
            }
        )
    return {"items": items}


# ----------------------------- 端点 8：订单类型分布 -----------------------------
@router.get("/order-types")
def order_types(
    days: int = Query(30, ge=1, le=365),
    shop_ids: str | None = Query(None, alias="shop_ids", description="逗号分隔的店铺ID"),
    db: Session = Depends(get_db),
) -> dict:
    """按 is_sample_order / is_cod 分类统计订单数与 GMV。

    优先级：样品单 > 货到付款 > 普通订单。
    """
    shop_conds = _shop_filter_conditions(shop_ids.split(",") if shop_ids else None)
    start, end_ex, _, _ = _window(days)
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_ex]
    if shop_conds:
        where_clauses.extend(shop_conds)
    type_expr = case(
        (StandardOrder.is_sample_order, "sample"),
        (StandardOrder.is_cod, "cod"),
        else_="normal",
    )
    stmt = (
        select(
            type_expr.label("type"),
            func.count(StandardOrder.id).label("orders"),
            func.coalesce(
                func.sum(
                    func.cast(StandardOrder.status != OrderStatus.REFUNDED, Integer) * StandardOrder.gmv
                ),
                0.0,
            ).label("gmv"),
        )
        .where(*where_clauses)
        .group_by(type_expr)
    )
    rows = db.execute(stmt).all()
    label_map = {
        "sample": "样品单",
        "cod": "货到付款",
        "normal": "普通订单",
    }
    items = []
    for r in rows:
        type_val = r.type
        items.append(
            {
                "type": type_val,
                "label": label_map.get(type_val, type_val),
                "orders": int(r.orders),
                "gmv": round(float(r.gmv), 2),
            }
        )
    return {"items": items}


# ----------------------------- 端点 9：物流统计 -----------------------------
@router.get("/shipping-stats")
def shipping_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    """按物流商分组统计订单数，并计算平均配送时长（delivery_time - rts_time，小时）。"""
    start, end_ex, _, _ = _window(days)
    where_clauses = [StandardOrder.paid_at >= start, StandardOrder.paid_at < end_ex]
    # 按物流商分组统计订单数
    provider_stmt = (
        select(
            StandardOrder.shipping_provider.label("name"),
            func.count(StandardOrder.id).label("orders"),
        )
        .where(*where_clauses)
        .group_by(StandardOrder.shipping_provider)
        .order_by(func.count(StandardOrder.id).desc())
    )
    provider_rows = db.execute(provider_stmt).all()
    providers = [
        {"name": (r.name or "未知"), "orders": int(r.orders)}
        for r in provider_rows
    ]
    # 平均配送时长（小时）：仅统计同时有 rts_time 和 delivery_time 的订单
    avg_stmt = select(
        func.avg(
            (func.julianday(StandardOrder.delivery_time) - func.julianday(StandardOrder.rts_time)) * 24.0
        )
    ).where(
        *where_clauses,
        StandardOrder.rts_time.isnot(None),
        StandardOrder.delivery_time.isnot(None),
    )
    avg_hours = db.execute(avg_stmt).scalar()
    avg_delivery_hours = round(float(avg_hours), 1) if avg_hours is not None else 0.0
    return {"providers": providers, "avg_delivery_hours": avg_delivery_hours}
