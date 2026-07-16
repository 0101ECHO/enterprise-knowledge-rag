"""
系统基础测试
验证核心模块的导入与配置
"""

import pytest
from app.core.config import settings


def test_config_loaded():
    """测试配置加载"""
    assert settings.APP_NAME is not None
    assert settings.DEEPSEEK_MODEL is not None
    assert settings.EMBEDDING_MODEL_NAME == "BAAI/bge-m3"


def test_security_password_hashing():
    """测试密码哈希"""
    from app.core.security import hash_password, verify_password

    password = "test123456"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_security_jwt_token():
    """测试 JWT 令牌"""
    from app.core.security import create_access_token, decode_token

    token = create_access_token("user-123", {"role": "admin"})
    assert token is not None

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_rbac_permissions():
    """测试 RBAC 权限"""
    from app.core.rbac import Role, Permission, has_permission, get_role_permissions

    # 管理员拥有全部权限
    admin_perms = get_role_permissions(Role.ADMIN)
    assert Permission.SYSTEM_ADMIN in admin_perms
    assert len(admin_perms) == len(Permission)

    # 普通用户只有问答权限
    user_perms = get_role_permissions(Role.USER)
    assert Permission.CHAT in user_perms
    assert Permission.USER_CREATE not in user_perms

    # 维护者有文档管理权限
    maintainer_perms = get_role_permissions(Role.MAINTAINER)
    assert Permission.DOC_UPLOAD in maintainer_perms
    assert Permission.SYSTEM_ADMIN not in maintainer_perms


def test_chunker():
    """测试文本分块器"""
    from app.services.document.chunker import TextChunker

    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = "这是一段测试文本。" * 50
    chunks = chunker._recursive_split(text)
    assert len(chunks) > 1
    assert all(len(c) <= 150 for c in chunks)  # 允许一些误差


def test_prompt_building():
    """测试 Prompt 构建"""
    from app.services.rag.prompt import build_context, build_chat_history

    docs = [
        {"content": "测试内容1", "score": 0.9, "payload": {"document_title": "doc1.pdf", "source_page": 1}},
        {"content": "测试内容2", "score": 0.8, "payload": {"document_title": "doc2.pdf", "source_page": 3}},
    ]
    context = build_context(docs)
    assert "测试内容1" in context
    assert "doc1.pdf" in context

    history = build_chat_history([
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"},
    ])
    assert "你好" in history


def test_tenant_context():
    """测试租户隔离上下文"""
    from app.core.rbac import TenantContext

    filter_dict = TenantContext.build_filter("tenant-123", {"kb_id": "kb-456"})
    assert filter_dict["tenant_id"] == "tenant-123"
    assert filter_dict["kb_id"] == "kb-456"
