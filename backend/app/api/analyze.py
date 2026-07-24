"""分析接口：创建报告任务，后台调 LLM，前端轮询状态。"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import Dataset, Report
from app.schemas import AnalyzeRequest, ReportOut
from app.services import llm_service

router = APIRouter(prefix="/api", tags=["analyze"])


def _run_analysis(report_id: str):
    """后台任务：独立 DB 会话，避免与请求会话冲突。"""
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if not report:
            return
        dataset = db.get(Dataset, report.dataset_id)
        report.status = "running"
        db.commit()
        try:
            content = llm_service.generate_analysis(
                summary=dataset.summary,
                data_type=dataset.data_type,
                report_type=report.report_type,
            )
            report.content_md = content
            report.status = "done"
        except Exception as e:
            report.status = "failed"
            report.error = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/analyze/{dataset_id}", response_model=ReportOut)
def create_analysis(
    dataset_id: str,
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "数据集不存在")
    if body.report_type not in ("weekly", "monthly"):
        raise HTTPException(400, "report_type 必须是 weekly 或 monthly")

    report = Report(dataset_id=dataset_id, report_type=body.report_type)
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(_run_analysis, report.id)
    return report
