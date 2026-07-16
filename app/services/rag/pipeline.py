"""
RAG 管道 - 集成 LangChain 实现: 检索 -> Prompt 组装 -> 生成
提供同步与流式接口
"""

from typing import Optional, AsyncIterator, Generator
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import log
from app.services.llm.deepseek import get_llm
from app.services.rag.retriever import get_retriever, RetrievalResult
from app.services.rag.prompt import (
    SYSTEM_PROMPT,
    NO_CONTEXT_PROMPT,
    build_context,
    build_chat_history,
)


@dataclass
class RAGResponse:
    """RAG 响应"""

    answer: str
    sources: list[dict] = field(default_factory=list)
    retrieval: Optional[RetrievalResult] = None
    metadata: dict = field(default_factory=dict)


class RAGPipeline:
    """RAG 管道 - 检索增强生成"""

    def __init__(self):
        self.llm = get_llm()
        self.retriever = get_retriever()

    def ask(
        self,
        question: str,
        kb_id: str,
        tenant_id: str,
        chat_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> RAGResponse:
        """完整 RAG 问答

        Args:
            question: 用户问题
            kb_id: 知识库 ID
            tenant_id: 租户 ID
            chat_history: 对话历史
            top_k: 检索数量
            score_threshold: 分数阈值

        Returns:
            RAGResponse: 包含答案和引用来源
        """
        log.info(f"RAG 问答开始: question='{question[:100]}', kb_id={kb_id}")

        # 1. 检索
        retrieval = self.retriever.retrieve(
            query=question,
            kb_id=kb_id,
            tenant_id=tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        # 2. 构建 Prompt
        context = build_context(retrieval.documents)
        history = build_chat_history(chat_history or [])

        if not retrieval.documents:
            # 无检索结果
            return RAGResponse(
                answer=NO_CONTEXT_PROMPT,
                sources=[],
                retrieval=retrieval,
                metadata={"has_context": False},
            )

        # 3. 组装消息
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    context=context, chat_history=history
                ),
            },
            {"role": "user", "content": question},
        ]

        # 4. 生成回答
        answer = self.llm.chat(messages)

        # 5. 构建引用来源
        sources = self._extract_sources(retrieval.documents)

        log.info(f"RAG 问答完成: answer_len={len(answer)}, sources={len(sources)}")

        return RAGResponse(
            answer=answer,
            sources=sources,
            retrieval=retrieval,
            metadata={
                "has_context": True,
                "retrieval_count": len(retrieval.documents),
                "top_score": retrieval.documents[0].get("score", 0) if retrieval.documents else 0,
            },
        )

    def ask_stream(
        self,
        question: str,
        kb_id: str,
        tenant_id: str,
        chat_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> Generator[dict, None, None]:
        """流式 RAG 问答

        Yields:
            {"type": "sources", "data": [...]}  - 引用来源
            {"type": "content", "data": "text"} - 答案片段
            {"type": "done", "data": {...}}     - 完成信号
        """
        log.info(f"RAG 流式问答开始: question='{question[:100]}'")

        # 1. 检索
        retrieval = self.retriever.retrieve(
            query=question,
            kb_id=kb_id,
            tenant_id=tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        # 2. 先发送引用来源
        sources = self._extract_sources(retrieval.documents)
        yield {"type": "sources", "data": sources}

        # 3. 无检索结果
        if not retrieval.documents:
            yield {"type": "content", "data": NO_CONTEXT_PROMPT}
            yield {"type": "done", "data": {"has_context": False, "retrieval_count": 0}}
            return

        # 4. 构建 Prompt
        context = build_context(retrieval.documents)
        history = build_chat_history(chat_history or [])

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    context=context, chat_history=history
                ),
            },
            {"role": "user", "content": question},
        ]

        # 5. 流式生成
        full_answer = ""
        for chunk in self.llm.chat_stream(messages):
            full_answer += chunk
            yield {"type": "content", "data": chunk}

        # 6. 完成
        yield {
            "type": "done",
            "data": {
                "has_context": True,
                "retrieval_count": len(retrieval.documents),
                "top_score": retrieval.documents[0].get("score", 0) if retrieval.documents else 0,
                "answer_length": len(full_answer),
            },
        }

        log.info(f"RAG 流式问答完成: answer_len={len(full_answer)}")

    async def ask_stream_async(
        self,
        question: str,
        kb_id: str,
        tenant_id: str,
        chat_history: Optional[list[dict]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> AsyncIterator[dict]:
        """异步流式 RAG 问答 - 用于 FastAPI SSE"""
        log.info(f"RAG 异步流式问答: question='{question[:100]}'")

        # 1. 检索
        retrieval = self.retriever.retrieve(
            query=question,
            kb_id=kb_id,
            tenant_id=tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        # 2. 发送引用来源
        sources = self._extract_sources(retrieval.documents)
        yield {"type": "sources", "data": sources}

        # 3. 无检索结果
        if not retrieval.documents:
            yield {"type": "content", "data": NO_CONTEXT_PROMPT}
            yield {"type": "done", "data": {"has_context": False}}
            return

        # 4. 构建 Prompt
        context = build_context(retrieval.documents)
        history = build_chat_history(chat_history or [])

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    context=context, chat_history=history
                ),
            },
            {"role": "user", "content": question},
        ]

        # 5. 异步流式生成
        full_answer = ""
        async for chunk in self.llm.chat_stream_async(messages):
            full_answer += chunk
            yield {"type": "content", "data": chunk}

        # 6. 完成
        yield {
            "type": "done",
            "data": {
                "has_context": True,
                "retrieval_count": len(retrieval.documents),
                "top_score": retrieval.documents[0].get("score", 0) if retrieval.documents else 0,
            },
        }

    def _extract_sources(self, documents: list[dict]) -> list[dict]:
        """从检索结果中提取引用来源"""
        sources = []
        for i, doc in enumerate(documents, 1):
            payload = doc.get("payload", {})
            sources.append({
                "index": i,
                "document_id": payload.get("document_id", ""),
                "document_title": payload.get("document_title", ""),
                "source_page": payload.get("source_page", None),
                "chunk_type": payload.get("chunk_type", "text"),
                "score": round(doc.get("score", 0), 4),
                "content_preview": doc.get("content", "")[:200] + "..."
                    if len(doc.get("content", "")) > 200
                    else doc.get("content", ""),
            })
        return sources


# 全局单例
_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
