"""BrushManager 选种过滤单测"""
from app.modules.brush.manager import BrushManager
from app.schemas import TorrentItem


def _item(free: str = "", seeders: int = 0, size: int = 0, pubdate: str | None = None) -> TorrentItem:
    return TorrentItem(
        site_id=1,
        site_name="M-Team",
        title="Test",
        enclosure="mteam_dl://123",
        free=free or None,
        seeders=seeders,
        size=size,
        pubdate=pubdate,
    )


def test_filter_promotion_50_percent_rejects_empty_free():
    mgr = BrushManager()
    config = {"selection_rules": {"promotion": "50%", "exclude_hr": False}}
    out = mgr._filter_torrents([_item(free="")], config)
    assert out == []


def test_filter_promotion_50_percent_accepts_match():
    mgr = BrushManager()
    config = {"selection_rules": {"promotion": "50%", "exclude_hr": False}}
    t = _item(free="50%", seeders=200, size=2 * 1024**3)
    out = mgr._filter_torrents([t], config)
    assert len(out) == 1
    assert out[0].free == "50%"


def test_filter_max_seeders_blocks_hot_torrents():
    mgr = BrushManager()
    config = {
        "selection_rules": {
            "promotion": "50%",
            "exclude_hr": False,
            "max_seeders": 100,
        }
    }
    out = mgr._filter_torrents([_item(free="50%", seeders=150)], config)
    assert out == []


def test_filter_max_seeders_zero_allows_any():
    mgr = BrushManager()
    config = {
        "selection_rules": {
            "promotion": "50%",
            "exclude_hr": False,
            "max_seeders": 0,
        }
    }
    out = mgr._filter_torrents([_item(free="50%", seeders=9999)], config)
    assert len(out) == 1
