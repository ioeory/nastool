"""
站点统计数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SiteStatistic(Base):
    """站点访问统计表——记录搜索成功/失败次数和响应时间"""
    __tablename__ = "site_statistic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, index=True, unique=True,
                                        comment="站点主域名")

    # ---- 访问统计 ----
    success_count: Mapped[int] = mapped_column(Integer, default=0, comment="成功次数")
    fail_count: Mapped[int] = mapped_column(Integer, default=0, comment="失败次数")
    avg_seconds: Mapped[float] = mapped_column(Float, default=0.0, comment="平均响应时间（秒）")
    last_success: Mapped[Optional[str]] = mapped_column(String(30), comment="最后成功时间")
    last_fail: Mapped[Optional[str]] = mapped_column(String(30), comment="最后失败时间")
    updated_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    def __repr__(self) -> str:
        return f"<SiteStatistic domain={self.domain} ok={self.success_count} fail={self.fail_count}>"
