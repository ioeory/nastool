"""
订阅数据模型（自动追剧/追电影）
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Subscribe(Base):
    """订阅表 — 记录用户想要自动下载的影视"""
    __tablename__ = "subscribe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # ---- 媒体信息 ----
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="媒体名称")
    keyword: Mapped[Optional[str]] = mapped_column(String(200), comment="搜索关键字")
    year: Mapped[Optional[str]] = mapped_column(String(10), comment="年份")
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="TMDB ID")
    douban_id: Mapped[Optional[str]] = mapped_column(String(50), comment="豆瓣 ID")
    media_type: Mapped[str] = mapped_column(String(20), default="movie",
                                            comment="类型: movie | tv")
    # 剧集专用
    season: Mapped[Optional[int]] = mapped_column(Integer, comment="季数（剧集）")
    episode: Mapped[Optional[int]] = mapped_column(Integer, comment="起始集数（剧集）")
    total_episode: Mapped[Optional[int]] = mapped_column(Integer, comment="总集数")
    current_episode: Mapped[int] = mapped_column(Integer, default=0, comment="已下载集数")

    # ---- 过滤规则 ----
    resolution: Mapped[Optional[str]] = mapped_column(String(50), comment="分辨率过滤（如 1080p,2160p）")
    quality: Mapped[Optional[str]] = mapped_column(String(100), comment="质量过滤（如 BluRay,WEB-DL）")
    release_group: Mapped[Optional[str]] = mapped_column(String(200), comment="制作组过滤")
    include: Mapped[Optional[str]] = mapped_column(String(500), comment="包含关键词（正则）")
    exclude: Mapped[Optional[str]] = mapped_column(String(500), comment="排除关键词（正则）")
    min_filesize: Mapped[int] = mapped_column(Integer, default=0, comment="最小文件大小（MB）")
    max_filesize: Mapped[int] = mapped_column(Integer, default=0, comment="最大文件大小（MB），0=不限")

    # ---- 下载配置 ----
    downloader: Mapped[Optional[str]] = mapped_column(String(50), comment="指定下载器（留空使用默认）")
    save_path: Mapped[Optional[str]] = mapped_column(String(500), comment="指定保存路径（留空使用默认）")
    sites: Mapped[Optional[str]] = mapped_column(String(500), comment="限定搜索站点（逗号分隔 domain）")

    # ---- 状态 ----
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用订阅")
    state: Mapped[str] = mapped_column(String(20), default="pending",
                                       comment="状态: pending|downloading|completed|error")
    last_update: Mapped[Optional[str]] = mapped_column(String(30), comment="最后更新时间")

    # ---- 元数据 ----
    poster: Mapped[Optional[str]] = mapped_column(String(500), comment="海报 URL")
    backdrop: Mapped[Optional[str]] = mapped_column(String(500), comment="背景图 URL")
    vote: Mapped[Optional[float]] = mapped_column(comment="评分")
    description: Mapped[Optional[str]] = mapped_column(String(2000), comment="简介")
    created_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    note: Mapped[Optional[str]] = mapped_column(String(500), comment="备注")

    def __repr__(self) -> str:
        return f"<Subscribe id={self.id} name={self.name} type={self.media_type}>"
