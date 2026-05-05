"""
通用 NexusPHP 站点爬虫
覆盖 90% 以上基于 NexusPHP 框架的国内 PT 站点，例如 HDSky, keepfrds 等
"""
import re
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urljoin, quote

from app.site.spiders.base import BaseSpider
from app.schemas import TorrentItem
from app.utils.url import normalize_url


class NexusPHPSpider(BaseSpider):
    
    async def get_client(self):
        """获取带有默认头信息的 httpx.AsyncClient"""
        headers = {
            "User-Agent": self.ua,
            "Cookie": self.cookie,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        return httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False, headers=headers)

    async def search(self, keyword: str = "", page: int = 0) -> List[TorrentItem]:
        """
        NexusPHP 标准搜索方式，通过 /torrents.php?search=xxx
        """
        search_path = self.meta.get("search_path", "/torrents.php")
        keyword = keyword.strip()
        # 修正：系统统一使用 1-based 页码，而 NexusPHP 需要 0-based
        page_index = max(0, page - 1)
        url = urljoin(self.url, f"{search_path}?search={quote(keyword)}&page={page_index}")
        
        # 融合用户提供的 KeepFrds 示例参数，增强搜索兼容性
        url += "&incldead=1&spstate=0&inclbookmarked=0&search_area=0&search_mode=0"
        
        logger.info(f"NexusPHPSpider [{self.site.name}] 搜索URL: {url}")
        
        html = ""
        try:
            async with await self.get_client() as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"/{self.site.name}/ 搜索返回HTTP状态码: {resp.status_code}")
                    return []
                html = resp.text
                logger.debug(f"/{self.site.name}/ HTML 长度: {len(html)}")
                if "未登录" in html or "login.php" in str(resp.url):
                    logger.warning(f"/{self.site.name}/ Cookie 可能已失效（检测到登录页面转向）")
                    return []
        except httpx.RequestError as e:
            logger.error(f"/{self.site.name}/ 请求发生错误: {e}")
            return []

        return self._parse_torrents(html)

    def _parse_torrents(self, html: str) -> List[TorrentItem]:
        """
        解析 NexusPHP 的 torrents.php HTML
        """
        torrents: List[TorrentItem] = []
        soup = BeautifulSoup(html, "lxml")
        
        # 找到包含种子的表，一般来说是 class="torrents"
        table = soup.find("table", class_="torrents")
        if not table:
            # 有的站点稍微有变种
            tables = soup.find_all("table")
            for t in tables:
                if 'class' in t.attrs and 'torrents' in t.attrs['class']:
                    table = t
                    break
            
            if not table:
                logger.warning(f"[{self.site.name}] 无法定位种子列表 table (class='torrents')，HTML开头: {html[:200]}")
                return []
            else:
                logger.debug(f"[{self.site.name}] 成功定位 table.torrents")

        rows = table.find_all("tr")
        if not rows or len(rows) < 2:
            return []

        # 第一行一般是表头，忽略
        for row in rows[1:]:
            try:
                # td的结构一般来说:
                # 0: 分类图标, 1: 标题名称与下载区, 2: 评论, 3: 发布时间, 4: 容量大小, 5: 种子数, 6: 下载数, 7: 完成数
                # 这是最经典的格式。但也有些有细微不同。
                tds = row.find_all("td", recursive=False)
                if len(tds) < 5:
                    continue
                
                # 查找包含标题的 td，通常其中有 href="details.php..."
                title_td = None
                detail_url = ""
                for td in tds:
                    a_tag = td.find("a", href=re.compile(r"details\.php\?id=\d+"))
                    if a_tag:
                        title_td = td
                        detail_url = urljoin(self.url, a_tag['href'])
                        title_text = a_tag.get('title') or a_tag.get_text(strip=True)
                        break
                        
                if not title_td or not detail_url:
                    continue

                # 提取下载链接
                # 多数是通过 download.php?id=xxx 下载，有些是详情里面才能下
                download_a = title_td.find("a", href=re.compile(r"download\.php\?id=\d+"))
                if download_a:
                    download_url = urljoin(self.url, download_a['href'])
                else:
                    # 获取ID手动组合
                    match = re.search(r"id=(\d+)", detail_url)
                    if match:
                        torrent_id = match.group(1)
                        dl_path = self.meta.get("torrent_path") or "/download.php?id="
                        download_url = urljoin(self.url, f"{dl_path}{torrent_id}")
                    else:
                        download_url = ""

                # 提取描述（通常在标题旁边的 span 或直接在下方的某个节点中）
                # 这是非常依赖具体站点的，这里做个通用匹配
                desc = ""
                sub_title_node = title_td.find("span", class_=lambda x: x and ("subtitle" in x or "torrentname" in x))
                if sub_title_node:
                    desc = sub_title_node.get_text(strip=True)

                # 提取促销标记 "free", "50%", "2x" 等
                free_text = ""
                # 提取 H&R
                is_hr = False
                
                # 遍历 title_td 中的所有图片和 span 来获取图标信息
                icons = title_td.find_all(["img", "span"], class_=True)
                for icon in icons:
                    cls = " ".join(icon.get("class", [])).lower()
                    title_attr = icon.get("title", "").lower()
                    alt_attr = icon.get("alt", "").lower()
                    
                    text_content = ""
                    if icon.name == "span":
                        text = icon.get_text(strip=True).lower()
                        # 判断是否为促销标签的特征，避免将搜索高亮的标题误判为促销
                        is_promo_tag = False
                        if "促" in title_attr or "promotion" in title_attr:
                            is_promo_tag = True
                        elif "tag" in cls or "label" in cls or "badge" in cls or "pro" in cls:
                            is_promo_tag = True
                        elif text in ["free", "2xfree", "50%", "30%", "2x"]:
                            # 排除常见的搜索高亮 class
                            if "high" not in cls and "match" not in cls and "key" not in cls:
                                is_promo_tag = True
                                
                        if is_promo_tag and len(text) < 20:
                            text_content = text

                    combined_info = f"{cls} {title_attr} {alt_attr} {text_content}"
                    
                    # 识别 H&R
                    if "hitrun" in combined_info or "h&r" in combined_info:
                        is_hr = True
                    # 识别优惠
                    if "twoupfree" in combined_info or "2xfree" in combined_info or "free2up" in combined_info:
                        free_text = "2XFREE"
                    elif "free" in combined_info:
                        free_text = "FREE"
                    elif "twoup" in combined_info or "2x" in combined_info:
                        free_text = "2X"
                    elif "halfdown" in combined_info or "50%" in combined_info:
                        free_text = "50%"
                    elif "thirtypercent" in combined_info or "30%" in combined_info:
                        free_text = "30%"

                # 文件大小，一般是含有 MB, GB, TB 的文本
                size_bytes = 0
                size_str = ""
                for td in tds[2:]:
                    text = td.get_text(strip=True).upper()
                    if any(x in text for x in ["MB", "GB", "TB", "KB"]):
                        size_str = text
                        break
                size_bytes = self._parse_size(size_str)

                # 发布时间（常见于 td[title="YYYY-MM-DD hh:mm:ss"]，用于刷流「发布时间」筛选）
                pubdate_str = None
                for td in tds:
                    tit = (td.get("title") or "").strip()
                    if tit and re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", tit):
                        pubdate_str = tit
                        break
                
                # 做种数（Seeders）
                seeders = 0
                for td in reversed(tds):
                    # 做种数通常是最右边的数字之一，通常有箭头或颜色标记，或 a 标签包含 peerlist
                    a_tag = td.find("a", href=re.compile("peerlist"))
                    if a_tag:
                        # 这是 seeders 或是 leechers，第一个 peerlist 通常是 seeders
                        num = re.sub(r"\D", "", a_tag.get_text(strip=True))
                        if num:
                            seeders = int(num)
                            break
                    else:
                        # 有些没有a标签
                        num_match = re.match(r"^\d+$", td.get_text(strip=True))
                        if num_match:
                            seeders = int(num_match.group(0))

                item = TorrentItem(
                    site_id=self.site.id,
                    site_name=self.site.name,
                    title=title_text,
                    description=desc,
                    enclosure=download_url,
                    detail_url=detail_url,
                    seeders=seeders,
                    size=size_bytes,
                    pubdate=pubdate_str,
                    free=free_text,
                    hr=is_hr
                )
                torrents.append(item)
            except Exception as e:
                logger.debug(f"NexusPHPSpider 解析行失败: {e}")
                continue

        return torrents

    def _parse_size(self, size_str: str) -> int:
        """解析字符串大小为主流的 bytes 大小"""
        if not size_str:
            return 0
        try:
            size_str = size_str.upper().replace(',', '')
            match = re.search(r"([\d\.]+)\s*(MB|GB|TB|KB)", size_str)
            if not match:
                return 0
            num = float(match.group(1))
            unit = match.group(2)
            if unit == "TB": return int(num * 1024**4)
            if unit == "GB": return int(num * 1024**3)
            if unit == "MB": return int(num * 1024**2)
            if unit == "KB": return int(num * 1024)
            return int(num)
        except Exception:
            return 0

    async def download_torrent(self, url: str) -> Optional[bytes]:
        try:
            async with await self.get_client() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.content
                else:
                    logger.error(f"下载种子失败 {url}: 状态码 {resp.status_code}")
        except Exception as e:
            logger.error(f"下载种子异常 {url}: {e}")
        return None

    async def get_user_info(self) -> dict:
        """NexusPHP 解析用户主页，通常用于自动登录检测和拿数据"""
        # 一般在 index.php 或 userdetails.php 可以找到数据
        # 这里简化为测试连接使用
        return {"status": "ok"}
