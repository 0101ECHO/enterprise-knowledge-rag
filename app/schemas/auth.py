"""认证相关 Schema"""

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名或邮箱")
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str | None = None
    role: str = Field(default="user", description="角色: admin/maintainer/user")
    tenant_code: str = Field(default="default", description="租户编码")


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: str | None = None
    tenant_id: str
    is_active: bool
