"""
认证 API - 登录、注册、刷新令牌
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.rbac import Role
from app.models.user import User, Tenant
from app.core.logging import log
from app.core.exceptions import ValidationException, NotFoundException
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserInfo,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，获取 JWT 令牌"""
    # 支持用户名或邮箱登录
    user = (
        db.query(User)
        .filter(
            (User.username == request.username) | (User.email == request.username),
            User.is_deleted == False,
        )
        .first()
    )

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()

    # 生成令牌
    extra_claims = {
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "username": user.username,
    }

    access_token = create_access_token(str(user.id), extra_claims)
    refresh_token = create_refresh_token(str(user.id), extra_claims)

    log.info(f"用户登录成功: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1440 * 60,
    )


@router.post("/register", response_model=UserInfo, summary="用户注册")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名/邮箱是否已存在
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

    # 查找租户
    tenant = db.query(Tenant).filter(Tenant.code == request.tenant_code).first()
    if tenant is None:
        raise NotFoundException("租户", request.tenant_code)

    # 创建用户
    user = User(
        tenant_id=tenant.id,
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        full_name=request.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log.info(f"用户注册成功: {user.username}, role={user.role}")

    return UserInfo(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
    )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """使用 Refresh Token 获取新的 Access Token"""
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    extra_claims = {
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "username": user.username,
    }

    new_access = create_access_token(str(user.id), extra_claims)
    new_refresh = create_refresh_token(str(user.id), extra_claims)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=1440 * 60,
    )


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
def get_me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前登录用户信息"""
    user_obj = db.query(User).filter(User.id == user["user_id"]).first()
    if user_obj is None:
        raise NotFoundException("用户")

    return UserInfo(
        id=str(user_obj.id),
        username=user_obj.username,
        email=user_obj.email,
        role=user_obj.role,
        full_name=user_obj.full_name,
        tenant_id=str(user_obj.tenant_id),
        is_active=user_obj.is_active,
    )
