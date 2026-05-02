"""
基础站点爬虫接口
"""
from typing import List, Optional
from abc import ABC, abstractmethod

from app.schemas import TorrentItem
from app.db.models.site import Site
from app.utils.cookie import parse_cookie_string


class BaseSpider(ABC):
    """站点爬虫基类"""

    def __init__(self, site: Site, meta: dict):
        self.site = site
        self.meta = meta
        self.timeout = site.timeout or 30
        
        # 提取经常使用的信息
        self.url = self.site.url.rstrip('/')
        self.cookie = parse_cookie_string(self.site.cookie or "")
        self.ua = self.site.ua or "Mozilla/5.0"
        self.apikey = self.site.apikey or ""

    @abstractmethod
    async def search(self, keyword: str = "", page: int = 0) -> List[TorrentItem]:
        """
        搜索种子
        :param keyword: 搜索关键词
        :param page: 页码
        :return: 种子列表
        """
        pass

    @abstractmethod
    async def download_torrent(self, url: str) -> Optional[bytes]:
        """
        下载种子文件内容
        :param url: 种子文件下载链接
        :return: bytes 内容或 None
        """
        pass
        
    @abstractmethod
    async def get_user_info(self) -> dict:
        """
        获取用户数据（上传/下载量/魔力值等）
        """
        pass
