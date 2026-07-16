"""
Prompt 模板 - RAG 系统的核心提示词
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# ========== 系统提示词 ==========

SYSTEM_PROMPT = """你是一个企业级知识库智能问答助手。请严格基于以下检索到的知识库内容回答用户问题。

## 检索到的知识片段:
{context}

## 回答要求:
1. **严格基于知识库内容回答**，不要编造或引用知识库以外的信息
2. 如果知识库内容无法回答用户问题，请明确说明"根据知识库内容，我无法回答该问题"
3. 在回答中标注引用来源，格式为 [来源: 文档名, 第X页] 或 [来源: 文档名]
4. 保持回答准确、简洁、有条理
5. 如果涉及表格数据，请用 Markdown 表格格式呈现
6. 对于多轮对话，结合上下文理解用户意图

## 对话历史:
{chat_history}
"""

# 无检索结果时的提示词
NO_CONTEXT_PROMPT = """根据知识库内容，我无法找到与您问题相关的信息。

您可以尝试:
- 重新表述您的问题
- 使用更具体的关键词
- 联系知识库管理员补充相关文档
"""

# 意图路由提示词
INTENT_ROUTER_PROMPT = """分析用户输入的意图，决定下一步操作:

用户输入: {query}

可用操作:
- retrieve: 需要检索知识库 (事实性问题、知识查询)
- generate: 直接生成回答 (闲聊、已知信息)
- summarize: 总结对话历史
- clarify: 需要用户澄清 (问题模糊)

请只输出操作名称，不要解释。
"""

# 答案反思提示词 - 检查答案是否充分回答了问题
REFLECTION_PROMPT = """你是一个答案质量审查员。请评估以下答案是否充分回答了用户的问题。

用户问题: {question}
生成的答案: {answer}
检索到的上下文: {context}

评估标准:
1. 答案是否直接回答了问题?
2. 答案是否基于检索到的上下文?
3. 答案是否完整，没有遗漏关键信息?

请输出:
- "sufficient" 如果答案充分
- "insufficient" 如果答案不充分，并说明原因

格式: sufficient 或 insufficient: 原因
"""


# ========== LangChain Prompt 模板 ==========

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])


# ========== 辅助函数 ==========

def build_context(retrieved_docs: list[dict]) -> str:
    """构建检索上下文文本

    Args:
        retrieved_docs: 检索结果列表

    Returns:
        格式化的上下文文本
    """
    if not retrieved_docs:
        return "(无检索结果)"

    context_parts = []
    for i, doc in enumerate(retrieved_docs, 1):
        content = doc.get("content", "")
        payload = doc.get("payload", {})
        source = payload.get("document_title", payload.get("document_id", "未知来源"))
        page = payload.get("source_page", "")
        score = doc.get("score", 0)

        source_str = f"[来源{i}: {source}"
        if page:
            source_str += f", 第{page}页"
        source_str += f", 相关度={score:.2f}]"

        context_parts.append(f"{source_str}\n{content}")

    return "\n\n---\n\n".join(context_parts)


def build_chat_history(messages: list[dict]) -> str:
    """构建对话历史文本"""
    if not messages:
        return "(无历史对话)"

    history_parts = []
    for msg in messages[-6:]:  # 保留最近3轮
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            history_parts.append(f"用户: {content}")
        elif role == "assistant":
            history_parts.append(f"助手: {content}")

    return "\n".join(history_parts) if history_parts else "(无历史对话)"
