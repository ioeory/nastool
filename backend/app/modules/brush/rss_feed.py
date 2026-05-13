"""
刷流：从 RSS/Atom 订阅拉取种子条目并转为 TorrentItem。
促销等结构化字段通常不在 RSS 中，free 等留空；选种规则若要求「仅 FREE」可能全部不匹配。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.db.models.site import Site
from app.schemas import TorrentItem
from app.utils.cookie import parse_cookie_string


def _local_tag(tag: str) -> str:
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[-1]
    return tag.split(":")[-1]


def _redact_feed_url(url: str) -> str:
    try:
        u = re.sub(r"(?i)(passkey|pass|token|apikey|key)=([^&]+)", r"\1=***", url)
        return u
    except Exception:
        return url


def _find_download_url(item_el: ET.Element) -> tuple[str, Optional[str]]:
    """返回 (下载链接, 详情页链接可选)。兼容 RSS2 enclosure 与 Atom link[@href]。"""
    enclosure_url: Optional[str] = None
    magnet_or_torrent: Optional[str] = None
    first_link: Optional[str] = None
    detail: Optional[str] = None

    for child in item_el:
        t = _local_tag(child.tag).lower()
        if t == "enclosure" and child.get("url"):
            enclosure_url = (child.get("url") or "").strip()
            continue
        if t == "link":
            href = (child.get("href") or "").strip()
            typ = (child.get("type") or "").lower()
            if href:
                if not first_link:
                    first_link = href
                if href.startswith("magnet:") or "torrent" in typ or href.endswith(".torrent"):
                    magnet_or_torrent = href
                elif "/download" in href.lower() or "passkey=" in href.lower():
                    magnet_or_torrent = magnet_or_torrent or href
            txt = (child.text or "").strip()
            if txt.startswith("http") or txt.startswith("magnet:"):
                first_link = first_link or txt
                if txt.startswith("magnet:"):
                    magnet_or_torrent = txt
        if t == "guid" and (child.text or "").strip() and not detail:
            detail = child.text.strip()

    dl = enclosure_url or magnet_or_torrent or first_link
    if not detail:
        detail = first_link if first_link and first_link.startswith("http") else None
    if not dl and detail:
        dl = detail
    return (dl or "", detail)


def _item_pubdate(item_el: ET.Element) -> Optional[str]:
    for tag_name in ("pubDate", "pubdate", "updated", "published", "date"):
        for child in item_el:
            if _local_tag(child.tag).lower() == tag_name and (child.text or "").strip():
                return child.text.strip()
    return None


def _item_title(item_el: ET.Element) -> str:
    for child in item_el:
        if _local_tag(child.tag).lower() == "title":
            return (child.text or "").strip() or "Unknown"
    return "Unknown"


def _item_description(item_el: ET.Element) -> str:
    for child in item_el:
        tag = _local_tag(child.tag).lower()
        if tag in ("description", "summary", "content", "encoded", "content:encoded"):
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def _infer_promotion(*parts: str) -> str:
    text = " ".join(p for p in parts if p).lower()
    if not text:
        return ""

    # 优先识别更具体的优惠类型，再回退到 FREE。
    if any(token in text for token in ("2xfree", "2x free", "free2up", "twoupfree", "freeleech")):
        return "2XFREE"
    if "50%" in text or "half" in text:
        return "50%"
    if "30%" in text:
        return "30%"
    if any(token in text for token in ("free", "freeleech")):
        return "FREE"
    return ""


def _parse_rss_channel(root: ET.Element) -> List[ET.Element]:
    items: List[ET.Element] = []
    for el in root.iter():
        if _local_tag(el.tag).lower() == "item":
            items.append(el)
    return items


def _parse_atom_feed(root: ET.Element) -> List[ET.Element]:
    entries: List[ET.Element] = []
    for el in root.iter():
        if _local_tag(el.tag).lower() == "entry":
            entries.append(el)
    return entries


async def fetch_rss_torrent_items_for_brush(site: Site, rss_url: str) -> List[TorrentItem]:
    """
    拉取 RSS/Atom，解析为 TorrentItem。site 用于 UA/Cookie 与 site_id。
    """
    if not rss_url or not str(rss_url).strip():
        return []

    headers = {
        "User-Agent": site.ua or "Mozilla/5.0 (compatible; NASTool/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    ck = parse_cookie_string(site.cookie or "")
    if ck:
        headers["Cookie"] = ck
    if site.apikey and str(site.apikey).strip():
        headers["x-api-key"] = str(site.apikey).strip()

    timeout = float(site.timeout or 30)
    safe_log = _redact_feed_url(rss_url.strip())

    try:
        async with httpx.AsyncClient(
            timeout=timeout, verify=False, follow_redirects=True, headers=headers
        ) as client:
            resp = await client.get(rss_url.strip())
            if resp.status_code != 200:
                logger.warning(f"[Brush][RSS] HTTP {resp.status_code} {_redact_feed_url(rss_url)}")
                return []
            body = resp.content
    except httpx.RequestError as e:
        logger.error(f"[Brush][RSS] 请求失败 {safe_log}: {e}")
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        logger.error(f"[Brush][RSS] XML 解析失败 {safe_log}: {e}")
        return []

    tag_root = _local_tag(root.tag).lower()
    raw_items: List[ET.Element] = []
    if tag_root == "rss":
        raw_items = _parse_rss_channel(root)
    elif tag_root == "feed":
        raw_items = _parse_atom_feed(root)
    else:
        raw_items = _parse_rss_channel(root) or _parse_atom_feed(root)

    out: List[TorrentItem] = []
    for item_el in raw_items:
        title = _item_title(item_el)
        desc = _item_description(item_el)
        dl, detail = _find_download_url(item_el)
        if not dl:
            continue
        pub = _item_pubdate(item_el)

        detail_page = detail
        if detail_page and not detail_page.startswith("http"):
            detail_page = None
        if dl.startswith("http"):
            try:
                p = urlparse(dl)
                if p.path.endswith(".torrent") or "download" in p.path.lower():
                    pass
                elif not detail_page:
                    detail_page = dl
            except Exception:
                pass

        out.append(
            TorrentItem(
                site_id=site.id,
                site_name=site.name,
                title=title,
                description=desc or None,
                enclosure=dl,
                detail_url=detail_page,
                pubdate=pub,
                size=0,
                seeders=0,
                leechers=0,
                downloads=0,
                free=_infer_promotion(title, desc),
            )
        )

    logger.info(f"[Brush][RSS] {_redact_feed_url(rss_url)} → {len(out)} 条 ({site.name})")
    return out
