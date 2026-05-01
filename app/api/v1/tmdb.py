from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import StreamingResponse
import httpx
from app.modules.themoviedb.client import TMDBClient
from app.core.security import get_current_user
from app.schemas import Response
from app.core.config import settings

router = APIRouter(prefix="/tmdb", tags=["TMDB 接口"])


@router.get("/discover", response_model=Response, summary="发现媒体流")
async def discover(request: Request, _=Depends(get_current_user)):
    """返回 TMDB discover 代理，带上分页和过滤参数"""
    q_params = dict(request.query_params)
    media_type = q_params.pop("media_type", "movie")
    
    tmdb = TMDBClient()
    res = await tmdb.discover(media_type, q_params)
    if res:
        return Response(data=res)
    return Response(code=1, message="获取 TMDB 发现数据失败")


@router.get("/genres/{media_type}", response_model=Response, summary="获取全站分类列表")
async def get_genres(media_type: str, _=Depends(get_current_user)):
    tmdb = TMDBClient()
    res = await tmdb.get_genres(media_type)
    if res and res.get("genres"):
        return Response(data=res["genres"])
    return Response(code=1, message="获取分类失败")


@router.get("/detail/{media_type}/{tmdb_id}", response_model=Response, summary="获取详情巨幅数据")
async def get_full_details(media_type: str, tmdb_id: int, _=Depends(get_current_user)):
    tmdb = TMDBClient()
    res = await tmdb.get_full_details(tmdb_id, media_type)
    if res:
        return Response(data=res)
    return Response(code=1, message="获取详情失败")


@router.get("/image", summary="TMDB 图片代理")
async def get_image(
    path: str = Query(..., description="图片路径，如 /pxZ9...jpg"),
    size: str = Query("w500", description="图片尺寸，如 original, w500, w185")
):
    """代理获取 TMDB 图片，解决墙内显示问题"""
    target_url = f"https://image.tmdb.org/t/p/{size}{path}"
    
    # 模拟浏览器 User-Agent，防止被 TMDB 拒绝
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 动态组装代理
    proxy = settings.PROXY_HOST if settings.USE_PROXY and settings.PROXY_HOST else None

    async def stream_image():
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=15) as client:
                async with client.stream("GET", target_url, headers=headers) as response:
                    # 如果上游返回非 200，停止流式传输
                    if response.status_code != 200:
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            # 记录错误但不崩溃，返回空流会导致前端显示破损图标
            print(f"Error proxying TMDB image: {e}")
            return

    return StreamingResponse(
        stream_image(), 
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=86400"} # 缓存 1 天
    )
