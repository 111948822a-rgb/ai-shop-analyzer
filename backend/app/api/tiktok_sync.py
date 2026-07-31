"""TikTok Shop 数据同步触发端点。

前端在「销售数据分析」页点「同步 TikTok 数据」调用此路由，后端同步拉取订单/商品
并落库；看板随即从同一张 StandardOrder 表读取聚合数据。

为避免长时间请求阻塞，默认用 BackgroundTasks 在后台执行，接口立即返回任务状态；
同时提供同步执行模式（foreground=true）便于调试。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.adapters.tiktok_shop import sync_tiktok_data
from app.core.config import settings
from app.services.tk_token_manager import get_token_status

router = APIRouter(prefix="/api/tiktok", tags=["tiktok"])


@router.get("/status")
def tiktok_status() -> dict:
    """返回 TikTok 配置与 token 状态，供前端判断「是否可同步」。"""
    configured = bool(
        settings.tk_partner_app_key
        and settings.tk_partner_app_secret
        and settings.tk_auth_shop_id
    )
    token = get_token_status()
    return {
        "configured": configured,
        "shop_id": settings.tk_auth_shop_id or None,
        "token": {
            "has_access_token": token["has_access_token"],
            "has_refresh_token": token["has_refresh_token"],
            "is_expiring_soon": token["is_expiring_soon"],
            "expires_at": token.get("expires_at"),
            "remaining_hours": token.get("remaining_hours"),
        },
    }


@router.post("/sync")
def tiktok_sync(
    background_tasks: BackgroundTasks,
    foreground: bool = Query(False, description="前台同步执行（调试用），默认后台异步"),
    days: int = Query(7, ge=1, le=365, description="回溯天数"),
) -> dict:
    """触发一次 TikTok 订单+商品同步。"""
    if not (
        settings.tk_partner_app_key
        and settings.tk_partner_app_secret
        and settings.tk_auth_shop_id
    ):
        raise HTTPException(400, "TikTok Partner API 未配置（缺 app_key/app_secret/shop_id）")

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    if foreground:
        # 同步执行，直接返回结果（小数据量调试用）
        try:
            result = sync_tiktok_data(start, end)
            return {"status": "done", "start": start, "end": end, "result": result}
        except Exception as e:
            raise HTTPException(500, f"同步失败: {e}")

    # 后台执行，立即返回
    background_tasks.add_task(sync_tiktok_data, start, end)
    return {"status": "scheduled", "start": start, "end": end, "message": "同步任务已在后台启动，稍后刷新看板查看数据"}
