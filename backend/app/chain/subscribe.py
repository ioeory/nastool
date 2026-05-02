from typing import List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.models.subscribe import Subscribe
from app.db.models.history import DownloadHistory
from app.chain.search import SearchChain
from app.chain.download import DownloadChain
from app.modules.notification import NotificationManager
from app.utils.media_parser import MediaParser


class SubscribeChain:
    """自动化订阅与追剧业务链"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_chain = SearchChain(db)
        self.download_chain = DownloadChain(db)

    async def execute(self):
        """执行全体自动订阅检查"""
        logger.info("开始执行自动订阅(追剧)检测周期...")
        
        # 1. 查出所有激活的订阅
        stmt = select(Subscribe).where(Subscribe.is_active == True)
        subs = (await self.db.scalars(stmt)).all()
        
        if not subs:
            return "无活跃订阅任务，跳过检测。"
            
        total_found = 0
        for sub in subs:
            logger.info(f"正在检查订阅: {sub.name} (关键字: {sub.keyword})")
            try:
                found = await self._process_subscription(sub)
                if found:
                    total_found += 1
            except Exception as e:
                logger.error(f"处理订阅 [{sub.name}] 异常: {e}")
                
        logger.info(f"订阅检测周期完毕，共命中 {total_found} 个新资源。")
        return f"订阅检测周期完毕，共命中 {total_found} 个新资源。"

    async def _process_subscription(self, sub: Subscribe):
        """处理单一规则"""
        # 1. 搜索
        # 此处复用已升级聚合去重能力的 SearchChain
        results = await self.search_chain.search(keyword=sub.keyword)
        
        if not results:
            return
            
        # 2. 深度过滤
        for item in results:
            # A. 基础去重（防止重复推送相同链接）
            exist_stmt = select(DownloadHistory).where(DownloadHistory.torrent_url == item.enclosure)
            if await self.db.scalar(exist_stmt):
                continue
                
            # B. 媒体信息解析
            info = MediaParser.parse(item.title)
            
            # C. 分辨率过滤
            if sub.resolution:
                allowed_res = [r.strip().lower() for r in sub.resolution.split(",")]
                item_res = (info.get("resolution") or "").lower()
                if item_res not in allowed_res:
                    logger.debug(f"订阅 [{sub.name}] 跳过分辨率不匹配资源: {item.title} ({item_res})")
                    continue

            # D. 年份匹配
            if sub.year and info.get("year"):
                if str(sub.year) != str(info["year"]):
                    continue

            # E. 剧集/集数匹配 (如果是 TV)
            if sub.media_type == "tv":
                # 检查季号
                if sub.season is not None and info.get("season") is not None:
                    if int(sub.season) != int(info["season"]):
                        continue
                
                # 检查集号：只下还没下的（大于等于当前进度的下一集）
                if info.get("episode") is not None:
                    # 如果订阅设置了 episode，则严格匹配集号
                    # 场景 1: 定向搜某一集
                    if sub.episode is not None and int(info["episode"]) != int(sub.episode):
                        continue
                    # 场景 2: 追更（自动下载未下载的新集）
                    # 下一集应该是 current_episode + 1
                    # 允许下载大于等于 current_episode + 1 的资源
                    if int(info["episode"]) <= sub.current_episode:
                        continue

            # --- 命中符合规则的资源 ---
            logger.info(f"订阅 [{sub.name}] 命中符合规则的新资源: {item.title}")
            
            # 3. 推送下载
            success = await self.download_chain.download(item)
            
            if success:
                # 写入下载历史
                self.db.add(DownloadHistory(
                    site_id=item.site_id,
                    title=item.title,
                    torrent_url=item.enclosure,
                    status="downloading",
                    size=item.size
                ))
                
                # 更新订阅状态与进度
                sub.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if sub.media_type == "tv" and info.get("episode") is not None:
                    # 动态更新已下载集数：取最大值
                    sub.current_episode = max(sub.current_episode, int(info["episode"]))
                    if sub.total_episode and sub.current_episode >= sub.total_episode:
                        sub.state = "completed"
                    else:
                        sub.state = "downloading"
                
                await self.db.commit()
                logger.info(f"订阅状态已更新: {sub.name} (当前集数: {sub.current_episode})")
                
                # 发送通知
                try:
                    await NotificationManager.send_subscribe_found(
                        title=item.title,
                        site=item.site_name
                    )
                except Exception as e:
                    logger.error(f"通知发送失败: {e}")
                
                # 通常一次检测周期下载一集即可（避免由于站点资源错位导致下错）
                # 当然这里可以根据业务需求选择是否继续循环
                return True

        return False
