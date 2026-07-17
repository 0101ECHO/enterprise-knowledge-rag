"""
RAG 检索器 - 向量检索 + 重排序
"""

from typing import Optional
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import log
from app.services.embedding.bge_m3 import get_embedder
from app.services.vectorstore.qdrant_store import QdrantVectorStore


@dataclass
class RetrievalResult:
    """检索结果"""

    query: str
    documents: list[dict]
    query_vector: list[float]
    total: int = 0


class RAGRetriever:
    """RAG 检索器"""

    def __init__(self):
        self.embedder = get_embedder()

    def retrieve(
        self,
        query: str,
        kb_id: str,
        tenant_id: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        document_ids: Optional[list[str]] = None,
        filters: Optional[dict] = None,
    ) -> RetrievalResult:
        """执行向量检索

        Args:
            query: 用户查询文本
            kb_id: 知识库 ID
            tenant_id: 租户 ID (强制隔离)
            top_k: 返回数量
            score_threshold: 分数阈值
            document_ids: 限定文档范围
            filters: 额过滤条件

        Returns:
            RetrievalResult: 检索结果
        """
        # 1. 生成查询向量
        query_vector = self.embedder.embed_query(query)
        log.info(f"查询向量化完成: dim={len(query_vector)}")

        # 2. 向量检索
        results = QdrantVectorStore.search(
            kb_id=kb_id,
            query_vector=query_vector,
            tenant_id=tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
            document_ids=document_ids,
            filters=filters,
        )

        # 3. 可选重排序
        if settings.RERANK_ENABLED and len(results) > 1:
            results = self._rerank(query, results)

        return RetrievalResult(
            query=query,
            documents=results,
            query_vector=query_vector,
            total=len(results),
        )

    def _rerank(self, query: str, documents: list[dict]) -> list[dict]:
        """重排序 - 使用 Cross-Encoder Reranker 提升检索精度"""
        try:
            from app.services.rag.reranker import get_reranker

            reranker = get_reranker()
            contents = [doc["content"] for doc in documents]
            top_k = min(settings.RERANK_TOP_K, len(documents))

            ranked = reranker.rerank(query, contents, top_k=top_k)

            # 重新排序
            reranked = []
            for idx, score in ranked:
                doc = documents[idx].copy()
                doc["rerank_score"] = float(score)
                reranked.append(doc)

            if reranked:
                log.info(
                    f"Reranker 完成: {len(reranked)}/{len(documents)} 结果, "
                    f"top_score={reranked[0].get('rerank_score', 0):.4f}"
                )
            return reranked
        except Exception as e:
            log.warning(f"重排序失败，使用原始排序: {e}")
            return documents

    def retrieve_multi_query(
        self,
        query: str,
        kb_id: str,
        tenant_id: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        """多查询检索 - 生成查询变体扩大召回

        通过 LLM 将原始查询改写为多个变体查询，分别检索后合并去重
        """
        from app.services.llm.deepseek import get_llm

        llm = get_llm()

        # 生成查询变体
        rewrite_prompt = [
            {
                "role": "system",
                "content": (
                    "你是一个查询改写助手。请将以下查询改写为3个不同的表述方式，"
                    "用于扩大知识库检索召回率。每行一个改写，不要编号。"
                ),
            },
            {"role": "user", "content": query},
        ]
        rewrite_result = llm.chat(rewrite_prompt, temperature=0.5, max_tokens=200)
        queries = [q.strip() for q in rewrite_result.strip().split("\n") if q.strip()]
        queries.insert(0, query)  # 包含原始查询

        log.info(f"多查询检索: {len(queries)} 个查询变体")

        # 对每个查询执行检索
        all_docs = {}
        for q in queries:
            result = self.retrieve(q, kb_id, tenant_id, top_k=top_k)
            for doc in result.documents:
                point_id = doc.get("point_id", "")
                if point_id not in all_docs:
                    all_docs[point_id] = doc
                else:
                    # 取较高分数
                    if doc.get("score", 0) > all_docs[point_id].get("score", 0):
                        all_docs[point_id] = doc

        # 按分数排序
        merged = sorted(all_docs.values(), key=lambda x: x.get("score", 0), reverse=True)
        merged = merged[:top_k]

        return RetrievalResult(
            query=query,
            documents=merged,
            query_vector=[],
            total=len(merged),
        )


# 全局单例
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
