"""Celery 应用配置：broker / backend 走 Redis，注册定时任务（beat）。

启动：
  celery -A app.tasks.celery_app.celery_app worker -l info
  celery -A app.tasks.celery_app.celery_app beat  -l info
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_shop_analyzer",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
)

# 自动发现 app/tasks 下的任务模块
celery_app.autodiscover_tasks(["app.tasks"])

# 定时任务：每天凌晨 2 点生成昨日日报
celery_app.conf.beat_schedule = {
    "daily-report-02am": {
        "task": "app.tasks.scheduled.daily_report_task",
        "schedule": crontab(hour=2, minute=0),
    },
}
