"""
转移历史记录模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TransferHistory(Base):
    """文件整理历史表——记录每一次文件转移操作"""
    __tablename__ = "transfer_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # ---- 来源信息 ----
    src: Mapped[str] = mapped_column(String(1000), nullable=False, comment="源文件路径")
    dest: Mapped[Optional[str]] = mapped_column(String(1000), comment="目标文件路径")

    # ---- 媒体信息 ----
    title: Mapped[Optional[str]] = mapped_column(String(200), comment="媒体标题")
    year: Mapped[Optional[str]] = mapped_column(String(10), comment="年份")
    media_type: Mapped[Optional[str]] = mapped_column(String(20), comment="类型: movie|tv")
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, comment="TMDB ID")
    season: Mapped[Optional[int]] = mapped_column(Integer, comment="季")
    episode: Mapped[Optional[int]] = mapped_column(Integer, comment="集")

    # ---- 转移配置 ----
    mode: Mapped[str] = mapped_column(String(20), default="hardlink",
                                      comment="转移模式: hardlink|copy|move|softlink")
    downloader: Mapped[Optional[str]] = mapped_column(String(50), comment="来源下载器")
    download_hash: Mapped[Optional[str]] = mapped_column(String(100), index=True,
                                                          comment="种子 Hash")

    # ---- 状态 ----
    success: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否成功")
    errmsg: Mapped[Optional[str]] = mapped_column(String(500), comment="失败原因")

    created_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<TransferHistory id={self.id} title={self.title} success={self.success}>"

class DownloadHistory(Base):
    """自动化下载历史表，追踪防止订阅或 RSS 重复处理"""
    __tablename__ = "download_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    site_id: Mapped[int] = mapped_column(Integer, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), comment="原种标题")
    torrent_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True, comment="种子下载链接或hash")
    status: Mapped[str] = mapped_column(String(50), default="downloading", comment="当前状态")
    size: Mapped[Optional[int]] = mapped_column(Integer, comment="大小")
    created_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        index=True,
    )
    def __repr__(self) -> str:
        return f"<DownloadHistory id={self.id} title={self.title}>"
