<<<<<<< HEAD
import asyncio
import uuid
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db
from app.services.ai_engine import analyze_influencer, save_analysis_result, get_analysis_result

router = APIRouter(prefix="/api/miaoda", tags=["miaoda"])


analysis_tasks: Dict[str, Dict[str, Any]] = {}


def validate_miaoda_secret(request: Request):
    secret = request.headers.get("X-Miaoda-Secret")
    if not secret or secret != settings.MIAODA_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Miaoda-Secret header"
        )


@router.post("/trigger_analysis", response_class=JSONResponse)
async def trigger_analysis(request: Request):
    validate_miaoda_secret(request)

    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )

    task_id = str(uuid.uuid4())
    analysis_tasks[task_id] = {
        "status": "pending",
        "data": data,
        "result": None,
        "error": None
    }

    report_url = f"{settings.REPORTS_BASE_URL}/api/reports/{task_id}"

    asyncio.create_task(_run_analysis_background(task_id, data))

    return JSONResponse(
        content={"task_id": task_id, "report_url": report_url},
        status_code=status.HTTP_200_OK
    )


async def _run_analysis_background(task_id: str, data: Dict[str, Any]):
    analysis_tasks[task_id]["status"] = "processing"

    try:
        db = next(get_db())
        analysis_result = await analyze_influencer(db, data)
        
        influencer_id = data.get("influencer_id", "")
        site_code = data.get("site_code", "")
        save_analysis_result(db, task_id, influencer_id, site_code, analysis_result)
        
        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["result"] = analysis_result
    except Exception as e:
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = str(e)


@router.get("/analysis_status/{task_id}", response_class=JSONResponse)
async def get_analysis_status(task_id: str):
    task = analysis_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return JSONResponse(content={
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"] if task["status"] == "completed" else None,
        "error": task["error"] if task["status"] == "failed" else None
    })
=======
"""飞书秒搭 Webhook 接口 + H5 报告查询接口。

防超时设计（关键）：
  秒搭大模型分析耗时 5-15s，HTTP 直等会超时。因此采用「立刻返回 URL + iframe 轮询」：
    1. POST /api/miaoda/trigger_analysis
       校验 X-Miaoda-Secret -> 字段映射兜底 -> 【同步】落一条 processing 记录
       -> 通过 BackgroundTasks（或 Celery）异步执行真实 AI 分析 -> 立刻返回 report_url。
    2. 秒搭前端拿到 report_url，用 iframe 打开并轮询 GET /report/{id}；
       记录状态 processing -> done（或 failed）后，iframe 即展示完整报告。

- GET  /api/miaoda/report/{record_id}
    H5 报告页（秒搭 iframe 内嵌）按 record_id 拉取分析结果（含 processing/done/failed 状态）。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Header, HTTPException

from app.core.config import get_settings
from app.services import miaoda_analysis

logger = logging.getLogger("miaoda_webhook")

router = APIRouter(prefix="/api/miaoda", tags=["miaoda"])

# 秒搭可能用到的字段别名 -> 内部标准字段（大小写/驼峰/下划线都兼容）
_ID_ALIASES = ("record_id", "id", "rec_id", "recordId")
_NAME_ALIASES = ("influencer_name", "name", "creator_name", "creatorName", "influencerName")
_PLATFORM_ALIASES = ("platform", "plat")
_FOLLOWERS_ALIASES = ("followers", "fans", "fan_count", "follower_count", "fanCount")
_PRODUCT_ALIASES = (
    "target_product",
    "targetProduct",
    "product",
    "product_name",
    "goods",
    "item",
)


def _first(payload: dict, aliases: tuple, default: Any = None) -> Any:
    """按别名优先级取第一个「非空」值。"""
    for k in aliases:
        v = payload.get(k)
        if v not in (None, ""):
            return v
    return default


def _map_payload(payload: dict) -> dict:
    """兼容秒搭不同字段命名，统一映射为内部标准字段。"""
    followers_raw = _first(payload, _FOLLOWERS_ALIASES, 0)
    try:
        followers = int(followers_raw) if followers_raw is not None else 0
    except (TypeError, ValueError):
        followers = 0
    return {
        "record_id": _first(payload, _ID_ALIASES),
        "influencer_name": _first(payload, _NAME_ALIASES),
        "platform": _first(payload, _PLATFORM_ALIASES),
        "followers": followers,
        "target_product": _first(payload, _PRODUCT_ALIASES),
    }


def _dispatch(mapped: dict, background_tasks: BackgroundTasks) -> str:
    """派发异步分析任务。优先 Celery（MIAODA_USE_CELERY=1 且 broker 可用），否则 BackgroundTasks。

    返回实际使用的渠道，便于日志。
    """
    settings = get_settings()
    if settings.miaoda_use_celery:
        try:
            from app.tasks.miaoda import miaoda_analysis_task

            miaoda_analysis_task.delay(mapped)
            logger.info("已通过 Celery 派发分析任务 record_id=%s", mapped["record_id"])
            return "celery"
        except Exception as e:  # noqa: BLE001
            logger.warning("Celery 不可用，回退 BackgroundTasks: %s", e)

    # FastAPI BackgroundTasks：在响应返回后、同一进程内执行，天然防超时
    background_tasks.add_task(miaoda_analysis.run_influencer_analysis, mapped)
    logger.info("已通过 BackgroundTasks 派发分析任务 record_id=%s", mapped["record_id"])
    return "background_tasks"


@router.post("/trigger_analysis")
def trigger_analysis(
    background_tasks: BackgroundTasks,
    payload: dict[str, Any] = Body(...),
    x_miaoda_secret: str | None = Header(None, alias="X-Miaoda-Secret"),
) -> dict:
    settings = get_settings()

    # 安全校验：未配置密钥时开发期放行并告警；生产务必配置
    if not settings.miaoda_webhook_secret:
        logger.warning("未配置 MIAODA_WEBHOOK_SECRET，跳过校验（生产务必配置）")
    elif x_miaoda_secret != settings.miaoda_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid X-Miaoda-Secret")

    # 字段映射兜底（秒搭字段命名可能不统一）
    mapped = _map_payload(payload)
    if not mapped.get("record_id") or not mapped.get("influencer_name"):
        raise HTTPException(
            status_code=422,
            detail="缺少必要字段：需提供 record_id(或 id) 与 influencer_name(或 name)",
        )

    # 关键：先同步创建 processing 记录，保证 iframe 轮询不会 404
    miaoda_analysis.ensure_processing(mapped)

    # 异步派发真实 AI 分析（不阻塞 HTTP 响应）
    channel = _dispatch(mapped, background_tasks)

    report_url = f"{settings.frontend_base_url}/report/influencer/{mapped['record_id']}"
    logger.info(
        "秒搭触发分析 record_id=%s 渠道=%s 立即返回 report_url=%s",
        mapped["record_id"],
        channel,
        report_url,
    )
    return {
        "success": True,
        "message": "AI 分析已触发",
        "report_url": report_url,
    }


@router.get("/report/{record_id}")
def get_report(record_id: str) -> dict:
    from app.db import SessionLocal
    from app.models.standard import MiaodaAnalysis

    with SessionLocal() as db:
        row = db.get(MiaodaAnalysis, record_id)
        if not row:
            raise HTTPException(status_code=404, detail="分析报告不存在")
        return {
            "record_id": row.record_id,
            "status": row.status,
            "influencer_name": row.influencer_name,
            "platform": row.platform,
            "followers": row.followers,
            "target_product": row.target_product,
            "ai_match_score": row.ai_match_score,
            "ai_risk_warning": row.ai_risk_warning,
            "ai_outreach_script": row.ai_outreach_script,
            "fit_analysis": row.fit_analysis,
            "radar": row.radar,
            "multilingual": row.multilingual,
            "ai_report_url": row.ai_report_url,
            "error": row.error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
