"""
用户数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    """用户账号表"""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True,
                                      comment="用户名（登录名）")
    password: Mapped[str] = mapped_column(String(200), nullable=False, comment="bcrypt 哈希密码")
    email: Mapped[Optional[str]] = mapped_column(String(200), comment="邮箱")
    avatar: Mapped[Optional[str]] = mapped_column(String(500), comment="头像 URL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="账号是否启用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")
    note: Mapped[Optional[str]] = mapped_column(String(500), comment="备注（权限描述等）")
    created_at: Mapped[str] = mapped_column(
        String(30),
        default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name} superuser={self.is_superuser}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "avatar": self.avatar,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "note": self.note,
            "created_at": self.created_at,
        }
