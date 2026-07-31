"""AI 分析报告生成端点。

用通义千问 + Function Calling 直接查 DB 生成店铺经营分析报告，
不依赖上传数据集，适合 TikTok 同步数据后的即时分析。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.db import SessionLocal
from app.models import Report
from app.services.ai_engine import generate_report

router = APIRouter(prefix="/api/ai-report", tags=["ai-report"])


class AIReportRequest(BaseModel):
    """前端请求体。"""
    query: str = ""
    days: int = 30


class AIReportResponse(BaseModel):
    report_id: str
    status: str
    content_md: str = ""
    error: str = ""


def _build_query(days: int, custom_query: str) -> str:
    """构造给 LLM 的 user prompt。"""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    base = (
        f"请分析店铺最近 {days} 天（{start} 至 {end}）的经营数据。"
        "先用 query_sales_data 工具查询该时段的销售汇总，再用 get_influencer_metrics 工具查询达人指标，"
        "然后基于工具返回的真实数据撰写分析报告。"
    )
    if custom_query:
        base += f"\n\n额外关注点：{custom_query}"
    return base


def _run_report(report_id: str, query: str):
    """后台任务：调通义千问生成报告并落库。"""
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if not report:
            return
        report.status = "running"
        db.commit()
        try:
            content = generate_report(query)
            report.content_md = content
            report.status = "done"
        except Exception as e:
            report.status = "failed"
            report.error = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/generate")
def generate_ai_report(
    body: AIReportRequest,
    background_tasks: BackgroundTasks,
    foreground: bool = Query(False, description="前台同步执行（小数据量调试用）"),
):
    """触发 AI 报告生成。默认后台异步，foreground=true 时同步返回结果。"""
    days = max(1, min(body.days, 365))
    query = _build_query(days, body.query)

    # 先创建一条 pending 报告记录
    db = SessionLocal()
    try:
        report = Report(dataset_id=None, report_type="weekly", status="pending")
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id
    finally:
        db.close()

    if foreground:
        # 同步执行，直接返回结果
        try:
            content = generate_report(query)
            db = SessionLocal()
            try:
                r = db.get(Report, report_id)
                r.content_md = content
                r.status = "done"
                db.commit()
            finally:
                db.close()
            return AIReportResponse(report_id=report_id, status="done", content_md=content)
        except Exception as e:
            db = SessionLocal()
            try:
                r = db.get(Report, report_id)
                r.status = "failed"
                r.error = str(e)
                db.commit()
            finally:
                db.close()
            raise HTTPException(500, f"AI 报告生成失败: {e}")

    # 后台异步执行
    background_tasks.add_task(_run_report, report_id, query)
    return AIReportResponse(report_id=report_id, status="pending")


@router.get("/{report_id}", response_model=AIReportResponse)
def get_ai_report(report_id: str):
    """轮询报告状态。"""
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if not report:
            raise HTTPException(404, "报告不存在")
        return AIReportResponse(
            report_id=report.id,
            status=report.status,
            content_md=report.content_md,
            error=report.error,
        )
    finally:
        db.close()
