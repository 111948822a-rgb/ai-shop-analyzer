import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Report(Base):
    """LLM 生成的分析报告存档。"""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    # dataset_id 可空：上传流程的报告关联 dataset；AI 直连 DB 的报告为 NULL
    dataset_id: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    report_type: Mapped[str] = mapped_column(String(20), default="weekly")  # weekly | monthly
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | done | failed
    content_md: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
