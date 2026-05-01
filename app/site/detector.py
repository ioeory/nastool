"""
站点框架自动探测器
通过分析站点 HTML 特征自动识别框架类型（NexusPHP / Gazelle / Unit3d 等）
"""
import re
from typing import Tuple

import httpx
from loguru import logger


# 各框架的 HTML 指纹（关键词 or 正则）
_FINGERPRINTS = {
    "nexusphp": [
        r'nexusphp',
        r'NexusPHP',
        r'class="torrents"',
        r'/userdetails\.php',
        r'torrents\.php\?',
        r'Powered by NexusPHP',
    ],
    "gazelle": [
        r'gazelle',
        r'\.gazellecd\.',
        r'searchstr=',
        r'class="torrent_table"',
        r'Orpheus',
    ],
    "unit3d": [
        r'UNIT3D',
        r'unit3d',
        r'/torrents\?name=',
        r'class="movie-card"',
    ],
    "mteam_api": [
        r'm-team\.io',
        r'm-team\.cc',
        r'api\.m-team',
    ],
}


class SiteDetector:
    """
    自动探测站点框架类型
    
    返回值约定（与 sites.json 的 parser 字段一致）：
    - "nexusphp"   → 通用 NexusPHP 框架（覆盖绝大多数中文PT）
    - "gazelle"    → Gazelle 框架
    - "unit3d"     → UNIT3D 框架
    - "mteam_api"  → M-Team REST API
    - "unknown"    → 无法识别（用通用爬虫尝试）
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def detect(self, url: str, cookie: str = None, ua: str = None) -> Tuple[str, str]:
        """
        访问站点首页，根据 HTML 内容识别框架类型

        :param url: 站点首页 URL
        :param cookie: 可选 Cookie
        :param ua: 可选 User-Agent
        :return: (框架类型, 额外消息)
        """
        headers = {}
        if ua:
            headers["User-Agent"] = ua
        if cookie:
            headers["Cookie"] = cookie

        html = ""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPStatusError as e:
            logger.warning(f"SiteDetector: HTTP {e.response.status_code} — {url}")
            return "unknown", f"HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"SiteDetector: 无法访问 {url} — {e}")
            return "unknown", str(e)

        return self._analyze(url, html)

    def _analyze(self, url: str, html: str) -> Tuple[str, str]:
        """分析 HTML 内容，返回框架类型"""
        # M-Team 特殊判断（通过 URL 域名即可识别）
        if "m-team.io" in url or "m-team.cc" in url:
            return "mteam_api", "M-Team REST API"

        for framework, patterns in _FINGERPRINTS.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    logger.info(f"SiteDetector: {url} → {framework}（匹配: {pattern}）")
                    return framework, f"识别为 {framework}"

        # 默认尝试 NexusPHP（最常见）
        if self._is_likely_nexus(html):
            return "nexusphp", "疑似 NexusPHP（默认回退）"

        return "unknown", "无法识别框架类型，将使用通用爬虫"

    @staticmethod
    def _is_likely_nexus(html: str) -> bool:
        """宽松判断是否可能是 NexusPHP"""
        indicators = [
            "torrents.php",
            "details.php",
            "userdetails.php",
            "seeding",
            "leeching",
            "passkey",
        ]
        count = sum(1 for kw in indicators if kw in html.lower())
        return count >= 3
