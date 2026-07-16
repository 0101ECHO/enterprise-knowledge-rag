"""用户管理 Schema"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str | None = None
    role: str = Field(default="user")
    tenant_id: str | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    full_name: str | None = None
    tenant_id: UUID
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]
