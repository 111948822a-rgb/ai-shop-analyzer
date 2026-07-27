import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

import dashscope
from dashscope import Generation

from app.core.config import settings
from app.core.database import SessionLocal, engine
from sqlalchemy import func

from app.models.standard import StandardOrder, StandardProduct, StandardInfluencer, ReportRecord
from app.services.preprocessor import get_sales_summary, get_influencer_metrics, get_top_suspicious_influencers

dashscope.api_key = settings.DASHSCOPE_API_KEY

logger = logging.getLogger(__name__)


def get_weekly_date_range() -> Dict[str, str]:
    today = date.today()
    end_date = today
    start_date = today - timedelta(days=6)
    return {
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d")
    }


def get_monthly_date_range() -> Dict[str, str]:
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    return {
        "start": start_of_month.strftime("%Y-%m-%d"),
        "end": today.strftime("%Y-%m-%d")
    }


def get_influencer_product_analysis(db, date_range: Dict[str, str]) -> List[Dict]:
    start_date = datetime.fromisoformat(date_range["start"])
    end_date = datetime.fromisoformat(date_range["end"])

    results = db.query(
        StandardInfluencer.influencer_id,
        StandardInfluencer.influencer_name,
        StandardProduct.product_id,
        StandardProduct.product_name,
        func.sum(StandardOrder.order_amount).label("total_sales"),
        func.count(StandardOrder.order_id).label("total_orders"),
        func.avg(StandardOrder.order_amount).label("avg_order_value"),
        func.sum(StandardOrder.quantity).label("total_units"),
        StandardInfluencer.conversion_rate,
        StandardInfluencer.roi,
    ).join(StandardOrder, StandardInfluencer.influencer_id == StandardOrder.influencer_id)\
     .join(StandardProduct, StandardOrder.product_id == StandardProduct.product_id)\
     .filter(StandardOrder.order_date.between(start_date, end_date))\
     .group_by(StandardInfluencer.influencer_id, StandardProduct.product_id)\
     .order_by(func.sum(StandardOrder.order_amount).desc())\
     .limit(20)\
     .all()

    return [
        {
            "influencer_id": r.influencer_id,
            "influencer_name": r.influencer_name,
            "product_id": r.product_id,
            "product_name": r.product_name,
            "total_sales": round(r.total_sales or 0, 2),
            "total_orders": r.total_orders or 0,
            "avg_order_value": round(r.avg_order_value or 0, 2),
            "total_units": r.total_units or 0,
            "conversion_rate": round(r.conversion_rate or 0, 4),
            "roi": round(r.roi or 0, 2),
        }
        for r in results
    ]


def get_daily_sales_trend(db, date_range: Dict[str, str]) -> List[Dict]:
    start_date = datetime.fromisoformat(date_range["start"])
    end_date = datetime.fromisoformat(date_range["end"])

    results = db.query(
        func.date(StandardOrder.order_date).label("date"),
        func.sum(StandardOrder.order_amount).label("daily_gmv"),
        func.count(StandardOrder.order_id).label("daily_orders"),
        func.sum(StandardOrder.quantity).label("daily_units"),
    ).filter(StandardOrder.order_date.between(start_date, end_date))\
     .group_by(func.date(StandardOrder.order_date))\
     .order_by(func.date(StandardOrder.order_date))\
     .all()

    return [
        {
            "date": str(r.date),
            "daily_gmv": round(r.daily_gmv or 0, 2),
            "daily_orders": r.daily_orders or 0,
            "daily_units": r.daily_units or 0,
        }
        for r in results
    ]


def get_product_sales_ranking(db, date_range: Dict[str, str], limit: int = 10) -> List[Dict]:
    start_date = datetime.fromisoformat(date_range["start"])
    end_date = datetime.fromisoformat(date_range["end"])

    results = db.query(
        StandardProduct.product_id,
        StandardProduct.product_name,
        StandardProduct.product_category,
        StandardProduct.product_price,
        func.sum(StandardOrder.order_amount).label("total_sales"),
        func.count(StandardOrder.order_id).label("total_orders"),
        func.sum(StandardOrder.quantity).label("total_units"),
    ).join(StandardOrder)\
     .filter(StandardOrder.order_date.between(start_date, end_date))\
     .group_by(StandardProduct.product_id)\
     .order_by(func.sum(StandardOrder.order_amount).desc())\
     .limit(limit)\
     .all()

    return [
        {
            "product_id": r.product_id,
            "product_name": r.product_name,
            "category": r.product_category,
            "price": round(r.product_price or 0, 2),
            "total_sales": round(r.total_sales or 0, 2),
            "total_orders": r.total_orders or 0,
            "total_units": r.total_units or 0,
            "avg_order_value": round((r.total_sales or 0) / max(r.total_orders or 1, 1), 2),
        }
        for r in results
    ]


def get_influencer_performance(db, date_range: Dict[str, str], limit: int = 10) -> List[Dict]:
    start_date = datetime.fromisoformat(date_range["start"])
    end_date = datetime.fromisoformat(date_range["end"])

    results = db.query(
        StandardInfluencer.influencer_id,
        StandardInfluencer.influencer_name,
        StandardInfluencer.follower_count,
        StandardInfluencer.engagement_rate,
        StandardInfluencer.conversion_rate,
        StandardInfluencer.roi,
        StandardInfluencer.is_suspicious,
        func.sum(StandardOrder.order_amount).label("total_sales"),
        func.count(StandardOrder.order_id).label("total_orders"),
    ).outerjoin(StandardOrder, StandardInfluencer.influencer_id == StandardOrder.influencer_id)\
     .filter(
         (StandardOrder.order_date.between(start_date, end_date)) |
         (StandardOrder.order_id.is_(None))
     )\
     .group_by(StandardInfluencer.influencer_id)\
     .order_by(func.sum(StandardOrder.order_amount).desc())\
     .limit(limit)\
     .all()

    return [
        {
            "influencer_id": r.influencer_id,
            "influencer_name": r.influencer_name,
            "follower_count": r.follower_count or 0,
            "engagement_rate": round(r.engagement_rate or 0, 4),
            "conversion_rate": round(r.conversion_rate or 0, 4),
            "roi": round(r.roi or 0, 2),
            "is_suspicious": r.is_suspicious or False,
            "total_sales": round(r.total_sales or 0, 2),
            "total_orders": r.total_orders or 0,
        }
        for r in results
    ]


def get_site_breakdown(db, date_range: Dict[str, str]) -> List[Dict]:
    start_date = datetime.fromisoformat(date_range["start"])
    end_date = datetime.fromisoformat(date_range["end"])

    results = db.query(
        StandardOrder.site_code,
        StandardOrder.currency,
        func.sum(StandardOrder.order_amount).label("total_gmv"),
        func.count(StandardOrder.order_id).label("total_orders"),
        func.avg(StandardOrder.order_amount).label("avg_order_value"),
    ).filter(StandardOrder.order_date.between(start_date, end_date))\
     .group_by(StandardOrder.site_code, StandardOrder.currency)\
     .order_by(func.sum(StandardOrder.order_amount).desc())\
     .all()

    return [
        {
            "site_code": r.site_code,
            "currency": r.currency or "USD",
            "total_gmv": round(r.total_gmv or 0, 2),
            "total_orders": r.total_orders or 0,
            "avg_order_value": round(r.avg_order_value or 0, 2),
        }
        for r in results
    ]


REPORT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "获取店铺销售汇总数据，包括GMV、订单数、客单价、Top 5爆款商品。用于分析店铺整体表现。",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_code": {"type": "string", "description": "站点代码"},
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_metrics",
            "description": "获取达人列表及其核心指标，包括ROI、互动率、转化率。用于评估达人质量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "site_code": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_suspicious_influencers",
            "description": "获取可疑水军达人列表。用于避坑预警。",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_code": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_sales_ranking",
            "description": "获取商品销售排行榜，按GMV排序。用于分析热销商品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}},
                    "limit": {"type": "integer"}
                },
                "required": ["date_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_performance",
            "description": "获取达人带货表现排行榜，按销售额排序。用于评估达人带货能力。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}},
                    "limit": {"type": "integer"}
                },
                "required": ["date_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_site_breakdown",
            "description": "获取各站点销售数据分解。用于跨站点对比分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
                },
                "required": ["date_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_sales_trend",
            "description": "获取每日销售趋势数据。用于分析销售波动和趋势。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
                },
                "required": ["date_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_influencer_product_analysis",
            "description": "获取达人-商品交叉分析数据，计算每个达人带货每个商品的销售额、订单数、ROI等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
                },
                "required": ["date_range"]
            }
        }
    },
]


def execute_report_tool(db, tool_name: str, parameters: Dict[str, Any]) -> Any:
    tool_map = {
        "get_sales_summary": get_sales_summary,
        "get_influencer_metrics": get_influencer_metrics,
        "get_top_suspicious_influencers": get_top_suspicious_influencers,
        "get_product_sales_ranking": get_product_sales_ranking,
        "get_influencer_performance": get_influencer_performance,
        "get_site_breakdown": get_site_breakdown,
        "get_daily_sales_trend": get_daily_sales_trend,
        "get_influencer_product_analysis": get_influencer_product_analysis,
    }

    if tool_name not in tool_map:
        return {"error": f"Tool {tool_name} not found"}

    try:
        return tool_map[tool_name](db, **parameters)
    except Exception as e:
        return {"error": str(e)}


REPORT_SYSTEM_PROMPT = """
你是一位资深的跨境电商数据分析师，精通 TikTok Shop 和 Shopee 平台的数据分析与报告生成。

你的核心任务：基于真实的店铺数据和达人数据，生成结构化的周度/月度分析报告。

报告结构要求：
1. **核心业绩概览**：GMV、订单数、客单价、同比环比变化
2. **商品红黑榜**：Top 5 热销商品（红榜）和表现不佳商品（黑榜）
3. **达人红黑榜**：Top 5 优质达人（红榜）和疑似水军达人（黑榜/预警）
4. **跨站点分析**：各站点销售贡献对比
5. **销售趋势分析**：每日销售波动和趋势解读
6. **异动归因分析**：异常数据的原因分析（如突增、骤降）
7. **下一步行动建议**：基于数据的具体运营建议

输出格式要求（必须返回严格的JSON格式）：
{
  "report_title": "报告标题",
  "report_type": "weekly/monthly",
  "period": "日期范围",
  "core_summary": {
    "total_gmv": 总GMV,
    "total_orders": 订单数,
    "avg_order_value": 客单价,
    "gmv_growth": GMV同比增长率%,
    "order_growth": 订单同比增长率%
  },
  "product_red_list": [Top 5热销商品],
  "product_black_list": [表现不佳商品],
  "influencer_red_list": [Top 5优质达人],
  "influencer_black_list": [疑似水军达人],
  "site_breakdown": [各站点数据],
  "trend_analysis": "趋势分析文本",
  "anomaly_analysis": "异动归因分析",
  "action_suggestions": ["建议1", "建议2", "建议3"],
  "generated_at": "生成时间"
}

注意：
- 必须先调用工具获取数据，再进行分析。
- 最终输出必须是合法的JSON格式，不要包含任何markdown格式标记。
- 水军达人用红色🚨标出，优质达人用绿色✅标出。
"""


def _generate_fallback_report(db, report_type: str, date_range: Dict[str, str], site_code: Optional[str] = None) -> Dict[str, Any]:
    sales_summary = get_sales_summary(db, date_range=date_range)
    product_ranking = get_product_sales_ranking(db, date_range=date_range, limit=10)
    influencer_performance = get_influencer_performance(db, date_range=date_range, limit=10)
    site_breakdown = get_site_breakdown(db, date_range=date_range)
    daily_trend = get_daily_sales_trend(db, date_range=date_range)
    suspicious_influencers = get_top_suspicious_influencers(db, limit=5)

    product_red_list = product_ranking[:5]
    product_black_list = product_ranking[-3:]

    influencer_red_list = [
        inf for inf in influencer_performance
        if not inf.get("is_suspicious") and inf.get("total_sales", 0) > 0
    ][:5]

    influencer_black_list = []
    for inf in suspicious_influencers[:5]:
        influencer_black_list.append({
            "influencer_id": inf.get("influencer_id"),
            "influencer_name": inf.get("influencer_name"),
            "follower_count": inf.get("follower_count", 0),
            "engagement_rate": inf.get("engagement_rate", 0),
            "conversion_rate": inf.get("conversion_rate", 0),
            "risk_reason": inf.get("suspicious_reason", "高互动低转化，疑似水军"),
        })

    gmv_values = [d.get("daily_gmv", 0) for d in daily_trend]
    avg_gmv = sum(gmv_values) / len(gmv_values) if gmv_values else 0
    max_gmv = max(gmv_values) if gmv_values else 0
    min_gmv = min(gmv_values) if gmv_values else 0

    trend_analysis = ""
    if len(gmv_values) >= 3:
        if max_gmv > avg_gmv * 1.2:
            trend_analysis = f"本周销售波动明显，峰值日GMV({max_gmv:.2f})较均值({avg_gmv:.2f})高出约20%以上。建议分析峰值日的营销活动或达人合作情况。"
        elif max_gmv < avg_gmv * 0.8:
            trend_analysis = f"本周销售整体平稳，但最低谷日GMV({min_gmv:.2f})较均值({avg_gmv:.2f})低约20%。建议关注该日的流量来源和转化率表现。"
        else:
            trend_analysis = f"本周销售趋势平稳，日均GMV约{avg_gmv:.2f}，波动幅度在正常范围内。"

    anomaly_analysis = ""
    if len(influencer_black_list) > 0:
        anomaly_analysis = f"发现{len(influencer_black_list)}位疑似水军达人，特征为高互动率但极低转化率。这些达人可能购买了虚假流量，建议暂停合作或深入调查。"

    action_suggestions = []
    if len(product_red_list) > 0:
        action_suggestions.append(f"重点推广红榜Top 1商品「{product_red_list[0].get('product_name', '')}」，加大达人投放力度。")
    if len(influencer_red_list) > 0:
        action_suggestions.append(f"与红榜Top达人「{influencer_red_list[0].get('influencer_name', '')}」加深合作，ROI表现优异。")
    if len(influencer_black_list) > 0:
        action_suggestions.append(f"立即暂停与黑榜达人的合作，避免资金浪费。")
    action_suggestions.append("持续监控各站点销售表现，优化跨站点资源分配。")

    return {
        "report_title": f"{report_type}分析报告",
        "report_type": report_type,
        "period": f"{date_range['start']} ~ {date_range['end']}",
        "core_summary": {
            "total_gmv": sales_summary.get("total_gmv", 0),
            "total_orders": sales_summary.get("total_orders", 0),
            "avg_order_value": sales_summary.get("avg_order_value", 0),
            "gmv_growth": None,
            "order_growth": None,
        },
        "product_red_list": product_red_list,
        "product_black_list": product_black_list,
        "influencer_red_list": influencer_red_list,
        "influencer_black_list": influencer_black_list,
        "site_breakdown": site_breakdown,
        "trend_analysis": trend_analysis,
        "anomaly_analysis": anomaly_analysis,
        "action_suggestions": action_suggestions,
        "generated_at": datetime.now().isoformat(),
    }


def generate_report(report_type: str = "weekly", site_code: Optional[str] = None) -> Dict[str, Any]:
    if report_type == "weekly":
        date_range = get_weekly_date_range()
    elif report_type == "monthly":
        date_range = get_monthly_date_range()
    else:
        date_range = get_weekly_date_range()

    report_id = f"RPT_{report_type.upper()}_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        report_data = None

        try:
            messages = [
                {
                    "role": "system",
                    "content": REPORT_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""
请生成{report_type}分析报告。
日期范围: {date_range['start']} ~ {date_range['end']}
站点: {site_code or '全部站点'}

请先查询店铺销售数据、达人数据、商品数据，然后生成结构化报告。
报告必须包含：核心业绩概览、商品红黑榜、达人红黑榜、跨站点分析、销售趋势、异动归因、行动建议。

请以JSON格式输出。
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
                    tools=REPORT_TOOLS,
                    tool_choice="auto",
                    result_format="json_object"
                )

                if response.status_code != 200:
                    logger.error(f"API调用失败: {response.status_code}")
                    break

                result = response.output

                if result.choices[0].finish_reason == "tool_call":
                    tool_calls = result.choices[0].message.tool_calls

                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        params = json.loads(tool_call.function.arguments)
                        logger.info(f"AI调用工具: {tool_name}, 参数: {params}")

                        tool_result = execute_report_tool(db, tool_name, params)
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
                    logger.info(f"AI报告生成完成，输出内容长度: {len(content)}")

                    try:
                        report_data = json.loads(content)
                    except json.JSONDecodeError:
                        logger.error("JSON解析失败，尝试清理内容")
                        content = content.replace("```json", "").replace("```", "").strip()
                        try:
                            report_data = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON解析失败: {e}")
                            report_data = None

                    if report_data and isinstance(report_data, dict) and "core_summary" in report_data:
                        break

        except Exception as e:
            logger.error(f"AI报告生成异常: {e}")

        if report_data is None:
            logger.info("AI报告生成失败，使用fallback报告生成逻辑")
            report_data = _generate_fallback_report(db, report_type, date_range, site_code)

        report_data["generated_at"] = datetime.now().isoformat()
        report_data["period"] = f"{date_range['start']} ~ {date_range['end']}"

        record = ReportRecord(
            report_id=report_id,
            report_type=report_type,
            site_code=site_code or "",
            status="completed",
            report_data=json.dumps(report_data, ensure_ascii=False),
            start_date=date_range["start"],
            end_date=date_range["end"],
        )
        db.add(record)
        db.commit()

        logger.info(f"报告已保存: {report_id}")
        return {"report_id": report_id, **report_data}

    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        record = ReportRecord(
            report_id=report_id,
            report_type=report_type,
            site_code=site_code or "",
            status="failed",
            report_data=json.dumps({"error": str(e)}),
            start_date=date_range["start"],
            end_date=date_range["end"],
        )
        db.add(record)
        db.commit()
        raise
    finally:
        db.close()


def get_report_by_id(report_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        record = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()

        if not record:
            return None

        if record.status == "completed" and record.report_data:
            try:
                return json.loads(record.report_data)
            except json.JSONDecodeError:
                return {}

        return {"status": record.status}
    finally:
        db.close()


def list_reports(report_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
    db = SessionLocal()
    try:
        query = db.query(ReportRecord).order_by(ReportRecord.generated_at.desc())

        if report_type:
            query = query.filter(ReportRecord.report_type == report_type)

        records = query.limit(limit).all()

        return [
            {
                "report_id": r.report_id,
                "report_type": r.report_type,
                "site_code": r.site_code,
                "status": r.status,
                "period": r.period,
                "generated_at": r.generated_at.isoformat() if r.generated_at else "",
            }
            for r in records
        ]
    finally:
        db.close()


def delete_report(report_id: str) -> bool:
    db = SessionLocal()
    try:
        record = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()

        if not record:
            return False

        db.delete(record)
        db.commit()
        return True
    finally:
        db.close()