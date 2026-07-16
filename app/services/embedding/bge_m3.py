"""
BGE-M3 Embedding 服务
基于 sentence-transformers 加载 BAAI/bge-m3 模型
支持: 多语言、稠密向量、稀疏向量、ColBERT 向量
"""

from typing import Optional
import numpy as np

from app.core.config import settings
from app.core.logging import log


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
        """加载 BGE-M3 模型"""
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                settings.EMBEDDING_MODEL_NAME,
                use_fp16=settings.EMBEDDING_MODEL_DEVICE != "cpu",
                device=settings.EMBEDDING_MODEL_DEVICE,
            )
            log.info(
                f"BGE-M3 模型加载成功: {settings.EMBEDDING_MODEL_NAME}, "
                f"device={settings.EMBEDDING_MODEL_DEVICE}"
            )
        except ImportError:
            log.warning("FlagEmbedding 未安装，尝试使用 sentence-transformers")
            self._load_with_sentence_transformers()
        except Exception as e:
            log.error(f"BGE-M3 模型加载失败: {e}")
            raise

    def _load_with_sentence_transformers(self):
        """使用 sentence-transformers 作为后备"""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_MODEL_DEVICE,
            )
            self._use_st = True
            log.info(f"sentence-transformers 加载成功: {settings.EMBEDDING_MODEL_NAME}")
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

        if hasattr(self, "_use_st") and self._use_st:
            embeddings = self._model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return np.array(embeddings)

        # FlagEmbedding BGEM3FlagModel
        embeddings = self._model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            max_length=8192,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return np.array(embeddings["dense_vecs"])

    def embed_query(self, text: str) -> list[float]:
        """生成查询向量"""
        vec = self.embed(text)
        return vec[0].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """生成文档向量"""
        vecs = self.embed(texts)
        return vecs.tolist()

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
