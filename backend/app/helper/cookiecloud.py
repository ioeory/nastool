"""
CookieCloud 辅助工具
"""
import base64
import json
from typing import Tuple, Dict, Optional

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger

from app.core.config import settings


class CookieCloudHelper:
    """
    CookieCloud 客户端
    解密并获取所有站点的 Cookie 字典
    """

    async def download(self) -> Tuple[Optional[Dict[str, str]], str]:
        """
        从 CookieCloud 服务下载并解密 Cookie

        :return: (domain -> cookie_string 字典, 错误信息)
        """
        if not all([settings.COOKIECLOUD_HOST, settings.COOKIECLOUD_KEY,
                    settings.COOKIECLOUD_PASSWORD]):
            return None, "未配置 CookieCloud 服务"

        url = f"{settings.COOKIECLOUD_HOST.rstrip('/')}/get/{settings.COOKIECLOUD_KEY}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return None, f"CookieCloud 请求失败: {e}"

        encrypted = data.get("encrypted")
        if not encrypted:
            return None, "CookieCloud 返回数据格式错误"

        try:
            decrypted = self._decrypt(encrypted)
            cookies_raw: dict = json.loads(decrypted).get("cookie_data", {})
        except Exception as e:
            return None, f"CookieCloud 解密失败: {e}"

        # 将每个域名的 cookie 数组转换为 cookie 字符串
        result: Dict[str, str] = {}
        for domain, cookie_list in cookies_raw.items():
            if not isinstance(cookie_list, list):
                continue
            cookie_str = "; ".join(
                f"{c['name']}={c['value']}" for c in cookie_list
                if c.get("name") and c.get("value")
            )
            if cookie_str:
                result[domain.lstrip(".")] = cookie_str

        logger.info(f"CookieCloud: 解密成功，获取 {len(result)} 个域名的 Cookie")
        return result, "成功"

    def _decrypt(self, encrypted: str) -> str:
        """AES-GCM 解密"""
        import hashlib
        # 密钥 = MD5(uuid + password) 的前16字节
        key_source = f"{settings.COOKIECLOUD_KEY}-{settings.COOKIECLOUD_PASSWORD}"
        md5 = hashlib.md5(key_source.encode()).hexdigest()
        key = md5[:16].encode()

        raw = base64.b64decode(encrypted)
        # 前 16 字节为 salt（OpenSSL 格式），跳过 "Salted__" + 8 bytes
        # 直接 AES-256-CBC 解密（CookieCloud 使用标准 JS crypto-js 格式）
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            # crypto-js 默认使用 CBC + PKCS7
            iv = raw[:16]
            cipher_text = raw[16:]
            # 密钥扩展到 32 字节
            full_key = hashlib.md5(key_source.encode()).hexdigest().encode()
            cipher = AES.new(full_key[:32], AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(cipher_text), 16)
            return decrypted.decode("utf-8")
        except ImportError:
            raise RuntimeError("请安装 pycryptodome: pip install pycryptodome")
