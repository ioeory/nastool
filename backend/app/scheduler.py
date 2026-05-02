from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import select

from app.db import AsyncSessionLocal

scheduler = AsyncIOScheduler()

async def initialize_default_automations():
    """系统启动时，确保默认的自动化任务存在"""
    from app.db.models.automation import Automation
    
    DEFAULTS = [
        {
            "name": "全自动整理与刮削",
            "description": "监控下载器并在下载完成后自动执行整理和媒体库更新",
            "type": "transfer",
            "trigger": "interval",
            "trigger_config": {"minutes": 5},
            "is_active": True
        },
        {
            "name": "定时订阅检查",
            "description": "检查所有有效的订阅规则并全站搜索资源推送下载",
            "type": "subscribe",
            "trigger": "interval",
            "trigger_config": {"minutes": 30},
            "is_active": True
        }
    ]
    
    async with AsyncSessionLocal() as db:
        for item in DEFAULTS:
            result = await db.execute(select(Automation).where(Automation.type == item["type"]))
            if not result.scalar_one_or_none():
                auto = Automation(**item)
                db.add(auto)
                logger.info(f"[Scheduler] 已初始化默认任务: {item['name']}")
        await db.commit()

def setup_scheduler():
    """初始化并启动调度器"""
    scheduler.start()
    logger.info("✅ APScheduler 核心已后台启动 (待同步任务)")

async def sync_scheduler():
    """同步数据库任务（需在应用生命周期中调用）"""
    from app.modules.automation.manager import AutomationManager
    await initialize_default_automations()
    manager = AutomationManager()
    await manager.sync_all_to_scheduler()

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("🛑 APScheduler 已停止")
