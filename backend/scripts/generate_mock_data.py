"""高质量 Mock 数据生成器：建表 + 生成符合真实电商分布的模拟数据。

业务约束（来自需求）：
- 至少 1000 订单 / 50 商品 / 20 达人，时间跨度覆盖最近 30 天。
- 二八定律：少数爆款贡献绝大多数 GMV，其余为长尾。
- 达人分层：优质达人（高 ROI）/ 普通达人 / 水军达人（高互动率、极低转化率，用于测试 AI 避坑预警）。
- 入库方式：SQLAlchemy ORM 批量写入；脚本可重复运行（先清空再插入）。

运行：
    cd backend
    python scripts/generate_mock_data.py
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 让脚本能 import app 包（脚本位于 backend/scripts/）
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models.standard import (  # noqa: E402
    Platform,
    StandardInfluencer,
    StandardOrder,
    StandardProduct,
)

# ----------------------------- 可调参数 -----------------------------
SEED = 20260723
N_PRODUCTS = 50
N_INFLUENCERS = 20
N_ORDERS = 1200          # >= 1000
SPAN_DAYS = 30           # 最近 30 天

CATEGORIES = ["美妆个护", "服饰鞋包", "数码3C", "家居生活", "食品生鲜", "母婴玩具", "运动户外"]
PROVINCES = ["广东", "浙江", "江苏", "北京", "上海", "四川", "山东", "湖北", "福建", "河南"]
SHOPS = ["SHOP_DY_001", "SHOP_DY_002", "SHOP_TB_001"]

WEEKDAY_WEIGHT = [1.0, 1.0, 1.05, 1.1, 1.4, 1.6, 1.5]  # 周一..周日，周末单量更高


def _rr(x: float, n: int = 2) -> float:
    return round(x, n)


def build_products(rng: random.Random) -> list[StandardProduct]:
    """50 个商品：价格对数正态，爆款权重用 Pareto 长尾分布。"""
    products: list[StandardProduct] = []
    # 每个商品一个 Pareto 权重（alpha≈1.2 对应明显的头部集中）
    weights = [rng.paretovariate(1.2) for _ in range(N_PRODUCTS)]
    for i in range(N_PRODUCTS):
        cat = CATEGORIES[i % len(CATEGORIES)]
        price = _rr(max(9.9, rng.lognormvariate(4.0, 0.55)))  # 约 15~400 元
        products.append(
            StandardProduct(
                product_id=f"P{i:04d}",
                platform=Platform.DOUYIN,
                name=f"{cat}-单品{i:03d}",
                category=cat,
                price=price,
                total_gmv=0.0,
                total_sold=0,
            )
        )
    # 把权重挂到对象上，供订单采样（不入库）
    for p, w in zip(products, weights):
        p._mock_weight = w  # type: ignore[attr-defined]
    return products


def build_influencers(rng: random.Random) -> list[StandardInfluencer]:
    """20 个达人，分三层：优质 / 普通 / 水军（高互动低转化）。"""
    influencers: list[StandardInfluencer] = []
    names_pool = [
        "美妆小美", "穿搭莉莉", "数码阿杰", "生活老王", "母婴豆豆", "运动大壮",
        "美食胖虎", "家居小柔", "护肤安娜", "潮玩kk", "数码老炮", "美妆娜娜",
        "穿搭cici", "户外风子", "零食王", "家电强哥", "母婴莉莉", "健身涛",
        "水军A", "水军B", "水军C", "水军D",
    ]

    def make(idx: int, tier: str) -> StandardInfluencer:
        name = names_pool[idx]
        if tier == "premium":
            followers = rng.randint(200_000, 1_500_000)
            engagement = _rr(rng.uniform(4.0, 9.0), 2)
            conversion = _rr(rng.uniform(4.0, 9.0), 2)
            target_roi = _rr(rng.uniform(3.5, 7.5), 2)
            target_orders = rng.randint(150, 420)
            suspicious = False
        elif tier == "normal":
            followers = rng.randint(20_000, 300_000)
            engagement = _rr(rng.uniform(2.0, 5.0), 2)
            conversion = _rr(rng.uniform(1.0, 3.0), 2)
            target_roi = _rr(rng.uniform(1.2, 2.8), 2)
            target_orders = rng.randint(30, 150)
            suspicious = False
        else:  # suspicious 水军：粉丝看着多、互动率高，但几乎不转化
            followers = rng.randint(80_000, 900_000)
            engagement = _rr(rng.uniform(15.0, 42.0), 2)   # 异常高互动（刷量）
            conversion = _rr(rng.uniform(0.03, 0.40), 3)    # 极低转化
            target_roi = _rr(rng.uniform(0.05, 0.40), 2)    # 严重亏损
            target_orders = rng.randint(3, 18)              # 真实带货极少
            suspicious = True
        inf = StandardInfluencer(
            creator_id=f"KOL{idx:03d}",
            platform=Platform.DOUYIN,
            name=name,
            category=CATEGORIES[idx % len(CATEGORIES)],
            followers=followers,
            gmv=0.0,
            orders=0,
            cost=0.0,
            roi=None,
            engagement_rate=engagement,
            conversion_rate=conversion,
            avg_views=rng.randint(int(followers * 0.1), int(followers * 0.6)),
            is_suspicious=suspicious,
        )
        # 仅用于生成阶段反推成本，不入库
        inf._mock_target_roi = target_roi        # type: ignore[attr-defined]
        inf._mock_target_orders = target_orders  # type: ignore[attr-defined]
        return inf

    # 6 优质 + 10 普通 + 4 水军
    tiers = ["premium"] * 6 + ["normal"] * 10 + ["suspicious"] * 4
    for idx, tier in enumerate(tiers):
        influencers.append(make(idx, tier))
    return influencers


def build_orders(
    rng: random.Random,
    products: list[StandardProduct],
    influencers: list[StandardInfluencer],
    now: datetime,
) -> list[StandardOrder]:
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days = [(base - timedelta(days=SPAN_DAYS - 1 - i)) for i in range(SPAN_DAYS)]
    day_weights = [WEEKDAY_WEIGHT[d.weekday()] for d in days]
    prod_weights = [getattr(p, "_mock_weight", 1.0) for p in products]
    # 达人按目标订单数加权（水军带单极少）
    inf_weights = [getattr(k, "_mock_target_orders", 1) for k in influencers]

    orders: list[StandardOrder] = []
    prod_gmv: dict[str, float] = {}
    prod_sold: dict[str, int] = {}
    inf_gmv: dict[str, float] = {}
    inf_orders: dict[str, int] = {}

    for n in range(N_ORDERS):
        day = rng.choices(days, weights=day_weights)[0]
        day_end = min(day + timedelta(days=1), now)  # 不超过当前时刻，避免未来订单
        span_sec = max(1, int((day_end - day).total_seconds()))
        paid_at = day + timedelta(seconds=rng.randint(0, span_sec - 1))
        p = rng.choices(products, weights=prod_weights)[0]
        qty = rng.choices([1, 2, 3, 4, 5], weights=[70, 18, 8, 3, 1])[0]
        discount = rng.uniform(0.8, 1.0)
        gmv = _rr((p.price or 50.0) * qty * discount)

        # 70% 订单归因到某个达人，否则自然流量
        creator_id = None
        if rng.random() < 0.7:
            k = rng.choices(influencers, weights=inf_weights)[0]
            creator_id = k.creator_id

        # 状态：近期多为进行中，历史多为完成，约 6% 退款
        age_days = (now - day).days
        if age_days <= 1:
            status = "paid" if rng.random() < 0.5 else "shipped"
        elif rng.random() < 0.06:
            status = "refunded"
        else:
            status = "completed"

        orders.append(
            StandardOrder(
                order_id=f"O{now.strftime('%Y%m%d')}{n:05d}",
                shop_id=rng.choice(SHOPS),
                platform=Platform.DOUYIN,
                product_id=p.product_id,
                product_name=p.name,
                gmv=gmv,
                quantity=qty,
                customer_id=f"C{rng.randint(1, 4000):05d}",
                creator_id=creator_id,
                status=status,
                paid_at=paid_at,
                province=rng.choices(PROVINCES, weights=[5, 4, 4, 3, 3, 2, 2, 2, 1.5, 1.5])[0],
            )
        )

        # 累计（用于回填商品/达人汇总，避免再把明细拉回 Python 做二次聚合）
        prod_gmv[p.product_id] = prod_gmv.get(p.product_id, 0.0) + gmv
        prod_sold[p.product_id] = prod_sold.get(p.product_id, 0) + qty
        if creator_id:
            inf_gmv[creator_id] = inf_gmv.get(creator_id, 0.0) + gmv
            inf_orders[creator_id] = inf_orders.get(creator_id, 0) + 1

    # 把汇总写回商品 / 达人对象
    for p in products:
        p.total_gmv = _rr(prod_gmv.get(p.product_id, 0.0))
        p.total_sold = prod_sold.get(p.product_id, 0)
    for k in influencers:
        g = inf_gmv.get(k.creator_id, 0.0)
        o = inf_orders.get(k.creator_id, 0)
        target_roi = getattr(k, "_mock_target_roi", 1.0)
        k.gmv = _rr(g)
        k.orders = o
        # ROI = GMV / 投放成本；用目标 ROI 反推成本，使 ROI 落在设定区间
        k.cost = _rr(g / target_roi) if target_roi > 0 else 0.0
        k.roi = _rr(g / k.cost) if k.cost > 0 else None
    return orders


def print_summary(products, influencers, orders):
    total_gmv = sum(o.gmv for o in orders)
    # 二八校验：按 GMV 排序的商品，头部 20% 占比
    ranked = sorted(products, key=lambda p: p.total_gmv, reverse=True)
    top20 = ranked[: max(1, N_PRODUCTS // 5)]
    top20_gmv = sum(p.total_gmv for p in top20)
    print("\n================ Mock 数据摘要 ================")
    print(f"订单数: {len(orders)}   商品数: {len(products)}   达人数: {len(influencers)}")
    print(f"总 GMV: ¥{total_gmv:,.2f}")
    print(
        f"二八定律: 头部 {len(top20)} 个商品(20%)贡献 GMV 占比 "
        f"{top20_gmv / total_gmv * 100:.1f}%"
    )
    print("\n-- 达人分层（ROI / 互动率 / 转化率 / 疑似水军）--")
    for k in sorted(influencers, key=lambda x: x.roi or 0, reverse=True):
        flag = " ⚠️水军" if k.is_suspicious else ""
        print(
            f"  {k.name:<10} ROI={ (k.roi or 0):>5.2f}  互动={k.engagement_rate:>5.1f}%  "
            f"转化={k.conversion_rate:>5.2f}%  GMV=¥{k.gmv:>10,.0f}  订单={k.orders:>4d}{flag}"
        )
    print("===============================================\n")


def main() -> None:
    rng = random.Random(SEED)
    Base.metadata.create_all(bind=engine)  # 幂等建表

    with SessionLocal() as db:
        # 清空旧数据（按外键顺序：订单 -> 达人 -> 商品）
        db.query(StandardOrder).delete()
        db.query(StandardInfluencer).delete()
        db.query(StandardProduct).delete()
        db.commit()

        now = datetime.now()
        products = build_products(rng)
        influencers = build_influencers(rng)
        orders = build_orders(rng, products, influencers, now)

        db.add_all(products)
        db.add_all(influencers)
        db.bulk_save_objects(orders)  # 大批量写入，避免逐条 flush
        db.commit()

        print_summary(products, influencers, orders)
        # 顺带用数据库层聚合核对总数（验证 ORM 聚合在 DB 端可用）
        cnt = db.query(func.count(StandardOrder.id)).scalar()
        g = db.query(func.coalesce(func.sum(StandardOrder.gmv), 0)).scalar()
        print(f"[DB 聚合核对] standard_orders 行数={cnt}, SUM(gmv)={float(g):,.2f}")


if __name__ == "__main__":
    main()
