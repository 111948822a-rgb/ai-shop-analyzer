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
import time
from collections import Counter
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Header, HTTPException, Query

from app.core.config import get_settings
from app.db import SessionLocal
from app.models.standard import StandardInfluencer
from app.services import miaoda_analysis, miaoda_data_fetcher

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


def _local_influencers() -> list[dict]:
    """本地达人库兜底：当秒搭未配置/拉取为空时返回（已归一化为看板统一结构）。"""
    with SessionLocal() as db:
        rows = db.query(StandardInfluencer).all()
        return [
            {
                "influencer_id": r.creator_id,
                "name": r.name,
                "platform": r.platform.value if hasattr(r.platform, "value") else r.platform,
                "followers": r.followers,
                "engagement_rate": r.engagement_rate,
                "conversion_rate": r.conversion_rate,
                "roi": r.roi,
                "is_suspicious": r.is_suspicious,
                "niche": r.category,
            }
            for r in rows
        ]


def _load_influencer_cards(site_id: str | None = None) -> tuple[list[dict], str, bool, "str | None"]:
    """统一拉取达人卡片列表，返回 (items, source, configured, error)。

    - 优先从秒搭 OpenAPI 拉取（MIAODA_API_URL + MIAODA_API_KEY 已配置时）；
    - 失败 / 未配置 / 空 -> 回退本地库；
    - configured 标记秒搭数据源是否已配置；error 携带拉取失败的原始原因，便于前端诊断。
    """
    settings = get_settings()
    configured = bool(settings.MIAODA_API_KEY and settings.MIAODA_API_URL)

    items: list[dict] = []
    source = "local"
    error: "str | None" = None
    try:
        raw = miaoda_data_fetcher.fetch_influencers_from_miaoda(site_id)
        if raw:
            source = "miaoda"
            for r in raw:
                m = miaoda_data_fetcher.map_influencer_data(r)
                items.append(
                    {
                        "influencer_id": m["influencer_id"] or m["influencer_name"],
                        "name": m["influencer_name"],
                        "platform": m["platform"],
                        "followers": m["follower_count"],
                        "engagement_rate": m["engagement_rate"] or None,
                        "conversion_rate": m["conversion_rate"] or None,
                        "roi": m["roi"] or None,
                        "is_suspicious": m["is_suspicious"],
                        "niche": m["niche"],
                    }
                )
        elif configured:
            # 已配置但秒搭返回空：明确提示，避免静默回退本地库让用户误以为「没数据」
            error = "秒搭已配置但返回空数据：请核对 MIAODA_API_URL 路径(/openapi/influencers)、X-API-Key 权限与筛选条件"
    except Exception as e:  # noqa: BLE001
        logger.warning("秒搭达人拉取失败，回退本地库: %s", e)
        error = f"秒搭拉取失败: {e}"

    if not items:
        source = "local"
        items = _local_influencers()

    return items, source, configured, error


def _build_summary(items: list[dict]) -> dict:
    """由达人卡片列表聚合看板所需的 KPI 与可视化数据。"""
    total = len(items)
    total_followers = sum(int(i.get("followers") or 0) for i in items)
    rois = [float(i["roi"]) for i in items if i.get("roi") is not None]
    avg_roi = round(sum(rois) / len(rois), 2) if rois else 0.0
    suspicious = sum(1 for i in items if i.get("is_suspicious"))

    plat = Counter((i.get("platform") or "未知") for i in items)
    platform_distribution = [{"platform": k, "count": v} for k, v in plat.most_common()]

    top = sorted(items, key=lambda x: int(x.get("followers") or 0), reverse=True)[:10]
    top_by_followers = [
        {"name": i["name"], "platform": i.get("platform"), "followers": i.get("followers")}
        for i in top
    ]

    buckets = {"0-1": 0, "1-3": 0, "3-5": 0, "5+": 0}
    for i in items:
        r = i.get("roi")
        if r is None:
            continue
        r = float(r)
        if r < 1:
            buckets["0-1"] += 1
        elif r < 3:
            buckets["1-3"] += 1
        elif r < 5:
            buckets["3-5"] += 1
        else:
            buckets["5+"] += 1
    roi_buckets = [{"range": k, "count": v} for k, v in buckets.items()]

    scatter = [
        {
            "name": i["name"],
            "followers": i.get("followers"),
            "engagement_rate": i.get("engagement_rate"),
            "conversion_rate": i.get("conversion_rate"),
            "roi": i.get("roi"),
            "is_suspicious": bool(i.get("is_suspicious")),
        }
        for i in items
    ]

    return {
        "total": total,
        "total_followers": total_followers,
        "avg_roi": avg_roi,
        "suspicious_count": suspicious,
        "platform_distribution": platform_distribution,
        "top_by_followers": top_by_followers,
        "roi_buckets": roi_buckets,
        "scatter": scatter,
    }


@router.get("/influencers")
def list_miaoda_influencers(
    site_id: str | None = Query(None, description="可选站点过滤：US / TH / MY"),
) -> dict:
    """拉取秒搭达人数据供前端展示（统一结构，前端无需关心来源）。"""
    items, source, _, _ = _load_influencer_cards(site_id)
    return {"source": source, "items": items}


@router.get("/dashboard")
def miaoda_dashboard(
    site_id: str | None = Query(None, description="可选站点过滤：US / TH / MY"),
) -> dict:
    """达人数据看板聚合接口：拉取秒搭（或本地）达人数据，返回 KPI 与可视化所需的聚合指标。

    前端「达人评估」页直接消费本接口即可渲染数据看板；configured 标记秒搭数据源是否已配置。
    """
    items, source, configured, error = _load_influencer_cards(site_id)
    summary = _build_summary(items)
    return {"configured": configured, "source": source, "error": error, "summary": summary, "items": items}


@router.post("/evaluate")
def evaluate_influencer(
    background_tasks: BackgroundTasks,
    payload: dict[str, Any] = Body(...),
) -> dict:
    """基于秒搭（或所选）达人数据，触发 AI 评估，立即返回报告页 URL。

    前端达人评估页点击「评估」时调用：传入达人基本信息，后端生成 record_id、
    同步落 processing 记录、后台派发 AI 分析，立刻返回 report_url 供前端跳转。
    """
    name = payload.get("influencer_name") or payload.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="缺少必要字段：influencer_name(或 name)")

    inf_id = payload.get("influencer_id") or name
    record_id = f"EVAL_{inf_id}_{int(time.time() * 1000)}"
    mapped = {
        "record_id": record_id,
        "influencer_name": name,
        "platform": payload.get("platform"),
        "followers": int(payload.get("followers") or 0),
        "target_product": payload.get("target_product") or "",
    }

    # 同步建 processing 记录（保证报告页轮询不会 404），再后台跑分析
    miaoda_analysis.ensure_processing(mapped)
    channel = _dispatch(mapped, background_tasks)

    report_url = f"{get_settings().frontend_base_url}/report/influencer/{record_id}"
    logger.info("前端触发达人评估 record_id=%s 渠道=%s", record_id, channel)
    return {"success": True, "record_id": record_id, "report_url": report_url}
