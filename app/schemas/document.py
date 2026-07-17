"""文档 Schema"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    summary: str | None = None
    doc_metadata: dict = Field(default_factory=dict, alias="metadata")
    created_at: datetime
    updated_at: datetime

    @field_validator("doc_metadata", mode="before")
    @classmethod
    def coerce_metadata(cls, v: Any) -> dict:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    message: str = "文档上传成功，正在处理中"


class DocumentProcessStatus(BaseModel):
    id: UUID
    status: str
    chunk_count: int
    processing_error: str | None = None
    summary: str | None = None
