"""
M-Team RSS 条目 API 补全：RSS 不含结构化优惠字段，通过 Search API 回填 free/size/seeders。

注意：M-Team API 有严格频率限制，补全策略为「少量精准查询」，避免对每条 RSS 逐 id 搜索。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from app.db.models.site import Site
from app.schemas import TorrentItem
from app.site.registry import SiteRegistry
from app.site.spiders.mteam import MTeamSpider, _extract_torrent_id_from_url

_PROMOTION_TO_API: dict[str, str] = {
    "FREE": "FREE",
    "2XFREE": "_2X_FREE",
    "50%": "PERCENT_50",
    "30%": "PERCENT_70",
}


def _discount_queries_for(promotion: Optional[str]) -> tuple[Optional[str], ...]:
    """
    按选种规则生成补全查询列表（尽量少请求，避免触发「請求過於頻繁」）。
    - 指定优惠：只查该 discount 一次
    - 未指定：只查一次无 discount 的最新列表
    """
    key = (promotion or "").strip().upper()
    preferred = _PROMOTION_TO_API.get(key)
    if preferred:
        return (preferred,)
    return (None,)


def _torrent_id_from_item(item: TorrentItem) -> Optional[str]:
    for url in (item.enclosure, item.detail_url or ""):
        tid = _extract_torrent_id_from_url(url)
        if tid:
            return tid
    return None


def _merge_api_fields(rss_item: TorrentItem, api_item: TorrentItem) -> TorrentItem:
    return rss_item.model_copy(
        update={
            "free": api_item.free or rss_item.free,
            "size": api_item.size or rss_item.size,
            "seeders": api_item.seeders or rss_item.seeders,
            "leechers": api_item.leechers or rss_item.leechers,
            "downloads": api_item.downloads or rss_item.downloads,
        }
    )


async def enrich_mteam_rss_torrent_items(
    site: Site,
    items: List[TorrentItem],
    *,
    max_pages: int = 3,
    promotion: Optional[str] = None,
) -> List[TorrentItem]:
    """
    对 M-Team RSS 解析出的 TorrentItem 调用 Search API 补全优惠与体积/做种数。
    非 mteam_api 站点或无法提取 id 的条目原样返回。
    """
    if not items:
        return items

    registry = SiteRegistry()
    meta = registry.get_indexer(site.domain)
    if not meta or meta.get("parser") != "mteam_api":
        return items

    id_to_indices: Dict[str, List[int]] = {}
    for idx, item in enumerate(items):
        tid = _torrent_id_from_item(item)
        if tid:
            id_to_indices.setdefault(tid, []).append(idx)

    if not id_to_indices:
        logger.warning(f"[Brush][M-Team enrich] {site.name}: RSS 条目均无法解析 torrent id，跳过补全")
        return items

    ids_needed = set(id_to_indices.keys())
    spider = MTeamSpider(site, meta)
    api_by_id: Dict[str, TorrentItem] = {}

    try:
        pages = max(1, min(int(max_pages or 3), 5))
        queries = _discount_queries_for(promotion)
        preferred = _PROMOTION_TO_API.get((promotion or "").strip().upper())

        for discount in queries:
            if spider._last_rate_limited:
                logger.warning(
                    f"[Brush][M-Team enrich] {site.name}: 已触发 API 频率限制，跳过后续补全查询"
                )
                break

            query_pages = min(pages + 2, 5) if discount == preferred else pages
            logger.info(
                f"[Brush][M-Team enrich] {site.name}: 查询 discount={discount!r} "
                f"max_pages={query_pages} (待匹配 id 数 {len(ids_needed)})"
            )
            batch = await spider.search(
                keyword="",
                page=1,
                discount=discount,
                max_pages=query_pages,
            )
            for t in batch:
                tid = _torrent_id_from_item(t)
                if tid and tid in ids_needed and tid not in api_by_id:
                    api_by_id[tid] = t

            if spider._last_rate_limited:
                break

            if len(api_by_id) >= len(ids_needed):
                break

    except Exception as e:
        logger.error(f"[Brush][M-Team enrich] {site.name} API 查询失败: {e}")
        return items

    out = list(items)
    enriched = 0
    missing = ids_needed - set(api_by_id.keys())
    for tid, indices in id_to_indices.items():
        api_item = api_by_id.get(tid)
        if not api_item:
            continue
        for idx in indices:
            out[idx] = _merge_api_fields(out[idx], api_item)
            enriched += 1

    if missing:
        sample = sorted(missing)[:5]
        if len(missing) > 5:
            logger.warning(
                f"[Brush][M-Team enrich] {site.name}: {len(missing)} 个 id 未在最近 API 结果中命中 "
                f"(示例: {sample} ...)"
            )
        else:
            logger.warning(
                f"[Brush][M-Team enrich] {site.name}: 未命中 id: {sorted(missing)}"
            )

    logger.info(
        f"[Brush][M-Team enrich] {site.name}: 补全 {enriched}/{len(items)} 条 "
        f"(需补全 id 数 {len(ids_needed)}, API 命中 {len(api_by_id)})"
    )
    return out
