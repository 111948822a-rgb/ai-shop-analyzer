"""飞书事件订阅路由（预留）：URL 验证 + 回调入口。

未来在此实现群内 @机器人 对话：
  1) 校验 verification token / 签名（config.feishu_event_verification_token）
  2) 按 event 类型（message / event_callback）路由到对话处理
  3) 调 AI Engine 生成回复，再通过 webhook 或 reply 接口回传
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/feishu", tags=["feishu"])


@router.post("/events")
async def feishu_events(request: Request) -> dict:
    body = await request.json()
    # 飞书订阅时的 URL 验证挑战
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    # TODO: 校验 token / 签名，按 event 类型路由到对话处理
    return {"code": 0}
