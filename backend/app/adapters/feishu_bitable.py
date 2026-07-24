"""飞书多维表格（Bitable）回写适配器。

业务侧「飞书秒搭」底层就是一张飞书多维表格。AI 分析完成后，我们需要
【主动】把结果写回这张表的对应记录，这样秒搭前台无需任何改造即可看到 AI 字段。

与 app/services/feishu.py（自定义机器人 Webhook 推送）的区别：
  - feishu.py 是「群机器人」，只能往群里发消息，不能写业务数据。
  - 这里用「飞书开放平台」应用身份（app_id/app_secret）拿 tenant_access_token，
    调用 Bitable Open API 直接改业务表记录。

核心方法：
  - get_tenant_access_token()：换取并缓存 tenant_access_token。
  - write_back_analysis(record_id, result)：把 AI 结果按字段映射更新到指定 record_id。
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from app.core.config import get_settings

# tenant_access_token 缓存（进程内，2 小时内复用）
_TOKEN_CACHE: dict[str, Any] = {"token": None, "exp": 0}

# 内部结果 key -> 多维表格列名（API 字段名）。
# 若你秒搭底表的列名不同，只改这里即可，无需动业务代码。
BITABLE_FIELD_MAP: dict[str, str] = {
    "ai_match_score": "ai_match_score",
    "ai_risk_warning": "ai_risk_warning",
    "ai_outreach_script": "ai_outreach_script",
    "ai_report_url": "ai_report_url",
}


def get_tenant_access_token() -> str:
    """用应用凭证换取 tenant_access_token（带进程内缓存，提前 60s 刷新）。"""
    settings = get_settings()
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        raise RuntimeError("未配置 FEISHU_APP_ID / FEISHU_APP_SECRET，无法回写多维表格")

    now = time.time()
    if _TOKEN_CACHE["token"] and _TOKEN_CACHE["exp"] > now + 60:
        return _TOKEN_CACHE["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = {
        "app_id": settings.feishu_app_id,
        "app_secret": settings.feishu_app_secret,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read().decode("utf-8"))

    if resp.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {resp}")
    token = resp["tenant_access_token"]
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["exp"] = now + int(resp.get("expire", 7200))
    return token


def _api_patch(url: str, payload: dict, token: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="PATCH",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def write_back_analysis(record_id: str, result: dict) -> dict:
    """把 AI 分析结果按 BITABLE_FIELD_MAP 更新到秒搭底层多维表格的指定记录。

    result 至少包含 ai_match_score / ai_risk_warning / ai_outreach_script / ai_report_url。
    返回飞书 API 原始响应；字段缺失或不可写时优雅跳过。
    """
    settings = get_settings()
    if not settings.miaoda_bitable_app_token or not settings.miaoda_bitable_table_id:
        raise RuntimeError("未配置 MIAODA_BITABLE_APP_TOKEN / MIAODA_BITABLE_TABLE_ID，无法回写")

    token = get_tenant_access_token()

    fields: dict[str, Any] = {}
    for key, col in BITABLE_FIELD_MAP.items():
        if key in result and result[key] is not None:
            fields[col] = result[key]
    if not fields:
        return {"ok": False, "reason": "无字段可写入"}

    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
        f"{settings.miaoda_bitable_app_token}/tables/"
        f"{settings.miaoda_bitable_table_id}/records/{record_id}"
    )
    resp = _api_patch(url, {"fields": fields}, token)
    if resp.get("code") != 0:
        raise RuntimeError(f"多维表格回写失败: {resp}")
    return resp
