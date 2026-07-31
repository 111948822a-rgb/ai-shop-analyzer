"""AI 分析引擎：通义千问 qwen-max + Function Calling。

核心思路（对照你说的"不要把大表扔给大模型"）：
  1. 把数据查询能力以「工具」形式声明给模型（不把大表塞进 prompt）。
  2. 模型自主决定调用 query_sales_data / get_influencer_metrics。
  3. 后端执行工具 -> 把结果回传给模型 -> 模型产出最终 Markdown 报告。

依赖：pip install dashscope
"""
from __future__ import annotations

import json

from dashscope import Generation

from app.core.config import get_settings
from app.services import ai_tools

# 工具声明（OpenAI / Dashscope 通用 schema）
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": "查询指定日期区间的店铺销售汇总，返回 GMV、订单数、客单价和 Top10 商品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                    "platform": {
                        "type": "string",
                        "description": "可选：tiktok / douyin / taobao",
                        "enum": ["tiktok", "douyin", "taobao"],
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
            "description": "查询达人指标（GMV / 订单 / ROI / 粉丝 / 互动率 / 转化率 / 疑似水军标记）。不传 name 则返回按 GMV 排序的 TopN；返回含 engagement_rate 与 conversion_rate，若互动率极高但转化率极低且 is_suspicious=true，应重点预警疑似水军/刷量达人。",
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
]

SYSTEM_PROMPT = (
    "你是资深电商数据分析师。请基于工具返回的真实数据撰写中文分析报告，"
    "包含：数据总结、问题诊断、达人匹配度打分、下一步行动建议。"
    "禁止编造任何数字；所有结论必须来自工具返回的数据。"
)


def _execute_tool(name: str, arguments: dict) -> object:
    func = ai_tools.AI_TOOLS.get(name)
    if not func:
        return {"error": f"未知工具: {name}"}
    return func(**arguments)


def _tc_attr(obj, key, default=None):
    """兼容 dashscope 返回 tool_call 为「对象」或「dict」两种形态。"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_api_tool_calls(tool_calls) -> list[dict]:
    """把 SDK 的 tool_calls 规整为可回传的 OpenAI 风格结构（兼容 dict/对象）。"""
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


def generate_report(user_query: str, max_rounds: int = 5) -> str:
    """驱动通义千问完成一次 Function Calling 循环，返回 Markdown 报告。"""
    settings = get_settings()
    if not settings.dashscope_api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用通义千问")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for _ in range(max_rounds):
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

        # 模型不再请求工具 -> 已给出最终答案
        tool_calls = _tc_attr(msg, "tool_calls")
        if not tool_calls:
            return _tc_attr(msg, "content", "") or ""

        # 执行工具并把结果回传给模型
        messages.append(
            {"role": "assistant", "content": _tc_attr(msg, "content", "") or "", "tool_calls": _to_api_tool_calls(tool_calls)}
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

    return "（已达到最大工具调用轮数，请简化问题后重试）"
