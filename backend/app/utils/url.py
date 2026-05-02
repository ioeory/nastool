"""
URL 处理工具函数
"""
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """
    规范化站点 URL：
    - 补全 https:// 前缀
    - 确保末尾有 /
    - 去除多余空格
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    # 确保 path 末尾有斜杠
    path = parsed.path if parsed.path.endswith("/") else parsed.path + "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def extract_domain(url: str) -> str:
    """
    从 URL 中提取主机名（不含端口号）
    例如：https://kp.m-team.io/torrents → kp.m-team.io
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.lower().strip()
    except Exception:
        return ""


def get_main_domain(domain: str) -> str:
    """
    提取主域名（去掉子域名）
    例如：kp.m-team.io → m-team.io
    """
    parts = domain.lower().strip().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain
