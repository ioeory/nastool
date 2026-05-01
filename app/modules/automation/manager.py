import asyncio
import time
from datetime import datetime
from typing import List, Optional
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.db.models.automation import Automation, AutomationHistory
from app.scheduler import scheduler

class AutomationManager:
    """
    自动化任务管理器：连接数据库定义与 APScheduler 执行器
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def get_db(self):
        if self.db:
            return self.db
        return AsyncSessionLocal()

    async def sync_all_to_scheduler(self):
        """将数据库中所有开启的任务同步到调度器"""
        logger.info("[Automation] 正在同步所有自动化任务到调度器...")
        
        # 先移除所有现有任务（除了系统内置必须保留的，如果有的话）
        for job in scheduler.get_jobs():
            if job.id.startswith("auto_"):
                scheduler.remove_job(job.id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Automation).where(Automation.is_active == True))
            automations = result.scalars().all()
            
            for auto in automations:
                await self._add_to_scheduler(auto)
        
        logger.info(f"[Automation] 同步完成，共加载 {len(automations)} 个任务")

    async def _add_to_scheduler(self, auto: Automation):
        """将单个任务添加到调度器"""
        job_id = f"auto_{auto.id}"
        
        # 允许重复替换
        # 提取当前触发器需要的参数，防止多余参数导致 TypeError
        full_config = auto.trigger_config or {}
        trigger_args = {}
        
        if auto.trigger == "interval":
            # 仅提取 interval 支持的参数
            if "minutes" in full_config:
                trigger_args["minutes"] = full_config["minutes"]
            if "hours" in full_config:
                trigger_args["hours"] = full_config["hours"]
            if "seconds" in full_config:
                trigger_args["seconds"] = full_config["seconds"]
                
            scheduler.add_job(
                self.execute_workflow,
                'interval',
                kwargs={"automation_id": auto.id},
                id=job_id,
                replace_existing=True,
                **trigger_args
            )
        elif auto.trigger == "cron":
            # 仅提取 cron 支持的参数
            if "cron" in full_config:
                # 解析 cron 字符串格式 (APScheduler 直接支持 cron 表达式作为参数名是不存在的，通常是分开的字段)
                # 但如果存的是 {"cron": "0 0 * * *"}，我们需要处理
                pass
            
            # 简化版：如果 trigger_config 里有 cron，我们假设它是 cron 格式字符串
            cron_val = full_config.get("cron")
            if cron_val:
                scheduler.add_job(
                    self.execute_workflow,
                    'cron',
                    kwargs={"automation_id": auto.id},
                    id=job_id,
                    replace_existing=True,
                    # 解析 5 位或 6 位 cron 表达式 (简单处理常见情况)
                    **self._parse_cron(cron_val)
                )
        
        logger.debug(f"[Automation] 已注册任务: {auto.name} (ID: {auto.id}, 触发: {auto.trigger})")

    async def execute_workflow(self, automation_id: int):
        """执行工作流核心逻辑"""
        start_time = datetime.now()
        
        async with AsyncSessionLocal() as db:
            # 1. 获取任务定义
            result = await db.execute(select(Automation).where(Automation.id == automation_id))
            auto = result.scalar_one_or_none()
            if not auto or not auto.is_active:
                return

            # 2. 创建历史记录
            history = AutomationHistory(
                automation_id=auto.id,
                name=auto.name,
                status="running"
            )
            db.add(history)
            await db.commit()
            await db.refresh(history)

            logger.info(f"[Automation] 🚀 开始执行任务: {auto.name}")
            
            error_msg = None
            try:
                # 3. 根据类型分发执行逻辑
                result_msg = "执行成功"
                if auto.type == "transfer":
                    from app.chain.transfer import TransferChain
                    chain = TransferChain(db)
                    result_msg = await chain.execute()
                elif auto.type == "subscribe":
                    from app.chain.subscribe import SubscribeChain
                    chain = SubscribeChain(db)
                    result_msg = await chain.execute()
                elif auto.type == "brush":
                    from app.modules.brush.manager import BrushManager
                    brush = BrushManager(db)
                    result_msg = await brush.execute(auto.id)
                elif auto.type in ("site_check", "site_checkin"):
                    from app.modules.checkin import CheckinManager
                    checkin_mgr = CheckinManager()
                    site_ids = (auto.task_config or {}).get("sites") or None
                    results = await checkin_mgr.checkin_all(site_ids=site_ids)
                    ok = sum(1 for r in results if r.success)
                    result_msg = f"签到完成: {ok}/{len(results)} 成功"
                else:
                    logger.warning(f"[Automation] 未知任务类型: {auto.type}")
                
                status = "success"
                message = result_msg or "执行成功"
            except Exception as e:
                logger.error(f"[Automation] 任务 {auto.name} 执行失败: {e}")
                status = "fail"
                message = str(e)
                error_msg = str(e)

            # 4. 更新历史与任务状态
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            history.status = status
            history.message = message
            history.end_time = end_time
            history.duration = duration
            
            auto.last_run = start_time
            # 更新下次运行时间（从 APScheduler 获取）
            job = scheduler.get_job(f"auto_{auto.id}")
            if job:
                auto.next_run = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None

            await db.commit()
            logger.info(f"[Automation] ✨ 任务执行完毕: {auto.name} (耗时 {duration}s, 状态: {status})")

    async def run_now(self, automation_id: int):
        """立即手动执行一次任务"""
        # 异步执行，不阻塞 API
        asyncio.create_task(self.execute_workflow(automation_id))
        return True

    def _parse_cron(self, cron_val: str) -> dict:
        """简单的 cron 字符串解析器 (兼容 5 位标准格式)"""
        try:
            parts = cron_val.split()
            if len(parts) == 5:
                return {
                    "minute": parts[0],
                    "hour": parts[1],
                    "day": parts[2],
                    "month": parts[3],
                    "day_of_week": parts[4]
                }
            return {"cron": cron_val}  # 兜底
        except:
            return {}
