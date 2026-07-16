"""
LangGraph 状态定义
定义对话状态机中流转的数据结构
"""

from typing import Optional, Annotated
from dataclasses import dataclass, field
from enum import Enum

from langgraph.graph import MessagesState


class NodeName(str, Enum):
    """工作流节点名称"""

    INTENT_CLASSIFY = "intent_classify"
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    REFLECT = "reflect"
    DIRECT_RESPONSE = "direct_response"
    SEARCH_RESULTS = "search_results"
    CLARIFY = "clarify"
    END = "end"


class ConversationState(MessagesState):
    """对话状态 - LangGraph 消息状态扩展

    继承 MessagesState 自动管理 messages 列表，
    额外添加 RAG 相关状态字段
    """

    # 用户输入
    query: str

    # 上下文信息
    tenant_id: str
    kb_id: str
    user_id: str
    conversation_id: Optional[str] = None

    # 意图分类
    intent: str = "qa"  # qa / chitchat / search / summary / clarify

    # 检索结果
    retrieved_docs: list[dict] = []
    retrieval_count: int = 0
    top_score: float = 0.0

    # 生成结果
    answer: str = ""
    sources: list[dict] = []

    # 反思
    reflection_result: str = ""  # sufficient / insufficient
    reflection_reason: str = ""
    retry_count: int = 0
    max_retries: int = 1

    # 元数据
    metadata: dict = {}

    # 错误
    error: Optional[str] = None
