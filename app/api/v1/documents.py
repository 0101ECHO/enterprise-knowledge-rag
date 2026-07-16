"""
文档管理 API - 上传、解析、向量化、删除
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, require_maintainer
from app.core.config import settings
from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    DocumentProcessingException,
)
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentChunk
from app.services.document.loader import DocumentLoader
from app.services.embedding.bge_m3 import get_embedder
from app.services.vectorstore.qdrant_store import QdrantVectorStore
from app.services.llm.deepseek import get_llm
from app.core.logging import log
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentProcessStatus,
)

router = APIRouter(prefix="/documents", tags=["文档管理"])

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "html", "htm", "md", "markdown", "txt",
    "png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp",
}


@router.post("/upload/{kb_id}", response_model=DocumentUploadResponse, summary="上传文档")
async def upload_document(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(require_maintainer),
    db: Session = Depends(get_db),
):
    """上传文档到指定知识库

    文档上传后将异步进行: 解析 -> 分块 -> 向量化 -> 存储
    """
    # 验证知识库
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == user["tenant_id"],
        KnowledgeBase.is_deleted == False,
    ).first()

    if kb is None:
        raise NotFoundException("知识库", kb_id)

    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    if file_ext not in ALLOWED_EXTENSIONS:
        raise DocumentProcessingException(
            f"不支持的文件类型: {file_ext}",
            {"allowed": list(ALLOWED_EXTENSIONS)},
        )

    # 验证文件大小
    content = await file.read()
    file_size = len(content)
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size > max_size:
        raise DocumentProcessingException(
            f"文件大小超出限制: {file_size / 1024 / 1024:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB"
        )

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR) / str(user["tenant_id"]) / kb_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_uuid = str(uuid.uuid4())
    saved_filename = f"{file_uuid}_{file.filename}"
    file_path = upload_dir / saved_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # 创建文档记录
    doc = Document(
        tenant_id=user["tenant_id"],
        kb_id=kb_id,
        uploaded_by=user["user_id"],
        title=Path(file.filename).stem,
        file_name=file.filename,
        file_path=str(file_path),
        file_type=file_ext,
        file_size=file_size,
        mime_type=file.content_type,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 异步处理文档
    background_tasks.add_task(
        process_document_task,
        document_id=str(doc.id),
        tenant_id=user["tenant_id"],
        kb_id=kb_id,
    )

    log.info(f"文档上传: id={doc.id}, name={file.filename}, size={file_size}")

    return DocumentUploadResponse(
        id=doc.id,
        title=doc.title,
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        message="文档上传成功，正在处理中",
    )


def process_document_task(document_id: str, tenant_id: str, kb_id: str):
    """后台任务: 文档处理流水线

    解析 -> 分块 -> 向量化 -> 存储到 Qdrant -> 生成摘要
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            log.error(f"文档不存在: {document_id}")
            return

        # 更新状态
        doc.status = "processing"
        db.commit()

        log.info(f"开始处理文档: {doc.file_name}")

        # 1. 加载并解析文档
        loader = DocumentLoader(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        chunk_result = loader.load_and_chunk(doc.file_path, doc.file_type)

        if not chunk_result.chunks:
            doc.status = "failed"
            doc.processing_error = "文档内容为空或解析失败"
            db.commit()
            return

        # 2. 生成向量
        embedder = get_embedder()
        texts = [chunk.content for chunk in chunk_result.chunks]
        vectors = embedder.embed_documents(texts)

        # 3. 存储到 Qdrant
        points = []
        for i, (chunk, vector) in enumerate(zip(chunk_result.chunks, vectors)):
            payload = {
                "tenant_id": tenant_id,
                "kb_id": kb_id,
                "document_id": document_id,
                "document_title": doc.title,
                "chunk_index": chunk.chunk_index,
                "chunk_type": chunk.chunk_type,
                "source_page": chunk.page,
                "content": chunk.content,
            }
            points.append({"vector": vector.tolist(), **payload})

        point_ids = QdrantVectorStore.upsert_points(kb_id, points)

        # 4. 保存分块记录到数据库
        for i, (chunk, point_id) in enumerate(zip(chunk_result.chunks, point_ids)):
            db_chunk = DocumentChunk(
                document_id=document_id,
                tenant_id=tenant_id,
                kb_id=kb_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                vector_point_id=point_id,
                chunk_metadata=chunk.metadata,
            )
            db.add(db_chunk)

        # 5. 更新文档状态
        doc.status = "completed"
        doc.chunk_count = len(chunk_result.chunks)
        doc.doc_metadata = chunk_result.document_metadata

        # 6. 更新知识库统计
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            kb.document_count = (kb.document_count or 0) + 1
            kb.chunk_count = (kb.chunk_count or 0) + len(chunk_result.chunks)

        db.commit()

        # 7. 生成文档摘要 (异步, 不阻塞主流程)
        try:
            llm = get_llm()
            summary = llm.generate_summary(chunk_result.get_full_text()[:4000])
            doc.summary = summary
            db.commit()
        except Exception as e:
            log.warning(f"文档摘要生成失败: {e}")

        log.info(
            f"文档处理完成: {doc.file_name}, "
            f"chunks={len(chunk_result.chunks)}, "
            f"vectors={len(vectors)}"
        )

    except Exception as e:
        log.error(f"文档处理失败: {document_id}, error={e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            doc.processing_error = str(e)
            db.commit()
    finally:
        db.close()


@router.get("", response_model=DocumentListResponse, summary="获取文档列表")
def list_documents(
    kb_id: str = Query(None, description="按知识库筛选"),
    status: str = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文档列表"""
    query = db.query(Document).filter(
        Document.tenant_id == user["tenant_id"],
        Document.is_deleted == False,
    )

    if kb_id:
        query = query.filter(Document.kb_id == kb_id)
    if status:
        query = query.filter(Document.status == status)

    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return DocumentListResponse(
        total=total,
        documents=[DocumentResponse.model_validate(d) for d in docs],
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="获取文档详情")
def get_document(
    document_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文档详情"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == user["tenant_id"],
        Document.is_deleted == False,
    ).first()

    if doc is None:
        raise NotFoundException("文档", document_id)

    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/status", response_model=DocumentProcessStatus, summary="获取文档处理状态")
def get_document_status(
    document_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文档处理状态"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == user["tenant_id"],
    ).first()

    if doc is None:
        raise NotFoundException("文档", document_id)

    return DocumentProcessStatus(
        id=doc.id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        processing_error=doc.processing_error,
        summary=doc.summary,
    )


@router.delete("/{document_id}", summary="删除文档")
def delete_document(
    document_id: str,
    user: dict = Depends(require_maintainer),
    db: Session = Depends(get_db),
):
    """删除文档 (同时删除向量数据)"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == user["tenant_id"],
        Document.is_deleted == False,
    ).first()

    if doc is None:
        raise NotFoundException("文档", document_id)

    # 删除 Qdrant 中的向量
    QdrantVectorStore.delete_by_document(str(doc.kb_id), document_id, user["tenant_id"])

    # 删除物理文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 更新知识库统计
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
    if kb:
        kb.document_count = max(0, (kb.document_count or 0) - 1)
        kb.chunk_count = max(0, (kb.chunk_count or 0) - (doc.chunk_count or 0))

    # 软删除
    doc.is_deleted = True
    db.commit()

    return {"message": "文档已删除", "id": document_id}
