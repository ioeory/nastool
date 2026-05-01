"""
搜索业务链
负责调度 IndexerModule 进行多站点并发搜索，
并应用过滤规则、合并去重返回。
"""
from typing import List, Optional, Dict
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.indexer import IndexerModule
from app.schemas import TorrentItem
from app.chain.filter import FilterChain
from app.utils.media_parser import MediaParser


class SearchChain:
    """搜索业务链"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.indexer = IndexerModule(db)
        self.filter_chain = FilterChain()

    async def search(self, keyword: str, page: int = 1) -> List[TorrentItem]:
        """
        全站聚合搜索
        """
        logger.info(f"====== 开始全局聚合搜索: [{keyword}], 第 {page} 页 ======")
        
        # 1. 异步并发收集结果
        raw_items = await self.indexer.search_all_sites(keyword=keyword, page=page)
        
        if not raw_items:
            logger.info("全局搜索没有获取到任何内容")
            return []
            
        logger.info(f"爬虫共返回 {len(raw_items)} 条初步结果，正在进行去重和规整...")

        # 2. 跨站去重与聚合
        aggregated_items = self._deduplicate(raw_items)
        
        # 3. 过滤（质量控制/排除关键字）
        valid_items = await self.filter_chain.apply_rules(aggregated_items)
        
        # 4. 默认排序：做种数倒序
        valid_items.sort(key=lambda x: x.seeders, reverse=True)
        
        logger.info(f"====== 全局聚合搜索完成: [{keyword}], 有效结果 {len(valid_items)} 条 ======")
        
        return valid_items

    def _deduplicate(self, items: List[TorrentItem]) -> List[TorrentItem]:
        """
        跨站去重与聚合逻辑：
        1. 识别同站重复 (detail_url)
        2. 识别跨站同内容 (Title + Year + Res + Season/Episode)
        """
        # 第一步：同站绝对去重
        site_detail_seen = set()
        stage1_items = []
        for item in items:
            uid = f"{item.site_id}_{item.detail_url}"
            if uid not in site_detail_seen:
                site_detail_seen.add(uid)
                stage1_items.append(item)

        # 第二步：跨站特征聚合
        groups: Dict[str, List[TorrentItem]] = {}
        for item in stage1_items:
            info = MediaParser.parse(item.title)
            # 生成指纹：名称 + 年份 + 分辨率 + 季集
            # 我们对 Title 做归一化处理（转小写），增加匹配率
            fingerprint = f"{str(info['title']).lower()}|{info['year']}|{info['resolution']}|{info['season']}|{info['episode']}"
            
            if fingerprint not in groups:
                groups[fingerprint] = []
            groups[fingerprint].append(item)

        final_items = []
        for fingerprint, group in groups.items():
            # 在组内按做种人数降序排列
            group.sort(key=lambda x: x.seeders, reverse=True)
            
            # 以最热的一条作为主条目
            primary = group[0]
            
            # 将组内所有条目作为来源记录（如果来源多于 1 个）
            primary.sources = [
                {
                    "site_id": s.site_id,
                    "site_name": s.site_name,
                    "title": s.title,
                    "enclosure": s.enclosure,
                    "detail_url": s.detail_url,
                    "seeders": s.seeders,
                    "size": s.size,
                    "free": s.free
                } for s in group
            ]
            
            final_items.append(primary)

        return final_items
