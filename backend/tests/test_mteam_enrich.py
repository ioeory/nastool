"""M-Team RSS 条目 API 补全单测"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.brush.mteam_enrich import (
    _discount_queries_for,
    enrich_mteam_rss_torrent_items,
)
from app.schemas import TorrentItem
from app.site.spiders.mteam import _is_rate_limit_message


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


def test_discount_queries_single_when_promotion_set():
    assert _discount_queries_for("FREE") == ("FREE",)
    assert _discount_queries_for("50%") == ("PERCENT_50",)
    assert _discount_queries_for("") == (None,)
    assert _discount_queries_for(None) == (None,)


def test_is_rate_limit_message():
    assert _is_rate_limit_message("請求過於頻繁")
    assert not _is_rate_limit_message("ok")


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
            spider._last_rate_limited = False
            spider.search = AsyncMock(return_value=[_api_item("999", free="FREE")])

            out = await enrich_mteam_rss_torrent_items(
                site, rss, max_pages=1, promotion="FREE"
            )

    assert len(out) == 1
    assert out[0].free == "FREE"
    spider.search.assert_called_once()
    call_kw = spider.search.call_args.kwargs
    assert call_kw.get("discount") == "FREE"


@pytest.mark.asyncio
async def test_enrich_stops_after_rate_limit():
    site = MagicMock()
    site.domain = "m-team.io"
    site.name = "M-Team"
    rss = [_rss_item("999")]

    with patch("app.modules.brush.mteam_enrich.SiteRegistry") as reg_cls:
        reg_cls.return_value.get_indexer.return_value = {"parser": "mteam_api"}
        with patch("app.modules.brush.mteam_enrich.MTeamSpider") as spider_cls:
            spider = spider_cls.return_value
            spider._last_rate_limited = True
            spider.search = AsyncMock(return_value=[])

            out = await enrich_mteam_rss_torrent_items(site, rss, promotion="FREE")

    spider.search.assert_not_called()
    assert out[0].free is None


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
