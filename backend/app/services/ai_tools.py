"""AI 可调用的后端数据工具（Function Calling 的落地实现）。

核心原则（对照需求）：大模型不直接读大表，而是调用这些函数获取【数据库层预计算】的聚合结果。
所有汇总都用 SQLAlchemy 的 select / func.sum / func.count / group_by 在数据库端完成，
严禁把订单明细拉到 Python 内存里再算。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.standard import Platform, StandardInfluencer, StandardOrder


def _parse_date(s: str) -> datetime:
    s = s.strip()
    if len(s) == 10:  # YYYY-MM-DD
        return datetime.strptime(s, "%Y-%m-%d")
    return datetime.fromisoformat(s)


def query_sales_data(start_date: str, end_date: str, platform: str | None = None) -> dict:
    """查询指定日期区间的销售汇总（GMV / 订单数 / 客单价 / Top10 商品）。

    全部在数据库层聚合：func.sum / func.count 算总量，group_by + order_by 取 TopN。
    end_date 当天含入（区间右端右移一天）。
    """
    start = _parse_date(start_date)
    end_exclusive = _parse_date(end_date) + timedelta(days=1)  # 含 end_date 当天

    with SessionLocal() as db:
        # —— 总量：SUM / COUNT / 客单价（DB 端计算）——
        total_stmt = select(
            func.coalesce(func.sum(StandardOrder.gmv), 0).label("gmv"),
            func.count(StandardOrder.id).label("orders"),
            func.coalesce(
                func.sum(StandardOrder.gmv) / func.nullif(func.count(StandardOrder.id), 0),
                0.0,
            ).label("aov"),
        ).where(StandardOrder.paid_at >= start, StandardOrder.paid_at < end_exclusive)
        if platform:
            total_stmt = total_stmt.where(StandardOrder.platform == Platform(platform))
        row = db.execute(total_stmt).one()

        # —— Top10 商品：GROUP BY + ORDER BY SUM DESC + LIMIT（DB 端计算）——
        top_stmt = (
            select(
                StandardOrder.product_name,
                func.sum(StandardOrder.gmv).label("gmv"),
                func.count(StandardOrder.id).label("orders"),
            )
            .where(StandardOrder.paid_at >= start, StandardOrder.paid_at < end_exclusive)
        )
        if platform:
            top_stmt = top_stmt.where(StandardOrder.platform == Platform(platform))
        top_stmt = top_stmt.group_by(StandardOrder.product_name).order_by(
            func.sum(StandardOrder.gmv).desc()
        ).limit(10)
        top_rows = db.execute(top_stmt).all()

    return {
        "gmv": round(float(row.gmv), 2),
        "orders": int(row.orders),
        "avg_order_value": round(float(row.aov), 2),
        "top_products": [
            {
                "product": r.product_name,
                "gmv": round(float(r.gmv), 2),
                "orders": int(r.orders),
            }
            for r in top_rows
        ],
    }


def get_influencer_metrics(creator_name: str | None = None, top_n: int = 10) -> dict:
    """查询达人指标（GMV / 订单 / ROI / 互动率 / 转化率 / 疑似水军）。

    仅查询 standard_influencers 维度表（20 行），用 ORM 过滤 + 排序，不碰订单明细。
    creator_name 不传则返回按 GMV 排序的 TopN；传了则精确匹配。
    关键：水军达人 GMV 通常极低、不会出现在 TopN 里，但 AI 必须能"看到"它们才能做避坑预警，
    因此返回列表【永远追加强制带上所有 is_suspicious=True 的达人】（去重）。
    """
    with SessionLocal() as db:
        stmt = select(StandardInfluencer)
        if creator_name:
            stmt = stmt.where(StandardInfluencer.name == creator_name)
        stmt = stmt.order_by(StandardInfluencer.gmv.desc()).limit(top_n)
        rows = db.execute(stmt).scalars().all()

        # 强制补齐所有疑似水军达人（即便 GMV 很低、不在 TopN 中）
        if not creator_name:
            suspicious = (
                db.execute(
                    select(StandardInfluencer).where(StandardInfluencer.is_suspicious.is_(True))
                )
                .scalars()
                .all()
            )
            seen = {r.creator_id for r in rows}
            for s in suspicious:
                if s.creator_id not in seen:
                    rows.append(s)
                    seen.add(s.creator_id)

    return {
        "influencers": [
            {
                "creator_id": r.creator_id,
                "name": r.name,
                "category": r.category,
                "gmv": round(float(r.gmv), 2),
                "orders": int(r.orders),
                "roi": round(float(r.roi), 2) if r.roi is not None else None,
                "followers": int(r.followers),
                # —— 避坑预警关键字段：高互动 + 低转化 = 疑似水军 ——
                "engagement_rate": r.engagement_rate,
                "conversion_rate": r.conversion_rate,
                "is_suspicious": bool(r.is_suspicious),
            }
            for r in rows
        ]
    }


# 供 AI 引擎注册使用的工具清单（name -> callable）
AI_TOOLS = {
    "query_sales_data": query_sales_data,
    "get_influencer_metrics": get_influencer_metrics,
}
