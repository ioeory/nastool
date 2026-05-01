from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Automation(Base):
    """
    自动化任务（Workflow）模型
    """
    __tablename__ = "automation"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # 任务类型：transfer(整理), subscribe(订阅), cleanup(清理), custom(自定义) 等
    type = Column(String, index=True, nullable=False)
    
    # 触发方式：cron, interval, manual_only
    trigger = Column(String, default="interval")
    
    # 触发配置：JSON格式，针对 interval 存 {"minutes": 5}，针对 cron 存 {"cron": "0 0 * * *"}
    trigger_config = Column(JSON, nullable=True)
    
    # 任务业务配置：JSON格式，针对刷流存选种、删种逻辑参数
    task_config = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class AutomationHistory(Base):
    """
    自动化任务运行历史记录
    """
    __tablename__ = "automation_history"

    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(Integer, index=True)
    name = Column(String)  # 冗余任务名称便于查询
    
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime, nullable=True)
    
    # 状态: success, fail, running
    status = Column(String, default="running")
    message = Column(String, nullable=True)  # 详细结果或错误信息
    
    # 耗时（秒）
    duration = Column(Integer, nullable=True)
