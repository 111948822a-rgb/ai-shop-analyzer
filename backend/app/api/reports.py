from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Report
from app.schemas import ReportOut

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).order_by(Report.created_at.desc()).limit(50).all()


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    return report
