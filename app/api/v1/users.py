"""
用户管理 API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.core.rbac import Role
from app.models.user import User
from app.core.exceptions import NotFoundException, ValidationException
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=UserListResponse, summary="获取用户列表")
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户列表 (管理员可查看全部，普通用户只看自己)"""
    query = db.query(User).filter(User.is_deleted == False)

    # 非管理员只能看到自己
    if user["role"] != Role.ADMIN.value:
        query = query.filter(User.id == user["user_id"])

    total = query.count()
    users = query.offset((page - 1) * size).limit(size).all()

    return UserListResponse(
        total=total,
        users=[UserResponse.model_validate(u) for u in users],
    )


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
def get_user(
    user_id: UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定用户详情"""
    target = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if target is None:
        raise NotFoundException("用户", str(user_id))

    # 权限检查: 非管理员只能查看自己
    if user["role"] != Role.ADMIN.value and str(target.id) != user["user_id"]:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException()

    return UserResponse.model_validate(target)


@router.post("", response_model=UserResponse, summary="创建用户")
def create_user(
    request: UserCreate,
    user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建新用户 (仅管理员)"""
    existing = (
        db.query(User)
        .filter(
            (User.username == request.username) | (User.email == request.email),
            User.is_deleted == False,
        )
        .first()
    )
    if existing:
        raise ValidationException("用户名或邮箱已存在")

    new_user = User(
        tenant_id=request.tenant_id or user["tenant_id"],
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        full_name=request.full_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.patch("/{user_id}", response_model=UserResponse, summary="更新用户")
def update_user(
    user_id: UUID,
    request: UserUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户信息"""
    target = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if target is None:
        raise NotFoundException("用户", str(user_id))

    # 权限检查
    if user["role"] != Role.ADMIN.value and str(target.id) != user["user_id"]:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException()

    # 普通用户不能修改角色
    if user["role"] != Role.ADMIN.value and request.role is not None:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException("仅管理员可修改用户角色")

    if request.email is not None:
        target.email = request.email
    if request.full_name is not None:
        target.full_name = request.full_name
    if request.role is not None and user["role"] == Role.ADMIN.value:
        target.role = request.role
    if request.is_active is not None and user["role"] == Role.ADMIN.value:
        target.is_active = request.is_active

    db.commit()
    db.refresh(target)

    return UserResponse.model_validate(target)


@router.delete("/{user_id}", summary="删除用户")
def delete_user(
    user_id: UUID,
    user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """软删除用户 (仅管理员)"""
    target = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if target is None:
        raise NotFoundException("用户", str(user_id))

    target.is_deleted = True
    target.is_active = False
    db.commit()

    return {"message": "用户已删除", "id": str(user_id)}
