"""秒搭达人 AI 分析服务（核心闭环）。

流程：
  1. 秒搭 Webhook 传入达人信息（record_id / influencer_name / platform / followers / target_product）。
  2. 这里调用通义千问 Function Calling：
       - 先用 query_sales_data / get_influencer_metrics 拉取「店铺商品 + 达人历史」真实数据；
       - 再调用 submit_influencer_analysis 工具，由模型产出结构化结果：
           ai_match_score(0-100) / ai_risk_warning / ai_outreach_script /
           fit_analysis(人货匹配) / radar(6 维) / multilingual_scripts(多语种话术)。
  3. 结果落库（MiaodaAnalysis），并生成 H5 报告链接 ai_report_url。
  4. 主动回写秒搭底层飞书多维表格（feishu_bitable.write_back_analysis），秒搭前台即见 AI 字段。

无密钥 / 演示模式：设置 MIAODA_MOCK=1 或未配置 DASHSCOPE_API_KEY 时，走 _mock_result，
不消耗 token、不依赖外部，便于联调与测试。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from dashscope import Generation
from sqlalchemy import select

from app.adapters import feishu_bitable
from app.core.config import get_settings
from app.db import SessionLocal
from app.models.standard import MiaodaAnalysis
from app.services import ai_tools

logger = logging.getLogger("miaoda_analysis")

# 雷达图 6 个维度（中文标签映射，模型返回英文 key）
RADAR_LABELS: dict[str, str] = {
    "fan_quality": "粉丝质量",
    "content_relevance": "内容契合度",
    "product_fit": "货品匹配度",
    "conversion_potential": "转化潜力",
    "cost_efficiency": "投放性价比",
    "risk_control": "风控健康度",
}

# 通义千问工具声明：2 个数据工具 + 1 个结构化提交工具
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": "查询指定日期区间的店铺销售汇总，返回 GMV、订单数、客单价和 Top10 商品。用于判断达人目标货品与店铺爆款的契合度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                    "platform": {
                        "type": "string",
                        "description": "可选：douyin / taobao",
                        "enum": ["douyin", "taobao"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_metrics",
            "description": "查询达人指标（GMV / 订单 / ROI / 粉丝 / 互动率 / 转化率 / 疑似水军标记）。可传 creator_name 精确匹配某达人。",
            "parameters": {
                "type": "object",
                "properties": {
                    "creator_name": {"type": "string", "description": "达人昵称，可选"},
                    "top_n": {"type": "integer", "description": "返回前 N 个达人，默认 10"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_influencer_analysis",
            "description": (
                "当你已完成数据探查，必须调用本工具提交【最终结构化分析结果】。不要返回自然语言，只能调用本工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ai_match_score": {
                        "type": "integer",
                        "description": "整体匹配度打分，0-100 整数",
                    },
                    "ai_risk_warning": {
                        "type": "string",
                        "description": "风险预警文案。如无风险写「暂未发现明显风险」；如疑似水军/低转化/数据异常，明确写出并给处置建议。",
                    },
                    "ai_outreach_script": {
                        "type": "string",
                        "description": "一段中文建联话术，自然、专业、可直接发给达人",
                    },
                    "fit_analysis": {
                        "type": "string",
                        "description": "人货匹配分析，中文 2-4 句，说明达人与目标货品/店铺受众的契合点与差异点",
                    },
                    "radar": {
                        "type": "object",
                        "description": "6 个维度打分(各 0-100) 的对象，key 必须为：fan_quality, content_relevance, product_fit, conversion_potential, cost_efficiency, risk_control",
                        "properties": {
                            "fan_quality": {"type": "integer"},
                            "content_relevance": {"type": "integer"},
                            "product_fit": {"type": "integer"},
                            "conversion_potential": {"type": "integer"},
                            "cost_efficiency": {"type": "integer"},
                            "risk_control": {"type": "integer"},
                        },
                        "required": [
                            "fan_quality",
                            "content_relevance",
                            "product_fit",
                            "conversion_potential",
                            "cost_efficiency",
                            "risk_control",
                        ],
                    },
                    "multilingual_scripts": {
                        "type": "object",
                        "description": "多语种建联话术，至少包含 zh(中文) 与 en(英文) 两个 key",
                        "properties": {
                            "zh": {"type": "string"},
                            "en": {"type": "string"},
                        },
                        "required": ["zh", "en"],
                    },
                },
                "required": [
                    "ai_match_score",
                    "ai_risk_warning",
                    "ai_outreach_script",
                    "fit_analysis",
                    "radar",
                    "multilingual_scripts",
                ],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "你是资深电商达人投放分析师。请先调用 query_sales_data 获取店铺近期销售与 Top 商品（按给定平台），"
    "再调用 get_influencer_metrics 获取该达人历史指标（若有），结合传入的粉丝量、目标商品、平台，"
    "对该达人做深度评估。最后【必须】调用 submit_influencer_analysis 提交结构化结果。"
    "所有结论必须基于工具返回的真实数据，禁止编造任何数字；若数据不足以判断某项，按保守值打分。"
)


# ----------------------------- 工具复用（与 ai_engine 同款兼容处理）-----------------------------
def _tc_attr(obj: Any, key: str, default: Any = None) -> Any:
    """兼容 dashscope 返回的 tool_call 为对象或 dict。"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_api_tool_calls(tool_calls: Any) -> list[dict]:
    out = []
    for tc in tool_calls:
        func = _tc_attr(tc, "function", {})
        out.append(
            {
                "id": _tc_attr(tc, "id"),
                "type": "function",
                "function": {
                    "name": _tc_attr(func, "name"),
                    "arguments": _tc_attr(func, "arguments", "{}"),
                },
            }
        )
    return out


def _execute_tool(name: str, arguments: dict) -> Any:
    func = ai_tools.AI_TOOLS.get(name)
    if not func:
        return {"error": f"未知工具: {name}"}
    return func(**arguments)


def _normalize(args: dict) -> dict:
    """把模型提交的参数规整成我们落库/回写用的结构。"""
    radar_obj = args.get("radar") or {}
    radar = [
        {"dimension": RADAR_LABELS.get(k, k), "key": k, "value": int(v)}
        for k, v in radar_obj.items()
        if k in RADAR_LABELS
    ]
    ml = args.get("multilingual_scripts") or {}
    multilingual = {
        "zh": ml.get("zh") or args.get("ai_outreach_script", ""),
        "en": ml.get("en") or "",
    }
    return {
        "ai_match_score": int(args.get("ai_match_score", 0)),
        "ai_risk_warning": args.get("ai_risk_warning", ""),
        "ai_outreach_script": args.get("ai_outreach_script", ""),
        "fit_analysis": args.get("fit_analysis", ""),
        "radar": radar,
        "multilingual": multilingual,
    }


def _mock_result(payload: dict) -> dict:
    """演示/无密钥模式：基于真实达人数据（若有）生成一个合理结果，不消耗 token。"""
    name = payload.get("influencer_name", "")
    followers = int(payload.get("followers") or 0)
    platform = payload.get("platform", "")
    target = payload.get("target_product", "")

    score = 72
    warning = "（演示模式）暂未发现明显风险，建议小预算测试后放量。"
    try:
        m = ai_tools.get_influencer_metrics(creator_name=name)
        influencers = m.get("influencers", [])
        if influencers:
            inf = influencers[0]
            roi = inf.get("roi") or 1.0
            score = max(20, min(98, int(roi * 30 + min(followers, 1_000_000) / 1_000_000 * 40)))
            if inf.get("is_suspicious"):
                warning = "⚠️ 该达人历史数据疑似水军/刷量（高互动低转化），强烈建议暂缓合作！"
                score = 25
    except Exception:
        pass

    return {
        "ai_match_score": score,
        "ai_risk_warning": warning,
        "ai_outreach_script": (
            f"您好 {name}，我们是专注「{target or '品类'}」的电商团队，看到您在"
            f"{platform or '平台'}的内容表现很出色，想邀请您体验我们的产品并探讨带货合作，"
            "可提供专属样品与佣金方案。"
        ),
        "fit_analysis": (
            f"{name} 粉丝量约 {followers:,}，主打与「{target or '相关'}」方向契合的内容，"
            "与店铺货盘在受众画像上匹配度较高，适合做「种草+转化」组合投放；"
            "建议先以短视频种草测款，再视 ROI 加投直播。"
        ),
        "radar": [
            {"dimension": "粉丝质量", "key": "fan_quality", "value": 78},
            {"dimension": "内容契合度", "key": "content_relevance", "value": 82},
            {"dimension": "货品匹配度", "key": "product_fit", "value": 75},
            {"dimension": "转化潜力", "key": "conversion_potential", "value": 68},
            {"dimension": "投放性价比", "key": "cost_efficiency", "value": 70},
            {"dimension": "风控健康度", "key": "risk_control", "value": 80},
        ],
        "multilingual": {
            "zh": f"您好 {name}，我们是「{target or '品牌'}」电商团队，期待与您合作带货。",
            "en": (
                f"Hi {name}, we are an e-commerce team specializing in "
                f"{target or 'our products'}. We'd love to explore a collaboration with you."
            ),
        },
    }


def analyze_influencer_llm(payload: dict) -> dict:
    """调用通义千问，返回结构化分析结果 dict。"""
    settings = get_settings()
    if not settings.dashscope_api_key or os.getenv("MIAODA_MOCK") == "1":
        return _mock_result(payload)

    # 构造用户问题：把秒搭传入的达人上下文带给模型
    user_query = (
        f"请分析以下达人是否适合与我们店铺合作：\n"
        f"- 达人昵称：{payload.get('influencer_name')}\n"
        f"- 平台：{payload.get('platform') or '未指定'}\n"
        f"- 粉丝量：{payload.get('followers') or '未知'}\n"
        f"- 目标商品/货品：{payload.get('target_product') or '未指定'}\n"
        f"请先查数据，再提交结构化分析结果。"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for _ in range(6):
        resp = Generation.call(
            model=settings.qwen_model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            result_format="message",
            api_key=settings.dashscope_api_key,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"通义千问调用失败: {resp.code} {resp.message}")

        msg = resp.output.choices[0].message
        tool_calls = _tc_attr(msg, "tool_calls")
        if not tool_calls:
            # 模型没调用工具也没提交 -> 继续引导
            messages.append(
                {"role": "assistant", "content": _tc_attr(msg, "content", "") or ""}
            )
            continue

        # 找到 submit 工具即视为完成
        submit = None
        for tc in tool_calls:
            func = _tc_attr(tc, "function", {})
            if _tc_attr(func, "name") == "submit_influencer_analysis":
                submit = tc
                break
        if submit:
            args = json.loads(
                _tc_attr(_tc_attr(submit, "function", {}), "arguments", "{}") or "{}"
            )
            return _normalize(args)

        # 执行数据工具并回传
        messages.append(
            {
                "role": "assistant",
                "content": _tc_attr(msg, "content", "") or "",
                "tool_calls": _to_api_tool_calls(tool_calls),
            }
        )
        for tc in tool_calls:
            func = _tc_attr(tc, "function", {})
            name = _tc_attr(func, "name")
            args = json.loads(_tc_attr(func, "arguments", "{}") or "{}")
            result = _execute_tool(name, args)
            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    raise RuntimeError("通义千问未在限定轮数内提交结构化分析结果")


def _persist(payload: dict, result: dict | None, status: str, error: str | None) -> None:
    """落库 / 更新 MiaodaAnalysis 记录。"""
    settings = get_settings()
    with SessionLocal() as db:
        row = db.get(MiaodaAnalysis, payload["record_id"])
        if row is None:
            row = MiaodaAnalysis(
                record_id=payload["record_id"],
                influencer_name=payload.get("influencer_name", ""),
                platform=payload.get("platform"),
                followers=int(payload.get("followers") or 0),
                target_product=payload.get("target_product"),
            )
            db.add(row)

        row.platform = payload.get("platform", row.platform)
        row.followers = int(payload.get("followers") or row.followers or 0)
        row.target_product = payload.get("target_product", row.target_product)
        row.status = status
        row.error = error

        if result is not None:
            report_url = (
                f"{settings.frontend_base_url}/report/influencer/{payload['record_id']}"
            )
            row.ai_match_score = result.get("ai_match_score")
            row.ai_risk_warning = result.get("ai_risk_warning")
            row.ai_outreach_script = result.get("ai_outreach_script")
            row.fit_analysis = result.get("fit_analysis")
            row.radar = result.get("radar")
            row.multilingual = result.get("multilingual")
            row.ai_report_url = report_url
            result["ai_report_url"] = report_url
        db.commit()


def ensure_processing(payload: dict) -> None:
    """Webhook 返回前同步创建/更新一条 processing 记录。

    目的：避免秒搭 iframe 打开 report_url 后立刻轮询 GET /report/{id} 时
    因后台分析尚未落库而出现 404。这条记录会在 BackgroundTasks/Celery
    真正跑分析时被 _persist(..., 'done', ...) 覆盖为最终结果。
    """
    with SessionLocal() as db:
        row = db.get(MiaodaAnalysis, payload["record_id"])
        if row is None:
            row = MiaodaAnalysis(
                record_id=payload["record_id"],
                influencer_name=payload.get("influencer_name", ""),
                platform=payload.get("platform"),
                followers=int(payload.get("followers") or 0),
                target_product=payload.get("target_product"),
                status="processing",
            )
            db.add(row)
        else:
            # 已存在则刷新为 processing（例如重复触发），并补全新传入的字段
            row.status = "processing"
            row.influencer_name = payload.get("influencer_name", row.influencer_name)
            row.platform = payload.get("platform", row.platform)
            row.followers = int(payload.get("followers") or row.followers or 0)
            row.target_product = payload.get("target_product", row.target_product)
            row.error = None
        db.commit()
        logger.info("已同步创建 processing 记录 record_id=%s", payload["record_id"])


def run_influencer_analysis(payload: dict) -> dict:
    """对外主入口：分析 -> 落库 -> 主动回写多维表格。可在 Celery 或后台线程中调用。"""
    record_id = payload.get("record_id")
    if not record_id or not payload.get("influencer_name"):
        raise ValueError("payload 必须包含 record_id 与 influencer_name")

    # 先落一条 processing 记录，H5 页据此显示「分析中」
    _persist(payload, None, "processing", None)

    try:
        result = analyze_influencer_llm(payload)
        _persist(payload, result, "done", None)
    except Exception as e:  # noqa: BLE001
        logger.exception("达人分析失败 record_id=%s", record_id)
        _persist(payload, None, "failed", str(e))
        raise

    # 主动回写秒搭底层多维表格（best effort：失败不影响主流程，仅告警）
    try:
        feishu_bitable.write_back_analysis(record_id, result)
    except Exception as e:  # noqa: BLE001
        logger.warning("多维表格回写失败(不影响主流程) record_id=%s: %s", record_id, e)

    return result
