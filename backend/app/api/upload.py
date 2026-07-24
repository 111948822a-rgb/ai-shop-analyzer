"""文件上传接口：接收 CSV/Excel → 保存 → Pandas 预处理 → 入库。"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Dataset
from app.schemas import UploadResponse
from app.services import preprocessor

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_SUFFIXES = {".csv", ".xlsx", ".xls"}
CHUNK_SIZE = 1024 * 1024  # 1MB


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    data_type: str = Form("shop"),  # shop=店铺销售数据 | creator=达人数据
    db: Session = Depends(get_db),
):
    settings = get_settings()

    if data_type not in ("shop", "creator"):
        raise HTTPException(400, "data_type 必须是 shop 或 creator")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"仅支持 CSV / Excel 文件，收到: {suffix or '未知格式'}")

    # 流式写盘 + 大小限制
    max_bytes = settings.max_upload_mb * 1024 * 1024
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = settings.upload_path / stored_name
    size = 0
    try:
        with open(stored_path, "wb") as f:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"文件超过 {settings.max_upload_mb}MB 限制")
                f.write(chunk)

        # Pandas 预处理：清洗 + 聚合 + 生成摘要
        try:
            summary, row_count, columns = preprocessor.build_summary(stored_path, data_type)
        except ValueError as e:
            raise HTTPException(422, str(e))

        dataset = Dataset(
            filename=file.filename or stored_name,
            stored_path=str(stored_path),
            data_type=data_type,
            row_count=row_count,
            columns=columns,
            summary=summary,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return UploadResponse(dataset=dataset)

    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(500, f"处理文件失败: {e}")


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    rows = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "data_type": d.data_type,
            "row_count": d.row_count,
            "created_at": d.created_at,
        }
        for d in rows
    ]
