#!/usr/bin/env python
"""端到端实跑：同步模拟 Celery 每日日报定时任务（不依赖 Celery 进程）。

完整链路（与生产 daily_report_task 完全一致，只是同步执行）：
  1) ai_tools 在数据库层聚合近 30 天销售数据 + 达人指标（不把大表拉进内存）
  2) ai_engine 驱动通义千问 qwen-max 的 Function Calling，自主调用上述工具后产出 Markdown 报告
  3) feishu 把报告组装成交互卡片并推送到飞书群

用法（在 backend/ 目录下执行）：
  # 真实跑：需要 .env 里配好 DASHSCOPE_API_KEY 与 FEISHU_WEBHOOK_URL
  python scripts/test_e2e_daily_report.py

  # 无 Key 也能验证整条链路：用内置 mock LLM 生成报告（仍真实查库、真实组装卡片）
  python scripts/test_e2e_daily_report.py --mock

  # 生成报告但不推飞书，仅打印卡片 JSON（方便预览手机端效果）
  python scripts/test_e2e_daily_report.py --no-push
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# 让脚本从 backend/ 任意子目录都能运行
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings
from app.services import ai_engine, ai_tools, feishu


def last_30_days() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=29)
    return start.isoformat(), end.isoformat()


def _detect_suspicious(influencers: list[dict]) -> list[dict]:
    return [
        i
        for i in influencers
        if i.get("is_suspicious")
        or (
            (i.get("engagement_rate") or 0) >= 20
            and i.get("conversion_rate") is not None
            and i.get("conversion_rate") < 0.5
        )
    ]


def mock_generate_report(query: str, sales: dict, influencers: list[dict]) -> str:
    """内置 mock 引擎：在没有 Dashscope Key 时，用真实聚合数据拼出一份结构完整的报告。
    仅用于本地验证链路，不调用任何大模型。"""
    suspicious = _detect_suspicious(influencers)
    top = sales.get("top_products", [])[:5]
    top_md = "\n".join(
        f"{idx + 1}. **{p['product']}** — GMV ¥{p['gmv']:,.2f}，{p['orders']} 单"
        for idx, p in enumerate(top)
    )
    # 按 ROI 排个序，给出优质/普通分层
    ranked = sorted(influencers, key=lambda x: (x.get("roi") or 0), reverse=True)
    best = ranked[:3]
    best_md = "\n".join(
        f"- {i['name']}（{i['category']}）：ROI {i.get('roi')}，GMV ¥{i['gmv']:,.2f}，订单 {i['orders']}"
        for i in best
    )
    susp_md = (
        "\n".join(
            f"- 🚨 **{i['name']}**：互动率 {i.get('engagement_rate')}% / 转化率 {i.get('conversion_rate')}% / "
            f"ROI {i.get('roi')} —— 高互动、极低转化，疑似水军/刷量，建议立即暂停合作并核查。"
            for i in suspicious
        )
        or "未发现明显异常达人。"
    )

    return f"""# 店铺经营日报（近 30 天）

> {query}

## 一、数据总结
- **总 GMV**：¥{sales['gmv']:,.2f}
- **总订单**：{sales['orders']:,} 单
- **客单价**：¥{sales['avg_order_value']:,.2f}
- 头部商品贡献了绝大部分 GMV，呈典型二八分布。

**Top 商品：**
{top_md}

## 二、问题诊断
- 销售高度依赖少数爆款，长尾商品动销不足，需补充引流与组合装策略。
- 达人投放存在质量分化，详见下方避坑预警。

## 三、达人匹配度打分（Top）
{best_md}

### 🚨 避坑预警（疑似水军 / 刷量）
{susp_md}

## 四、下一步行动建议
1. 对高 ROI 优质达人追加预算与独家机制，放大确定性收益。
2. **立即排查并暂停与疑似水军达人的合作**，避免预算浪费与数据污染。
3. 针对长尾商品做内容化改造 + 短视频种草，平滑 GMV 对爆款的依赖。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Shop Analyzer 端到端日报实跑（同步模拟 Celery 任务）")
    parser.add_argument("--mock", action="store_true", help="使用内置 mock LLM，无需 Dashscope Key")
    parser.add_argument("--no-push", action="store_true", help="生成报告但不推飞书，仅打印卡片 JSON")
    args = parser.parse_args()

    settings = get_settings()
    start, end = last_30_days()
    date_label = f"{start} ~ {end}"

    print("=" * 64)
    print(" AI Shop Analyzer · 端到端日报实跑")
    print("=" * 64)
    print(f" 数据区间 : {date_label}")
    print(f" 数据库   : {settings.database_url}")
    print(f" 模型     : {settings.qwen_model}")
    print(f" Dashscope: {'已配置' if settings.dashscope_api_key else '未配置 → 将用 mock'}")
    print(f" 飞书     : {'已配置' if settings.feishu_webhook_url else '未配置 → 仅打印卡片'}")
    print("-" * 64)

    # —— 步骤 1：数据库层聚合（Function Calling 的底层数据来源）——
    print("① 调用 ai_tools 在数据库层聚合近 30 天数据 ...")
    sales = ai_tools.query_sales_data(start, end)
    metrics = ai_tools.get_influencer_metrics(top_n=20)
    influencers = metrics["influencers"]
    print(f"   → GMV ¥{sales['gmv']:,.2f} | 订单 {sales['orders']:,} | 客单价 ¥{sales['avg_order_value']:,.2f}")

    # —— 步骤 2：通义千问 Function Calling 生成报告 ——
    query = (
        f"请基于 {start} 至 {end} 的店铺销售数据生成一份近 30 天经营日报，"
        f"评估达人表现与匹配度，并重点排查疑似水军/刷量达人。"
    )
    if settings.dashscope_api_key and not args.mock:
        print("② 调用通义千问 qwen-max（Function Calling）生成报告 ...")
        try:
            report_md = ai_engine.generate_report(query)
        except Exception as e:  # 失败时给明确提示，不静默
            print(f"   ✗ 通义千问调用失败：{e}")
            return 1
    else:
        mode = "mock（--mock 指定）" if args.mock else "mock（未配置 DASHSCOPE_API_KEY）"
        print(f"② 使用 {mode} 引擎生成报告（仍真实查库、真实组装卡片）...")
        report_md = mock_generate_report(query, sales, influencers)
    print(f"   → 报告生成完成，字数 {len(report_md)}")

    # —— 步骤 3：组装飞书卡片并推送 ——
    print("③ 组装飞书交互卡片 ...")
    if settings.feishu_webhook_url and not args.no_push:
        print("   推送中 ...")
        try:
            resp = feishu.push_report_card(date_label, sales, influencers, report_md)
            print(f"   飞书返回：{resp}")
        except Exception as e:
            print(f"   ✗ 飞书推送失败：{e}")
            return 1
    else:
        reason = "（--no-push）" if args.no_push else "（未配置 FEISHU_WEBHOOK_URL）"
        print(f"   不推送 {reason}，打印卡片 JSON 预览：")
        card = feishu.build_daily_report_card(date_label, sales, influencers, report_md)
        print(json.dumps(card, ensure_ascii=False, indent=2))

    # —— 执行摘要 ——
    suspicious = _detect_suspicious(influencers)
    print("-" * 64)
    print(" 执行摘要")
    print(f"   数据区间   : {date_label}")
    print(f"   GMV        : ¥{sales['gmv']:,.2f}")
    print(f"   订单数     : {sales['orders']:,}")
    print(f"   客单价     : ¥{sales['avg_order_value']:,.2f}")
    print(f"   疑似水军   : {len(suspicious)} 个 -> " + (", ".join(i["name"] for i in suspicious) or "无"))
    print(f"   报告字数   : {len(report_md)}")
    print("=" * 64)
    print(" ✅ 端到端链路跑通")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
