from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.report_generator import generate_report, get_report_by_id, list_reports, delete_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate")
async def generate_report_endpoint(
    report_type: str = Query("weekly", enum=["weekly", "monthly"]),
    site_code: Optional[str] = None,
):
    try:
        report_data = generate_report(report_type=report_type, site_code=site_code)
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}")
async def get_report_endpoint(report_id: str):
    report_data = get_report_by_id(report_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_data


@router.get("/")
async def list_reports_endpoint(
    report_type: Optional[str] = Query(None, enum=["weekly", "monthly"]),
    limit: int = Query(20, ge=1, le=100),
):
    reports = list_reports(report_type=report_type, limit=limit)
    return {"reports": reports}


@router.delete("/{report_id}")
async def delete_report_endpoint(report_id: str):
    success = delete_report(report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}