from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalyzeRequest(BaseModel):
    report_type: str = "weekly"  # weekly | monthly


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    report_type: str
    status: str
    content_md: str
    error: str
    created_at: datetime
