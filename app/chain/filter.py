"""
搜索结果过滤规则层
利用用户配置的正则表达式、文件大小阈值和站内关键字体系，对聚合所得的搜索结果进行二次清洗。
"""

import re
from typing import List
from loguru import logger

from app.schemas import TorrentItem

class FilterChain:
    """过滤业务链"""
    
    def __init__(self, include_kw: str = "", exclude_kw: str = "", min_mb: int = 0, max_mb: int = 0):
        self.include_kw = include_kw.strip()
        self.exclude_kw = exclude_kw.strip()
        self.min_bytes = int(min_mb) * 1024 * 1024
        self.max_bytes = int(max_mb) * 1024 * 1024

    async def apply_rules(self, items: List[TorrentItem]) -> List[TorrentItem]:
        """对结果列表应用过滤规则"""
        if not items:
            return []

        filtered = []
        for item in items:
            if not self._check_size(item):
                continue
            if not self._check_include(item):
                continue
            if not self._check_exclude(item):
                continue
                
            filtered.append(item)
            
        logger.debug(f"规则过滤完成: 过滤前 {len(items)} -> 过滤后 {len(filtered)}")
        return filtered

    def _check_size(self, item: TorrentItem) -> bool:
        if self.min_bytes > 0 and item.size < self.min_bytes:
            return False
        if self.max_bytes > 0 and item.size > self.max_bytes:
            return False
        return True

    def _check_include(self, item: TorrentItem) -> bool:
        if not self.include_kw:
            return True
        try:
            # 在标题或描述中找
            target = f"{item.title} {item.description}"
            if re.search(self.include_kw, target, re.IGNORECASE):
                return True
        except Exception as e:
            logger.warning(f"包含正则校验异常: {e}")
            return True
        return False

    def _check_exclude(self, item: TorrentItem) -> bool:
        if not self.exclude_kw:
            return True
        try:
            target = f"{item.title} {item.description}"
            if re.search(self.exclude_kw, target, re.IGNORECASE):
                return False
        except Exception as e:
            logger.warning(f"排除正则校验异常: {e}")
            return True
        return True
