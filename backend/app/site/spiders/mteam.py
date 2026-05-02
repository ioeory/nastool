"""
M-Team API 专属爬虫
M-Team 从 2024 年初大量转用自研的 API 进行前后端分离，故不再适用 NexusPHP 通用库
"""
from typing import List, Optional
import httpx
from loguru import logger
from urllib.parse import urljoin

from app.site.spiders.base import BaseSpider
from app.schemas import TorrentItem
from app.utils.url import extract_domain


class MTeamSpider(BaseSpider):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain = extract_domain(self.url)
        # M-Team API 域名一般为 api.{domain} 
        # 用户通常填的大多是 kp.m-team.io
        if self.domain.startswith("kp."):
            self.api_base = f"https://api.{self.domain[3:]}"
        else:
            self.api_base = f"https://api.{self.domain}"

    async def get_client(self):
        headers = {
            "User-Agent": self.ua,
            "x-api-key": self.apikey,
            "Accept": "application/json, text/plain, */*",
        }
        return httpx.AsyncClient(timeout=self.timeout, verify=False, follow_redirects=True, headers=headers)

    async def search(self, keyword: str = "", page: int = 1) -> List[TorrentItem]:
        """
        利用 M-Team Search API
        POST /api/torrent/search
        """
        # M-Team API 中 Page 是 1 基底的
        if page < 1:
            page = 1
            
        url = urljoin(self.api_base, "/api/torrent/search")
        
        payload = {
            "mode": "normal",
            "categories": [],
            "keyword": keyword,
            "pageNumber": page,
            "pageSize": 50
        }
        
        logger.info(f"MTeamSpider [{self.site.name}] 搜索API: {url}")
        
        try:
            async with await self.get_client() as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"/{self.site.name}/ 搜索返回HTTP状态码: {resp.status_code}")
                    return []
                
                data = resp.json()
                if data.get("code") != "0":
                    logger.error(f"/{self.site.name}/ API请求返回错误: {data.get('message')}")
                    return []
                    
                return self._parse_torrents(data.get("data", {}).get("data", []))
                
        except httpx.RequestError as e:
            logger.error(f"/{self.site.name}/ 请求发生错误: {e}")
            return []
        except Exception as e:
            logger.error(f"/{self.site.name}/ JSON 解析失败或其它异常: {e}")
            return []

    def _parse_torrents(self, items: list) -> List[TorrentItem]:
        """把 M-Team JSON 转换成 TorrentItem"""
        torrents: List[TorrentItem] = []
        
        for item in items:
            try:
                torrent_id = item.get("id")
                # 下载链接通常可以直接构造: /api/torrent/genDlToken 根据 ID 拿 token，但这不适合批量爬取提供下载链接。
                # 由于 Mteam 需要 POST GenDlToken，我们在真正的下载阶段才做。这里 enclosure 改用特殊标识。
                download_url = f"mteam_dl://{torrent_id}"
                
                detail_url = urljoin(self.url, f"/detail/{torrent_id}")
                
                raw_cd = (
                    item.get("createdDate")
                    or item.get("created_at")
                    or item.get("created_at_time")
                )
                pubdate_val = str(raw_cd).strip() if raw_cd else None

                t = TorrentItem(
                    site_id=self.site.id,
                    site_name=self.site.name,
                    title=item.get("name", "Unknown"),
                    description=item.get("smallDescr", ""),
                    enclosure=download_url,
                    detail_url=detail_url,
                    seeders=int(item.get("status", {}).get("seeders", 0)),
                    leechers=int(item.get("status", {}).get("leechers", 0)),
                    downloads=int(item.get("status", {}).get("times", 0)),
                    size=int(item.get("size", 0)),
                    pubdate=pubdate_val,
                    free="" # Mteam 现在用折扣代替
                )
                
                # M-Team 打折
                discount = item.get("discount", "")
                if "FREE" in discount:
                    t.free = "FREE"
                elif "50%" in discount:
                    t.free = "50%"
                    
                torrents.append(t)
            except Exception as e:
                logger.debug(f"MTeamSpider parse error: {e}")
                
        return torrents

    async def download_torrent(self, url: str) -> Optional[bytes]:
        """
        处理特殊的 mteam_dl:// 下载链接
        1. POST /api/torrent/genDlToken 取 token
        2. GET 下载流
        """
        if not url.startswith("mteam_dl://"):
            return None
            
        torrent_id = url.split("mteam_dl://")[1]
        token_url = urljoin(self.api_base, "/api/torrent/genDlToken")
        
        try:
            async with await self.get_client() as client:
                # 获取 Token
                # 这里很多 API 默认是 JSON 体，所以尝试 data 还是 json
                token_resp = await client.post(token_url, data={"id": torrent_id})
                if token_resp.status_code != 200:
                    logger.error(f"/{self.site.name}/ genDlToken HTTP报错: {token_resp.status_code} - {token_resp.text}")
                    # 尝试用 json:
                    token_resp_json = await client.post(token_url, json={"id": torrent_id})
                    if token_resp_json.status_code == 200:
                        token_resp = token_resp_json
                    else:
                        return None
                    
                token_data = token_resp.json()
                if token_data.get("code") != "0":
                    logger.error(f"/{self.site.name}/ genDlToken 业务报错: {token_data}")
                    
                    # 再试一次 json= （防止上面返回的其实是 HTTP 200 但业务报错了，比如 form 不支持）
                    token_resp2 = await client.post(token_url, json={"id": str(torrent_id)})
                    if token_resp2.status_code == 200 and token_resp2.json().get("code") == "0":
                        token_data = token_resp2.json()
                    else:
                        return None
                    
                download_url = token_data.get("data")
                if not download_url:
                    logger.error(f"/{self.site.name}/ genDlToken 没有拿到 data")
                    return None
                    
                # 请求文件内容
                logger.debug(f"成功拿到 M-Team 专属下载地址: {download_url}")
                file_resp = await client.get(download_url)
                if file_resp.status_code == 200:
                    return file_resp.content
                else:
                    logger.error(f"获取种子实体失败: {file_resp.status_code} - {file_resp.text}")
                    
        except Exception as e:
            logger.error(f"/{self.site.name}/ 下载种子异常: {e}")
            
        return None

    async def get_user_info(self) -> dict:
        url = urljoin(self.api_base, "/api/member/profile")
        try:
            async with await self.get_client() as client:
                resp = await client.post(url)
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass
        return {}
