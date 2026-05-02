"""
站点数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Site(Base):
    """
    PT 站点信息表
    存储用户配置的站点认证信息，与 site/registry.py 的元数据分离
    """
    __tablename__ = "site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # ---- 基础信息（来自 SiteRegistry） ----
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="站点显示名称")
    domain: Mapped[str] = mapped_column(String(200), nullable=False, index=True, unique=True,
                                        comment="主域名（如 m-team.io），用作唯一标识")
    url: Mapped[str] = mapped_column(String(500), nullable=False, comment="站点首页 URL")

    # ---- 认证信息 ----
    cookie: Mapped[Optional[str]] = mapped_column(String(4096), comment="会话 Cookie")
    ua: Mapped[Optional[str]] = mapped_column(String(500), comment="自定义 User-Agent")
    apikey: Mapped[Optional[str]] = mapped_column(String(500), comment="API Key（M-Team 等）")
    token: Mapped[Optional[str]] = mapped_column(String(500), comment="Token")

    # ---- 功能配置 ----
    rss: Mapped[Optional[str]] = mapped_column(String(500), comment="RSS 订阅地址")
    pri: Mapped[int] = mapped_column(Integer, default=50, comment="搜索优先级（数字越小越优先）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否公开站点（无需登录）")

    # ---- 访问配置 ----
    proxy: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否使用代理")
    render: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否启用浏览器渲染（CF 站点）")
    timeout: Mapped[int] = mapped_column(Integer, default=30, comment="请求超时时间（秒）")

    # ---- 流控 ----
    limit_interval: Mapped[int] = mapped_column(Integer, default=0, comment="流控周期（分钟），0=不限制")
    limit_count: Mapped[int] = mapped_column(Integer, default=0, comment="流控周期内最大请求次数")

    # ---- 元数据 ----
    note: Mapped[Optional[str]] = mapped_column(String(500), comment="备注")
    last_checkin: Mapped[Optional[str]] = mapped_column(String(30), comment="最后签到时间")
    created_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        comment="创建时间"
    )
    updated_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        onupdate=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        comment="最后更新时间"
    )

    def __repr__(self) -> str:
        return f"<Site id={self.id} name={self.name} domain={self.domain}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "url": self.url,
            "rss": self.rss,
            "pri": self.pri,
            "is_active": self.is_active,
            "public": self.public,
            "proxy": self.proxy,
            "render": self.render,
            "timeout": self.timeout,
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # 认证信息不在 to_dict 中暴露
        }
