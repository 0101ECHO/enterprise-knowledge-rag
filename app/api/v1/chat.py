"""
对话/问答 API - 支持同步问答与 SSE 流式返回
"""

import json
import asyncio
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase
from app.services.rag.pipeline import get_pipeline
from app.services.graph.workflow import get_workflow
from app.core.logging import log
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceItem,
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)

router = APIRouter(prefix="/chat", tags=["对话问答"])


@router.post("/ask", response_model=ChatResponse, summary="同步问答")
def ask(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """同步问答 - 等待完整结果后返回"""
    # 验证知识库
    kb = _validate_kb(request.kb_id, user, db)

    # 获取/创建对话
    conversation = _get_or_create_conversation(
        request.conversation_id, user, request.kb_id, db
    )

    # 获取对话历史
    history = _get_chat_history(conversation, db)

    if request.use_workflow:
        # 使用 LangGraph 工作流
        workflow = get_workflow()
        result = workflow.run(
            query=request.question,
            tenant_id=user["tenant_id"],
            kb_id=request.kb_id,
            user_id=user["user_id"],
            conversation_id=str(conversation.id),
            chat_history=history,
        )

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        intent = result.get("intent", "qa")
        metadata = {
            "intent": intent,
            "retrieval_count": result.get("retrieval_count", 0),
            "top_score": result.get("top_score", 0),
        }
    else:
        # 直接使用 RAG 管道
        pipeline = get_pipeline()
        result = pipeline.ask(
            question=request.question,
            kb_id=request.kb_id,
            tenant_id=user["tenant_id"],
            chat_history=history,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

        answer = result.answer
        sources = result.sources
        intent = None
        metadata = result.metadata

    # 保存消息
    _save_messages(
        conversation, request.question, answer, sources, metadata, db
    )

    return ChatResponse(
        answer=answer,
        sources=[SourceItem(**s) for s in sources],
        conversation_id=str(conversation.id),
        intent=intent,
        metadata=metadata,
    )


@router.post("/stream", summary="流式问答 (SSE)")
async def ask_stream(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式问答 - 通过 SSE 逐步返回结果

    SSE 事件格式:
    - event: sources  data: [{"document_id": "...", ...}]
    - event: content  data: {"text": "..."}
    - event: done     data: {"answer_length": 123, ...}
    - event: error    data: {"message": "..."}
    """
    # 验证知识库
    kb = _validate_kb(request.kb_id, user, db)

    # 获取/创建对话
    conversation = _get_or_create_conversation(
        request.conversation_id, user, request.kb_id, db
    )

    # 获取对话历史
    history = _get_chat_history(conversation, db)

    async def event_stream():
        full_answer = ""
        all_sources = []

        try:
            pipeline = get_pipeline()

            async for event in pipeline.ask_stream_async(
                question=request.question,
                kb_id=request.kb_id,
                tenant_id=user["tenant_id"],
                chat_history=history,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            ):
                event_type = event["type"]
                event_data = event["data"]

                if event_type == "sources":
                    all_sources = event_data
                    yield _sse_event("sources", event_data)

                elif event_type == "content":
                    full_answer += event_data
                    yield _sse_event("content", {"text": event_data})

                elif event_type == "done":
                    # 保存消息到数据库
                    _save_messages(
                        conversation,
                        request.question,
                        full_answer,
                        all_sources,
                        event_data,
                        db,
                    )

                    yield _sse_event("done", {
                        "conversation_id": str(conversation.id),
                        "answer_length": len(full_answer),
                        **event_data,
                    })

        except Exception as e:
            log.error(f"流式问答错误: {e}")
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/workflow/stream", summary="LangGraph 工作流流式问答 (SSE)")
async def workflow_stream(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """LangGraph 工作流流式问答 - 展示工作流各节点执行过程"""
    kb = _validate_kb(request.kb_id, user, db)
    conversation = _get_or_create_conversation(
        request.conversation_id, user, request.kb_id, db
    )
    history = _get_chat_history(conversation, db)

    async def event_stream():
        try:
            workflow = get_workflow()

            for output in workflow.run_stream(
                query=request.question,
                tenant_id=user["tenant_id"],
                kb_id=request.kb_id,
                user_id=user["user_id"],
                conversation_id=str(conversation.id),
                chat_history=history,
            ):
                node = output["node"]
                state = output["state"]

                yield _sse_event("node", {
                    "node": node,
                    "state_keys": list(state.keys()) if isinstance(state, dict) else [],
                })

                # 如果是生成节点，输出答案
                if node == "generate" and "answer" in state:
                    yield _sse_event("content", {"text": state["answer"]})

                # 如果是检索节点，输出来源
                if node == "retrieve" and "retrieved_docs" in state:
                    sources = _extract_sources_from_docs(state["retrieved_docs"])
                    yield _sse_event("sources", sources)

            # 保存最终结果
            final_state = workflow.run(
                query=request.question,
                tenant_id=user["tenant_id"],
                kb_id=request.kb_id,
                user_id=user["user_id"],
                conversation_id=str(conversation.id),
                chat_history=history,
            )

            _save_messages(
                conversation,
                request.question,
                final_state.get("answer", ""),
                final_state.get("sources", []),
                {"intent": final_state.get("intent")},
                db,
            )

            yield _sse_event("done", {
                "conversation_id": str(conversation.id),
                "intent": final_state.get("intent"),
            })

        except Exception as e:
            log.error(f"工作流流式问答错误: {e}")
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========== 对话历史管理 ==========

@router.get("/conversations", response_model=list[ConversationResponse], summary="获取对话列表")
def list_conversations(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的对话列表"""
    conversations = (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == user["tenant_id"],
            Conversation.user_id == user["user_id"],
            Conversation.status == "active",
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, summary="获取对话详情")
def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取对话详情及所有消息"""
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user["tenant_id"],
            Conversation.user_id == user["user_id"],
        )
        .first()
    )

    if conversation is None:
        raise NotFoundException("对话", conversation_id)

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )

    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conversation),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}", summary="删除对话")
def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除对话"""
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user["tenant_id"],
            Conversation.user_id == user["user_id"],
        )
        .first()
    )

    if conversation is None:
        raise NotFoundException("对话", conversation_id)

    conversation.status = "archived"
    db.commit()

    return {"message": "对话已归档", "id": conversation_id}


# ========== 辅助函数 ==========

def _validate_kb(kb_id: str, user: dict, db: Session) -> KnowledgeBase:
    """验证知识库是否存在且用户有权限访问"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
        KnowledgeBase.is_active == True,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    # 检查可见性权限
    if kb.visibility == "private":
        # 维护者和管理员可以访问
        if user["role"] not in ("admin", "maintainer"):
            # 检查是否是创建者
            if str(kb.created_by) != user["user_id"]:
                raise ValidationException("您没有权限访问此知识库")

    return kb


def _get_or_create_conversation(
    conversation_id: str | None,
    user: dict,
    kb_id: str,
    db: Session,
) -> Conversation:
    """获取或创建对话"""
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user["tenant_id"],
            Conversation.user_id == user["user_id"],
        ).first()
        if conv:
            return conv

    # 创建新对话
    conv = Conversation(
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        kb_id=kb_id,
        title="新对话",
        status="active",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _get_chat_history(conversation: Conversation, db: Session) -> list[dict]:
    """获取对话历史"""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .limit(10)  # 最近 5 轮
        .all()
    )

    return [{"role": m.role, "content": m.content} for m in messages]


def _save_messages(
    conversation: Conversation,
    question: str,
    answer: str,
    sources: list[dict],
    metadata: dict,
    db: Session,
):
    """保存用户问题和助手回答到数据库"""
    # 保存用户消息
    user_msg = Message(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role="user",
        content=question,
    )
    db.add(user_msg)

    # 保存助手消息
    assistant_msg = Message(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role="assistant",
        content=answer,
        sources=sources,
        metadata_=metadata,
    )
    db.add(assistant_msg)

    # 更新对话统计
    conversation.message_count = (conversation.message_count or 0) + 2
    if conversation.title == "新对话":
        conversation.title = question[:50] + ("..." if len(question) > 50 else "")

    db.commit()


def _sse_event(event_type: str, data) -> str:
    """格式化 SSE 事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_sources_from_docs(docs: list[dict]) -> list[dict]:
    """从检索结果提取来源信息"""
    sources = []
    for i, doc in enumerate(docs, 1):
        payload = doc.get("payload", {})
        sources.append({
            "index": i,
            "document_id": payload.get("document_id", ""),
            "document_title": payload.get("document_title", ""),
            "source_page": payload.get("source_page"),
            "score": round(doc.get("score", 0), 4),
        })
    return sources
