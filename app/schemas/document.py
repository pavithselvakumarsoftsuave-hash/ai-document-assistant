"""Document API response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
