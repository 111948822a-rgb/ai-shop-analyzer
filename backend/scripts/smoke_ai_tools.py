"""集成冒烟测试：直接调用 AI 工具（Function Calling 的落地函数），验证数据库层聚合可用。

这等价于通义千问在 Function Calling 循环里会拿到的真实返回。
运行：cd backend && python scripts/smoke_ai_tools.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services import ai_tools  # noqa: E402


def main() -> None:
    end = datetime.now()
    start = end - timedelta(days=30)
    start_s, end_s = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    print("========== query_sales_data（数据库层 SUM/COUNT/GROUP BY）==========")
    sales = ai_tools.query_sales_data(start_s, end_s)
    print(f"区间 {start_s} ~ {end_s}")
    print(f"  GMV={sales['gmv']:,}  订单数={sales['orders']}  客单价={sales['avg_order_value']}")
    print(f"  Top10 商品（按 GMV）：")
    for i, p in enumerate(sales["top_products"], 1):
        print(f"    {i:2d}. {p['product']:<16} GMV={p['gmv']:>10,.2f}  订单={p['orders']}")

    print("\n========== get_influencer_metrics（ORM 过滤+排序，含避坑字段）==========")
    inf = ai_tools.get_influencer_metrics(top_n=20)
    susp = [x for x in inf["influencers"] if x["is_suspicious"]]
    print(f"  返回达人 {len(inf['influencers'])} 个，其中疑似水军 {len(susp)} 个：")
    for x in inf["influencers"][:6]:
        tag = " ⚠️水军" if x["is_suspicious"] else ""
        print(
            f"    {x['name']:<10} ROI={x['roi']:>5} 互动={x['engagement_rate']}% "
            f"转化={x['conversion_rate']}% GMV={x['gmv']:>10,.0f}{tag}"
        )

    # 断言：水军必须“高互动 + 极低转化”，且 ROI 明显低于优质达人
    assert susp, "未检测到疑似水军达人，数据不符合预期"
    assert all(x["engagement_rate"] >= 15 and x["conversion_rate"] < 0.5 for x in susp), \
        "水军特征异常：应满足 互动率>=15% 且 转化率<0.5%"
    print("\n✅ 断言通过：Function Calling 工具可在数据库层聚合，并正确暴露水军避坑信号。")


if __name__ == "__main__":
    main()
