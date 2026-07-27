"""定时任务示例：每天凌晨 2 点拉取昨日数据 -> AI 日报 -> 飞书推送。

完整链路：
  1) 适配器 ETL 把平台订单写入 standard_orders（生产环境常驻运行）。
  2) 让通义千问基于工具查询生成日报（Function Calling）。
  3) 通过飞书 Webhook 推送到群里。
"""
from __future__ import annotations

from datetime import date, timedelta

from app.tasks.celery_app import celery_app
from app.services import ai_engine, feishu


@celery_app.task(name="app.tasks.scheduled.daily_report_task")
def daily_report_task(shop_id: str = "default") -> str:
    yesterday = date.today() - timedelta(days=1)
    day = yesterday.isoformat()

    # 1) 拉取昨日数据（生产环境由适配器 ETL 写入 standard_orders 表）
    # TODO: adapter = AdapterRegistry.get(Platform.DOUYIN)
    #       adapter.pull_orders(shop_id=shop_id, date=day)

    # 2) 让通义千问基于工具查询生成日报
    query = f"请基于 {day} 的店铺数据生成一份日报，并评估达人表现与匹配度。"
    try:
        report_md = ai_engine.generate_report(query)
    except Exception as e:  # 失败时也通知，避免静默
        feishu.push_markdown("AI 日报生成失败", f"错误：{e}")
        raise

    # 3) 推送飞书
    feishu.push_markdown(f"📊 {day} 店铺日报", report_md[:4000])
    return "ok"
