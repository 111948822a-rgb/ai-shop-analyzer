"""FastAPI 主入口：装配路由、CORS、生命周期，串起各核心模块。

保留 v1 的 upload / analyze / reports 路由，并新增飞书 webhook / 事件订阅 /
手动触发日报任务等企业版能力。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai_report, analyze, dashboard, feishu_events, miaoda_webhook, reports, tiktok_sync, upload
from app.core.config import get_settings
from app.services import feishu

import app.adapters  # noqa: F401  触发抖店等适配器自注册
import app.models.standard  # noqa: F401  确保 MiaodaAnalysis 等表被注册，create_all 才会建表


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 生产建议用 Alembic；开发期自动建表
    from app.db import Base, engine
    from sqlalchemy import text

    # 迁移：旧的 platform / status 列用的是 PostgreSQL 原生 enum 类型，
    # 新增 TIKTOK 枚举值时无法自动 ALTER TYPE，改为 VARCHAR + CHECK。
    # 检测到任一 standard 表的 platform 列为 USER-DEFINED（enum）时，
    # DROP 相关表和类型，让下面的 create_all 用新结构（VARCHAR）重建。
    if engine.dialect.name == "postgresql":
        try:
            with engine.connect() as conn:
                # 检测三个表里是否有任一 platform 列仍是原生 enum
                rows = conn.execute(text(
                    "SELECT table_name, data_type FROM information_schema.columns "
                    "WHERE column_name = 'platform' "
                    "AND table_name IN ('standard_orders','standard_products','standard_influencers')"
                )).fetchall()
                need_migrate = any(r[1] == "USER-DEFINED" for r in rows)
                if need_migrate:
                    print(f"[migrate] 检测到旧 PG enum 列: {rows}，重建 standard 表为 VARCHAR 结构...")
                    conn.execute(text("DROP TABLE IF EXISTS standard_orders CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS standard_products CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS standard_influencers CASCADE"))
                    # 清理可能残留的 enum 类型（多种可能的命名）
                    for t in ("platform", "orderstatus", "Platform", "OrderStatus"):
                        conn.execute(text(f"DROP TYPE IF EXISTS {t} CASCADE"))
                    # 兜底：删除所有名为 platform/orderstatus 的独立类型
                    conn.execute(text(
                        "DO $$ DECLARE r RECORD; BEGIN "
                        "FOR r IN SELECT t.typname FROM pg_type t "
                        "JOIN pg_namespace n ON t.typnamespace=n.oid "
                        "WHERE n.nspname='public' AND t.typtype='e' "
                        "AND t.typname IN ('platform','orderstatus','Platform','OrderStatus') "
                        "LOOP EXECUTE 'DROP TYPE IF EXISTS ' || r.typname || ' CASCADE'; END LOOP; END $$;"
                    ))
                    conn.commit()
                    print("[migrate] 旧表与 enum 类型已删除，将由 create_all 重建")
                else:
                    print(f"[migrate] platform 列已是 VARCHAR，无需迁移: {rows}")
        except Exception as e:
            print(f"[migrate] 迁移检查跳过: {e}")

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Shop Analyzer API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ai-shop-analyzer-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# ---- TikTok Shop 数据同步 ----
app.include_router(tiktok_sync.router)
# ---- AI 分析报告生成 ----
app.include_router(ai_report.router)


@app.get("/health")
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
