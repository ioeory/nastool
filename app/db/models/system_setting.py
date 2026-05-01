from sqlalchemy import Column, Integer, String, Text, Boolean
from app.db import Base

class SystemSetting(Base):
    """
    系统配置表
    用于动态存储前端配置的所有核心变量，脱离 .env 的只读限制
    """
    __tablename__ = "system_setting"

    key = Column(String(100), primary_key=True, index=True, comment="配置键名,如 TMDB_API_KEY")
    value = Column(Text, nullable=True, comment="配置项值,以字符串形式存取")
    description = Column(String(255), nullable=True, comment="注释")
