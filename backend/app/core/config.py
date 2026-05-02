from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    """
    应用全局配置，由环境变量 / .env 文件驱动。
    Pydantic-Settings 会自动读取同名环境变量（大小写不敏感）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 基础 ----
    APP_NAME: str = "NasTool"
    APP_DOMAIN: str = ""
    API_PORT: int = 3001
    DEBUG: bool = False
    TZ: str = "Asia/Shanghai"

    # ---- 安全 ----
    SECRET_KEY: str = "CHANGE_ME_TO_A_RANDOM_64_CHAR_STRING"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 天
    SUPERUSER: str = "admin"
    SUPERUSER_PASSWORD: str = "password"
    # 对外访问的 JWT 算法
    ALGORITHM: str = "HS256"

    # ---- 数据库 ----
    DB_TYPE: str = "sqlite"
    SQLITE_DB_PATH: str = "/data/db/nastool.db"
    POSTGRESQL_URI: Optional[str] = None

    # ---- 数据目录 ----
    LOG_PATH: str = "/data/logs"
    DOWNLOAD_PATH: str = "/media/downloads"
    LIBRARY_PATH: str = "/media/library"

    # ---- 代理 ----
    PROXY_HOST: Optional[str] = None
    USE_PROXY: bool = False

    # ---- 媒体元数据 ----
    TMDB_API_KEY: Optional[str] = None
    TMDB_IMAGE_URL: str = "https://image.tmdb.org/t/p/"

    # ---- 用户 Agent ----
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # ---- 下载器 ----
    QB_HOST: str = "http://localhost:8080"
    QB_USERNAME: str = "admin"
    QB_PASSWORD: str = "adminadmin"
    QB_CATEGORY: str = "nastool"
    TR_HOST: Optional[str] = None
    TR_USERNAME: Optional[str] = None
    TR_PASSWORD: Optional[str] = None

    # ---- 媒体服务器 ----
    EMBY_HOST: Optional[str] = None
    EMBY_API_KEY: Optional[str] = None
    JELLYFIN_HOST: Optional[str] = None
    JELLYFIN_API_KEY: Optional[str] = None
    PLEX_HOST: Optional[str] = None
    PLEX_TOKEN: Optional[str] = None

    # ---- 通知 ----
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    WECHAT_CORP_ID: Optional[str] = None
    WECHAT_CORP_SECRET: Optional[str] = None
    WECHAT_AGENT_ID: Optional[str] = None

    # ---- CookieCloud ----
    COOKIECLOUD_HOST: Optional[str] = None
    COOKIECLOUD_KEY: Optional[str] = None
    COOKIECLOUD_PASSWORD: Optional[str] = None

    # ---- 内部计算属性 ----
    @property
    def database_url(self) -> str:
        """返回 SQLAlchemy 异步连接 URL"""
        if self.DB_TYPE == "postgresql" and self.POSTGRESQL_URI:
            return self.POSTGRESQL_URI
        # 确保目录存在
        db_path = Path(self.SQLITE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"

    @property
    def database_url_sync(self) -> str:
        """返回 SQLAlchemy 同步连接 URL（用于 Alembic 迁移）"""
        if self.DB_TYPE == "postgresql" and self.POSTGRESQL_URI:
            return self.POSTGRESQL_URI.replace("+asyncpg", "+psycopg2")
        db_path = Path(self.SQLITE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.SQLITE_DB_PATH}"

    @property
    def proxy(self) -> Optional[dict]:
        """返回 requests 格式的代理配置"""
        if self.PROXY_HOST:
            return {"http": self.PROXY_HOST, "https": self.PROXY_HOST}
        return None

    @property
    def log_path(self) -> Path:
        p = Path(self.LOG_PATH)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "CHANGE_ME_TO_A_RANDOM_64_CHAR_STRING":
            # 采用固定 fallback 避免多 worker 进程下生成的秘钥不一致导致 JWT 签名报错
            return "nastool_local_dev_secret_key_change_me_in_prod"
        return v


# 全局单例
settings = Settings()
