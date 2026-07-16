"""
基于角色的访问控制 (RBAC)
定义角色、权限以及装饰器风格的权限检查
"""

from enum import Enum
from typing import List, Set

from fastapi import HTTPException, status


class Role(str, Enum):
    """系统角色枚举"""

    ADMIN = "admin"             # 管理员：全部权限
    MAINTAINER = "maintainer"   # 知识库维护者：文档管理、知识库管理
    USER = "user"               # 普通用户：问答、查看文档


class Permission(str, Enum):
    """权限枚举"""

    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # 知识库管理
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"

    # 文档管理
    DOC_UPLOAD = "doc:upload"
    DOC_READ = "doc:read"
    DOC_DELETE = "doc:delete"

    # 问答
    CHAT = "chat:ask"
    CHAT_HISTORY = "chat:history"

    # 系统
    SYSTEM_ADMIN = "system:admin"


# 角色 -> 权限映射表
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # 全部权限
    Role.MAINTAINER: {
        Permission.KB_CREATE,
        Permission.KB_READ,
        Permission.KB_UPDATE,
        Permission.DOC_UPLOAD,
        Permission.DOC_READ,
        Permission.DOC_DELETE,
        Permission.CHAT,
        Permission.CHAT_HISTORY,
        Permission.USER_READ,
    },
    Role.USER: {
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.CHAT,
        Permission.CHAT_HISTORY,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """获取角色对应的所有权限"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """检查角色是否拥有指定权限"""
    return permission in get_role_permissions(role)


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """检查角色是否拥有给定权限中的任意一个"""
    return any(p in get_role_permissions(role) for p in permissions)


class PermissionChecker:
    """权限检查器 - 在端点函数体内调用

    用法:
        @router.post("/users")
        def create_user(user=Depends(get_current_user)):
            PermissionChecker([Permission.USER_CREATE]).check(user)
            ...

    注意: 对于路由级别的依赖注入，请使用 app/api/deps.py 中的
    require_admin / require_maintainer 函数。
    """

    def __init__(self, required_permissions: List[Permission]):
        self.required_permissions = required_permissions

    def check(self, user: dict) -> bool:
        """检查用户是否拥有所需权限，不通过则抛出 403"""
        user_role = Role(user.get("role", "user"))
        if not has_any_permission(user_role, self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要以下权限之一: {[p.value for p in self.required_permissions]}",
            )
        return True


def check_permissions(user: dict, permissions: List[Permission]) -> bool:
    """便捷函数: 检查用户权限"""
    return PermissionChecker(permissions).check(user)


class TenantContext:
    """租户上下文 - 用于租户隔离"""

    @staticmethod
    def build_filter(tenant_id: str, extra: dict | None = None) -> dict:
        """构建 Qdrant 过滤条件，确保租户隔离"""
        filter_dict = {"tenant_id": tenant_id}
        if extra:
            filter_dict.update(extra)
        return filter_dict
