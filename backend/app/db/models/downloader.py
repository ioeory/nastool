from sqlalchemy import Column, Integer, String, Boolean
from app.db import Base

class Downloader(Base):
    """
    下载器配置表
    支持无限多个不同类别下载器（qBittorrent / Transmission）
    """
    __tablename__ = "downloader"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True, comment="别名，如 qB主流节点")
    client_type = Column(String(50), nullable=False, default="qbittorrent", comment="qbittorrent 或 transmission")
    host = Column(String(255), nullable=False, comment="连接地址")
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, comment="默认分类")
    save_path = Column(String(255), nullable=True, comment="强制下载路径(可选)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=100, comment="分发优先级，数值越小越优")
    
    # 进阶配置
    auto_category_management = Column(Boolean, default=False, comment="自动分类管理")
    sequential_download = Column(Boolean, default=False, comment="顺序下载")
    force_resume = Column(Boolean, default=False, comment="强制恢复下载")
    first_last_piece_priority = Column(Boolean, default=False, comment="首尾区块优先")
    
    # JSON 结构存储映射表: [{"storage_path": "/x", "download_path": "/y"}]
    path_mapping = Column(String(2000), default="[]", comment="路径映射规则(JSON array)")
