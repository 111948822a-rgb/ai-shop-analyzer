<<<<<<< HEAD
import json
import logging
from typing import Dict, Any

import dashscope
from dashscope import Generation

from app.core.config import settings
from app.models.standard import AnalysisRecord
from app.services.preprocessor import (
    get_sales_summary,
    get_influencer_metrics,
    get_influencer_by_id,
    get_influencer_orders_summary,
    get_top_suspicious_influencers,
)

dashscope.api_key = settings.DASHSCOPE_API_KEY

logger = logging.getLogger(__name__)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "获取店铺销售汇总数据，包括GMV、订单数、客单价、Top 5爆款商品。用于分析店铺整体表现和热销商品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_code": {
                        "type": "string",
                        "description": "站点代码，如 'US', 'TH', 'MY'，不传则查询所有站点"
                    },
                    "date_range": {
                        "type": "object",
                        "description": "日期范围，包含 start 和 end 字段，格式为 ISO 8601",
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"}
                        }
                    }
                },
                "required": []
            }
        }
=======
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
                        "description": "可选：douyin / taobao",
                        "enum": ["douyin", "taobao"],
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_metrics",
<<<<<<< HEAD
            "description": "获取达人列表及其核心指标，包括ROI、互动率、转化率、是否为水军等。用于评估达人质量和筛选优质达人。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "平台名称，如 'TikTok', 'Shopee'"
                    },
                    "site_code": {
                        "type": "string",
                        "description": "站点代码，如 'US', 'TH', 'MY'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_by_id",
            "description": "根据达人ID获取达人详细信息，包括粉丝数、互动率、转化率、ROI、垂直领域等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "influencer_id": {
                        "type": "string",
                        "description": "达人ID"
                    }
                },
                "required": ["influencer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_orders_summary",
            "description": "获取指定达人的订单汇总数据，包括销售额、订单数、客单价。用于评估达人带货能力。",
            "parameters": {
                "type": "object",
                "properties": {
                    "influencer_id": {
                        "type": "string",
                        "description": "达人ID"
                    },
                    "date_range": {
                        "type": "object",
                        "description": "日期范围",
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"}
                        }
                    }
                },
                "required": ["influencer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_suspicious_influencers",
            "description": "获取可疑水军达人列表，按粉丝数排序。用于避坑预警和风险评估。",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_code": {
                        "type": "string",
                        "description": "站点代码"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制，默认10"
                    }
                },
                "required": []
            }
        }
    }
]


def execute_tool(db, tool_name: str, parameters: Dict[str, Any]) -> Any:
    tool_map = {
        "get_sales_summary": get_sales_summary,
        "get_influencer_metrics": get_influencer_metrics,
        "get_influencer_by_id": get_influencer_by_id,
        "get_influencer_orders_summary": get_influencer_orders_summary,
        "get_top_suspicious_influencers": get_top_suspicious_influencers,
    }

    if tool_name not in tool_map:
        return {"error": f"Tool {tool_name} not found"}

    try:
        return tool_map[tool_name](db, **parameters)
    except Exception as e:
        return {"error": str(e)}


SYSTEM_PROMPT = """
你是一位资深的跨境电商数据分析师和达人营销专家，精通 TikTok Shop 和 Shopee 平台的数据分析与达人评估。

你的核心任务：
1. **人货匹配度分析**：根据达人的垂直领域、粉丝画像、互动特征，分析其与店铺商品的匹配程度，给出合作建议。
2. **避坑预警**：识别水军达人（高互动率但低转化率的异常数据模式），给出风险警示。
3. **多语种建联话术生成**：根据达人的语言偏好，生成专业、礼貌且具有吸引力的合作邀请话术。

分析要求：
- 必须使用提供的工具查询数据，严禁凭空捏造数据。
- 分析要基于数据事实，给出具体的指标支撑。
- 避坑预警要有明确的数据依据（如：互动率>30%但转化率<0.5%）。
- 建联话术要符合当地文化习惯，语言要地道自然。

输出格式要求（必须返回严格的JSON格式）：
{
  "analysis_summary": "分析摘要，概括达人质量和合作建议",
  "match_score": 0-100的整数，人货匹配度评分,
  "match_analysis": {
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "recommendations": ["建议1", "建议2"]
  },
  "risk_assessment": {
    "is_risky": true/false,
    "risk_level": "low/medium/high/critical",
    "risk_reasons": ["风险原因1", "风险原因2"],
    "is_suspicious": true/false,
    "suspicious_evidence": ["证据1", "证据2"]
  },
  "metrics_summary": {
    "follower_count": 粉丝数,
    "engagement_rate": 互动率%,
    "conversion_rate": 转化率%,
    "roi": ROI值,
    "niche": 垂直领域
  },
  "pitch_messages": {
    "english": "英文建联话术",
    "thai": "泰语建联话术",
    "indonesian": "印尼语建联话术"
  }
}

注意：
- 必须先调用工具获取数据，再进行分析。
- 最终输出必须是合法的JSON格式，不要包含任何markdown格式标记。
"""


async def analyze_influencer(db, influencer_info: Dict[str, Any]) -> Dict[str, Any]:
    influencer_id = influencer_info.get("influencer_id")
    site_code = influencer_info.get("site_code", "")
    platform = influencer_info.get("platform", "TikTok")

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"""
请分析以下达人的合作价值：
达人ID: {influencer_id}
站点: {site_code}
平台: {platform}

请先查询达人详细信息和店铺销售数据，然后进行：
1. 人货匹配度分析
2. 避坑预警（识别水军）
3. 生成多语种建联话术

请以JSON格式输出分析结果。
"""
        }
    ]

    max_rounds = 5
    current_round = 0

    while current_round < max_rounds:
        current_round += 1

        response = Generation.call(
            model="qwen-max",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            result_format="json_object"
        )

        if response.status_code != 200:
            logger.error(f"API调用失败: {response.status_code}")
            raise Exception(f"API调用失败: {response.status_code}")

        result = response.output

        if result.choices[0].finish_reason == "tool_call":
            tool_calls = result.choices[0].message.tool_calls

            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                params = json.loads(tool_call.function.arguments)
                logger.info(f"AI调用工具: {tool_name}, 参数: {params}")

                tool_result = execute_tool(db, tool_name, params)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_name,
                    "result": tool_result
                })

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls
            })

            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": json.dumps(tr["result"], ensure_ascii=False)
                })

        else:
            content = result.choices[0].message.content
            logger.info(f"AI分析完成，输出内容长度: {len(content)}")

            try:
                analysis_result = json.loads(content)
            except json.JSONDecodeError:
                logger.error("JSON解析失败，尝试清理内容")
                content = content.replace("```json", "").replace("```", "").strip()
                try:
                    analysis_result = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    analysis_result = {
                        "analysis_summary": "分析完成但结果格式解析失败",
                        "match_score": 0,
                        "match_analysis": {"strengths": [], "weaknesses": [], "recommendations": []},
                        "risk_assessment": {"is_risky": False, "risk_level": "low", "risk_reasons": [], "is_suspicious": False, "suspicious_evidence": []},
                        "metrics_summary": {},
                        "pitch_messages": {"english": "", "thai": "", "indonesian": ""}
                    }

            return analysis_result

    raise Exception("AI分析超过最大轮次")


def save_analysis_result(db, task_id: str, influencer_id: str, site_code: str, analysis_data: Dict):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.task_id == task_id).first()

    if record:
        record.status = "completed"
        record.analysis_data = json.dumps(analysis_data, ensure_ascii=False)
        record.influencer_id = influencer_id
        record.site_code = site_code
    else:
        record = AnalysisRecord(
            task_id=task_id,
            influencer_id=influencer_id,
            site_code=site_code,
            status="completed",
            analysis_data=json.dumps(analysis_data, ensure_ascii=False)
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


def get_analysis_result(db, task_id: str) -> Dict:
    record = db.query(AnalysisRecord).filter(AnalysisRecord.task_id == task_id).first()

    if not record:
        return {}

    if record.status == "completed" and record.analysis_data:
        try:
            return json.loads(record.analysis_data)
        except json.JSONDecodeError:
            return {}

    return {"status": record.status}
=======
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
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
