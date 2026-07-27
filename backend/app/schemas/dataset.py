from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    data_type: str
    row_count: int
    columns: list
    summary: dict
    created_at: datetime


class UploadResponse(BaseModel):
    dataset: DatasetOut
    message: str = "上传并预处理成功"
