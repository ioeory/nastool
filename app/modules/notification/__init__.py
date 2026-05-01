from typing import Optional
from loguru import logger
from app.core.config import settings
from app.modules.notification.telegram import TelegramBot
from app.modules.notification.wechat import WeChatBot

class NotificationManager:
    """消息分发中心"""
    
    @staticmethod
    async def send_message(
        title: str, 
        message: str, 
        image_url: Optional[str] = None, 
        url: str = ""
    ):
        """同时向已配置的所有通道发送消息"""
        logger.info(f"发送系统通知: {title}")
        
        # 1. Telegram
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            tg = TelegramBot(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID)
            # 拼装 TG 格式
            tg_text = f"<b>{title}</b>\n\n{message}"
            if url:
                tg_text += f"\n\n<a href='{url}'>查看详情</a>"
            await tg.send_message(tg_text, image_url)
            
        # 2. 企业微信
        if settings.WECHAT_CORP_ID and settings.WECHAT_CORP_SECRET:
            wx = WeChatBot(
                settings.WECHAT_CORP_ID, 
                settings.WECHAT_CORP_SECRET, 
                settings.WECHAT_AGENT_ID
            )
            # 企业微信使用卡片消息更美观
            # 简单的 HTML 标签转换
            clean_message = message.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            await wx.send_text_card(title, clean_message, url)

    @classmethod
    async def send_transfer_ok(cls, title: str, category: str, path: str, tmdb_id: Optional[int] = None):
        """搬运成功通知专场"""
        msg_title = f"✅ 资源整理成功: {title}"
        msg_body = f"<b>分类:</b> {category}\n<b>存储路径:</b> {path}"
        
        # 尝试构造详情页地址 (如果配置了域名)
        detail_url = ""
        if settings.APP_DOMAIN:
            # 假设我们有这个路由
            detail_url = f"{settings.APP_DOMAIN}/history"
            
        # 海报地址
        poster_url = None
        if tmdb_id:
            poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg" # 简化版，实际可能需要更准
            
        await cls.send_message(msg_title, msg_body, poster_url, detail_url)

    @classmethod
    async def send_subscribe_found(cls, title: str, site: str):
        """订阅发现通知"""
        msg_title = f"📺 发现订阅资源: {title}"
        msg_body = f"已经在站点 <b>{site}</b> 匹配到记录，已推送到下载队列。"
        await cls.send_message(msg_title, msg_body)

    @classmethod
    async def test_notification(cls, channel: str, config: dict) -> bool:
        """测试特定通道的连通性"""
        title = "NasTool 测试通知"
        message = "这是一条来自 NasTool 的配置测试消息，如果您能看到这条消息，说明配置正确！"
        
        try:
            if channel == "telegram":
                token = config.get("TELEGRAM_BOT_TOKEN")
                chat_id = config.get("TELEGRAM_CHAT_ID")
                if not token or not chat_id:
                    return False
                tg = TelegramBot(token, chat_id)
                return await tg.send_message(f"<b>{title}</b>\n\n{message}")
                
            elif channel == "wechat":
                corpid = config.get("WECHAT_CORP_ID")
                secret = config.get("WECHAT_CORP_SECRET")
                agentid = config.get("WECHAT_AGENT_ID")
                if not corpid or not secret:
                    return False
                wx = WeChatBot(corpid, secret, agentid)
                return await wx.send_text_card(title, message, "")
                
            return False
        except Exception as e:
            logger.error(f"通知测试失败 [{channel}]: {e}")
            return False
