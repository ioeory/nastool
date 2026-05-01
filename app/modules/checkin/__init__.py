"""
站点签到管理器
支持 NexusPHP / M-Team 等主流 PT 站点的自动签到
"""
import asyncio
from datetime import datetime
from typing import Optional, Tuple, List
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.db import AsyncSessionLocal
from app.db.models.site import Site
from app.utils.cookie import parse_cookie_string


class CheckinResult:
    """签到结果数据类"""
    def __init__(self, site_id: int, site_name: str, success: bool, message: str):
        self.site_id = site_id
        self.site_name = site_name
        self.success = success
        self.message = message

    def __repr__(self):
        status = "✅" if self.success else "❌"
        return f"{status} [{self.site_name}] {self.message}"


class CheckinManager:
    """
    站点签到管理器
    支持手动触发（单站点）和批量自动签到（所有激活站点）
    """

    # NexusPHP 常见签到路径
    NEXUSPHP_CHECKIN_PATHS = [
        "/attendance.php",
        "/daily_bonus.php",
        "/sign_in.php",
        "/checkin.php",
    ]

    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    #  批量签到入口（自动化任务调用）
    # ------------------------------------------------------------------ #
    async def checkin_all(self, site_ids: Optional[List[int]] = None) -> List[CheckinResult]:
        """
        对所有激活站点（或指定 site_ids）执行签到
        :param site_ids: 指定站点 ID 列表，None 则对所有激活站点签到
        """
        results = []
        async with AsyncSessionLocal() as db:
            if site_ids:
                stmt = select(Site).where(
                    Site.id.in_(site_ids),
                    Site.is_active == True,
                )
            else:
                stmt = select(Site).where(Site.is_active == True)

            sites = (await db.execute(stmt)).scalars().all()

            if not sites:
                logger.info("[Checkin] 没有激活的站点需要签到")
                return []

            logger.info(f"[Checkin] 开始批量签到，共 {len(sites)} 个站点")

            for site in sites:
                result = await self._checkin_site(site, db)
                results.append(result)
                # 避免频繁请求被封
                await asyncio.sleep(2)

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        logger.info(f"[Checkin] 批量签到完成: {success_count}/{len(results)} 成功")

        # 发送汇总通知
        from app.modules.notification import NotificationManager
        summary_title = f"📝 站点签到汇总报表 ({success_count}/{len(results)})"
        
        lines = [f"成功: {success_count}, 失败: {fail_count}", "-----------------"]
        for r in results:
            status = "✅" if r.success else "❌"
            lines.append(f"{status} {r.site_name}: {r.message}")
            
        await NotificationManager.send_message(
            title=summary_title,
            message="\n".join(lines)
        )
        
        return results

    # ------------------------------------------------------------------ #
    #  单站点签到（API 手动触发）
    # ------------------------------------------------------------------ #
    async def checkin_one(self, site_id: int) -> CheckinResult:
        """对指定站点执行签到"""
        async with AsyncSessionLocal() as db:
            result_row = await db.execute(select(Site).where(Site.id == site_id))
            site = result_row.scalar_one_or_none()
            if not site:
                return CheckinResult(site_id, "未知", False, "站点不存在")
            return await self._checkin_site(site, db)

    # ------------------------------------------------------------------ #
    #  核心签到逻辑
    # ------------------------------------------------------------------ #
    async def _checkin_site(self, site: Site, db: AsyncSession) -> CheckinResult:
        """根据站点类型选择签到策略"""
        logger.info(f"[Checkin] 正在签到: {site.name} ({site.domain})")

        try:
            # 根据站点特征选择签到方式
            if site.apikey and "m-team" in site.domain.lower():
                success, message = await self._checkin_mteam(site)
            elif site.apikey and not site.cookie:
                # 纯 API Key 站点
                success, message = await self._checkin_api_generic(site)
            else:
                # NexusPHP 或 Gazelle 通用 Cookie 签到
                success, message = await self._checkin_nexusphp(site)

            # 更新签到时间
            if success:
                await self._update_last_checkin(site, db)

            result = CheckinResult(site.id, site.name, success, message)
            logger.info(str(result))
            return result

        except Exception as e:
            logger.error(f"[Checkin] 站点 {site.name} 签到异常: {e}")
            return CheckinResult(site.id, site.name, False, f"异常: {e}")

    # ------------------------------------------------------------------ #
    #  NexusPHP 签到
    # ------------------------------------------------------------------ #
    async def _checkin_nexusphp(self, site: Site) -> Tuple[bool, str]:
        """
        NexusPHP 签到：尝试 attendance.php 等常见路径
        部分站点签到即访问页面，部分需要 POST
        """
        cookie = parse_cookie_string(site.cookie or "")
        ua = site.ua or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        headers = {
            "User-Agent": ua,
            "Cookie": cookie,
            "Referer": site.url,
        }

        proxy = None
        if site.proxy:
            from app.core.config import settings
            if settings.PROXY_HOST:
                proxy = settings.PROXY_HOST

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            verify=False,
            proxy=proxy,
        ) as client:
            for path in self.NEXUSPHP_CHECKIN_PATHS:
                url = site.url.rstrip("/") + path
                try:
                    resp = await client.get(url, headers=headers)

                    if resp.status_code == 404:
                        continue  # 该路径不存在，试下一个

                    if resp.status_code == 200:
                        text = resp.text
                        # 判断签到结果
                        return self._parse_checkin_response(text)

                    if resp.status_code in (302, 301):
                        # 重定向到登录页说明 Cookie 失效
                        if "login" in str(resp.headers.get("location", "")):
                            return False, "Cookie 已失效，请更新"
                        return True, "签到成功（重定向）"

                except httpx.TimeoutException:
                    continue
                except Exception as e:
                    logger.debug(f"[Checkin] 路径 {path} 失败: {e}")
                    continue

            # 所有路径均 404/失败，尝试首页访问（部分站点登录即算签到）
            return await self._checkin_by_visiting_homepage(site, headers, client)

    async def _checkin_by_visiting_homepage(
        self, site: Site, headers: dict, client: httpx.AsyncClient
    ) -> Tuple[bool, str]:
        """访问首页，部分站点登录即自动签到"""
        try:
            resp = await client.get(site.url, headers=headers)
            if resp.status_code == 200:
                text = resp.text.lower()
                if any(kw in text for kw in ["已签到", "已签", "签到成功", "seeded today", "signed"]):
                    return True, "今日已签到"
                # 能正常访问说明 Cookie 有效，但未找到签到入口
                return True, "访问成功（该站点无独立签到页）"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, f"连接失败: {e}"

    def _parse_checkin_response(self, text: str) -> Tuple[bool, str]:
        """解析签到响应，识别常见的成功/失败标记"""
        text_lower = text.lower()

        # 已签到的标记
        already_patterns = ["已签到", "今天已经签到", "已经签过", "already checked", "already signed"]
        for p in already_patterns:
            if p in text_lower:
                return True, "今日已签到"

        # 签到成功的标记
        success_patterns = [
            "签到成功", "签到完成", "恭喜", "奖励", "魔力",
            "bonus", "check in success", "attendance success",
            "感谢", "天天", "连续"
        ]
        for p in success_patterns:
            if p in text_lower:
                # 尝试提取奖励信息
                reward = self._extract_reward(text)
                return True, f"签到成功{' — ' + reward if reward else ''}"

        # 登录失效
        if any(p in text_lower for p in ["login", "未登录", "请先登录", "sign in to"]):
            return False, "Cookie 已失效，请更新"

        # 无法判断，但页面正常返回
        return True, "签到请求已发送（无法确认结果）"

    @staticmethod
    def _extract_reward(text: str) -> str:
        """从响应中提取奖励数值（如魔力值/积分）"""
        import re
        patterns = [
            r"奖励.*?(\d+\.?\d*)\s*(?:魔力|积分|bonus|坊)",
            r"获得.*?(\d+\.?\d*)",
            r"\+(\d+\.?\d*)\s*(?:魔力|bonus|MB|GB)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(0).strip()
        return ""

    # ------------------------------------------------------------------ #
    #  M-Team API 签到
    # ------------------------------------------------------------------ #
    async def _checkin_mteam(self, site: Site) -> Tuple[bool, str]:
        """M-Team API 签到（bonus/attendance）"""
        from app.utils.url import extract_domain
        domain = extract_domain(site.url)
        if domain.startswith("kp."):
            api_domain = f"api.{domain[3:]}"
        else:
            api_domain = f"api.{domain}"

        url = f"https://{api_domain}/api/member/attendance"
        headers = {
            "User-Agent": site.ua or "Mozilla/5.0",
            "x-api-key": site.apikey,
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20, verify=False) as client:
                resp = await client.post(url, headers=headers)
                data = resp.json()
                if resp.status_code == 200:
                    msg = data.get("message", "")
                    if "already" in msg.lower() or "已" in msg:
                        return True, f"今日已签到: {msg}"
                    return True, f"签到成功: {msg}"
                return False, data.get("message", f"HTTP {resp.status_code}")
        except Exception as e:
            return False, f"API 请求失败: {e}"

    # ------------------------------------------------------------------ #
    #  通用 API Key 签到（预留）
    # ------------------------------------------------------------------ #
    async def _checkin_api_generic(self, site: Site) -> Tuple[bool, str]:
        """通用 API Key 站点签到（预留扩展）"""
        return False, "该站点类型暂不支持自动签到"

    # ------------------------------------------------------------------ #
    #  更新签到时间
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _update_last_checkin(site: Site, db: AsyncSession):
        """更新站点的最后签到时间"""
        try:
            site.last_checkin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.commit()
        except Exception as e:
            logger.warning(f"[Checkin] 更新 last_checkin 失败: {e}")
