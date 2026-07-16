"""对话/问答 Schema"""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ChatRequest(BaseModel):
    """问答请求"""

    question: str = Field(..., min_length=1, max_length=2000)
    kb_id: str = Field(..., description="知识库 ID")
    conversation_id: str | None = Field(None, description="对话 ID (多轮对话)")
    top_k: int | None = Field(None, ge=1, le=20, description="检索数量")
    score_threshold: float | None = Field(None, ge=0, le=1, description="分数阈值")
    use_workflow: bool = Field(True, description="是否使用 LangGraph 工作流")


class SourceItem(BaseModel):
    index: int
    document_id: str
    document_title: str
    source_page: int | None = None
    chunk_type: str = "text"
    score: float
    content_preview: str = ""


class ChatResponse(BaseModel):
    """问答响应"""

    answer: str
    sources: list[SourceItem] = []
    conversation_id: str | None = None
    intent: str | None = None
    metadata: dict = {}


class ConversationResponse(BaseModel):
    id: UUID
    title: str | None = None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list = []
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
