"""
FastAPI 应用入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import log
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    log.info(f"=== {settings.APP_NAME} 启动中 ===")
    log.info(f"环境: {settings.APP_ENV}, 端口: {settings.APP_PORT}")
    log.info(f"DeepSeek 模型: {settings.DEEPSEEK_MODEL}")
    log.info(f"Embedding 模型: {settings.EMBEDDING_MODEL_NAME}")
    log.info(f"向量维度: {settings.EMBEDDING_DIMENSION}")

    # 检查数据库连接
    from app.db.session import check_db_connection
    check_db_connection()

    # 初始化数据库表和种子数据
    from app.db.init_db import init_db
    try:
        init_db()
    except Exception as e:
        log.error(f"数据库初始化失败: {e}")

    log.info(f"=== {settings.APP_NAME} 启动完成 ===")

    yield

    # 关闭
    log.info(f"=== {settings.APP_NAME} 关闭 ===")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
## 企业级知识库 RAG 系统 API

基于 DeepSeek + LangChain + LangGraph + Qdrant 构建的企业级知识库问答系统。

### 核心功能
- **多源文档接入**: PDF/Word/网页/图片，保留表格结构与 OCR
- **向量化存储与检索**: BGE-M3 Embedding + Qdrant 向量数据库
- **带引用来源的问答**: 答案附带文档来源、页码、相关度
- **多轮对话管理**: 基于 LangGraph 的状态机工作流
- **RBAC 权限控制**: 管理员/维护者/普通用户三级角色
- **租户隔离**: 多租户数据隔离
- **SSE 流式返回**: 实时流式输出答案

### 技术栈
- LLM: DeepSeek (deepseek-chat)
- RAG: LangChain + LangGraph
- Embedding: BAAI/bge-m3
- Vector DB: Qdrant
- API: FastAPI + SSE
- Auth: JWT + RBAC
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册路由
    app.include_router(api_router)

    # 健康检查
    @app.get("/health", tags=["系统"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    # 根路径
    @app.get("/", tags=["系统"])
    async def root():
        return {
            "message": f"欢迎使用 {settings.APP_NAME}",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
