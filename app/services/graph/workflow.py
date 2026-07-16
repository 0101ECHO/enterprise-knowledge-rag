"""
LangGraph 工作流编排
构建多轮对话状态机: 意图分类 -> 检索 -> 生成 -> 反思 -> (重试/结束)

工作流拓扑:
  START -> intent_classify
  intent_classify -> retrieve       (intent=qa)
  intent_classify -> direct_response (intent=chitchat)
  intent_classify -> retrieve       (intent=search)
  intent_classify -> summarize      (intent=summary)
  intent_classify -> clarify        (intent=clarify)
  retrieve -> generate              (intent=qa)
  retrieve -> search_results        (intent=search)
  generate -> reflect
  reflect -> retrieve               (insufficient, retry)
  reflect -> END                    (sufficient)
  direct_response -> END
  search_results -> END
  summarize -> END
  clarify -> END
"""

from typing import Optional, AsyncIterator, Generator

from langgraph.graph import StateGraph, END

from app.core.logging import log
from app.services.graph.state import ConversationState
from app.services.graph.nodes import (
    intent_classify_node,
    retrieve_node,
    generate_node,
    reflect_node,
    direct_response_node,
    search_results_node,
    clarify_node,
    summarize_node,
    route_after_intent,
    route_after_retrieve,
    route_after_reflect,
)


class ConversationWorkflow:
    """对话工作流 - LangGraph 状态机"""

    _graph = None
    _app = None

    def __init__(self):
        self._build_graph()

    def _build_graph(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(ConversationState)

        # 添加节点
        workflow.add_node("intent_classify", intent_classify_node)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)
        workflow.add_node("reflect", reflect_node)
        workflow.add_node("direct_response", direct_response_node)
        workflow.add_node("search_results", search_results_node)
        workflow.add_node("clarify", clarify_node)
        workflow.add_node("summarize", summarize_node)

        # 设置入口
        workflow.set_entry_point("intent_classify")

        # 意图分类后的条件路由
        workflow.add_conditional_edges(
            "intent_classify",
            route_after_intent,
            {
                "retrieve": "retrieve",
                "direct_response": "direct_response",
                "summarize": "summarize",
                "clarify": "clarify",
            },
        )

        # 检索后的条件路由
        workflow.add_conditional_edges(
            "retrieve",
            route_after_retrieve,
            {
                "generate": "generate",
                "search_results": "search_results",
            },
        )

        # 生成 -> 反思
        workflow.add_edge("generate", "reflect")

        # 反思后的条件路由
        workflow.add_conditional_edges(
            "reflect",
            route_after_reflect,
            {
                "retrieve": "retrieve",
                "end": END,
            },
        )

        # 终端节点
        workflow.add_edge("direct_response", END)
        workflow.add_edge("search_results", END)
        workflow.add_edge("clarify", END)
        workflow.add_edge("summarize", END)

        # 编译
        self._app = workflow.compile()
        log.info("[Graph] LangGraph 工作流构建完成")

    def run(
        self,
        query: str,
        tenant_id: str,
        kb_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> dict:
        """执行工作流

        Returns:
            最终状态 dict，包含 answer, sources, intent 等字段
        """
        # 构建初始状态
        initial_state = ConversationState(
            query=query,
            tenant_id=tenant_id,
            kb_id=kb_id,
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in (chat_history or [])
            ] + [{"role": "user", "content": query}],
        )

        log.info(
            f"[Graph] 工作流启动: query='{query[:50]}', "
            f"kb_id={kb_id}, user_id={user_id}"
        )

        # 执行
        final_state = self._app.invoke(initial_state)

        log.info(
            f"[Graph] 工作流完成: intent={final_state.get('intent')}, "
            f"answer_len={len(final_state.get('answer', ''))}"
        )

        return final_state

    def run_stream(
        self,
        query: str,
        tenant_id: str,
        kb_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> Generator[dict, None, None]:
        """流式执行工作流

        Yields:
            各节点的输出状态更新
        """
        initial_state = ConversationState(
            query=query,
            tenant_id=tenant_id,
            kb_id=kb_id,
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in (chat_history or [])
            ] + [{"role": "user", "content": query}],
        )

        for output in self._app.stream(initial_state):
            for node_name, state_update in output.items():
                log.debug(f"[Graph] 节点完成: {node_name}")
                yield {"node": node_name, "state": state_update}


# 全局单例
_workflow: Optional[ConversationWorkflow] = None


def get_workflow() -> ConversationWorkflow:
    """获取工作流单例"""
    global _workflow
    if _workflow is None:
        _workflow = ConversationWorkflow()
    return _workflow
