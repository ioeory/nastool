import os
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import PTN

from app.core.config import settings
from app.db.models.downloader import Downloader
from app.db.models.history import TransferHistory
from app.helper.transfer import TransferHelper
from app.modules.themoviedb.client import TMDBClient
from app.modules.qbittorrent import QbittorrentClient
from app.modules.transmission import TransmissionClient
from app.modules.notification import NotificationManager
from app.modules.mediaserver.base import EmbyClient, JellyfinClient

class TransferChain:
    """自动化文件整理/硬链接与刮削业务链"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tmdb = TMDBClient()

    async def execute(self):
        """执行一轮全局增量整理"""
        logger.info("开始执行资源整理刮削周期...")
        
        if not getattr(settings, "LIBRARY_PATH", None):
            logger.error("未配置媒体库基础路径 (LIBRARY_PATH)，跳过整理。")
            return
            
        lib_base = Path(settings.LIBRARY_PATH)
        
        # 1. 抓取所有处于激活状态的下载器
        d_stmt = select(Downloader).where(Downloader.is_active == True)
        downloaders = (await self.db.execute(d_stmt)).scalars().all()
        
        total_count = 0
        for d in downloaders:
            try:
                count = await self._process_downloader(d, lib_base)
                total_count += count
            except Exception as e:
                logger.error(f"处理下载器 [{d.name}] 时异常: {e}")
                
        logger.info(f"资源整理周期执行完毕，共处理 {total_count} 个资源。")
        return f"整理周期执行完毕，共处理 {total_count} 个资源。"

    async def _process_downloader(self, downloader: Downloader, lib_base: Path):
        """抓取并处理单个下载器的已完成任务"""
        # 初始化客户端
        if downloader.client_type == "qbittorrent":
            client = QbittorrentClient(downloader.host, downloader.username, downloader.password)
            # qB 状态 mapping: 'completed', 'stalledUP', 'uploading', 'pausedUP'
            # 我们直接拿全部，然后自己判断 progress == 1
            torrents = await client.get_torrents()
            completed = [t for t in torrents if t.get('progress') == 1]
            get_hash = lambda t: t.get('hash')
            get_save_path = lambda t: Path(t.get('save_path', '')) / t.get('name', '')
            get_name = lambda t: t.get('name')
            
        elif downloader.client_type == "transmission":
            client = TransmissionClient(downloader.host, downloader.username, downloader.password)
            torrents = await client.get_torrents()
            completed = [t for t in torrents if t.get('percentDone') == 1]
            get_hash = lambda t: str(t.get('id'))  # TR 简化版取 id
            get_save_path = lambda t: Path(t.get('downloadDir', '')) / t.get('name', '')
            get_name = lambda t: t.get('name')
        else:
            return

        processed_count = 0
        for t in completed:
            thash = get_hash(t)
            name = get_name(t)
            src_path = get_save_path(t)
            
            # 2. 检查库中是否已经处理过
            exist_stmt = select(TransferHistory).where(TransferHistory.download_hash == thash)
            if await self.db.scalar(exist_stmt):
                continue
                
            logger.info(f"发现新下载完成资源: {name}")
            
            # 解析 path_mapping 修正 src_path
            if downloader.path_mapping:
                try:
                    mappings = json.loads(downloader.path_mapping)
                    for mapping in mappings:
                        sp = mapping.get('storage_path')
                        dp = mapping.get('download_path')
                        if sp and dp and str(src_path).startswith(dp):
                            # 将 downloader 的路径前缀替换为宿主机的 storage_path 前缀
                            new_path_str = str(src_path).replace(dp, sp, 1)
                            src_path = Path(new_path_str)
                            break
                except Exception as e:
                    logger.warning(f"解析/应用下载器 path_mapping 异常: {e}")

            if not src_path.exists():
                logger.warning(f"源路径不存在，可能被删或者跨容器路径不一致: {src_path}")
                continue
                
            # 3. PTN 静态提取信息
            parsed = PTN.parse(name)
            search_title = parsed.get("title", name)
            year = parsed.get("year", "")
            
            logger.debug(f">> 解析到标题: {search_title}, 年份: {year}")
            
            # 4. TMDB 刮削获取官方译名
            tmdb_info = await self.tmdb.search_multi(search_title, str(year) if year else None)
            
            if tmdb_info:
                # 重组标准名称
                media_type = tmdb_info.get("media_type", "movie")
                std_title = tmdb_info.get("title") or tmdb_info.get("name")
                std_year = (tmdb_info.get("release_date") or tmdb_info.get("first_air_date") or "").split("-")[0]
                std_folder_name = f"{std_title} ({std_year})" if std_year else std_title
                sub_dir = "电影" if media_type == "movie" else "剧集"
                
                logger.info(f"TMDB 匹配成功: 类型={sub_dir}, 译名={std_folder_name}")
            else:
                # 盲识别回退
                sub_dir = "未识别"
                std_folder_name = f"{search_title} ({year})" if year else search_title
                media_type = ""
                logger.warning("TMDB 未匹配到结果，采用解析备用名硬链接。")
                
            # 5. 生成目标路径
            dest_dir = lib_base / sub_dir / std_folder_name
            
            # 6. 开始硬链接物理文件
            # 兼容单文件做种和多文件文件夹的情况
            success = TransferHelper.transfer(str(src_path), str(dest_dir), mode="hardlink")
            
            if success:
                logger.info(f"硬链接创建成功: -> {dest_dir}")
                processed_count += 1
                
                # 7. 写入 NFO 元数据 (简单占位，能被 Emby 扫出)
                if tmdb_info:
                    try:
                        nfo_content = f"<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\"?>\n<{media_type}>\n  <title>{std_title}</title>\n  <tmdbid>{tmdb_info.get('id')}</tmdbid>\n</{media_type}>"
                        nfo_path = dest_dir / ("movie.nfo" if media_type == "movie" else "tvshow.nfo")
                        if not nfo_path.exists():
                            with open(nfo_path, "w", encoding="utf-8") as f:
                                f.write(nfo_content)
                    except Exception as e:
                        logger.error(f"写入 NFO 时错误: {e}")

                # 8. 持久化记录到历史
                history = TransferHistory(
                    download_hash=thash,
                    title=name,
                    src=str(src_path),
                    dest=str(dest_dir),
                    success=True,
                    tmdb_id=tmdb_info.get("id") if tmdb_info else None
                )
                self.db.add(history)
                await self.db.commit()
                
                # ---- Phase 7: Hooks ----
                # 1. 消息通知
                try:
                    await NotificationManager.send_transfer_ok(
                        title=std_folder_name,
                        category=sub_dir,
                        path=str(dest_dir),
                        tmdb_id=tmdb_info.get("id") if tmdb_info else None
                    )
                except Exception as e:
                    logger.error(f"通知发送失败: {e}")
                
                # 2. 刷新媒体服务器
                try:
                    if settings.EMBY_HOST:
                        await EmbyClient().refresh_library()
                    if settings.JELLYFIN_HOST:
                        await JellyfinClient().refresh_library()
                except Exception as e:
                    logger.error(f"媒体服务器刷新失败: {e}")
            else:
                logger.error(f"硬链接发生异常，该资源已被挂起: {name}")
                
        return processed_count
                
