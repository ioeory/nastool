"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.db import init_db, close_db
from app.log import setup_logger, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    - startup: 初始化日志、数据库、定时任务、超级管理员
    - shutdown: 优雅关闭
    """
    # ---- Startup ----
    setup_logger()
    logger.info(f"🚀 {settings.APP_NAME} 启动中...")

    # 初始化数据库（建表）
    await init_db()

    # 加载系统设置
    await _load_db_settings()

    # 创建超级管理员（首次启动）
    await _create_superuser()

    logger.info(f"✅ {settings.APP_NAME} 启动完成，API 地址: http://0.0.0.0:{settings.API_PORT}")

    # 启动后台调度器
    from app.scheduler import setup_scheduler, shutdown_scheduler, sync_scheduler
    setup_scheduler()
    await sync_scheduler()

    yield  # 应用运行中

    # ---- Shutdown ----
    logger.info(f"🛑 {settings.APP_NAME} 正在关闭...")
    shutdown_scheduler()
    await close_db()
    logger.info("👋 关闭完成")


async def _create_superuser() -> None:
    """首次启动时创建超级管理员账号"""
    from app.db import AsyncSessionLocal
    from app.db.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.name == settings.SUPERUSER)
        )
        if not result.scalar_one_or_none():
            admin = User(
                name=settings.SUPERUSER,
                password=get_password_hash(settings.SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                note="超级管理员（自动创建）",
            )
            session.add(admin)
            await session.commit()
            logger.info(f"✅ 超级管理员 [{settings.SUPERUSER}] 创建成功")

async def _load_db_settings() -> None:
    """从数据库加载并覆盖系统动态设置"""
    from app.db import AsyncSessionLocal
    from app.db.models.system_setting import SystemSetting
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemSetting))
        settings_in_db = result.scalars().all()
        
        for item in settings_in_db:
            if not hasattr(settings, item.key):
                continue
            v = item.value
            current_val = getattr(settings, item.key)
            
            if isinstance(current_val, bool):
                setattr(settings, item.key, v.lower() in ["true", "1", "yes"] if v else False)
            elif isinstance(current_val, int):
                setattr(settings, item.key, int(v) if v and v.isdigit() else 0)
            else:
                setattr(settings, item.key, v)
        logger.info(f"✅ 动态系统配置装载完毕 (共 {len(settings_in_db)} 项)")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="NAS 媒体库自动化管理工具 API",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,  # 生产环境隐藏 Swagger
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [settings.APP_DOMAIN or "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- API 路由 ----
    from app.api.v1 import api_router
    app.include_router(api_router)

    # ---- 前端静态文件服务（生产环境）----
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        logger.info(f"前端静态文件已挂载: {frontend_dist}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
