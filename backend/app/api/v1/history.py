"""
整理历史 / 下载历史 列表 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.downloader import Downloader
from app.db.models.history import DownloadHistory, TransferHistory
from app.db.models.site import Site
from app.db.models.user import User
from app.schemas import PageResponse

router = APIRouter(prefix="/history", tags=["历史记录"])


# qBittorrent state → 统一状态码
_QB_STATE_MAP = {
    "uploading": "completed",
    "stalledUP": "completed",
    "queuedUP": "completed",
    "forcedUP": "completed",
    "checkingUP": "completed",
    "pausedUP": "paused",
    "downloading": "downloading",
    "metaDL": "downloading",
    "stalledDL": "downloading",
    "queuedDL": "downloading",
    "forcedDL": "downloading",
    "checkingDL": "downloading",
    "allocating": "downloading",
    "pausedDL": "paused",
    "checkingResumeData": "checking",
    "moving": "moving",
    "error": "error",
    "missingFiles": "error",
    "unknown": "unknown",
}

# Transmission status (int) → 统一状态码
_TR_STATE_MAP = {
    0: "paused",
    1: "checking",
    2: "checking",
    3: "downloading",
    4: "downloading",
    5: "completed",
    6: "completed",
}


def _normalize_title(s: Optional[str]) -> str:
    return (s or "").strip().lower()


async def _build_torrent_state_index(db: AsyncSession) -> dict:
    """
    汇总所有启用下载器中的种子，按标题建立 {归一化标题: {status, size}} 索引
    """
    from app.modules.qbittorrent import QbittorrentClient
    from app.modules.transmission import TransmissionClient

    index: dict[str, dict] = {}
    try:
        result = await db.execute(select(Downloader).where(Downloader.is_active == True))
        downloaders = result.scalars().all()
    except Exception as e:
        logger.warning(f"加载下载器列表失败: {e}")
        return index

    for d in downloaders:
        try:
            if d.client_type == "qbittorrent":
                client = QbittorrentClient(
                    host=d.host, username=d.username, password=d.password, category=d.category
                )
                torrents = await client.get_torrents()
                for t in torrents or []:
                    name = _normalize_title(t.get("name"))
                    if not name:
                        continue
                    index[name] = {
                        "status": _QB_STATE_MAP.get(t.get("state"), t.get("state") or "unknown"),
                        "size": t.get("size") or t.get("total_size"),
                        "progress": t.get("progress"),
                    }
            elif d.client_type == "transmission":
                client = TransmissionClient(host=d.host, username=d.username, password=d.password)
                torrents = await client.get_torrents()
                for t in torrents or []:
                    name = _normalize_title(t.get("name"))
                    if not name:
                        continue
                    index[name] = {
                        "status": _TR_STATE_MAP.get(t.get("status"), "unknown"),
                        "size": t.get("totalSize"),
                        "progress": t.get("percentDone"),
                    }
        except Exception as e:
            logger.warning(f"查询下载器 {d.name} 状态失败: {e}")
    return index


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

    # 站点 ID → 站点名称
    site_id_set = {r.site_id for r in rows if r.site_id is not None}
    site_name_map: dict[int, str] = {}
    if site_id_set:
        site_rows = (await db.execute(select(Site).where(Site.id.in_(site_id_set)))).scalars().all()
        site_name_map = {s.id: s.name for s in site_rows}

    # 下载器中的实时状态（按标题匹配）
    torrent_index = await _build_torrent_state_index(db)

    data = []
    for r in rows:
        live = torrent_index.get(_normalize_title(r.title))
        status = (live or {}).get("status") or r.status
        size = r.size if r.size else (live or {}).get("size")
        data.append({
            "id": r.id,
            "site_id": r.site_id,
            "site_name": site_name_map.get(r.site_id) if r.site_id is not None else None,
            "title": r.title,
            "torrent_url": r.torrent_url,
            "status": status,
            "size": size,
            "created_at": r.created_at,
        })
    return PageResponse(total=total, page=page, page_size=page_size, data=data)
