# 企业级知识库 RAG 系统

> 基于 DeepSeek + LangChain + LangGraph + Qdrant + FastAPI 构建的企业级知识库问答系统

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        客户端 (Web / API)                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼───────────────────────────────────────┐
│                     FastAPI 应用层                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Auth API │ │ Users API│ │  KB API  │ │ Chat API │            │
│  │ (JWT)    │ │ (RBAC)   │ │          │ │ (SSE)    │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
│       └────────────┴────────────┴────────────┘                   │
│                    JWT 鉴权 + RBAC 权限控制                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                   LangGraph 工作流编排层                           │
│  ┌─────────────┐     ┌──────────┐     ┌──────────┐              │
│  │ 意图分类     │────►│ 向量检索  │────►│ 答案生成  │              │
│  │ IntentClass │     │ Retrieve │     │ Generate │              │
│  └──────┬──────┘     └────┬─────┘     └────┬─────┘              │
│         │                 │                │                     │
│    ┌────▼────┐       ┌────▼────┐     ┌────▼────┐               │
│    │ 闲聊/搜索 │       │ 重排序   │     │ 反思检查 │               │
│    │ 路由     │       │ Rerank  │     │ Reflect │               │
│    └─────────┘       └─────────┘     └────┬────┘               │
│                                         │ 不充分 → 重试检索        │
└─────────────────────────────────────────┼────────────────────────┘
                                          │
┌─────────────────────────────────────────▼────────────────────────┐
│                      RAG 服务层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ DeepSeek LLM │  │ BGE-M3       │  │ 文档处理      │           │
│  │ (答案生成)    │  │ Embedding    │  │ (PDF/Word/   │           │
│  │              │  │ (向量化)      │  │  HTML/OCR)   │           │
│  └──────────────┘  └──────┬───────┘  └──────────────┘           │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                      基础设施层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ PostgreSQL   │  │ Qdrant       │  │ Redis        │           │
│  │ (用户/文档/   │  │ (向量存储与   │  │ (缓存/消息   │           │
│  │  对话/权限)   │  │  检索)       │  │  队列)       │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

## 技术选型说明

### 向量数据库: Qdrant

| 对比项 | Qdrant | Milvus | pgvector |
|--------|--------|--------|----------|
| 部署复杂度 | 低 (单容器) | 高 (多组件) | 低 (PG 插件) |
| 检索性能 | 优秀 (Rust + HNSW) | 优秀 (C++ + 多索引) | 一般 (大规模时下降) |
| Payload 过滤 | 原生支持，性能优 | 支持 | SQL WHERE |
| 多租户隔离 | payload 过滤天然支持 | partition/key | SQL 行级隔离 |
| API 友好度 | 高 (REST + gRPC) | 中 | SQL |
| 适用规模 | 百万~千万级 | 亿级 | 十万~百万级 |

**选择 Qdrant 的理由**:
1. **部署简单**: 单个 Docker 容器即可启动，无需额外依赖
2. **租户隔离**: payload 过滤天然支持多租户与 RBAC，性能优于 SQL JOIN
3. **性能优秀**: Rust 实现，HNSW 索引，在百万级向量下检索延迟 <10ms
4. **API 友好**: REST + Python SDK，文档完善，集成成本低
5. **功能丰富**: 支持批量操作、量化压缩、快照备份

### Embedding: BAAI/bge-m3

- **多语言**: 支持 100+ 语言，中英文效果优秀
- **多粒度**: 稠密向量 (1024维) + 稀疏向量 + ColBERT
- **长序列**: 支持最长 8192 token 输入
- **开源免费**: 可本地部署，无 API 调用成本

### LLM: DeepSeek

- **性价比高**: API 价格远低于 GPT-4，效果接近
- **中文优秀**: 中文理解和生成能力出色
- **OpenAI 兼容**: 可直接使用 LangChain ChatOpenAI 适配器

## 项目结构

```
企业级知识库RAG/
├── app/
│   ├── main.py                          # FastAPI 应用入口
│   ├── core/                            # 核心模块
│   │   ├── config.py                    # 配置中心 (Pydantic Settings)
│   │   ├── security.py                  # JWT 生成/验证、密码哈希
│   │   ├── rbac.py                      # 角色权限控制 (RBAC)
│   │   ├── logging.py                   # 结构化日志 (Loguru)
│   │   └── exceptions.py                # 自定义异常与全局处理
│   ├── api/
│   │   ├── deps.py                      # 依赖注入 (认证、权限、DB)
│   │   └── v1/
│   │       ├── router.py                # 路由聚合
│   │       ├── auth.py                  # 认证接口 (登录/注册/刷新)
│   │       ├── users.py                 # 用户管理接口
│   │       ├── knowledge_base.py        # 知识库管理接口
│   │       ├── documents.py             # 文档上传/管理接口
│   │       └── chat.py                  # 问答接口 (同步/SSE流式)
│   ├── models/                          # SQLAlchemy 数据模型
│   │   ├── user.py                      # 用户、租户模型
│   │   ├── knowledge_base.py            # 知识库模型
│   │   ├── document.py                  # 文档、分块模型
│   │   └── conversation.py              # 对话、消息模型
│   ├── schemas/                         # Pydantic 请求/响应模型
│   ├── services/                        # 业务服务层
│   │   ├── document/                    # 文档处理
│   │   │   ├── loader.py                # 多格式文档加载器
│   │   │   ├── parser.py                # PDF/Word/HTML/图片解析
│   │   │   ├── chunker.py               # 智能分块 (保留表格)
│   │   │   └── ocr.py                   # OCR 服务 (RapidOCR)
│   │   ├── embedding/
│   │   │   └── bge_m3.py                # BGE-M3 Embedding 服务
│   │   ├── vectorstore/
│   │   │   └── qdrant_store.py          # Qdrant 向量存储
│   │   ├── llm/
│   │   │   └── deepseek.py              # DeepSeek LLM 客户端
│   │   ├── rag/
│   │   │   ├── retriever.py             # 向量检索 + 重排序
│   │   │   ├── prompt.py                # Prompt 模板
│   │   │   └── pipeline.py              # RAG 管道 (LangChain)
│   │   └── graph/                       # LangGraph 工作流
│   │       ├── state.py                 # 对话状态定义
│   │       ├── nodes.py                 # 工作流节点
│   │       └── workflow.py              # 工作流编排
│   └── db/                              # 数据库
│       ├── session.py                   # 会话管理
│       └── init_db.py                   # 初始化与种子数据
├── docker-compose.yml                   # Docker Compose 部署
├── Dockerfile                           # 应用镜像构建
├── requirements.txt                     # Python 依赖
├── .env.example                         # 环境变量模板
└── README.md
```

## 快速开始

### 方式一: Docker Compose 一键部署 (推荐)

```bash
# 1. 克隆项目
git clone <repository-url>
cd 企业级知识库RAG

# 2. 复制环境变量配置
cp .env.example .env

# 3. 编辑 .env，填写关键配置
#    - JWT_SECRET_KEY: 生成密钥 (openssl rand -hex 32)
#    - DEEPSEEK_API_KEY: 你的 DeepSeek API Key
#    - 其他配置保持默认即可

# 4. 一键启动所有服务
docker-compose up -d

# 5. 查看启动日志
docker-compose logs -f app

# 6. 访问服务
#    API 文档: http://localhost:8000/docs
#    健康检查: http://localhost:8000/health
```

### 方式二: 本地开发运行

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制并配置环境变量
cp .env.example .env
# 编辑 .env，修改数据库/Redis/Qdrant 地址为 localhost

# 4. 启动依赖服务 (PostgreSQL + Qdrant + Redis)
#    方式 A: 仅启动基础设施
docker-compose up -d postgres qdrant redis
#
#    方式 B: 本地安装各服务

# 5. 初始化数据库
python -m app.db.init_db

# 6. 启动应用
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 7. 访问 http://localhost:8000/docs
```

## 默认账号

系统初始化后自动创建以下账号:

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin | admin123456 | 管理员 | 全部权限 |
| maintainer | maintainer123 | 维护者 | 文档/知识库管理 + 问答 |
| user | user123456 | 普通用户 | 问答 + 查看文档 |

## API 使用示例

### 1. 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123456"}'
```

### 2. 创建知识库

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "产品文档库", "description": "产品相关文档", "visibility": "private"}'
```

### 3. 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload/<kb_id> \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/document.pdf"
```

### 4. 查询文档处理状态

```bash
curl http://localhost:8000/api/v1/documents/<document_id>/status \
  -H "Authorization: Bearer <token>"
```

### 5. 同步问答

```bash
curl -X POST http://localhost:8000/api/v1/chat/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "产品的核心功能有哪些？", "kb_id": "<kb_id>"}'
```

### 6. 流式问答 (SSE)

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "产品的主要特性是什么？", "kb_id": "<kb_id>"}'
```

## RBAC 权限模型

| 权限 | 管理员 | 维护者 | 普通用户 |
|------|--------|--------|----------|
| 用户管理 | ✅ | ❌ | ❌ |
| 创建知识库 | ✅ | ✅ | ❌ |
| 上传文档 | ✅ | ✅ | ❌ |
| 删除文档 | ✅ | ✅ | ❌ |
| 知识库问答 | ✅ | ✅ | ✅ |
| 查看对话历史 | ✅ | ✅ | ✅ |
| 系统管理 | ✅ | ❌ | ❌ |

## LangGraph 工作流

系统使用 LangGraph 构建多轮对话状态机:

```
START → 意图分类 → ┬─ 知识问答 → 向量检索 → 答案生成 → 反思检查 → ┬─ 充分 → END
                   ├─ 闲聊     → 直接响应 → END                      └─ 不充分 → 重试检索
                   ├─ 搜索     → 向量检索 → 返回搜索结果 → END
                   ├─ 摘要     → 总结对话 → END
                   └─ 澄清     → 请求澄清 → END
```

**核心节点**:
- **意图分类**: 使用 LLM + 规则判断用户意图
- **向量检索**: BGE-M3 向量化 + Qdrant 检索 + 可选重排序
- **答案生成**: 基于检索上下文的 Prompt 组装 + DeepSeek 生成
- **反思检查**: 评估答案质量，不充分时自动重试

## 可观测性

- **结构化日志**: Loguru JSON 格式，按天轮转，错误日志独立文件
- **请求追踪**: 每个请求记录路径、耗时、用户信息
- **健康检查**: `/health` 端点 + Docker HEALTHCHECK
- **API 文档**: Swagger UI (`/docs`) + ReDoc (`/redoc`)

## 环境变量说明

参见 `.env.example` 文件，关键配置:

| 变量 | 说明 | 默认值 |
|------|------|--------|
| JWT_SECRET_KEY | JWT 签名密钥 | (必须修改) |
| DEEPSEEK_API_KEY | DeepSeek API Key | (必须填写) |
| EMBEDDING_MODEL_NAME | Embedding 模型 | BAAI/bge-m3 |
| CHUNK_SIZE | 文档分块大小 | 512 |
| RETRIEVAL_TOP_K | 检索返回数量 | 5 |
| OCR_ENABLED | 是否启用 OCR | true |

## License

MIT
