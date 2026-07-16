"""
DeepSeek LLM 客户端
通过 OpenAI 兼容接口调用 DeepSeek API
集成 LangChain ChatOpenAI 适配器
"""

from typing import Optional, AsyncIterator, Generator
import json

from app.core.config import settings
from app.core.logging import log
from app.core.exceptions import LLMException


class DeepSeekClient:
    """DeepSeek LLM 客户端 - 同步与流式调用"""

    _instance: Optional["DeepSeekClient"] = None
    _client = None
    _langchain_llm = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._init_client()

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        log.info(f"DeepSeek 客户端初始化: model={settings.DEEPSEEK_MODEL}")

    @property
    def langchain_llm(self):
        """获取 LangChain 兼容的 LLM 实例"""
        if self._langchain_llm is None:
            from langchain_openai import ChatOpenAI

            self._langchain_llm = ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=settings.DEEPSEEK_TEMPERATURE,
                max_tokens=settings.DEEPSEEK_MAX_TOKENS,
                streaming=True,
            )
        return self._langchain_llm

    def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """同步对话

        Args:
            messages: [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 生成的文本
        """
        try:
            response = self._client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature or settings.DEEPSEEK_TEMPERATURE,
                max_tokens=max_tokens or settings.DEEPSEEK_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            log.debug(
                f"DeepSeek chat: tokens={response.usage.total_tokens if response.usage else 'N/A'}"
            )
            return content
        except Exception as e:
            log.error(f"DeepSeek 调用失败: {e}")
            raise LLMException(f"DeepSeek 调用失败: {e}")

    def chat_stream(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """流式对话 - 逐 token 返回

        Yields:
            内容片段 (delta text)
        """
        try:
            response = self._client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature or settings.DEEPSEEK_TEMPERATURE,
                max_tokens=max_tokens or settings.DEEPSEEK_MAX_TOKENS,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            log.error(f"DeepSeek 流式调用失败: {e}")
            raise LLMException(f"DeepSeek 流式调用失败: {e}")

    async def chat_stream_async(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """异步流式对话"""
        from openai import AsyncOpenAI

        async_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

        try:
            response = await async_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature or settings.DEEPSEEK_TEMPERATURE,
                max_tokens=max_tokens or settings.DEEPSEEK_MAX_TOKENS,
                stream=True,
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            log.error(f"DeepSeek 异步流式调用失败: {e}")
            raise LLMException(f"DeepSeek 异步流式调用失败: {e}")

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """生成文档摘要"""
        messages = [
            {
                "role": "system",
                "content": "你是一个文档摘要生成助手。请用简洁的中文概括以下文档的核心内容。",
            },
            {
                "role": "user",
                "content": f"请为以下内容生成一段不超过{max_length}字的摘要:\n\n{text[:4000]}",
            },
        ]
        return self.chat(messages, temperature=0.1, max_tokens=max_length * 2)

    def classify_intent(self, query: str) -> str:
        """意图分类 - 判断用户查询意图

        Returns:
            意图标签: "qa" (知识问答) / "chitchat" (闲聊) / "search" (搜索) / "summary" (摘要)
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个意图分类器。请将用户输入分类为以下之一:\n"
                    "- qa: 基于知识库的事实性问答\n"
                    "- chitchat: 闲聊、问候、无关问题\n"
                    "- search: 搜索特定文档或信息\n"
                    "- summary: 要求总结或概述\n"
                    "只输出分类标签，不要解释。"
                ),
            },
            {"role": "user", "content": query},
        ]
        result = self.chat(messages, temperature=0.0, max_tokens=20)
        intent = result.strip().lower()
        log.info(f"意图分类: query='{query[:50]}', intent={intent}")
        return intent if intent in ("qa", "chitchat", "search", "summary") else "qa"


# 全局单例
_llm_client: Optional[DeepSeekClient] = None


def get_llm() -> DeepSeekClient:
    """获取 DeepSeek 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = DeepSeekClient()
    return _llm_client
