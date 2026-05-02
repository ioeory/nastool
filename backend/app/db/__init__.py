"""
数据库初始化 — SQLAlchemy 2.x 异步引擎 + Session 工厂
支持 SQLite（开发/默认）和 PostgreSQL（生产）
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.log import logger


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


# ---- 引擎配置 ----
_engine_kwargs: dict = {
    "echo": settings.DEBUG,
}

if settings.DB_TYPE == "sqlite":
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """创建所有表（如果不存在）"""
    from app.db.models import site, user, subscribe, history, sitestatistic
    from app.db.models import system_setting, downloader # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")


async def close_db() -> None:
    """关闭数据库连接池"""
    await engine.dispose()
    logger.info("数据库连接池已关闭")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """异步数据库会话上下文管理器"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入 Session 生成器"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
