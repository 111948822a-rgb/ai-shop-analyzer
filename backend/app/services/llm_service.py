"""LLM 分析服务：把 Pandas 摘要 + System Prompt 发给大模型，拿回 Markdown 报告。"""

import json
from pathlib import Path

from openai import OpenAI

from app.config import get_settings

PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _load_prompt(data_type: str) -> str:
    name = "creator_analysis.md" if data_type == "creator" else "shop_analysis.md"
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def generate_analysis(summary: dict, data_type: str, report_type: str = "weekly") -> str:
    """同步调用 LLM，返回 Markdown 报告。由 BackgroundTasks 在后台执行。"""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("未配置 OPENAI_API_KEY，请在 backend/.env 中设置")

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    period = "周报" if report_type == "weekly" else "月报"
    user_content = (
        f"请基于以下数据摘要生成{period}。数据摘要（JSON）：\n\n"
        f"```json\n{json.dumps(summary, ensure_ascii=False, indent=2)}\n```"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _load_prompt(data_type)},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=3000,
    )
    return response.choices[0].message.content or ""
