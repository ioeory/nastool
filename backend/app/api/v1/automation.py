from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.user import User
from app.db.models.automation import Automation, AutomationHistory
from app.schemas import Response, AutomationCreate, AutomationUpdate
from app.modules.automation.manager import AutomationManager

router = APIRouter(prefix="/automation", tags=["自动化任务"])


def _merge_task_config(existing: Optional[Dict[str, Any]], incoming: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    PATCH 合并 task_config，避免前端某次只提交部分字段时整包覆盖，把 feed_source/rss_url 等刷流关键键弄丢。
    """
    if not incoming:
        return dict(existing or {})
    if not existing:
        return dict(incoming)
    merged: Dict[str, Any] = {**existing, **incoming}
    for key in ("selection_rules", "delete_rules"):
        if key in incoming and isinstance(incoming[key], dict):
            merged[key] = {**(existing.get(key) or {}), **incoming[key]}
    return merged

@router.get("/", response_model=Response, summary="获取所有自动化任务")
async def list_automations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Automation).order_by(Automation.id))
    automations = result.scalars().all()
    # 转换为 dict 并包含 next_run 信息
    data = []
    for a in automations:
        item = {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "type": a.type,
            "trigger": a.trigger,
            "trigger_config": a.trigger_config,
            "task_config": a.task_config,
            "is_active": a.is_active,
            "last_run": a.last_run.isoformat() if a.last_run else None,
            "next_run": a.next_run.isoformat() if a.next_run else None,
        }
        data.append(item)
    return Response(data=data)

@router.get("/history", response_model=Response, summary="获取任务运行历史")
async def get_history(
    limit: int = 50,
    automation_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(AutomationHistory).order_by(AutomationHistory.start_time.desc())
    if automation_id is not None:
        stmt = stmt.where(AutomationHistory.automation_id == automation_id)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    history = result.scalars().all()
    return {"code": 0, "message": "success", "data": [{
        "id": h.id,
        "automation_id": h.automation_id,
        "name": h.name,
        "start_time": h.start_time,
        "end_time": h.end_time,
        "status": h.status,
        "message": h.message,
        "duration": h.duration
    } for h in history]}

@router.post("/", response_model=Response, summary="创建自动化任务")
async def create_automation(
    data: AutomationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    new_auto = Automation(**data.model_dump())
    db.add(new_auto)
    await db.commit()
    await db.refresh(new_auto)
    
    # 同步到调度器
    manager = AutomationManager(db)
    await manager.sync_all_to_scheduler()
    
    return {"code": 0, "message": "任务创建成功并已加入调度器", "data": {"id": new_auto.id}}

@router.api_route("/{automation_id}/run", methods=["GET", "POST"], response_model=Response, summary="立即执行任务")
async def run_automation(
    automation_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # 检查任务是否存在
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    # 使用 FastAPI 的 BackgroundTasks 启动，避免 Session 冲突
    # 这里通过一个新的 Session 运行
    async def run_task():
        manager = AutomationManager()
        await manager.run_now(automation_id)
        
    background_tasks.add_task(run_task)
    return {"code": 0, "message": "任务已进入后台队列，请稍后在历史记录中查看结果"}

@router.post("/{automation_id}/toggle", response_model=Response, summary="启用/禁用任务")
async def toggle_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    auto.is_active = not auto.is_active
    await db.commit()
    
    # 同步到调度器
    manager = AutomationManager(db)
    await manager.sync_all_to_scheduler()
    
    return {"code": 0, "message": f"任务已{'启用' if auto.is_active else '禁用'}"}

@router.patch("/{automation_id}", response_model=Response, summary="更新任务配置")
async def update_automation(
    automation_id: int,
    data: AutomationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Automation).where(Automation.id == automation_id))
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "task_config" in update_data and update_data["task_config"] is not None:
        update_data["task_config"] = _merge_task_config(
            auto.task_config if isinstance(auto.task_config, dict) else {},
            update_data["task_config"],
        )

    if update_data:
        await db.execute(
            update(Automation).where(Automation.id == automation_id).values(**update_data)
        )
        await db.commit()

    # 同步到调度器
    manager = AutomationManager(db)
    await manager.sync_all_to_scheduler()

    return Response(message="更新成功并已同步到调度器")

@router.delete("/{automation_id}", response_model=Response, summary="删除自动化任务")
async def delete_automation(
    automation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await db.execute(delete(Automation).where(Automation.id == automation_id))
    await db.commit()
    
    # 同步到调度器
    manager = AutomationManager(db)
    await manager.sync_all_to_scheduler()
    
    return Response(message="任务已删除并从调度器移除")
