"""
API v1 路由聚合
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.documents import router as documents_router
from app.api.v1.chat import router as chat_router

api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(kb_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
