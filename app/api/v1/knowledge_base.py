"""
知识库管理 API
"""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, require_maintainer
from app.core.config import settings
from app.core.rbac import Role
from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.services.vectorstore.qdrant_store import QdrantVectorStore
from app.core.logging import log
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库管理"])


@router.get("", response_model=KnowledgeBaseListResponse, summary="获取知识库列表")
def list_knowledge_bases(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前租户的知识库列表"""
    query = db.query(KnowledgeBase).filter(
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
        KnowledgeBase.is_active == True,
    )

    total = query.count()
    kbs = query.offset((page - 1) * size).limit(size).all()

    return KnowledgeBaseListResponse(
        total=total,
        knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in kbs],
    )


@router.post("", response_model=KnowledgeBaseResponse, summary="创建知识库")
def create_knowledge_base(
    request: KnowledgeBaseCreate,
    user: dict = Depends(require_maintainer),
    db: Session = Depends(get_db),
):
    """创建新知识库 (维护者/管理员)"""
    # 先生成 KB ID，用于 Qdrant collection 命名
    import uuid as _uuid
    kb_id = str(_uuid.uuid4())

    # 在 Qdrant 中创建集合
    collection_name = QdrantVectorStore.collection_name(kb_id)
    QdrantVectorStore.create_collection(kb_id, settings.EMBEDDING_DIMENSION)

    kb = KnowledgeBase(
        id=kb_id,
        tenant_id=user["tenant_id"],
        name=request.name,
        description=request.description,
        collection_name=collection_name,
        visibility=request.visibility,
        allowed_roles=request.allowed_roles,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        embedding_dim=settings.EMBEDDING_DIMENSION,
        created_by=user["user_id"],
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    log.info(f"知识库创建: id={kb.id}, name={kb.name}")

    return KnowledgeBaseResponse.model_validate(kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse, summary="获取知识库详情")
def get_knowledge_base(
    kb_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定知识库详情"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    return KnowledgeBaseResponse.model_validate(kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdate,
    user: dict = Depends(require_maintainer),
    db: Session = Depends(get_db),
):
    """更新知识库信息"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    if request.name is not None:
        kb.name = request.name
    if request.description is not None:
        kb.description = request.description
    if request.visibility is not None:
        kb.visibility = request.visibility
    if request.allowed_roles is not None:
        kb.allowed_roles = request.allowed_roles

    db.commit()
    db.refresh(kb)

    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/{kb_id}", summary="删除知识库")
def delete_knowledge_base(
    kb_id: str,
    user: dict = Depends(require_maintainer),
    db: Session = Depends(get_db),
):
    """删除知识库 (同时删除 Qdrant 集合)"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    # 删除 Qdrant 集合
    kb_uuid = str(kb.id)
    QdrantVectorStore.delete_collection(kb_uuid)

    # 软删除
    kb.is_deleted = True
    kb.is_active = False
    db.commit()

    return {"message": "知识库已删除", "id": kb_id}


@router.get("/{kb_id}/stats", summary="获取知识库统计")
def get_kb_stats(
    kb_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库统计信息"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    # 从 Qdrant 获取向量数量
    vector_count = QdrantVectorStore.count_points(str(kb.id), user["tenant_id"])

    return {
        "kb_id": str(kb.id),
        "name": kb.name,
        "document_count": kb.document_count,
        "chunk_count": kb.chunk_count,
        "vector_count": vector_count,
        "embedding_model": kb.embedding_model,
        "embedding_dim": kb.embedding_dim,
    }
