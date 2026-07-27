"""飞书集成：自定义机器人 Webhook 推送（支持签名 + 消息卡片）。

- push_markdown：推送 markdown 消息（最省事，适合日报正文）。
- push_card：推送交互式消息卡片（更美观，可带按钮/链接）。
事件订阅(URL 校验 + 回调)放在 api/feishu_events.py，此处只负责发送。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.request
from typing import Any

from app.core.config import get_settings


def _sign(secret: str) -> tuple[str, int]:
    timestamp = int(time.time())
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode()
    return sign, timestamp


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def push_markdown(title: str, content: str) -> dict:
    """推送 markdown 消息到飞书群。"""
    settings = get_settings()
    if not settings.feishu_webhook_url:
        raise RuntimeError("未配置 FEISHU_WEBHOOK_URL")
    payload: dict[str, Any] = {"msg_type": "markdown", "content": {"title": title, "text": content}}
    if settings.feishu_webhook_secret:
        sign, ts = _sign(settings.feishu_webhook_secret)
        payload["timestamp"] = str(ts)
        payload["sign"] = sign
    return _post(settings.feishu_webhook_url, payload)


def push_card(card: dict) -> dict:
    """推送交互式消息卡片（更美观的日报样式）。"""
    settings = get_settings()
    if not settings.feishu_webhook_url:
        raise RuntimeError("未配置 FEISHU_WEBHOOK_URL")
    payload: dict[str, Any] = {"msg_type": "interactive", "card": card}
    if settings.feishu_webhook_secret:
        sign, ts = _sign(settings.feishu_webhook_secret)
        payload["timestamp"] = str(ts)
        payload["sign"] = sign
    return _post(settings.feishu_webhook_url, payload)


# ---------------------------------------------------------------------------
# 每日经营日报 · 交互式卡片（移动端友好）
# 设计要点：
#   - 核心指标 GMV / 订单数 加粗大字号，GMV 用红色强调
#   - 疑似水军达人用 🚨 + 红色文本标出，移动端一眼可见
#   - wide_screen_mode 适配手机横竖屏
# ---------------------------------------------------------------------------
def _fmt_roi(v) -> str:
    return f"{v:.2f}" if isinstance(v, (int, float)) else "N/A"


def build_daily_report_card(
    date_label: str,
    sales: dict,
    influencers: list[dict],
    report_md: str,
    suspicious: list[dict] | None = None,
) -> dict:
    """根据聚合数据 + 达人数据 + AI 报告，组装飞书交互式卡片 dict。"""
    gmv = sales.get("gmv", 0) or 0
    orders = sales.get("orders", 0) or 0
    aov = sales.get("avg_order_value", 0) or 0
    top = (sales.get("top_products") or [])[:3]

    # 避坑预警：is_suspicious 或 高互动(>=20%) + 极低转化(<0.5%)
    if suspicious is None:
        suspicious = [
            i
            for i in influencers
            if i.get("is_suspicious")
            or (
                (i.get("engagement_rate") or 0) >= 20
                and (i.get("conversion_rate") is not None and i.get("conversion_rate") < 0.5)
            )
        ]

    elements: list[dict] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**总 GMV**　<font color='red'>**¥{gmv:,.2f}**</font>\n"
                    f"**订单数**　**{orders:,}**\n"
                    f"**客单价**　¥{aov:,.2f}"
                ),
            },
        },
        {"tag": "hr"},
    ]

    if top:
        lines = "\n".join(
            f"{idx + 1}. {p['product']} — ¥{p['gmv']:,.2f}（{p['orders']} 单）"
            for idx, p in enumerate(top)
        )
        elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"🏆 **Top 商品**\n{lines}"}}
        )
        elements.append({"tag": "hr"})

    if suspicious:
        warn_lines = "\n".join(
            f"🚨 <font color='red'>{i['name']}</font>：互动率 {i.get('engagement_rate')}% / "
            f"转化率 {i.get('conversion_rate')}% / ROI {_fmt_roi(i.get('roi'))} "
            f"— 高互动低转化，疑似刷量，建议暂停合作"
            for i in suspicious
        )
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"⚠️ **疑似水军达人预警（{len(suspicious)} 个）**\n{warn_lines}",
                },
            }
        )
        elements.append({"tag": "hr"})

    summary = (report_md or "").strip()
    if len(summary) > 6000:
        summary = summary[:6000] + "\n\n…（完整报告见后台 /api/reports）"
    elements.append(
        {"tag": "div", "text": {"tag": "lark_md", "content": f"📝 **AI 分析摘要**\n{summary}"}}
    )
    elements.append(
        {
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": f"由 AI Shop Analyzer 自动生成 · 数据区间 {date_label}"}
            ],
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "red" if suspicious else "blue",
            "title": {"tag": "plain_text", "content": f"📊 AI Shop 每日经营日报 · {date_label}"},
        },
        "elements": elements,
    }


def push_report_card(
    date_label: str,
    sales: dict,
    influencers: list[dict],
    report_md: str,
    suspicious: list[dict] | None = None,
) -> dict:
    """组装并推送每日经营日报卡片。"""
    card = build_daily_report_card(date_label, sales, influencers, report_md, suspicious)
    return push_card(card)
