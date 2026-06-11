"""M-Team RSS 条目 API 补全单测"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.brush.mteam_enrich import enrich_mteam_rss_torrent_items
from app.schemas import TorrentItem


def _rss_item(tid: str = "999") -> TorrentItem:
    return TorrentItem(
        site_id=1,
        site_name="M-Team",
        title="No discount in title",
        enclosure=f"mteam_dl://{tid}",
        detail_url=f"https://kp.m-team.cc/detail/{tid}",
        free=None,
        size=0,
        seeders=0,
    )


def _api_item(tid: str, free: str = "50%") -> TorrentItem:
    return TorrentItem(
        site_id=1,
        site_name="M-Team",
        title="API",
        enclosure=f"mteam_dl://{tid}",
        free=free,
        size=1073741824,
        seeders=42,
    )


@pytest.mark.asyncio
async def test_enrich_mteam_fills_free_from_api():
    site = MagicMock()
    site.domain = "m-team.io"
    site.name = "M-Team"

    meta = {"parser": "mteam_api"}
    rss = [_rss_item("999")]

    with patch("app.modules.brush.mteam_enrich.SiteRegistry") as reg_cls:
        reg_cls.return_value.get_indexer.return_value = meta
        with patch("app.modules.brush.mteam_enrich.MTeamSpider") as spider_cls:
            spider = spider_cls.return_value
            spider.search = AsyncMock(return_value=[_api_item("999")])

            out = await enrich_mteam_rss_torrent_items(site, rss, max_pages=1)

    assert len(out) == 1
    assert out[0].free == "50%"
    assert out[0].size == 1073741824
    assert out[0].seeders == 42


@pytest.mark.asyncio
async def test_enrich_skips_non_mteam_parser():
    site = MagicMock()
    site.domain = "example.com"
    rss = [_rss_item()]

    with patch("app.modules.brush.mteam_enrich.SiteRegistry") as reg_cls:
        reg_cls.return_value.get_indexer.return_value = {"parser": "nexusphp"}
        out = await enrich_mteam_rss_torrent_items(site, rss)

    assert out[0].free is None
    assert out[0].size == 0
