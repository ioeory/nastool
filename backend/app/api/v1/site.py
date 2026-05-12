"""
站点管理 API
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.site import Site
from app.db.models.user import User
from app.schemas import Response, SiteCreate, SiteUpdate, SiteOut, SiteTestResult, CheckinOut
from app.site.registry import SiteRegistry
from app.site.manager import SiteManager
from app.utils.url import extract_domain, normalize_url

router = APIRouter(prefix="/site", tags=["站点管理"])
registry = SiteRegistry()


@router.get("/", response_model=Response, summary="获取所有站点列表")
async def list_sites(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Site).order_by(Site.pri)
    if active_only:
        query = query.where(Site.is_active == True)
    result = await db.execute(query)
    sites = result.scalars().all()
    return Response(data=[SiteOut.model_validate(s) for s in sites])


@router.post("/", response_model=Response, summary="手动添加站点")
async def add_site(
    site_in: SiteCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    添加站点流程：
    1. 自动探测站点框架（NexusPHP / Gazelle 等）
    2. 在 SiteRegistry 中查找内置配置
    3. 验证 Cookie 有效性
    4. 写入数据库
    5. 后台缓存 favicon
    """
    manager = SiteManager(db)
    try:
        site = await manager.add_site(site_in)
        # 后台缓存图标
        background_tasks.add_task(manager.cache_favicon, site.domain)
        return Response(data=SiteOut.model_validate(site), message="站点添加成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/registry/list", response_model=Response, summary="查看内置支持的站点列表（注册表）")
async def list_registry(_: User = Depends(get_current_user)):
    """返回内置 sites.json 中所有支持的站点元数据（不含认证信息）"""
    indexers = registry.get_all_indexers()
    return Response(data=indexers, message=f"共 {len(indexers)} 个内置站点")


@router.post("/cookiecloud/sync", response_model=Response, summary="同步 CookieCloud")
async def sync_cookiecloud(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """从 CookieCloud 服务同步站点 Cookie"""
    from app.core.config import settings
    if not settings.COOKIECLOUD_HOST:
        raise HTTPException(status_code=400, detail="未配置 CookieCloud 服务")
    manager = SiteManager(db)
    background_tasks.add_task(manager.sync_cookiecloud)
    return Response(message="CookieCloud 同步已在后台启动")


@router.post("/checkin/all", response_model=Response, summary="批量签到所有激活站点")
async def checkin_all_sites(
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_user),
):
    """在后台对所有激活站点批量执行签到"""
    from app.modules.checkin import CheckinManager
    manager = CheckinManager()
    background_tasks.add_task(manager.checkin_all)
    return Response(message="批量签到已在后台启动，请查看日志")


@router.get("/{site_id}", response_model=Response, summary="获取站点详情")
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")
    return Response(data=SiteOut.model_validate(site))


@router.patch("/{site_id}", response_model=Response, summary="更新站点配置")
async def update_site(
    site_id: int,
    site_in: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    update_data = site_in.model_dump(exclude_unset=True)

    # 敏感字段：仅空白则不更新，避免 PATCH 误清空
    for secret_key in ("cookie", "apikey", "token"):
        if secret_key in update_data:
            val = update_data[secret_key]
            if val is None or (isinstance(val, str) and not val.strip()):
                del update_data[secret_key]

    # URL 变更时同步 domain（与添加站点时 extract_domain 一致）
    if "url" in update_data and update_data["url"]:
        norm = normalize_url(update_data["url"])
        new_domain = extract_domain(norm)
        if not new_domain:
            raise HTTPException(status_code=400, detail="无效的站点 URL")
        if new_domain != site.domain:
            clash = await db.execute(
                select(Site.id).where(Site.domain == new_domain, Site.id != site_id)
            )
            if clash.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"域名 {new_domain} 已被其他站点占用",
                )
        update_data["url"] = norm
        update_data["domain"] = new_domain

    if update_data:
        await db.execute(
            update(Site).where(Site.id == site_id).values(**update_data)
        )
        await db.commit()
    return Response(message="更新成功")


@router.delete("/{site_id}", response_model=Response, summary="删除站点")
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await db.execute(delete(Site).where(Site.id == site_id))
    await db.commit()
    return Response(message="删除成功")


@router.post("/{site_id}/test", response_model=Response, summary="测试站点连通性")
async def test_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    manager = SiteManager(db)
    test_result = await manager.test_site(site)
    return Response(data=test_result)


@router.post("/{site_id}/checkin", response_model=Response, summary="手动触发站点签到")
async def checkin_site(
    site_id: int,
    _: User = Depends(get_current_user),
):
    """手动对指定站点执行签到，立即返回结果"""
    from app.modules.checkin import CheckinManager
    manager = CheckinManager()
    result = await manager.checkin_one(site_id)
    return Response(
        data=CheckinOut(
            site_id=result.site_id,
            site_name=result.site_name,
            success=result.success,
            message=result.message,
        ),
        message="签到成功" if result.success else "签到失败",
    )
