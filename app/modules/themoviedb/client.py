import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from app.core.config import settings

class TMDBClient:
    """TMDB API 封装"""
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self):
        self.language = "zh-CN"

    async def _request(self, endpoint: str, params: dict = None) -> Optional[Dict[str, Any]]:
        api_key = settings.TMDB_API_KEY
        if not api_key:
            logger.warning("未配置 TMDB API_KEY！")
            return None
            
        url = f"{self.BASE_URL}{endpoint}"
        p = {
            "api_key": api_key,
            "language": self.language,
        }
        if params:
            p.update(params)
            
        # 动态组装代理
        proxy = settings.PROXY_HOST if settings.USE_PROXY and settings.PROXY_HOST else None
            
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=15) as client:
                res = await client.get(url, params=p)
                if res.status_code == 200:
                    return res.json()
                else:
                    logger.error(f"TMDB 请求失败 [{res.status_code}]: {res.text}")
        except Exception as e:
            logger.error(f"TMDB 请求发生异常: {e}")
            
        return None

    async def search_multi(self, query: str, year: str = None) -> Optional[Dict[str, Any]]:
        """基于关键词和年份搜索（混合电影和剧集搜）"""
        params = {"query": query}
        if year:
            params["year"] = year
        data = await self._request("/search/multi", params=params)
        if data and data.get("results"):
            # 返回最匹配的第一个
            return data["results"][0]
        return None

    async def get_details(self, tmdb_id: int, media_type: str) -> Optional[Dict[str, Any]]:
        """获取具体的电影/剧集详情页（含类别、季集信息）"""
        if media_type not in ["movie", "tv"]:
            return None
            
        return await self._request(f"/{media_type}/{tmdb_id}")

    async def get_full_details(self, tmdb_id: int, media_type: str) -> Optional[Dict[str, Any]]:
        """提取带演职员表和推荐影视的完整信息"""
        if media_type not in ["movie", "tv"]:
            return None
        return await self._request(f"/{media_type}/{tmdb_id}", params={"append_to_response": "credits,recommendations,similar"})

    async def get_genres(self, media_type: str) -> Optional[Dict[str, Any]]:
        """获取全站分类列表"""
        if media_type not in ["movie", "tv"]:
            return None
        return await self._request(f"/genre/{media_type}/list")
        
    async def discover(self, media_type: str, query_params: dict) -> Optional[Dict[str, Any]]:
        """通过灵活的筛选参数（年代、分类、评级、排序规则）拉取影视卡片流"""
        if media_type not in ["movie", "tv"]:
            return None
        return await self._request(f"/discover/{media_type}", params=query_params)
