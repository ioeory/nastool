"""
索引器模块 — 融合 SiteRegistry 和 Spiders，提供统一的搜索接口
"""
import asyncio
from typing import List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.site import Site
from app.site.registry import SiteRegistry
from app.site.spiders.base import BaseSpider
from app.site.spiders.nexusphp import NexusPHPSpider
from app.site.spiders.mteam import MTeamSpider
from app.schemas import TorrentItem

class IndexerModule:
    """提供统一接口加载特定站点的解析器/爬虫，执行搜索或数据获取"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = SiteRegistry()

    def _get_spider(self, site: Site, meta: dict) -> Optional[BaseSpider]:
        """根据站点注册表里的 parser 信息，实例化对应的爬虫类"""
        parser_type = meta.get("parser", "nexusphp")
        
        try:
            if parser_type == "nexusphp":
                return NexusPHPSpider(site, meta)
            elif parser_type == "mteam_api":
                return MTeamSpider(site, meta)
            else:
                # 可以继续扩展 gazelle 等
                logger.warning(f"/{site.name}/ 暂不支持的 parser_type [{parser_type}]，回退到 nexusphp")
                return NexusPHPSpider(site, meta)
        except Exception as e:
            logger.error(f"初始化爬虫失败: {site.name} -> {e}")
            return None

    async def search_site(self, site: Site, keyword: str, page: int = 0) -> List[TorrentItem]:
        """在一个特定站点执行搜索"""
        if not site.is_active:
            logger.debug(f"/{site.name}/ 站点未启用，跳过搜索")
            return []

        meta = self.registry.get_indexer(site.domain)
        if not meta:
            logger.warning(f"/{site.name}/ 在注册表中未找到配置信息，跳过搜索")
            return []

        spider = self._get_spider(site, meta)
        if not spider:
            return []

        try:
            logger.info(f"==> 开始在 / {site.name} / 搜索关键字: {keyword} (页码:{page})")
            results = await spider.search(keyword, page)
            logger.info(f"<== / {site.name} / 返回了 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"/{site.name}/ 搜索时出现异常: {e}")
            return []
            
    async def search_all_sites(self, keyword: str, page: int = 0) -> List[TorrentItem]:
        """在所有已启用的站点并发执行搜索（由 SearchChain 进一步包装，这里提供底层并发实现）"""
        # 获取所有启用的站点
        result = await self.db.execute(select(Site).where(Site.is_active == True))
        active_sites = result.scalars().all()
        
        if not active_sites:
            logger.warning("未配置或启用任何站点，停止搜索。")
            return []

        # 并发执行
        tasks = [self.search_site(site, keyword, page) for site in active_sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items: List[TorrentItem] = []
        for res in results:
            if isinstance(res, list):
                all_items.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"并发搜索异常: {res}")
                
        # 排序：可以按种子数、做种数等排序
        all_items.sort(key=lambda x: x.seeders, reverse=True)
        return all_items

    async def download_torrent(self, site: Site, url: str) -> Optional[bytes]:
        """利用对应站点的爬虫下种子（处理Mteam等的特殊逻辑）"""
        meta = self.registry.get_indexer(site.domain)
        if not meta:
            return None
            
        spider = self._get_spider(site, meta)
        if not spider:
            return None
            
        return await spider.download_torrent(url)
