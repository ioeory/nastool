"""
Pydantic API Schema 统一定义
"""
from typing import Optional, Any
from pydantic import BaseModel


# ---- 通用响应体 ----
class Response(BaseModel):
    """标准 JSON 响应"""
    code: int = 0          # 0=成功，非0=错误
    message: str = "ok"
    data: Optional[Any] = None


class PageResponse(BaseModel):
    """分页响应"""
    code: int = 0
    message: str = "ok"
    total: int = 0
    page: int = 1
    page_size: int = 20
    data: Optional[Any] = None


# ---- 认证 ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ---- 用户 ----
class UserCreate(BaseModel):
    name: str
    password: str
    email: Optional[str] = None
    is_superuser: bool = False
    note: Optional[str] = None


class UserUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: Optional[str]
    avatar: Optional[str]
    is_active: bool
    is_superuser: bool
    note: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class ChangePasswordBody(BaseModel):
    """修改登录密码"""
    old_password: str
    new_password: str


# ---- 站点 ----
class SiteCreate(BaseModel):
    """手动添加站点"""
    url: str                            # 必填：站点首页 URL
    cookie: Optional[str] = None        # Cookie（与 apikey 二选一）
    apikey: Optional[str] = None        # API Key
    token: Optional[str] = None
    ua: Optional[str] = None
    rss: Optional[str] = None
    pri: int = 50
    proxy: bool = False
    render: bool = False
    timeout: int = 30
    note: Optional[str] = None


class SiteUpdate(BaseModel):
    """更新站点信息（敏感字段传空字符串表示不修改，由 API 层剔除）"""
    url: Optional[str] = None
    cookie: Optional[str] = None
    apikey: Optional[str] = None
    token: Optional[str] = None
    ua: Optional[str] = None
    rss: Optional[str] = None
    pri: Optional[int] = None
    proxy: Optional[bool] = None
    render: Optional[bool] = None
    timeout: Optional[int] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class SiteOut(BaseModel):
    """站点详情（不含敏感 Cookie）"""
    id: int
    name: str
    domain: str
    url: str
    rss: Optional[str]
    pri: int
    is_active: bool
    public: bool
    proxy: bool
    render: bool
    timeout: int
    note: Optional[str]
    last_checkin: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CheckinOut(BaseModel):
    """签到结果"""
    site_id: int
    site_name: str
    success: bool
    message: str


class SiteTestResult(BaseModel):
    """站点连通性测试结果"""
    success: bool
    message: str
    latency_ms: Optional[int] = None


# ---- 搜索 ----
class TorrentItem(BaseModel):
    """种子搜索结果条目"""
    site_id: int
    site_name: str
    title: str
    description: Optional[str] = None
    enclosure: str                      # 种子下载 URL / 磁力链
    detail_url: Optional[str] = None    # 详情页 URL
    seeders: int = 0
    leechers: int = 0
    downloads: int = 0
    size: int = 0                       # 字节
    pubdate: Optional[str] = None
    free: Optional[str] = None          # 核心优惠标识 (FREE, 2X, etc.)
    hr: bool = False                    # 是否是 H&R 资源
    labels: list[str] = []
    imdb_id: Optional[str] = None
    # 扩展字段：跨站聚合来源
    sources: list[dict] = []


# ---- 订阅 ----
class SubscribeCreate(BaseModel):
    name: str
    year: Optional[str] = None
    tmdb_id: Optional[int] = None
    douban_id: Optional[str] = None
    media_type: str = "movie"
    season: Optional[int] = None
    resolution: Optional[str] = None
    quality: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    min_filesize: int = 0
    max_filesize: int = 0
    sites: Optional[str] = None


class SubscribeOut(BaseModel):
    id: int
    name: str
    year: Optional[str]
    tmdb_id: Optional[int]
    media_type: str
    season: Optional[int]
    state: str
    is_active: bool
    current_episode: int
    total_episode: Optional[int]
    poster: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


# ---- 自动化任务 ----
class AutomationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # transfer, subscribe, cleanup, brush etc.
    trigger: str = "interval"  # interval, cron
    trigger_config: Optional[dict] = None
    task_config: Optional[dict] = None
    is_active: bool = True


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    trigger: Optional[str] = None
    trigger_config: Optional[dict] = None
    task_config: Optional[dict] = None
    is_active: Optional[bool] = None
