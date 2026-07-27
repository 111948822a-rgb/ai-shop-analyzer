import asyncio
import uuid
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db
from app.services.ai_engine import analyze_influencer, save_analysis_result, get_analysis_result

router = APIRouter(prefix="/api/miaoda", tags=["miaoda"])


analysis_tasks: Dict[str, Dict[str, Any]] = {}


def validate_miaoda_secret(request: Request):
    secret = request.headers.get("X-Miaoda-Secret")
    if not secret or secret != settings.MIAODA_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Miaoda-Secret header"
        )


@router.post("/trigger_analysis", response_class=JSONResponse)
async def trigger_analysis(request: Request):
    validate_miaoda_secret(request)

    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )

    task_id = str(uuid.uuid4())
    analysis_tasks[task_id] = {
        "status": "pending",
        "data": data,
        "result": None,
        "error": None
    }

    report_url = f"{settings.REPORTS_BASE_URL}/api/reports/{task_id}"

    asyncio.create_task(_run_analysis_background(task_id, data))

    return JSONResponse(
        content={"task_id": task_id, "report_url": report_url},
        status_code=status.HTTP_200_OK
    )


async def _run_analysis_background(task_id: str, data: Dict[str, Any]):
    analysis_tasks[task_id]["status"] = "processing"

    try:
        db = next(get_db())
        analysis_result = await analyze_influencer(db, data)
        
        influencer_id = data.get("influencer_id", "")
        site_code = data.get("site_code", "")
        save_analysis_result(db, task_id, influencer_id, site_code, analysis_result)
        
        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["result"] = analysis_result
    except Exception as e:
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = str(e)


@router.get("/analysis_status/{task_id}", response_class=JSONResponse)
async def get_analysis_status(task_id: str):
    task = analysis_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return JSONResponse(content={
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"] if task["status"] == "completed" else None,
        "error": task["error"] if task["status"] == "failed" else None
    })