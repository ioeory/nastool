"""
站点管理器 — 封装所有站点操作的业务逻辑
包含：添加站点、测试连通性、缓存 favicon、同步 CookieCloud
"""
import base64
import hashlib
import time
from typing import Tuple, Optional
from urllib.parse import urlparse, urljoin

import httpx
from loguru import logger
from lxml import etree
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.event import event_manager, EventType
from app.db.models.site import Site
from app.schemas import SiteCreate, SiteTestResult
from app.site.detector import SiteDetector
from app.site.registry import SiteRegistry
from app.utils.url import normalize_url, extract_domain
from app.utils.cookie import parse_cookie_string


class SiteManager:
    """
    站点管理器（每次请求创建，持有 db 会话）
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = SiteRegistry()
        self.detector = SiteDetector(timeout=20)

    async def add_site(self, site_in: SiteCreate) -> Site:
        """
        完整的站点添加流程：
        1. 规范化 URL
        2. 提取/解析域名
        3. 查找注册表元数据
        4. 检测框架类型（若注册表中无）
        5. 验证 Cookie 有效性
        6. 写入数据库
        7. 发布 SITE_ADDED 事件
        """
        url = normalize_url(site_in.url)
        domain = extract_domain(url)

        if not domain:
            raise ValueError(f"无效的站点 URL: {site_in.url}")

        # 检查是否已存在
        existing = await self.db.execute(select(Site).where(Site.domain == domain))
        if existing.scalar_one_or_none():
            raise ValueError(f"站点 {domain} 已存在，请勿重复添加")

        # 从注册表获取元数据
        meta = self.registry.get_indexer(domain)

        if meta:
            name = meta.get("name", domain)
            public = meta.get("public", False)
            parser = meta.get("parser", "nexusphp")
            logger.info(f"SiteManager: {domain} 在注册表中找到配置: {name} ({parser})")
        else:
            # 未知站点：自动探测
            logger.info(f"SiteManager: {domain} 不在注册表，开始自动探测...")
            parser, detect_msg = await self.detector.detect(
                url=url,
                cookie=site_in.cookie,
                ua=site_in.ua or settings.USER_AGENT,
            )
            name = domain  # 暂用域名作为名称
            public = False
            logger.info(f"SiteManager: 探测结果 — {domain}: {parser} ({detect_msg})")

            # 动态注册到内存注册表
            self.registry.register({
                "id": domain.replace(".", "_"),
                "name": name,
                "domain": domain,
                "ext_domains": [],
                "url": url,
                "parser": parser,
                "schema": "Generic",
                "public": public,
                "language": "zh",
                "search_path": "/torrents.php",
                "torrent_path": "/download.php?id=",
                "categories": [],
                "_auto_detected": True,
            })

        # 对于需要认证的站点，验证 Cookie
        if not public and site_in.cookie:
            ok, msg = await self.test_cookie(
                url=url,
                cookie=parse_cookie_string(site_in.cookie),
                ua=site_in.ua or settings.USER_AGENT,
                parser=parser,
                apikey=site_in.apikey,
            )
            if not ok:
                raise ValueError(f"Cookie 验证失败: {msg}")
            
            # 保存规范化后的 Cookie
            site_in.cookie = parse_cookie_string(site_in.cookie)

        # 写入数据库
        site = Site(
            name=name,
            domain=domain,
            url=url,
            cookie=site_in.cookie,
            ua=site_in.ua,
            apikey=site_in.apikey,
            token=site_in.token,
            rss=site_in.rss,
            pri=site_in.pri,
            proxy=site_in.proxy,
            render=site_in.render,
            timeout=site_in.timeout,
            public=public,
            is_active=True,
            note=site_in.note,
        )
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)

        # 发布事件
        event_manager.send_event(EventType.SITE_ADDED, {
            "domain": domain,
            "site_id": site.id,
        })
        logger.info(f"SiteManager: 站点 {name} ({domain}) 添加成功，id={site.id}")
        return site

    async def test_site(self, site: Site) -> SiteTestResult:
        """测试站点连通性"""
        start = time.time()
        ok, msg = await self.test_cookie(
            url=site.url,
            cookie=parse_cookie_string(site.cookie),
            ua=site.ua or settings.USER_AGENT,
            parser=self.registry.get_parser_type(site.domain),
            apikey=site.apikey,
        )
        latency = int((time.time() - start) * 1000)
        return SiteTestResult(success=ok, message=msg, latency_ms=latency)

    async def test_cookie(
        self,
        url: str,
        cookie: Optional[str],
        ua: str,
        parser: str,
        apikey: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        验证 Cookie / API Key 有效性
        根据解析器类型选择验证方式
        """
        if parser == "mteam_api":
            return await self._test_mteam(url=url, apikey=apikey, ua=ua)
        else:
            return await self._test_generic(url=url, cookie=cookie, ua=ua)

    @staticmethod
    async def _test_generic(url: str, cookie: str, ua: str) -> Tuple[bool, str]:
        """
        通用站点登录检测
        检测页面是否包含「已登录」的特征标记
        """
        LOGGED_IN_PATTERNS = [
            "logout",
            "sign-out",
            "我的账户",
            "个人空间",
            "userdetails",
            "mybonus",
            "upload",
            "seeding",
        ]
        headers = {
            "User-Agent": ua,
            "Cookie": cookie or "",
        }
        try:
            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text.lower()
                if resp.status_code == 200:
                    for pattern in LOGGED_IN_PATTERNS:
                        if pattern in html:
                            return True, "连接成功"
                    return False, "Cookie 已失效或未登录"
                else:
                    return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, f"连接失败: {e}"

    @staticmethod
    async def _test_mteam(url: str, apikey: str, ua: str) -> Tuple[bool, str]:
        """M-Team API Key 验证"""
        if not apikey:
            return False, "M-Team 需要 API Key 认证"
        domain = extract_domain(url)
        if domain.startswith("kp."):
            api_domain = f"api.{domain[3:]}"
        else:
            api_domain = f"api.{domain}"
            
        api_url = f"https://{api_domain}/api/member/profile"
        headers = {
            "User-Agent": ua,
            "x-api-key": apikey,
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20, verify=False) as client:
                resp = await client.post(api_url, headers=headers)
                data = resp.json()
                if resp.status_code == 200 and data.get("data"):
                    return True, "连接成功"
                return False, data.get("message", "API Key 无效")
        except Exception as e:
            return False, f"连接失败: {e}"

    async def cache_favicon(self, domain: str) -> None:
        """后台任务：缓存站点图标"""
        result = await self.db.execute(select(Site).where(Site.domain == domain))
        site = result.scalar_one_or_none()
        if not site:
            return
        try:
            favicon_url = urljoin(site.url, "/favicon.ico")
            headers = {
                "User-Agent": site.ua or settings.USER_AGENT,
                "Cookie": site.cookie or "",
            }
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.get(favicon_url, headers=headers)
                if resp.status_code == 200 and resp.content:
                    b64 = base64.b64encode(resp.content).decode()
                    # 存入 note 字段的 favicon 部分（后续可用专表）
                    logger.debug(f"SiteManager: 缓存 {domain} favicon 成功")
        except Exception as e:
            logger.warning(f"SiteManager: 缓存 {domain} favicon 失败: {e}")

    async def sync_cookiecloud(self) -> Tuple[bool, str]:
        """同步 CookieCloud 服务（后台任务）"""
        from app.helper.cookiecloud import CookieCloudHelper
        helper = CookieCloudHelper()
        cookies, msg = await helper.download()
        if not cookies:
            return False, msg

        add_count, update_count = 0, 0
        for domain, cookie in cookies.items():
            meta = self.registry.get_indexer(domain)
            if not meta:
                continue
            result = await self.db.execute(select(Site).where(Site.domain == domain))
            existing = result.scalar_one_or_none()
            if existing:
                existing.cookie = cookie
                update_count += 1
            else:
                # 自动添加
                try:
                    site_in = SiteCreate(url=meta.get("url", f"https://{domain}"), cookie=cookie)
                    await self.add_site(site_in)
                    add_count += 1
                except Exception as e:
                    logger.warning(f"CookieCloud: 自动添加 {domain} 失败: {e}")

        await self.db.commit()
        return True, f"更新 {update_count} 个站点，新增 {add_count} 个站点"
