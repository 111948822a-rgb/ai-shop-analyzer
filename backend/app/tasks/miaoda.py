"""秒搭达人分析的 Celery 异步任务。

Webhook 收到请求后通过 miaoda_analysis_task.delay(payload) 派发到这里；
若 Celery broker/worker 不可用，webhook 层会回退到后台线程调用同一函数。
"""
from __future__ import annotations

from app.tasks.celery_app import celery_app
from app.services import miaoda_analysis


@celery_app.task(name="app.tasks.miaoda.miaoda_analysis_task", bind=True, max_retries=1)
def miaoda_analysis_task(self, payload: dict) -> dict:
    try:
        return miaoda_analysis.run_influencer_analysis(payload)
    except Exception as e:  # noqa: BLE001
        # 失败已在服务内落库为 failed；这里再给 Celery 一次重试机会
        raise self.retry(exc=e, countdown=5)
