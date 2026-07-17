"""
Reranker 重排序服务
使用 BAAI/bge-reranker-v2-m3 对检索结果进行重排序，提升答案准确性
"""

import os
from typing import List, Tuple
import torch
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.logging import log

# 设置 HuggingFace 国内镜像 (解决模型下载被墙问题)
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 禁用 Xet 存储协议 (镜像不支持)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"


class RerankerService:
    """Cross-Encoder 重排序器 (单例)"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is not None:
            return
        model_name = settings.RERANKER_MODEL_NAME
        log.info(f"加载 Reranker 模型: {model_name}")
        try:
            self._model = CrossEncoder(
                model_name,
                max_length=settings.RERANKER_MAX_LENGTH,
                device="cpu",
                trust_remote_code=True,
            )
        except Exception as e:
            log.warning(f"Reranker 加载失败，将使用无重排序模式: {e}")
            self._model = None

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """对检索结果重排序

        Args:
            query: 用户查询
            documents: 候选文档文本列表
            top_k: 返回数量

        Returns:
            [(索引, 分数), ...] 按分数降序排列
        """
        self._load_model()
        if self._model is None or not documents:
            return list(enumerate([1.0] * min(len(documents), top_k)))

        # 构建 (query, doc) 对
        pairs = [(query, doc[:settings.RERANKER_MAX_LENGTH]) for doc in documents]

        try:
            scores = self._model.predict(pairs)
        except Exception as e:
            log.warning(f"Reranker 预测失败: {e}")
            return list(enumerate([1.0] * min(len(documents), top_k)))

        # 按分数排序
        scored = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )
        return scored[:top_k]


# 全局单例
_reranker = None


def get_reranker() -> RerankerService:
    global _reranker
    if _reranker is None:
        _reranker = RerankerService()
    return _reranker
