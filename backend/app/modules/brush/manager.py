"""
站点刷流管理器
负责：RSS 抓种 → 过滤 → 绑定下载器下发 → 定期删种
"""
import asyncio
from typing import List, Optional, Set
from loguru import logger

import arrow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.db.models.automation import Automation
from app.db.models.downloader import Downloader
from app.db.models.site import Site
from app.db.models.history import DownloadHistory
from app.modules.indexer import IndexerModule
from app.schemas import TorrentItem


def _torrent_age_minutes(pubdate: Optional[str]) -> Optional[float]:
    """返回种子发布时间距今的分钟数；无法解析则返回 None（调用方通常视为不拦截）。"""
    if not pubdate or not str(pubdate).strip():
        return None
    try:
        dt = arrow.get(pubdate.strip())
        return (arrow.now("UTC") - dt.to("UTC")).total_seconds() / 60.0
    except Exception:
        return None


def _parse_exclude_label_set(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    return {x.strip().lower() for x in str(raw).split(",") if x.strip()}


class BrushManager:
    """
    站点刷流管理器
    每个刷流任务通过 task_config 绑定：
      - sites: List[int]     — 目标站点 ID 列表
      - downloader_id: int   — 绑定的下载器节点 ID（必填）
      - max_tasks: int       — 单次最多推送种子数
      - keep_volume: float   — 保留磁盘体积上限(GB)
      - category: str        — 下载器分类标签，默认 Brushing
      - selection_rules: {}  — 选种规则（min/max 体积、max_pub_time 分钟、include_free 等）
      - delete_rules: {}     — 删种规则（exclude_labels：含任一标签则不删）
      - save_path: str       — 可选，覆盖下载保存路径
      - dynamic_delete: bool — 默认 True；False 则本轮不执行删种清理
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    # ------------------------------------------------------------------ #
    #  主入口
    # ------------------------------------------------------------------ #
    async def execute(self, automation_id: int):
        """执行具体的刷流任务"""
        async with AsyncSessionLocal() as db:
            # 1. 读取任务配置
            result = await db.execute(
                select(Automation).where(Automation.id == automation_id)
            )
            auto = result.scalar_one_or_none()
            if not auto or not auto.task_config:
                logger.warning(f"[Brush] 任务 {automation_id} 不存在或未配置业务参数")
                return

            config = auto.task_config
            site_ids: List[int] = config.get("sites", [])
            downloader_id: Optional[int] = config.get("downloader_id")

            if not site_ids:
                logger.warning(f"[Brush] 任务 {auto.name} 未配置目标站点")
                return

            if not downloader_id:
                logger.warning(f"[Brush] 任务 {auto.name} 未绑定下载器节点，跳过执行")
                return

            # 2. 验证绑定的下载器是否存在且启用
            dl_result = await db.execute(
                select(Downloader).where(
                    Downloader.id == downloader_id,
                    Downloader.is_active == True,
                )
            )
            downloader = dl_result.scalar_one_or_none()
            if not downloader:
                logger.error(
                    f"[Brush] 任务 {auto.name} 绑定的下载器 ID={downloader_id} 不存在或已禁用"
                )
                return

            logger.info(
                f"[Brush] 任务 {auto.name} 使用下载器: {downloader.name} "
                f"({downloader.client_type} @ {downloader.host})"
            )

            # 3. 抓取各站点 RSS 种子
            torrents: List[TorrentItem] = []
            indexer = IndexerModule(db)
            for sid in site_ids:
                site_res = await db.execute(select(Site).where(Site.id == sid))
                site = site_res.scalar_one_or_none()
                if not site:
                    continue

                logger.info(f"[Brush] 正在抓取站点: {site.name}")
                try:
                    site_torrents = await indexer.search_site(site, keyword="")
                    logger.info(f"[Brush] {site.name} 抓取到 {len(site_torrents)} 个种子")
                    torrents.extend(site_torrents)
                except Exception as e:
                    logger.error(f"[Brush] 抓取站点 {site.name} 失败: {e}")

            if not torrents:
                logger.info(f"[Brush] 任务 {auto.name} 未发现新种子")
                return f"扫描 {len(site_ids)} 站，未发现新种子"

            # 4. 过滤种子
            filtered = self._filter_torrents(torrents, config)
            logger.info(
                f"[Brush] 过滤完成: 共 {len(torrents)} 个 → 匹配 {len(filtered)} 个"
            )
            if not filtered:
                return f"扫描 {len(site_ids)} 站，抓取 {len(torrents)} 种，匹配 0 种"

            # 5. 去重（防止重复推送）
            new_torrents = await self._deduplicate(filtered, db)
            logger.info(f"[Brush] 去重后剩余: {len(new_torrents)} 个待下载")
            if not new_torrents:
                return f"扫描 {len(site_ids)} 站，抓取 {len(torrents)} 种，匹配 {len(filtered)} 种，已下载过 (去重后 0)"

            # 6. 先清理超出规则的旧种子腾出空间（可关闭）
            deleted_count = 0
            if config.get("dynamic_delete", True):
                deleted_count = await self._cleanup_by_rules(downloader, config)

            # 7. 检查保种体积上限
            max_tasks: int = config.get("max_tasks", 3)
            category: str = config.get("category", "Brushing")
            save_path: Optional[str] = config.get("save_path") or downloader.save_path
            keep_volume: float = config.get("keep_volume", 0.0)

            if keep_volume > 0:
                current_size = await self._get_category_size(downloader, category)
                if current_size / (1024 ** 3) >= keep_volume:
                    logger.info(f"[Brush] 分类 {category} 占用体积 {(current_size/(1024**3)):.2f}GB 已达到上限 {keep_volume}GB，暂缓下发")
                    return f"扫描 {len(site_ids)} 站，过滤后匹配 {len(filtered)} 种，已达保种体积上限暂缓推送，自动清理 {deleted_count} 种"

            # 8. 推送到绑定下载器
            pushed = await self._push_to_downloader(
                torrents=new_torrents[:max_tasks],
                downloader=downloader,
                category=category,
                save_path=save_path,
                db=db,
            )
            logger.info(f"[Brush] 任务 {auto.name} 本轮推送 {pushed} 个种子")

            return f"扫描 {len(site_ids)} 站，抓取 {len(torrents)} 种，过滤后匹配 {len(filtered)} 种，推送 {pushed} 种，自动清理 {deleted_count} 种"
        
        return "执行完成"

    # ------------------------------------------------------------------ #
    #  过滤
    # ------------------------------------------------------------------ #
    def _filter_torrents(
        self, torrents: List[TorrentItem], config: dict
    ) -> List[TorrentItem]:
        """根据 selection_rules 过滤种子"""
        rules = config.get("selection_rules", {})
        include_free: bool = rules.get("include_free", True)
        promotion: str = rules.get("promotion", "")        # "" = 不限; "FREE"/"2XFREE"/"50%"
        exclude_hr: bool = rules.get("exclude_hr", True)
        min_size: float = rules.get("min_size_gb", 0) * 1024**3
        max_size: float = rules.get("max_size_gb", 0) * 1024**3
        max_seeders: int = rules.get("max_seeders", 0)     # 0 = 不限
        max_pub_time: int = int(rules.get("max_pub_time", 0) or 0)  # 分钟，仅接受「发布时间」距今不超过此值的种子；0=不限

        matched = []
        for t in torrents:
            # --- 优惠过滤 ---
            if promotion:
                # 指定了具体优惠类型
                if t.free != promotion:
                    continue
            elif include_free:
                # 只要免费的
                if not t.free:
                    continue

            # --- H&R 过滤 ---
            if exclude_hr and t.hr:
                continue

            # --- 体积过滤 ---
            if min_size > 0 and (t.size or 0) < min_size:
                continue
            if max_size > 0 and (t.size or 0) > max_size:
                continue

            # --- 做种人数过滤 ---
            if max_seeders > 0 and (t.seeders or 0) > max_seeders:
                continue

            # --- 发布时间（种子年龄上限，分钟）---
            if max_pub_time > 0:
                age_min = _torrent_age_minutes(t.pubdate)
                if age_min is not None and age_min > float(max_pub_time):
                    continue

            matched.append(t)

        return matched

    # ------------------------------------------------------------------ #
    #  防重复
    # ------------------------------------------------------------------ #
    async def _deduplicate(
        self, torrents: List[TorrentItem], db: AsyncSession
    ) -> List[TorrentItem]:
        """过滤掉已经下载过的种子（通过 torrent_url 比较）"""
        new_items = []
        for t in torrents:
            if not t.enclosure:
                continue
            exist = await db.scalar(
                select(DownloadHistory).where(
                    DownloadHistory.torrent_url == t.enclosure
                )
            )
            if not exist:
                new_items.append(t)
        return new_items

    # ------------------------------------------------------------------ #
    #  体积检查
    # ------------------------------------------------------------------ #
    async def _get_category_size(self, downloader: Downloader, category: str) -> float:
        """获取特定分类当前的占用总体积(字节)"""
        if downloader.client_type == "qbittorrent":
            from app.modules.qbittorrent import QbittorrentClient
            try:
                client = QbittorrentClient(
                    host=downloader.host,
                    username=downloader.username,
                    password=downloader.password,
                )
                torrents = await client.get_torrents(filter_state="all", category=category)
                return sum(t.get("size", 0) for t in torrents)
            except Exception as e:
                logger.error(f"[Brush] 获取下载器分类 {category} 体积异常: {e}")
        return 0.0

    # ------------------------------------------------------------------ #
    #  推送下载器
    # ------------------------------------------------------------------ #
    async def _push_to_downloader(
        self,
        torrents: List[TorrentItem],
        downloader: Downloader,
        category: str,
        save_path: Optional[str],
        db: AsyncSession,
    ) -> int:
        """将种子推送到指定下载器节点，返回成功数量"""
        from app.modules.indexer import IndexerModule
        from app.modules.qbittorrent import QbittorrentClient
        from app.modules.transmission import TransmissionClient

        indexer = IndexerModule(db)
        pushed = 0

        for t in torrents:
            logger.info(f"[Brush] 下发种子: [{t.site_name}] {t.title}")

            # 获取站点信息（用于携带认证头下载 .torrent 文件）
            site_res = await db.execute(
                select(Site).where(Site.id == t.site_id)
            )
            site = site_res.scalar_one_or_none()
            if not site:
                logger.warning(f"[Brush] 找不到种子对应的站点 id={t.site_id}，跳过")
                continue

            # 下载 .torrent 文件内容
            try:
                torrent_bytes = await indexer.download_torrent(site, t.enclosure)
            except Exception as e:
                logger.error(f"[Brush] 下载种子文件失败: {t.title} — {e}")
                continue

            if not torrent_bytes:
                logger.warning(f"[Brush] 种子文件为空，跳过: {t.title}")
                continue

            # 推送到下载器
            try:
                if downloader.client_type == "qbittorrent":
                    client = QbittorrentClient(
                        host=downloader.host,
                        username=downloader.username,
                        password=downloader.password,
                        category=category,
                    )
                elif downloader.client_type == "transmission":
                    client = TransmissionClient(
                        host=downloader.host,
                        username=downloader.username,
                        password=downloader.password,
                    )
                else:
                    logger.warning(f"[Brush] 未知下载器类型: {downloader.client_type}")
                    continue

                ok = await client.add_torrent(
                    content=torrent_bytes,
                    save_path=save_path,
                    category=category,
                )
                if ok:
                    # 写入历史，防止下次重复
                    db.add(DownloadHistory(
                        site_id=t.site_id,
                        title=t.title,
                        torrent_url=t.enclosure,
                        status="downloading",
                        size=t.size,
                    ))
                    await db.commit()
                    pushed += 1
                    logger.info(f"[Brush] ✅ 推送成功: {t.title}")
                else:
                    logger.warning(f"[Brush] 推送失败: {t.title}")

            except Exception as e:
                logger.error(f"[Brush] 推送异常: {t.title} — {e}")

        return pushed

    # ------------------------------------------------------------------ #
    #  删种清理
    # ------------------------------------------------------------------ #
    async def _cleanup_by_rules(
        self, downloader: Downloader, config: dict
    ):
        """
        查询下载器中属于刷流分类的种子，
        对满足删除规则（最低做种时间 / 最低分享率）的种子执行删除。
        """
        from app.modules.qbittorrent import QbittorrentClient

        delete_rules = config.get("delete_rules", {})
        min_seeding_hours: float = delete_rules.get("min_seeding_hours", 2)
        min_ratio: float = delete_rules.get("min_ratio", 1.0)
        delete_files: bool = bool(delete_rules.get("delete_files", False))
        exclude_labels = _parse_exclude_label_set(delete_rules.get("exclude_labels"))
        category: str = config.get("category", "Brushing")

        if downloader.client_type != "qbittorrent":
            # Transmission 删种逻辑后续扩展
            return

        try:
            client = QbittorrentClient(
                host=downloader.host,
                username=downloader.username,
                password=downloader.password,
            )
            torrents = await client.get_torrents(
                filter_state="all", category=category
            )

            delete_hashes = []
            for t in torrents:
                if exclude_labels:
                    tags_raw = t.get("tags") or ""
                    tags_lower = {
                        x.strip().lower()
                        for x in str(tags_raw).split(",")
                        if x.strip()
                    }
                    if tags_lower & exclude_labels:
                        continue

                seeding_secs = t.get("seeding_time", 0) or t.get("time_active", 0)
                ratio = t.get("ratio", 0)
                seeding_hours = seeding_secs / 3600

                if seeding_hours >= min_seeding_hours and ratio >= min_ratio:
                    delete_hashes.append(t.get("hash"))
                    logger.info(
                        f"[Brush] 删种候选: {t.get('name')} "
                        f"(做种 {seeding_hours:.1f}h, 分享率 {ratio:.2f})"
                    )

            if delete_hashes:
                await client.delete_torrents(delete_hashes, delete_files=delete_files)
                logger.info(
                    f"[Brush] 已删除 {len(delete_hashes)} 个满足条件的刷流种子"
                    f"（{'含本地文件' if delete_files else '仅任务'}）"
                )
                return len(delete_hashes)

        except Exception as e:
            logger.error(f"[Brush] 删种过程异常: {e}")

        return 0
