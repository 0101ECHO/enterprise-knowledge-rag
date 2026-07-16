"""
LangGraph 节点定义
每个节点是一个处理函数，接收状态、返回更新后的状态
"""

from typing import Optional

from app.core.logging import log
from app.services.llm.deepseek import get_llm
from app.services.rag.retriever import get_retriever
from app.services.rag.prompt import (
    SYSTEM_PROMPT,
    NO_CONTEXT_PROMPT,
    build_context,
    build_chat_history,
    REFLECTION_PROMPT,
)
from app.services.graph.state import ConversationState


def intent_classify_node(state: ConversationState) -> dict:
    """节点: 意图分类

    使用 LLM 判断用户查询意图，决定后续路由
    """
    query = state.get("query", "")
    llm = get_llm()

    # 快速规则判断 (减少 LLM 调用)
    query_lower = query.lower().strip()
    if any(greeting in query_lower for greeting in ["你好", "hello", "hi", "hey", "在吗", "谢谢"]):
        intent = "chitchat"
    elif any(kw in query_lower for kw in ["总结", "摘要", "概括", "summarize", "总结一下"]):
        intent = "summary"
    elif any(kw in query_lower for kw in ["搜索", "查找", "找到", "有哪些文档", "search", "find"]):
        intent = "search"
    else:
        # 调用 LLM 分类
        intent = llm.classify_intent(query)

    log.info(f"[Graph] 意图分类: query='{query[:50]}', intent={intent}")

    return {"intent": intent}


def retrieve_node(state: ConversationState) -> dict:
    """节点: 向量检索

    从知识库检索相关文档片段
    """
    query = state.get("query", "")
    kb_id = state.get("kb_id", "")
    tenant_id = state.get("tenant_id", "")

    if not kb_id:
        return {"retrieved_docs": [], "retrieval_count": 0, "error": "未指定知识库"}

    retriever = get_retriever()
    result = retriever.retrieve(
        query=query,
        kb_id=kb_id,
        tenant_id=tenant_id,
    )

    log.info(f"[Graph] 检索完成: {len(result.documents)} 条结果")

    return {
        "retrieved_docs": result.documents,
        "retrieval_count": len(result.documents),
        "top_score": result.documents[0].get("score", 0) if result.documents else 0,
    }


def generate_node(state: ConversationState) -> dict:
    """节点: 答案生成

    基于检索结果和对话历史生成回答
    """
    query = state.get("query", "")
    docs = state.get("retrieved_docs", [])
    messages = state.get("messages", [])
    intent = state.get("intent", "qa")

    llm = get_llm()

    # 闲聊模式: 不使用知识库上下文
    if intent == "chitchat":
        chat_messages = [
            {"role": "system", "content": "你是一个友好的企业知识库助手。请简洁地回应用户的闲聊。"},
            {"role": "user", "content": query},
        ]
        answer = llm.chat(chat_messages)
        return {"answer": answer, "sources": []}

    # 知识库问答
    context = build_context(docs)
    history = build_chat_history(
        [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages[-6:]]
    )

    if not docs:
        return {"answer": NO_CONTEXT_PROMPT, "sources": []}

    chat_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(context=context, chat_history=history),
        },
        {"role": "user", "content": query},
    ]

    answer = llm.chat(chat_messages)
    sources = _extract_sources(docs)

    log.info(f"[Graph] 答案生成完成: len={len(answer)}, sources={len(sources)}")

    return {"answer": answer, "sources": sources}


def reflect_node(state: ConversationState) -> dict:
    """节点: 答案反思

    检查生成的答案是否充分回答了问题
    如果不充分，决定是否需要重试
    """
    query = state.get("query", "")
    answer = state.get("answer", "")
    docs = state.get("retrieved_docs", [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    # 如果已经达到最大重试次数，直接通过
    if retry_count >= max_retries:
        return {"reflection_result": "sufficient", "reflection_reason": "达到最大重试次数"}

    # 如果无检索结果或闲聊，跳过反思
    if not docs or not answer:
        return {"reflection_result": "sufficient", "reflection_reason": "无需反思"}

    # 如果是"无法回答"的答案，不需要重试
    if "无法回答" in answer or "无法找到" in answer:
        return {"reflection_result": "sufficient", "reflection_reason": "知识库内容不足"}

    llm = get_llm()

    context = build_context(docs)
    prompt = REFLECTION_PROMPT.format(
        question=query,
        answer=answer[:1000],
        context=context[:2000],
    )

    try:
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100,
        )
        result = result.strip()

        if result.startswith("sufficient"):
            return {"reflection_result": "sufficient", "reflection_reason": result}
        else:
            reason = result.replace("insufficient:", "").strip()
            log.info(f"[Graph] 反思: 不充分, 原因={reason}")
            return {
                "reflection_result": "insufficient",
                "reflection_reason": reason,
                "retry_count": retry_count + 1,
            }
    except Exception as e:
        log.warning(f"[Graph] 反思失败: {e}")
        return {"reflection_result": "sufficient", "reflection_reason": f"反思异常: {e}"}


def direct_response_node(state: ConversationState) -> dict:
    """节点: 直接响应 (闲聊/简单问题)"""
    query = state.get("query", "")
    llm = get_llm()

    messages = [
        {"role": "system", "content": "你是一个企业知识库助手。请简洁友好地回应用户。"},
        {"role": "user", "content": query},
    ]
    answer = llm.chat(messages, temperature=0.5, max_tokens=500)

    return {"answer": answer, "sources": []}


def search_results_node(state: ConversationState) -> dict:
    """节点: 搜索结果返回 (仅返回检索结果不生成答案)"""
    docs = state.get("retrieved_docs", [])
    sources = _extract_sources(docs)

    # 构建简要答案
    if sources:
        answer = f"为您找到 {len(sources)} 条相关结果:\n\n"
        for s in sources:
            answer += f"- **{s.get('document_title', '未知文档')}**"
            if s.get("source_page"):
                answer += f" (第{s['source_page']}页)"
            answer += f" [相关度: {s.get('score', 0):.2f}]\n"
    else:
        answer = "未找到相关结果。"

    return {"answer": answer, "sources": sources}


def clarify_node(state: ConversationState) -> dict:
    """节点: 请求澄清 (问题模糊)"""
    return {
        "answer": (
            "您的问题似乎不够明确，能否请您提供更多细节？\n"
            "例如：\n"
            "- 您想查询哪方面的信息？\n"
            "- 有具体的关键词或文档名称吗？"
        ),
        "sources": [],
    }


def summarize_node(state: ConversationState) -> dict:
    """节点: 总结对话"""
    messages = state.get("messages", [])
    llm = get_llm()

    history_text = build_chat_history(
        [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
    )

    summary = llm.chat(
        [
            {"role": "system", "content": "请总结以下对话的要点，用简洁的中文输出。"},
            {"role": "user", "content": history_text},
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return {"answer": summary, "sources": []}


# ========== 路由函数 ==========

def route_after_intent(state: ConversationState) -> str:
    """意图分类后的路由"""
    intent = state.get("intent", "qa")

    routing = {
        "qa": "retrieve",
        "chitchat": "direct_response",
        "search": "retrieve",
        "summary": "summarize",
        "clarify": "clarify",
    }

    next_node = routing.get(intent, "retrieve")
    log.info(f"[Graph] 路由: intent={intent} -> {next_node}")
    return next_node


def route_after_retrieve(state: ConversationState) -> str:
    """检索后的路由"""
    intent = state.get("intent", "qa")

    if intent == "search":
        return "search_results"
    return "generate"


def route_after_reflect(state: ConversationState) -> str:
    """反思后的路由"""
    reflection = state.get("reflection_result", "sufficient")

    if reflection == "insufficient" and state.get("retry_count", 0) < state.get("max_retries", 1):
        log.info("[Graph] 反思不充分，重试检索")
        return "retrieve"

    return "end"


# ========== 辅助函数 ==========

def _extract_sources(documents: list[dict]) -> list[dict]:
    """从检索结果中提取引用来源"""
    sources = []
    for i, doc in enumerate(documents, 1):
        payload = doc.get("payload", {})
        sources.append({
            "index": i,
            "document_id": payload.get("document_id", ""),
            "document_title": payload.get("document_title", ""),
            "source_page": payload.get("source_page"),
            "chunk_type": payload.get("chunk_type", "text"),
            "score": round(doc.get("score", 0), 4),
            "content_preview": doc.get("content", "")[:200],
        })
    return sources
