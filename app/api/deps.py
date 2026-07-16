"""
FastAPI 依赖注入
提供: 当前用户获取、权限校验、数据库会话、租户隔离
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.core.rbac import Role
from app.models.user import User
from app.core.logging import log


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """从 JWT 令牌中解析当前用户信息

    Returns:
        用户信息 dict: {user_id, tenant_id, role, username, email}
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 解析 Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，应为 Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
        )

    # 验证用户是否存在且活跃
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "username": user.username,
        "email": user.email,
    }


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """可选的用户获取 (不强制认证)"""
    if not authorization:
        return None
    try:
        return get_current_user(authorization, db)
    except HTTPException:
        return None


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求管理员权限"""
    if user.get("role") != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


def require_maintainer(user: dict = Depends(get_current_user)) -> dict:
    """要求维护者或更高权限"""
    if user.get("role") not in (Role.ADMIN.value, Role.MAINTAINER.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要知识库维护者权限",
        )
    return user
