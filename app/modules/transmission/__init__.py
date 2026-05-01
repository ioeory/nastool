import httpx
from typing import List, Dict, Any, Optional
from loguru import logger

class TransmissionClient:
    """Transmission RPC 轻量级客户端"""
    def __init__(self, host: str, username: Optional[str] = None, password: Optional[str] = None):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self._session_id = ""

    @property
    def _rpc_url(self):
        return f"{self.host}/transmission/rpc"

    async def _get_auth(self):
        if self.username and self.password:
            return (self.username, self.password)
        return None

    async def _request(self, method: str, arguments: dict = None) -> httpx.Response:
        headers = {}
        if self._session_id:
            headers["X-Transmission-Session-Id"] = self._session_id

        payload = {"method": method}
        if arguments:
            payload["arguments"] = arguments

        async with httpx.AsyncClient(timeout=10, verify=False, auth=await self._get_auth()) as client:
            res = await client.post(self._rpc_url, json=payload, headers=headers)
            
            # TR 返回 409 代表 Session ID 过期或需要获取
            if res.status_code == 409:
                self._session_id = res.headers.get("X-Transmission-Session-Id", "")
                headers["X-Transmission-Session-Id"] = self._session_id
                res = await client.post(self._rpc_url, json=payload, headers=headers)
                
            return res

    async def login(self) -> bool:
        """测试连接并获取 Session ID"""
        if not self.host:
            return False
            
        try:
            res = await self._request("session-get")
            if res.status_code == 200:
                logger.info("Transmission 连通测试成功")
                return True
            else:
                logger.error(f"Transmission 连接失败: HTTP {res.status_code}")
                return False
        except Exception as e:
            logger.error(f"Transmission 连接异常: {e}")
            return False

    async def add_torrent(self, content: bytes, save_path: str = None, category: str = None) -> bool:
        """不支持 Bytes 上传，必须转换为 Base64 (TR 规范)"""
        import base64
        import json
        
        args = {
            "metainfo": base64.b64encode(content).decode("utf-8"),
            "paused": False
        }
        if save_path:
            args["download-dir"] = save_path
            
        try:
            res = await self._request("torrent-add", args)
            if res.status_code == 200:
                data = res.json()
                if data.get("result") == "success":
                    logger.info("种子成功推送到 Transmission")
                    return True
                else:
                    logger.error(f"Transmission 添加失败: {data}")
                    return False
            else:
                logger.error(f"Transmission 响应异常: {res.status_code}")
                return False
        except Exception as e:
            logger.error(f"Transmission 添加种子异常: {e}")
            return False

    async def get_torrents(self, filter_state: str = "all", category: str = None) -> List[Dict[str, Any]]:
        """获取所有任务（简化版）"""
        try:
            args = {"fields": ["id", "name", "status", "percentDone", "downloadDir"]}
            res = await self._request("torrent-get", args)
            if res.status_code == 200:
                data = res.json()
                if data.get("result") == "success":
                    return data.get("arguments", {}).get("torrents", [])
        except Exception as e:
            logger.error(f"Transmission 获取状态异常: {e}")
        return []

