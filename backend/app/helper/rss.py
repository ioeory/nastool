"""
RSS 解析与获取辅助类
基于用户登录态自动从相关页面获取 RSS/Passkey 链接。
"""
import re
from loguru import logger
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote


class RSSHelper:
    @staticmethod
    async def auto_fetch_rss_link(url: str, cookie: str, ua: str, framework: str) -> str:
        """
        基于框架类型自动从网站上抓取 RSS 链接。
        返回RSS的完整链接或者空字符串。
        """
        if framework == "nexusphp":
            return await RSSHelper._fetch_nexusphp_rss(url, cookie, ua)
        elif framework == "mteam_api":
            # API站不走RSS，或者是特殊接口，通常不自动填。
            return ""
        return ""

    @staticmethod
    async def _fetch_nexusphp_rss(url: str, cookie: str, ua: str) -> str:
        headers = {"User-Agent": ua, "Cookie": cookie}
        try:
            async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True, headers=headers) as client:
                # 一般在控制面板页面(usercp.php)或者详情页能找到 passkey
                # 最简单的方法是去下载页 /details.php 这里很多会显示RSS链接。
                # 另一个路径是去首页或者 index.php 右方可能有 RSS 图标
                
                resp = await client.get(urljoin(url, "/index.php"))
                if resp.status_code == 200:
                    # 匹配 torrenters.php? 或 torrents.php? 中的 passkey=xxx&passkey=xxx
                    # 或者包含 /torrentrss.php
                    html = resp.text
                    
                    # 暴力正则匹配常见 RSS 链接形式
                    # 例: torrentrss.php?passkey=xxxxxxxxx
                    # 例: getrss.php?passkey=xxxxxxxxx
                    match = re.search(r"href=['\"]([^'\"]*(?:torrentrss|getrss)\.php\?[^'\"]*passkey=[a-zA-Z0-9]+[^'\"]*)['\"]", html)
                    if match:
                        link = match.group(1).replace("&amp;", "&")
                        return urljoin(url, link)
                        
                    # 如果没有找到 rss，找一下有没有单纯的 passkey
                    passkey_match = re.search(r"passkey=([a-zA-Z0-9]{32})", html)
                    if passkey_match:
                        # 拼接一个通用的
                        pk = passkey_match.group(1)
                        # 这里只能猜测，最好就是用户自己填写，因为各个PT站的RSS链接格式都不太一样
                        logger.debug(f"找到 Passkey: {pk} 但未能直接找到 RSS 链接格式")
                        return ""
        except Exception as e:
            logger.debug(f"自动抓取 {url} RSS失败: {e}")
            
        return ""
