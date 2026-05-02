"""
站点注册表 — 本地维护，完全替代 MoviePilot 的第三方 SitesHelper
管理内置 sites.json 以及用户自定义站点元数据
"""
import json
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger


# 内置 sites.json：随 Python 包发布（Docker 仅需 COPY app/，无需单独 config 目录）
_BUILTIN_SITES_FILE = Path(__file__).parent.parent / "config" / "sites.json"
_USER_SITES_FILE = Path("/data/config/user_sites.json")


class SiteRegistry:
    """
    站点注册表（单例）
    
    职责：
    - 加载并合并内置 + 用户自定义站点配置
    - 按域名查找站点元数据
    - 支持运行时动态注册站点
    
    不存储认证信息（Cookie/ApiKey）—— 那些存在 DB 的 Site 表中
    """
    _instance: Optional["SiteRegistry"] = None
    _sites: Dict[str, dict] = {}   # domain -> site_meta

    def __new__(cls) -> "SiteRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sites = {}
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """加载站点配置"""
        sites: List[dict] = []

        # 加载内置站点
        if _BUILTIN_SITES_FILE.exists():
            try:
                with open(_BUILTIN_SITES_FILE, encoding="utf-8") as f:
                    sites.extend(json.load(f))
                logger.info(f"SiteRegistry: 加载内置站点 {len(sites)} 个")
            except Exception as e:
                logger.error(f"SiteRegistry: 加载内置 sites.json 失败: {e}")

        # 加载用户自定义站点（会覆盖同域名的内置配置）
        if _USER_SITES_FILE.exists():
            try:
                with open(_USER_SITES_FILE, encoding="utf-8") as f:
                    user_sites = json.load(f)
                sites.extend(user_sites)
                logger.info(f"SiteRegistry: 加载用户自定义站点 {len(user_sites)} 个")
            except Exception as e:
                logger.error(f"SiteRegistry: 加载用户 sites.json 失败: {e}")

        # 按域名建立索引
        for site in sites:
            domain = site.get("domain", "").strip().lower()
            if not domain:
                continue
            self._sites[domain] = site
            # 扩展域名也指向同一元数据
            for ext in site.get("ext_domains", []):
                ext = ext.strip().lower()
                if ext:
                    self._sites[ext] = site

        logger.info(f"SiteRegistry: 共加载 {len(set(s['id'] for s in self._sites.values()))} 个站点配置")

    def reload(self) -> None:
        """热重载配置（不重启服务）"""
        self._sites.clear()
        self._load()

    def get_indexer(self, domain: str) -> Optional[dict]:
        """
        根据域名（支持子域名）查找站点配置
        
        :param domain: 完整域名或主域名，如 "kp.m-team.io" 或 "m-team.io"
        :return: 站点元数据 dict 或 None
        """
        domain = domain.strip().lower()
        # 精确匹配
        if domain in self._sites:
            return self._sites[domain]
        # 去掉 www 匹配
        if domain.startswith("www."):
            bare = domain[4:]
            if bare in self._sites:
                return self._sites[bare]
        # 提取末级域名（如 m-team.io 匹配 kp.m-team.io）
        parts = domain.split(".")
        if len(parts) >= 2:
            main_domain = ".".join(parts[-2:])
            if main_domain in self._sites:
                return self._sites[main_domain]
        return None

    def get_all_indexers(self) -> List[dict]:
        """返回所有不重复的站点配置列表"""
        seen_ids = set()
        result = []
        for site in self._sites.values():
            site_id = site.get("id")
            if site_id not in seen_ids:
                seen_ids.add(site_id)
                result.append(site)
        return sorted(result, key=lambda x: x.get("name", ""))

    def register(self, site_meta: dict) -> None:
        """
        动态注册站点配置（用于用户手动添加未知站点后自动识别）
        不持久化到磁盘，重启后需重新识别
        """
        domain = site_meta.get("domain", "").strip().lower()
        if not domain:
            raise ValueError("站点 domain 不能为空")
        self._sites[domain] = site_meta
        logger.info(f"SiteRegistry: 动态注册站点 {site_meta.get('name', domain)}")

    def get_parser_type(self, domain: str) -> str:
        """获取站点的解析器类型（nexusphp / gazelle / mteam_api / ...）"""
        meta = self.get_indexer(domain)
        return meta.get("parser", "nexusphp") if meta else "nexusphp"

    def is_registered(self, domain: str) -> bool:
        """判断域名是否在注册表中"""
        return self.get_indexer(domain) is not None
