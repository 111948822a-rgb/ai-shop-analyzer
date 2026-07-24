import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Report(Base):
    """LLM 生成的分析报告存档。"""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(String(32), ForeignKey("datasets.id"))
    report_type: Mapped[str] = mapped_column(String(20), default="weekly")  # weekly | monthly
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | done | failed
    content_md: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
