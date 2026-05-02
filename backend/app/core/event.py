"""
事件总线 — 轻量级发布/订阅系统
支持同步和异步事件处理器
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from loguru import logger


class EventType(str, Enum):
    """系统事件类型"""
    # 站点相关
    SITE_ADDED = "site.added"
    SITE_UPDATED = "site.updated"
    SITE_DELETED = "site.deleted"
    SITE_COOKIE_EXPIRED = "site.cookie_expired"

    # 下载相关
    DOWNLOAD_ADDED = "download.added"
    DOWNLOAD_COMPLETED = "download.completed"
    DOWNLOAD_FAILED = "download.failed"

    # 转移相关
    TRANSFER_COMPLETED = "transfer.completed"

    # 订阅相关
    SUBSCRIBE_ADDED = "subscribe.added"
    SUBSCRIBE_COMPLETED = "subscribe.completed"

    # 媒体服务器
    MEDIASERVER_REFRESHED = "mediaserver.refreshed"

    # 系统
    SCHEDULER_RUN = "scheduler.run"
    PLUGIN_LOADED = "plugin.loaded"


@dataclass
class Event:
    """事件数据结构"""
    event_type: EventType
    event_data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


class EventManager:
    """
    事件管理器（单例）
    支持同步 / 异步处理器混合注册
    """
    _instance: Optional["EventManager"] = None
    _handlers: Dict[EventType, List[Callable]] = {}

    def __new__(cls) -> "EventManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def register(self, event_type: EventType, handler: Callable) -> None:
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"EventManager: 注册处理器 {handler.__name__} -> {event_type.value}")

    def unregister(self, event_type: EventType, handler: Callable) -> None:
        """注销事件处理器"""
        if event_type in self._handlers:
            self._handlers[event_type].discard(handler)

    def send_event(self, event_type: EventType, data: Dict[str, Any] = None,
                   source: str = None) -> None:
        """
        发送同步事件
        所有注册的处理器将被顺序调用（异步处理器会在新的事件循环中执行）
        """
        event = Event(event_type=event_type, event_data=data or {}, source=source)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # 在后台线程中运行异步处理器
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(handler(event))
                        else:
                            loop.run_until_complete(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"EventManager: 处理器 {handler.__name__} 执行失败: {e}")

    async def async_send_event(self, event_type: EventType, data: Dict[str, Any] = None,
                               source: str = None) -> None:
        """发送异步事件（在异步上下文中使用）"""
        event = Event(event_type=event_type, event_data=data or {}, source=source)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"EventManager: 异步处理器 {handler.__name__} 执行失败: {e}")


# 全局事件管理器单例
event_manager = EventManager()


def on_event(event_type: EventType):
    """
    装饰器：将函数注册为事件处理器
    用法：
        @on_event(EventType.SITE_UPDATED)
        def handle_site_update(event: Event):
            ...
    """
    def decorator(func: Callable) -> Callable:
        event_manager.register(event_type, func)
        return func
    return decorator
