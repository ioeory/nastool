"""
搜索与下载 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.security import get_current_user
from app.db import get_db
from app.db.models.user import User
from app.schemas import Response, TorrentItem
from app.chain.search import SearchChain
from app.chain.download import DownloadChain

router = APIRouter(prefix="/search", tags=["搜索与下载"])

class SearchRequest(BaseModel):
    keyword: str
    page: int = 1

class DownloadRequest(BaseModel):
    item: TorrentItem
    save_path: Optional[str] = None
    category: Optional[str] = None

@router.post("/", response_model=Response, summary="全站聚合聚合搜索")
async def perform_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """根据关键词在所有启用的站点进行并发搜索"""
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
        
    chain = SearchChain(db)
    items = await chain.search(req.keyword, req.page)
    
    return Response(data=[item.model_dump() for item in items], message=f"搜索到 {len(items)} 条结果")


@router.post("/download", response_model=Response, summary="触发下载")
async def trigger_download(
    req: DownloadRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    接收前端选定的搜索条目，触发推送到下载器（qBittorrent）
    """
    chain = DownloadChain(db)
    success = await chain.download(req.item, save_path=req.save_path, category=req.category)
    
    if success:
        return Response(message="推送下载成功")
    else:
        raise HTTPException(status_code=500, detail="推送下载失败，请检查配置或原站授权状态")
