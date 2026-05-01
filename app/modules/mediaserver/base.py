import httpx
from loguru import logger
from app.core.config import settings

class EmbyClient:
    """Emby 媒体服务器 API 联动"""
    
    def __init__(self):
        self.host = settings.EMBY_HOST
        self.api_key = settings.EMBY_API_KEY

    async def refresh_library(self):
        """触发全库扫描（最简单通用）"""
        if not self.host or not self.api_key:
            return
            
        url = f"{self.host}/Library/Refresh?api_key={self.api_key}"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                res = await client.post(url)
                if res.status_code < 300:
                    logger.info("Emby 库刷新请求已发送成功")
                else:
                    logger.warning(f"Emby 刷新请求返回异常: {res.status_code}")
            except Exception as e:
                logger.error(f"Emby 刷新异常: {e}")

class JellyfinClient:
    """Jellyfin 媒体服务器 API 联动 (与 Emby 接口基本一致)"""
    
    def __init__(self):
        self.host = settings.JELLYFIN_HOST
        self.api_key = settings.JELLYFIN_API_KEY

    async def refresh_library(self):
        if not self.host or not self.api_key:
            return
            
        # 认证头方式 (Jellyfin 有时需要自定义头部)
        url = f"{self.host}/Library/Refresh"
        headers = {
            "X-Emby-Token": self.api_key,
            "Authorization": f'MediaBrowser Token="{self.api_key}"'
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                res = await client.post(url, headers=headers)
                if res.status_code < 300:
                    logger.info("Jellyfin 库刷新请求已发送成功")
                else:
                    logger.warning(f"Jellyfin 刷新请求返回异常: {res.status_code}")
            except Exception as e:
                logger.error(f"Jellyfin 刷新异常: {e}")
