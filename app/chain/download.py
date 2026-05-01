"""
下载业务链
负责调度 IndexerModule 下载对应 Torrent 文件，然后推送到下载器（目前仅实现 qBittorrent）。
"""
from typing import Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.site import Site
from app.modules.indexer import IndexerModule
from app.schemas import TorrentItem

class DownloadChain:
    """下载统一调度中心"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.indexer = IndexerModule(db)

    async def download(self, item: TorrentItem, save_path: str = None, category: str = None) -> bool:
        """
        触发针对某一搜索结果的下载操作
        :param item: 从搜索链返回的种子信息
        :param save_path: 覆盖下载路径
        :param category: 覆盖分类
        """
        logger.info(f"开始触发下载: {item.title}")
        
        # 1. 查找此资源对应的站点信息
        result = await self.db.execute(select(Site).where(Site.id == item.site_id))
        site = result.scalar_one_or_none()
        
        if not site:
            logger.error("找不到对应的站点记录，下载取消。")
            return False
            
        if not site.is_active:
            logger.error("对应站点当前被禁用，下载取消。")
            return False

        # 2. 从原始网站或者API接口下载 Torrent bytes 数据
        logger.info("正在从网站源下载 Torrent 种子数据流...")
        torrent_bytes = await self.indexer.download_torrent(site, item.enclosure)
        
        if not torrent_bytes:
            logger.error("未能成功载入 Torrent 数据或验证失败（未返回 bytes）。")
            return False
            
        logger.info(f"Torrent 文件下载完成（大小：{len(torrent_bytes)} 字节），正在推送到下载器...")

        # 3. 分发到可用的下载器
        from app.db.models.downloader import Downloader
        from app.modules.qbittorrent import QbittorrentClient
        from app.modules.transmission import TransmissionClient

        # 获取启用的下载器并按优先级排序
        d_stmt = select(Downloader).where(Downloader.is_active == True).order_by(Downloader.priority.asc())
        downloaders = (await self.db.execute(d_stmt)).scalars().all()
        
        if not downloaders:
            logger.error("系统中未配置或未启用任何下载器！")
            return False

        for d in downloaders:
            logger.info(f"正在尝试推送到下载器节点: {d.name} ({d.client_type})")
            try:
                # 依据类型初始化工厂实例
                if d.client_type == "qbittorrent":
                    client = QbittorrentClient(host=d.host, username=d.username, password=d.password, category=d.category)
                elif d.client_type == "transmission":
                    client = TransmissionClient(host=d.host, username=d.username, password=d.password)
                else:
                    logger.warning(f"未知下载器类型: {d.client_type}")
                    continue
                
                is_pushed = await client.add_torrent(
                    content=torrent_bytes, 
                    save_path=save_path or d.save_path, 
                    category=category or d.category
                )
                
                if is_pushed:
                    logger.info(f"✅ 下载已成功推送到节点 [{d.name}]: {item.title}")
                    return True
                else:
                    logger.warning(f"节点 [{d.name}] 推送失败，将尝试下一个节点")
                    
            except Exception as e:
                logger.error(f"推送节点 [{d.name}] 时发生异常: {e}")
                
        logger.error("所有可用下载器节点均推送失败！")
        return False
