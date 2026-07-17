"""
应用配置中心 - 基于 Pydantic Settings
所有配置项从环境变量 / .env 文件读取，支持类型校验与默认值
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- 应用 ---
    APP_NAME: str = "企业级知识库RAG"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- PostgreSQL ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "raguser"
    POSTGRES_PASSWORD: str = "ragpassword"
    POSTGRES_DB: str = "ragdb"
    DATABASE_URL: str = ""

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # --- Qdrant ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_PREFIX: str = "rag_"

    # --- DeepSeek ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TEMPERATURE: float = 0.3
    DEEPSEEK_MAX_TOKENS: int = 4096

    # --- Embedding ---
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_MODEL_DEVICE: str = "cpu"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 32

    # --- 文档处理 ---
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_FILE_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./data/uploads"

    # --- RAG ---
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SCORE_THRESHOLD: float = 0.5
    RERANK_ENABLED: bool = True
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_MAX_LENGTH: int = 512
    RERANK_TOP_K: int = 5

    # --- OCR ---
    OCR_ENABLED: bool = True
    OCR_LANG: str = "ch"

    # --- 日志 ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./data/logs"

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def qdrant_url(self) -> str:
        """获取 Qdrant 连接 URL"""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


# 全局单例
settings = Settings()
