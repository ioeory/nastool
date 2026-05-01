import httpx
from loguru import logger
from typing import Optional, Dict
from app.core.config import settings

class WeChatBot:
    """企业微信消息推送客户端"""
    
    _access_token_cache: Dict[str, str] = {}

    def __init__(self, corp_id: str, secret: str, agent_id: str):
        self.corp_id = corp_id
        self.secret = secret
        self.agent_id = agent_id

    async def _get_access_token(self) -> Optional[str]:
        """获取企业微信 AccessToken"""
        cache_key = f"{self.corp_id}_{self.secret}"
        if cache_key in self._access_token_cache:
            return self._access_token_cache[cache_key]
            
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                res = await client.get(url, params=params)
                data = res.json()
                if data.get("errcode") == 0:
                    token = data.get("access_token")
                    self._access_token_cache[cache_key] = token
                    return token
                else:
                    logger.error(f"获取微信 AccessToken 失败: {data.get('errmsg')}")
                    return None
            except Exception as e:
                logger.error(f"获取微信 AccessToken 异常: {e}")
                return None

    async def send_text_card(self, title: str, description: str, url: str = "", btn_txt: str = "详情") -> bool:
        """发送卡片消息消息 (最美观)"""
        if not self.corp_id or not self.secret or not self.agent_id:
            return False
            
        token = await self._get_access_token()
        if not token:
            return False
            
        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        payload = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btn_txt
            },
            "safe": 0
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                res = await client.post(api_url, json=payload)
                data = res.json()
                if data.get("errcode") == 0:
                    return True
                else:
                    logger.error(f"微信推送失败: {data.get('errmsg')}")
                    return False
            except Exception as e:
                logger.error(f"微信推送异常: {e}")
                return False
                
    async def send_message(self, text: str) -> bool:
        """发送纯文本消息"""
        token = await self._get_access_token()
        if not token: return False
        
        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        payload = {
            "touser": "@all", "msgtype": "text", "agentid": self.agent_id,
            "text": {"content": text}, "safe": 0
        }
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(api_url, json=payload)
            return res.json().get("errcode") == 0
