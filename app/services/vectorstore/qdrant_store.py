"""
Qdrant 向量存储服务
选型说明:
  - Qdrant 是专为向量搜索优化的数据库，支持高效过滤(租户隔离)、混合检索
  - 相比 pgvector: 在大规模向量检索时性能更优，内置 HNSW 索引
  - 相比 Milvus: 部署更简单，API 更友好，Docker 一键启动
  - payload 过滤天然支持多租户隔离与 RBAC
"""

from typing import Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
    SearchParams,
    CollectionInfo,
)

from app.core.config import settings
from app.core.logging import log


class QdrantVectorStore:
    """Qdrant 向量存储"""

    _client: Optional[QdrantClient] = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        """获取 Qdrant 客户端 (单例)"""
        if cls._client is None:
            cls._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.QDRANT_API_KEY or None,
                timeout=60,
            )
            log.info(f"Qdrant 客户端已连接: {settings.qdrant_url}")
        return cls._client

    @classmethod
    def collection_name(cls, kb_id: str) -> str:
        """根据知识库 ID 生成集合名"""
        return f"{settings.QDRANT_COLLECTION_PREFIX}{kb_id.replace('-', '_')}"

    @classmethod
    def create_collection(
        cls,
        kb_id: str,
        vector_dim: Optional[int] = None,
    ) -> str:
        """创建向量集合

        Args:
            kb_id: 知识库 ID
            vector_dim: 向量维度，默认从配置读取

        Returns:
            集合名称
        """
        client = cls.get_client()
        collection = cls.collection_name(kb_id)
        dim = vector_dim or settings.EMBEDDING_DIMENSION

        # 检查集合是否已存在
        existing = cls.get_collection(kb_id)
        if existing:
            log.info(f"集合已存在: {collection}")
            return collection

        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

        # 创建 payload 索引 (加速过滤)
        for field_name, field_type in [
            ("tenant_id", PayloadSchemaType.KEYWORD),
            ("kb_id", PayloadSchemaType.KEYWORD),
            ("document_id", PayloadSchemaType.KEYWORD),
            ("chunk_index", PayloadSchemaType.INTEGER),
            ("chunk_type", PayloadSchemaType.KEYWORD),
            ("source_page", PayloadSchemaType.INTEGER),
        ]:
            try:
                client.create_payload_index(
                    collection_name=collection,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except Exception as e:
                log.warning(f"创建索引 {field_name} 失败: {e}")

        log.info(f"向量集合创建成功: {collection}, dim={dim}")
        return collection

    @classmethod
    def get_collection(cls, kb_id: str) -> Optional[CollectionInfo]:
        """获取集合信息"""
        client = cls.get_client()
        collection = cls.collection_name(kb_id)
        try:
            return client.get_collection(collection)
        except Exception:
            return None

    @classmethod
    def delete_collection(cls, kb_id: str) -> bool:
        """删除集合"""
        client = cls.get_client()
        collection = cls.collection_name(kb_id)
        try:
            client.delete_collection(collection)
            log.info(f"集合已删除: {collection}")
            return True
        except Exception as e:
            log.error(f"删除集合失败: {collection}, {e}")
            return False

    @classmethod
    def upsert_points(
        cls,
        kb_id: str,
        points: list[dict],
    ) -> list[str]:
        """批量插入/更新向量点

        Args:
            kb_id: 知识库 ID
            points: [{vector, content, tenant_id, document_id, chunk_index, chunk_type, source_page, ...}]

        Returns:
            插入的 point_id 列表
        """
        client = cls.get_client()
        collection = cls.collection_name(kb_id)

        qdrant_points = []
        point_ids = []

        for p in points:
            point_id = str(uuid4())
            point_ids.append(point_id)

            vector = p.pop("vector")
            content = p.pop("content", "")

            payload = {
                "content": content,
                **p,  # tenant_id, document_id, chunk_index, etc.
            }

            qdrant_points.append(
                PointStruct(id=point_id, vector=vector, payload=payload)
            )

        # 分批 upsert (每批 100 个)
        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            client.upsert(collection_name=collection, points=batch)
            log.debug(f"Upsert batch {i // batch_size + 1}: {len(batch)} points")

        log.info(f"向量插入完成: {collection}, 共 {len(point_ids)} 个点")
        return point_ids

    @classmethod
    def search(
        cls,
        kb_id: str,
        query_vector: list[float],
        tenant_id: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        document_ids: Optional[list[str]] = None,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """向量检索

        Args:
            kb_id: 知识库 ID
            query_vector: 查询向量
            tenant_id: 租户 ID (强制隔离)
            top_k: 返回数量
            score_threshold: 分数阈值
            document_ids: 限定文档 ID 列表
            filters: 额外过滤条件

        Returns:
            检索结果列表 [{content, score, payload, ...}]
        """
        client = cls.get_client()
        collection = cls.collection_name(kb_id)
        k = top_k or settings.RETRIEVAL_TOP_K
        threshold = score_threshold or settings.RETRIEVAL_SCORE_THRESHOLD

        # 构建过滤条件 - 强制租户隔离
        must_conditions = [
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
        ]

        if document_ids:
            must_conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_ids[0]))
            )

        query_filter = Filter(must=must_conditions)

        # 合并额外过滤条件
        if filters:
            for key, value in filters.items():
                query_filter.must.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )

        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=k,
            score_threshold=threshold,
            query_filter=query_filter,
            with_payload=True,
            search_params=SearchParams(hnsw_ef=128, exact=False),
        )

        scored = []
        for hit in results:
            scored.append({
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "payload": hit.payload,
                "point_id": hit.id,
            })

        log.info(
            f"向量检索: collection={collection}, "
            f"top_k={k}, results={len(scored)}, "
            f"top_score={scored[0]['score'] if scored else 0:.4f}"
        )
        return scored

    @classmethod
    def delete_by_document(cls, kb_id: str, document_id: str, tenant_id: str) -> bool:
        """删除指定文档的所有向量"""
        client = cls.get_client()
        collection = cls.collection_name(kb_id)

        try:
            client.delete(
                collection_name=collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="tenant_id", match=MatchValue(value=tenant_id)
                        ),
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        ),
                    ]
                ),
            )
            log.info(f"文档向量已删除: document_id={document_id}")
            return True
        except Exception as e:
            log.error(f"删除文档向量失败: {e}")
            return False

    @classmethod
    def count_points(cls, kb_id: str, tenant_id: Optional[str] = None) -> int:
        """统计集合中的向量数量"""
        client = cls.get_client()
        collection = cls.collection_name(kb_id)

        try:
            if tenant_id:
                result = client.count(
                    collection_name=collection,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="tenant_id",
                                match=MatchValue(value=tenant_id),
                            )
                        ]
                    ),
                )
                return result.count
            else:
                result = client.count(collection_name=collection)
                return result.count
        except Exception as e:
            log.error(f"统计向量数量失败: {e}")
            return 0
