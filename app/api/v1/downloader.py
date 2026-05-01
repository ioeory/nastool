from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.downloader import Downloader
from app.schemas import Response

router = APIRouter(prefix="/downloader", tags=["下载器"])

@router.get("/", response_model=Response, summary="获取下载器列表")
async def list_downloaders(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user)
):
    stmt = select(Downloader).order_by(Downloader.priority.asc())
    if active_only:
        stmt = stmt.where(Downloader.is_active == True)
        
    result = await db.execute(stmt)
    downloaders = result.scalars().all()
    
    return Response(data=[
        {
            "id": d.id,
            "name": d.name,
            "client_type": d.client_type,
            "host": d.host,
            "username": d.username,
            "password": d.password,
            "category": d.category,
            "save_path": d.save_path,
            "is_active": d.is_active,
            "priority": d.priority,
            "auto_category_management": getattr(d, 'auto_category_management', False),
            "sequential_download": getattr(d, 'sequential_download', False),
            "force_resume": getattr(d, 'force_resume', False),
            "first_last_piece_priority": getattr(d, 'first_last_piece_priority', False),
            "path_mapping": getattr(d, 'path_mapping', "[]"),
        }
        for d in downloaders
    ])


@router.post("/", response_model=Response, summary="添加新下载器")
async def add_downloader(data: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    # 查重
    stmt = select(Downloader).where(Downloader.name == data.get("name"))
    existing = await db.scalar(stmt)
    if existing:
        return Response(code=1, message="下载器名称已存在")
        
    d = Downloader(
        name=data.get("name"),
        client_type=data.get("client_type", "qbittorrent"),
        host=data.get("host", ""),
        username=data.get("username"),
        password=data.get("password"),
        category=data.get("category"),
        save_path=data.get("save_path"),
        is_active=data.get("is_active", True),
        priority=data.get("priority", 100),
        auto_category_management=data.get("auto_category_management", False),
        sequential_download=data.get("sequential_download", False),
        force_resume=data.get("force_resume", False),
        first_last_piece_priority=data.get("first_last_piece_priority", False),
        path_mapping=data.get("path_mapping", "[]"),
    )
    db.add(d)
    await db.commit()
    return Response(message="添加下载器成功")


@router.patch("/{d_id}", response_model=Response, summary="更新下载器")
async def update_downloader(d_id: int, data: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    stmt = select(Downloader).where(Downloader.id == d_id)
    d = await db.scalar(stmt)
    if not d:
        return Response(code=1, message="下载器不存在")
        
    # 如果修改名称，检查重名
    new_name = data.get("name")
    if new_name and new_name != d.name:
        exist_stmt = select(Downloader).where(Downloader.name == new_name)
        if await db.scalar(exist_stmt):
            return Response(code=1, message="下载器名称已存在")

    for k, v in data.items():
        if hasattr(d, k) and k != "id":
            setattr(d, k, v)
            
    await db.commit()
    return Response(message="更新下载器成功")


@router.delete("/{d_id}", response_model=Response, summary="删除下载器")
async def delete_downloader(d_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    stmt = select(Downloader).where(Downloader.id == d_id)
    d = await db.scalar(stmt)
    if not d:
        return Response(code=1, message="下载器不存在")
        
    await db.delete(d)
    await db.commit()
    return Response(message="删除下载器成功")


@router.post("/{d_id}/test", response_model=Response, summary="测试下载器连通性")
async def test_downloader(d_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    stmt = select(Downloader).where(Downloader.id == d_id)
    d = await db.scalar(stmt)
    if not d:
        return Response(code=1, message="下载器不存在")
        
    from app.modules.qbittorrent import QbittorrentClient
    from app.modules.transmission import TransmissionClient

    try:
        if d.client_type == "qbittorrent":
            client = QbittorrentClient(host=d.host, username=d.username, password=d.password)
            if await client.login():
                return Response(message="qBittorrent 测试连通成功")
            else:
                return Response(code=1, message="qBittorrent 登录失败或连通超时")
        elif d.client_type == "transmission":
            client = TransmissionClient(host=d.host, username=d.username, password=d.password)
            if await client.login():
                return Response(message="Transmission 测试连通成功")
            else:
                return Response(code=1, message="Transmission 登录失败或连通超时")
        else:
            return Response(code=1, message="不支持的下载器类型")
    except Exception as e:
        return Response(code=1, message=f"测试过程发生异常: {str(e)}")
@router.get("/speed", response_model=Response, summary="获取全站实时下载/上传速度汇总")
async def get_total_speed(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """获取所有活跃下载器的实时速度并汇总"""
    from app.modules.qbittorrent import QbittorrentClient

    stmt = select(Downloader).where(Downloader.is_active == True)
    result = await db.execute(stmt)
    downloaders = result.scalars().all()
    
    total_dl = 0
    total_ul = 0
    
    for d in downloaders:
        if d.client_type == "qbittorrent":
            try:
                client = QbittorrentClient(host=d.host, username=d.username, password=d.password)
                info = await client.get_transfer_info()
                if info:
                    total_dl += info.get("dl_info_speed", 0)
                    total_ul += info.get("up_info_speed", 0)
            except Exception:
                continue
                
    return Response(data={
        "dl_speed": total_dl,
        "ul_speed": total_ul
    })
