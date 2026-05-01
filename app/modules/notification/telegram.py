import httpx
from loguru import logger
from typing import Optional
from app.core.config import settings

class TelegramBot:
    """Telegram 消息推送客户端"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.proxy = settings.proxy if settings.USE_PROXY else None

    async def send_message(self, text: str, image_url: Optional[str] = None) -> bool:
        """发送文本消息，如果有图片则发送图片"""
        if not self.token or not self.chat_id:
            return False
            
        async with httpx.AsyncClient(proxy=self.proxy, timeout=10) as client:
            try:
                if image_url:
                    # 发送图片
                    url = f"{self.base_url}/sendPhoto"
                    res = await client.post(url, data={
                        "chat_id": self.chat_id,
                        "photo": image_url,
                        "caption": text,
                        "parse_mode": "HTML"
                    })
                else:
                    # 发送文本
                    url = f"{self.base_url}/sendMessage"
                    res = await client.post(url, data={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML"
                    })
                
                if res.status_code == 200:
                    return True
                else:
                    logger.error(f"Telegram 推送失败: {res.text}")
                    return False
            except Exception as e:
                logger.error(f"Telegram 推送异常: {e}")
                return False
