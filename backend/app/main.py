<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.miaoda_webhook import router as miaoda_router
from app.api.reports import router as reports_router

app = FastAPI(
    title="AI Shop Analyzer API",
    description="跨境电商店铺数据AI分析、达人评估与避坑预警",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
=======
"""FastAPI 主入口：装配路由、CORS、生命周期，串起各核心模块。

保留 v1 的 upload / analyze / reports 路由，并新增飞书 webhook / 事件订阅 /
手动触发日报任务等企业版能力。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, dashboard, feishu_events, miaoda_webhook, reports, upload
from app.core.config import get_settings
from app.services import feishu

import app.adapters  # noqa: F401  触发抖店等适配器自注册
import app.models.standard  # noqa: F401  确保 MiaodaAnalysis 等表被注册，create_all 才会建表


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 生产建议用 Alembic；开发期自动建表
    from app.db import Base, engine

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Shop Analyzer API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
app.include_router(miaoda_router)
app.include_router(reports_router)


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {"message": "AI Shop Analyzer API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
=======
settings = get_settings()

# ---- v1 路由（上传 / 分析 / 报告）----
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(reports.router)
# ---- 企业版路由（飞书）----
app.include_router(feishu_events.router)
# ---- 数据看板路由（前端 Dashboard 聚合数据）----
app.include_router(dashboard.router)
# ---- 飞书秒搭 Webhook + H5 报告查询 ----
app.include_router(miaoda_webhook.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------- 飞书 Webhook 推送（供其他服务 / 前端调用）----------------
@app.post("/api/feishu/push")
def feishu_push(payload: dict[str, Any] = Body(...)) -> dict:
    return feishu.push_markdown(payload.get("title", "通知"), payload.get("content", ""))


# ---------------- 手动触发日报任务（测试用）----------------
@app.post("/api/tasks/daily-report/trigger")
def trigger_daily_report() -> dict:
    from app.tasks.scheduled import daily_report_task

    task = daily_report_task.delay()
    return {"task_id": task.id}
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
