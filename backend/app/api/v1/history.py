"""
整理历史 / 下载历史 列表 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.history import DownloadHistory, TransferHistory
from app.db.models.user import User
from app.schemas import PageResponse

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("/transfers", response_model=PageResponse, summary="分页查询文件整理历史")
async def list_transfer_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    success: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cnt_stmt = select(func.count()).select_from(TransferHistory)
    stmt = select(TransferHistory).order_by(TransferHistory.id.desc())
    if success is not None:
        cnt_stmt = cnt_stmt.where(TransferHistory.success == success)
        stmt = stmt.where(TransferHistory.success == success)

    total = int(await db.scalar(cnt_stmt) or 0)
    offset = (page - 1) * page_size
    result = await db.execute(stmt.offset(offset).limit(page_size))
    rows = result.scalars().all()

    data = [
        {
            "id": r.id,
            "src": r.src,
            "dest": r.dest,
            "title": r.title,
            "year": r.year,
            "media_type": r.media_type,
            "tmdb_id": r.tmdb_id,
            "season": r.season,
            "episode": r.episode,
            "mode": r.mode,
            "downloader": r.downloader,
            "download_hash": r.download_hash,
            "success": r.success,
            "errmsg": r.errmsg,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return PageResponse(total=total, page=page, page_size=page_size, data=data)


@router.get("/downloads", response_model=PageResponse, summary="分页查询下载历史")
async def list_download_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cnt_stmt = select(func.count()).select_from(DownloadHistory)
    total = int(await db.scalar(cnt_stmt) or 0)
    offset = (page - 1) * page_size
    result = await db.execute(
        select(DownloadHistory)
        .order_by(DownloadHistory.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()
    data = [
        {
            "id": r.id,
            "site_id": r.site_id,
            "title": r.title,
            "torrent_url": r.torrent_url,
            "status": r.status,
            "size": r.size,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return PageResponse(total=total, page=page, page_size=page_size, data=data)
