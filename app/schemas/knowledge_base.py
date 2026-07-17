"""知识库 Schema"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    visibility: str = Field(default="private", description="public/private/role_based")
    allowed_roles: list[str] = Field(default_factory=list)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    allowed_roles: list[str] | None = None


class KnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    collection_name: str
    visibility: str
    allowed_roles: list[str] = []
    document_count: int
    chunk_count: int
    embedding_model: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("allowed_roles", mode="before")
    @classmethod
    def coerce_roles(cls, v: Any) -> list:
        if v is None or callable(v):
            return []
        if isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    total: int
    knowledge_bases: list[KnowledgeBaseResponse]
