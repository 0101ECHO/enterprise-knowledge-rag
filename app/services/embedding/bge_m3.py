"""
BGE-M3 Embedding 服务
使用 sentence-transformers 加载 BAAI/bge-m3 模型
支持: 多语言、稠密向量 (1024维)
"""

import os
from typing import Optional
import numpy as np

from app.core.config import settings
from app.core.logging import log

# 设置 HuggingFace 国内镜像 (解决模型下载被墙问题)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


class BGE_M3_Embedder:
    """BGE-M3 Embedding 服务 (单例模式)"""

    _instance: Optional["BGE_M3_Embedder"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """加载 BGE-M3 模型 (优先 sentence-transformers，避免 FlagEmbedding 的 .DS_Store 问题)"""
        model_name = settings.EMBEDDING_MODEL_NAME
        log.info(f"加载 Embedding 模型: {model_name} (via sentence-transformers)")

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                model_name,
                device=settings.EMBEDDING_MODEL_DEVICE,
                trust_remote_code=True,
            )
            log.info(
                f"Embedding 模型加载成功: {model_name}, "
                f"device={settings.EMBEDDING_MODEL_DEVICE}"
            )
        except Exception as e:
            log.error(f"sentence-transformers 加载失败: {e}")
            raise

    def embed(self, texts: str | list[str]) -> np.ndarray:
        """生成文本的稠密向量

        Args:
            texts: 单条文本或文本列表

        Returns:
            向量数组, shape=(n, 1024)
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.array(embeddings)

    def embed_query(self, text: str) -> list[float]:
        """生成查询向量"""
        vec = self.embed(text)
        return vec[0].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """生成文档向量"""
        vecs = self.embed(texts)
        if isinstance(vecs, np.ndarray):
            return vecs.tolist()
        return list(vecs)

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        return settings.EMBEDDING_DIMENSION


# 全局单例
_embedder: Optional[BGE_M3_Embedder] = None


def get_embedder() -> BGE_M3_Embedder:
    """获取 Embedding 服务单例"""
    global _embedder
    if _embedder is None:
        _embedder = BGE_M3_Embedder()
    return _embedder
