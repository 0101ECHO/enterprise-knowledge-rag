"""
数据库初始化脚本
创建所有表并插入初始数据
"""

from app.db.session import engine, Base, SessionLocal
from app.models.user import Tenant, User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentChunk
from app.models.conversation import Conversation, Message
from app.core.security import hash_password
from app.core.logging import log


def init_tables():
    """创建所有数据库表"""
    log.info("开始创建数据库表...")
    Base.metadata.create_all(bind=engine)
    log.info("数据库表创建完成")


def init_seed_data():
    """创建初始种子数据：默认租户、管理员用户"""
    db = SessionLocal()
    try:
        # 检查是否已有租户
        existing = db.query(Tenant).first()
        if existing:
            log.info("种子数据已存在，跳过初始化")
            return

        # 创建默认租户
        tenant = Tenant(
            name="默认租户",
            code="default",
            description="系统默认租户",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

        # 创建管理员用户
        admin = User(
            tenant_id=tenant.id,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("admin123456"),
            role="admin",
            full_name="系统管理员",
            is_active=True,
        )
        db.add(admin)

        # 创建维护者用户
        maintainer = User(
            tenant_id=tenant.id,
            username="maintainer",
            email="maintainer@example.com",
            hashed_password=hash_password("maintainer123"),
            role="maintainer",
            full_name="知识库维护者",
            is_active=True,
        )
        db.add(maintainer)

        # 创建普通用户
        user = User(
            tenant_id=tenant.id,
            username="user",
            email="user@example.com",
            hashed_password=hash_password("user123456"),
            role="user",
            full_name="普通用户",
            is_active=True,
        )
        db.add(user)

        db.commit()
        log.info(f"种子数据创建完成: 租户={tenant.code}, 管理员={admin.username}")
        log.info("默认账号: admin/admin123456, maintainer/maintainer123, user/user123456")

    except Exception as e:
        db.rollback()
        log.error(f"种子数据创建失败: {e}")
        raise
    finally:
        db.close()


def init_db():
    """完整初始化：建表 + 种子数据"""
    init_tables()
    init_seed_data()


if __name__ == "__main__":
    init_db()
