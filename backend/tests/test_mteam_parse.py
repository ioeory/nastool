"""
M-Team Search API 条目解析单测（结构参考 github.com/sagan/ptool site/mtorrent/types.go）
"""
from unittest.mock import MagicMock

import pytest

from app.site.spiders.mteam import MTeamSpider

# 脱敏示例：与公开 ptool Torrent JSON 字段一致
SAMPLE_API_ITEM_FREE = {
    "id": "12345",
    "name": "Example.Release.2024",
    "smallDescr": "demo",
    "createdDate": "2024-01-15T12:00:00.000Z",
    "size": 1073741824,
    "status": {
        "discount": "FREE",
        "seeders": 120,
        "leechers": 5,
        "times": 99,
    },
}

SAMPLE_API_ITEM_50 = {
    "id": "22345",
    "name": "Another.Release",
    "smallDescr": "",
    "createdDate": "2024-01-16T08:00:00.000Z",
    "size": "2147483648",
    "status": {
        "discount": "PERCENT_50",
        "seeders": 10,
        "leechers": 2,
    },
}

SAMPLE_API_ITEM_LABELS_2X = {
    "id": "32345",
    "name": "Labeled.2x",
    "smallDescr": "",
    "size": 1000,
    "status": {"discount": "NORMAL", "seeders": 1, "leechers": 0},
    "labels": [{"name": "2XFREE"}, {"id": 1, "title": "other"}],
}


def _make_spider():
    site = MagicMock()
    site.id = 1
    site.name = "M-Team"
    site.url = "https://kp.m-team.cc"
    site.cookie = ""
    site.ua = ""
    site.apikey = ""
    site.timeout = 30
    return MTeamSpider(site, {})


@pytest.fixture
def spider():
    return _make_spider()


def test_parse_status_discount_free(spider):
    out = spider._parse_torrents([SAMPLE_API_ITEM_FREE])
    assert len(out) == 1
    assert out[0].free == "FREE"
    assert out[0].seeders == 120
    assert out[0].size == 1073741824


def test_parse_percent_50(spider):
    out = spider._parse_torrents([SAMPLE_API_ITEM_50])
    assert out[0].free == "50%"
    assert out[0].size == 2147483648


def test_parse_labels_2xfree(spider):
    out = spider._parse_torrents([SAMPLE_API_ITEM_LABELS_2X])
    assert out[0].free == "2XFREE"


def test_parse_percent_70():
    sp = _make_spider()
    item = {
        "id": "1",
        "name": "x",
        "size": 1,
        "status": {"discount": "PERCENT_70", "seeders": 0, "leechers": 0},
    }
    assert sp._parse_torrents([item])[0].free == "30%"


def test_parse_discount_bool_true():
    sp = _make_spider()
    item = {
        "id": "1",
        "name": "x",
        "size": 100,
        "status": {"discount": True, "seeders": 3, "leechers": 0},
    }
    assert sp._parse_torrents([item])[0].free == "FREE"


def test_top_level_seeders_when_status_missing():
    sp = _make_spider()
    item = {
        "id": "1",
        "name": "x",
        "size": 100,
        "seeders": 42,
        "leechers": 1,
        "discount": "FREE",
    }
    assert sp._parse_torrents([item])[0].seeders == 42
    assert sp._parse_torrents([item])[0].free == "FREE"


def test_parse_api_discount_2x_free_underscore():
    """ptool 使用 _2X_FREE 字串，与 2XFREE 不同。"""
    sp = _make_spider()
    item = {
        "id": "618195",
        "name": "x",
        "size": 1000,
        "status": {"discount": "_2X_FREE", "seeders": 1, "leechers": 0},
    }
    assert sp._parse_torrents([item])[0].free == "2XFREE"


def test_parse_api_discount_2x_percent_50():
    sp = _make_spider()
    item = {
        "id": "1",
        "name": "x",
        "size": 1000,
        "status": {"discount": "_2X_PERCENT_50", "seeders": 1, "leechers": 0},
    }
    assert sp._parse_torrents([item])[0].free == "50%"


def test_parse_discount_numeric_50():
    sp = _make_spider()
    item = {
        "id": "1",
        "name": "x",
        "size": 1000,
        "status": {"discount": 50, "seeders": 1, "leechers": 0},
    }
    assert sp._parse_torrents([item])[0].free == "50%"


def test_parse_topping_free_when_discount_normal():
    """置顶免费：discount=NORMAL 但 topping 进行中。"""
    sp = _make_spider()
    item = {
        "id": "789199",
        "name": "topped release",
        "size": 1000,
        "status": {"discount": "NORMAL", "seeders": 5, "leechers": 1},
        "toppingLevel": 1,
        "topping": {"status": "ONGOING", "freeDay": "3"},
    }
    assert sp._parse_torrents([item])[0].free == "FREE"
