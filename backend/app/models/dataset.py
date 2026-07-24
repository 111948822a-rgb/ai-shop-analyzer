import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Dataset(Base):
    """一次上传的数据集：元信息 + Pandas 预处理产出的指标摘要。"""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    data_type: Mapped[str] = mapped_column(String(20))  # shop | creator
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # 预处理指标摘要（喂给 LLM）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
