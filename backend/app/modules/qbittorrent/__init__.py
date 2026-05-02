"""
qBittorrent 连接器
通过 WebAPI V2 接口与 qBittorrent 交互，用于添加种子及监控状态。
"""
from typing import Optional, List, Dict, Any
import httpx
from loguru import logger

from app.core.config import settings


class QbittorrentClient:
    """qBittorrent WebAPI V2 轻量级客户端"""

    def __init__(self, host: str, username: Optional[str] = None, password: Optional[str] = None, category: Optional[str] = None):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.category = category or "nastool"
        self._cookie_str = ""

    async def _get_client(self):
        """配置客户端，注入Cookie维持登录态"""
        headers = {}
        if self._cookie_str:
            headers["Cookie"] = self._cookie_str
        return httpx.AsyncClient(timeout=10, headers=headers, verify=False)

    async def login(self) -> bool:
        """登录并获取 Cookie (SID)"""
        if not self.host:
            logger.warning("未配置 QB_HOST，跳过 qBittorrent 登录")
            return False

        try:
            url = f"{self.host}/api/v2/auth/login"
            data = {"username": self.username, "password": self.password}
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                res = await client.post(url, data=data)
                
            if "Ok" in res.text:
                cookie_parts = []
                for k, v in res.cookies.items():
                    cookie_parts.append(f"{k}={v}")
                self._cookie_str = "; ".join(cookie_parts)
                logger.info("qBittorrent 登录成功")
                
                # 检查并创建专属默认分类
                await self._ensure_category()
                return True
            else:
                logger.error(f"qBittorrent 登录失败: {res.text}")
                return False
        except Exception as e:
            logger.error(f"qBittorrent 登录异常: {e}")
            return False

    async def _ensure_category(self):
        """确保设置好的 category 存在"""
        if not self.category:
            return
            
        try:
            url = f"{self.host}/api/v2/torrents/categories"
            async with await self._get_client() as client:
                res = await client.get(url)
                if res.status_code == 200:
                    categories = res.json()
                    if self.category not in categories:
                        # 创建分类
                        create_url = f"{self.host}/api/v2/torrents/createCategory"
                        post_data = {"category": self.category}
                        # 这里如果用户在系统级别配置了 DOWNLOAD_PATH，依然可以作为分类默认路径
                        if hasattr(settings, 'DOWNLOAD_PATH') and settings.DOWNLOAD_PATH:
                             post_data["savePath"] = settings.DOWNLOAD_PATH
                        await client.post(create_url, data=post_data)
                        logger.info(f"已自动为 qBittorrent 创建分类: {self.category}")
        except Exception as e:
            logger.error(f"检查 qB 分类异常: {e}")

    async def add_torrent(self, content: bytes, save_path: str = None, category: str = None) -> bool:
        """
        向 qBittorrent 追加种子
        :param content: 种子的二进制 bytes 内容
        :param save_path: 覆盖默认下载路径
        :param category: 覆盖默认分类
        """
        if not self._cookie_str:
            if not await self.login():
                return False

        url = f"{self.host}/api/v2/torrents/add"
        
        # 构建 multipart 传参
        files = {
            "torrents": ("torrent.torrent", content, "application/x-bittorrent")
        }
        
        data = {
            "category": category or self.category,
            "autoTMM": "false",  # 关闭自动种子管理，以免打乱路径
            "paused": "false"
        }
        if save_path:
            data["savepath"] = save_path

        try:
            async with await self._get_client() as client:
                res = await client.post(url, data=data, files=files)
                if "Ok" in res.text:
                    logger.info("种子成功推送到 qBittorrent。")
                    return True
                else:
                    logger.error(f"qBittorrent 添加种子失败: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"qBittorrent 添加种子异常: {e}")
            return False

    async def get_torrents(self, filter_state: str = "all", category: str = None) -> List[Dict[str, Any]]:
        """
        获取当前任务列表，用于下载监控
        filter_state 取值范围：all, downloading, completed, paused, active, inactive, resumed 
        """
        if not self._cookie_str:
            if not await self.login():
                return []
                
        url = f"{self.host}/api/v2/torrents/info"
        params = {"filter": filter_state}
        if category:
            params["category"] = category
            
        try:
            async with await self._get_client() as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.error(f"获取 qBittorrent 状态异常: {e}")
            
        return []

    async def delete_torrents(self, hashes: list, delete_files: bool = False) -> bool:
        """
        批量删除种子
        :param hashes: 种子 hash 列表
        :param delete_files: 是否同时删除本地文件（刷流任务可在 delete_rules.delete_files 中配置）
        """
        if not hashes:
            return True
        if not self._cookie_str:
            if not await self.login():
                return False

        url = f"{self.host}/api/v2/torrents/delete"
        data = {
            "hashes": "|".join(hashes),
            "deleteFiles": "true" if delete_files else "false",
        }
        try:
            async with await self._get_client() as client:
                res = await client.post(url, data=data)
                if res.status_code == 200:
                    logger.info(f"qBittorrent 已删除 {len(hashes)} 个种子")
                    return True
                else:
                    logger.error(f"qBittorrent 删除种子失败: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"qBittorrent 删除种子异常: {e}")
            return False
    async def get_transfer_info(self) -> Dict[str, Any]:
        """
        获取全局传输信息（下载/上传速度、数据总量等）
        API: /api/v2/transfer/info
        """
        if not self._cookie_str:
            if not await self.login():
                return {}

        url = f"{self.host}/api/v2/transfer/info"
        try:
            async with await self._get_client() as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.error(f"获取 qBittorrent 传输速度异常: {e}")
            
        return {}
