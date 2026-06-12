"""RSS 优惠推断单测"""
from app.modules.brush.rss_feed import _infer_promotion


def test_infer_free_from_html_description():
    desc = '<span class="tag">Free</span> 2d 11h remaining'
    assert _infer_promotion("Some Release", desc) == "FREE"


def test_infer_free_chinese():
    assert _infer_promotion("某资源", "限时免费 3天") == "FREE"


def test_infer_no_false_positive_from_title():
    assert _infer_promotion("120%リアルガチ", "") == ""
