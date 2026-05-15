"""
M-Team API 专属爬虫
M-Team 从 2024 年初大量转用自研的 API 进行前后端分离，故不再适用 NexusPHP 通用库

Search 返回体结构见 github.com/sagan/ptool/site/mtorrent/types.go：
  - 优惠在 status.discount，取值如 FREE / PERCENT_50 / PERCENT_70 / NORMAL
"""
from typing import Any, List, Optional
import httpx
import re
from loguru import logger
from urllib.parse import urljoin

from app.site.spiders.base import BaseSpider
from app.schemas import TorrentItem
from app.utils.url import extract_domain

# 部署校验哨兵：启动后第一时间在日志里输出，证明本文件版本已被加载
logger.warning("[MTeamSpider] module loaded build=2026-05-15-debug-logs")


def _int_safe(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _flatten_promo_values(val: Any, out: List[str]) -> None:
    """把 labels / promotionRule 等嵌套结构压成字符串片段，供子串匹配。"""
    if val is None:
        return
    if isinstance(val, bool):
        return
    if isinstance(val, (str, int, float)):
        s = str(val).strip()
        if s:
            out.append(s)
        return
    if isinstance(val, dict):
        for v in val.values():
            _flatten_promo_values(v, out)
        return
    if isinstance(val, (list, tuple)):
        for v in val:
            _flatten_promo_values(v, out)


def _normalize_status(item: dict) -> dict:
    """
    统一取出 M-Team 条目的 status 字典。
    部分响应里做种人数在顶层；极少数情况下字段形态异常时尽量降级为 dict。
    """
    raw = item.get("status")
    if isinstance(raw, dict):
        st = dict(raw)
    else:
        st = {}
    # 顶层兜底（与 API 文档不一致时的兼容）
    if "seeders" not in st and item.get("seeders") is not None:
        st["seeders"] = item.get("seeders")
    if "leechers" not in st and item.get("leechers") is not None:
        st["leechers"] = item.get("leechers")
    if "times" not in st and item.get("times") is not None:
        st["times"] = item.get("times")
    if "discount" not in st and item.get("discount") is not None:
        st["discount"] = item.get("discount")
    return st


def _discount_token(raw: Any) -> str:
    """将 API 中的 discount 原始值规范成可与枚举比对的大写字符串。"""
    if raw is None:
        return ""
    if raw is True:
        return "FREE"
    if raw is False:
        return ""
    if isinstance(raw, (int, float)):
        return str(int(raw)).strip().upper()
    return str(raw).strip().upper()


def _promo_search_blob(item: dict, status: dict) -> str:
    parts: List[str] = []
    for key in ("discount",):
        v = status.get(key)
        if v is not None and str(v).strip():
            parts.append(str(v).strip())
        v2 = item.get(key)
        if v2 is not None and str(v2).strip() and str(v2).strip() != str(v).strip():
            parts.append(str(v2).strip())
    for key in ("promotionRule", "promotion_rule"):
        raw = status.get(key) or item.get(key)
        _flatten_promo_values(raw, parts)
    for key in ("labels", "labelsNew", "labels_new"):
        _flatten_promo_values(item.get(key), parts)
    return " ".join(parts).upper()


def _resolve_free_from_mteam_item(item: dict) -> str:
    """
    将 API 条目映射为刷流使用的 t.free：FREE / 2XFREE / 50% / 30% / "" 。
    优先识别 2XFREE（常出现在 labels），再识别 status.discount 枚举，最后对合并文本做子串匹配。
    """
    status = _normalize_status(item)
    sd = _discount_token(status.get("discount"))
    td = _discount_token(item.get("discount"))
    primary = sd or td
    blob = _promo_search_blob(item, status)
    compact = blob.replace(" ", "").replace("_", "")

    # API 折扣字串见 sagan/ptool site/mtorrent/mtorrent.go downloadMultipliers（含下划线形式）
    if "2XFREE" in compact:
        return "2XFREE"

    enum_map = {
        "FREE": "FREE",
        "_2X_FREE": "2XFREE",
        "PERCENT_50": "50%",
        "_2X_PERCENT_50": "50%",
        "PERCENT_70": "30%",
    }
    if primary in enum_map:
        return enum_map[primary]

    if "PERCENT_50" in blob or "50%" in blob:
        return "50%"
    if "PERCENT_70" in blob or "30%" in blob:
        return "30%"
    if "FREE" in blob:
        return "FREE"
    return ""


def _extract_torrent_id_from_url(url: str) -> Optional[str]:
    text = str(url or "").strip()
    if not text:
        return None
    if text.startswith("mteam_dl://"):
        torrent_id = text.split("mteam_dl://", 1)[1].strip()
        return torrent_id or None

    patterns = (
        r"[?&](?:tid|torrent_id|torrentId|id)=(\d+)",
        r"/detail/(\d+)",
        r"/torrent/(\d+)",
        r"/download/(\d+)",
        r"/(\d+)(?:[/?#]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


_SENSITIVE_QS = ("sign", "passkey", "uid", "token", "auth")


def _redact_url(url: str) -> str:
    """脱敏 URL 中的 sign/passkey/uid/token 等参数，方便日志输出。"""
    text = str(url or "")
    if not text:
        return text
    for key in _SENSITIVE_QS:
        text = re.sub(
            rf"({key}=)([^&#\s]+)",
            lambda m: f"{m.group(1)}***{m.group(2)[-4:] if len(m.group(2)) > 4 else ''}",
            text,
            flags=re.IGNORECASE,
        )
    return text


def _preview_bytes(data: bytes, limit: int = 200) -> str:
    if not data:
        return "<empty>"
    sample = data[:limit]
    try:
        text = sample.decode("utf-8", errors="replace")
    except Exception:
        text = repr(sample)
    return text.replace("\n", "\\n").replace("\r", "\\r")


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

        与 ptool GetLatestTorrents 一致：同时请求 **normal + adult**，否则成人区种子不会出现在结果中，
        刷流会表现为「站上有 FREE、API 却永远匹配不到」。
        """
        if page < 1:
            page = 1

        url = urljoin(self.api_base, "/api/torrent/search")
        logger.info(
            f"MTeamSpider [{self.site.name}] 搜索API: {url} "
            f"(page={page}, modes=normal+adult)"
        )

        merged: dict[str, dict] = {}
        try:
            async with await self.get_client() as client:
                for mode in ("normal", "adult"):
                    payload = {
                        "mode": mode,
                        "categories": [],
                        "keyword": keyword,
                        "pageNumber": page,
                        "pageSize": 50,
                    }
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        logger.warning(
                            f"/{self.site.name}/ 搜索 mode={mode} HTTP {resp.status_code}"
                        )
                        continue
                    data = resp.json()
                    if str(data.get("code")) != "0":
                        logger.warning(
                            f"/{self.site.name}/ 搜索 mode={mode} 业务错误: {data.get('message')}"
                        )
                        continue
                    rows = data.get("data", {}).get("data", []) or []
                    for row in rows:
                        rid = row.get("id")
                        if rid is None:
                            continue
                        merged[str(rid)] = row

            items = list(merged.values())
            logger.info(
                f"MTeamSpider [{self.site.name}] 合并去重后 {len(items)} 条 "
                f"(normal+adult 各最多 50)"
            )
            return self._parse_torrents(items)

        except httpx.RequestError as e:
            logger.error(f"/{self.site.name}/ 请求发生错误: {e}")
            return []
        except Exception as e:
            logger.error(f"/{self.site.name}/ JSON 解析失败或其它异常: {e}")
            return []

    def _parse_torrents(self, items: list) -> List[TorrentItem]:
        """把 M-Team JSON 转换成 TorrentItem"""
        torrents: List[TorrentItem] = []

        for idx, item in enumerate(items):
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

                st = _normalize_status(item)

                t = TorrentItem(
                    site_id=self.site.id,
                    site_name=self.site.name,
                    title=item.get("name", "Unknown"),
                    description=item.get("smallDescr", ""),
                    enclosure=download_url,
                    detail_url=detail_url,
                    seeders=_int_safe(st.get("seeders")),
                    leechers=_int_safe(st.get("leechers")),
                    downloads=_int_safe(st.get("times")),
                    size=_int_safe(item.get("size")),
                    pubdate=pubdate_val,
                    free=_resolve_free_from_mteam_item(item),
                )

                if idx == 0:
                    logger.info(
                        f"MTeamSpider 首条样例: raw.discount={item.get('discount')!r} "
                        f"status.discount={st.get('discount')!r} -> free={t.free!r} "
                        f"size={t.size} seeders={t.seeders}"
                    )
                elif idx < 3:
                    logger.debug(
                        f"MTeamSpider parse[{idx}] title={t.title!r} "
                        f"status.discount={st.get('discount')!r} free={t.free!r} "
                        f"seeders={t.seeders} size={t.size}"
                    )

                torrents.append(t)
            except Exception as e:
                logger.debug(f"MTeamSpider parse error: {e}")
                
        return torrents

    async def download_torrent(self, url: str) -> Optional[bytes]:
        """
        优先从 URL 中提取 torrent id 并通过 genDlToken 换取真实下载地址；
        若无法提取 id，再回退到 RSS/HTML 中的直链请求。
        全程打印详细 debug 日志，便于排查 “种子文件为空” 的根因。
        """
        site_tag = f"/{self.site.name}/"
        safe_input = _redact_url(url)
        logger.warning(f"{site_tag} >>> MTeamSpider.download_torrent 入参 url={safe_input!r}")

        try:
            async with await self.get_client() as client:
                torrent_id = _extract_torrent_id_from_url(url)
                logger.warning(
                    f"{site_tag} 解析 torrent_id={torrent_id!r} "
                    f"(来源: {'mteam_dl' if str(url).startswith('mteam_dl://') else 'url-pattern'})"
                )

                if torrent_id:
                    token_url = urljoin(self.api_base, "/api/torrent/genDlToken")
                    logger.warning(f"{site_tag} 请求 genDlToken: POST {token_url} id={torrent_id}")

                    # 先尝试 form
                    token_resp = await client.post(token_url, data={"id": torrent_id})
                    logger.warning(
                        f"{site_tag} genDlToken[form] resp status={token_resp.status_code} "
                        f"len={len(token_resp.content or b'')} "
                        f"content-type={token_resp.headers.get('content-type','')!r} "
                        f"body={token_resp.text[:500]!r}"
                    )
                    if token_resp.status_code != 200:
                        # 再试 json
                        logger.warning(f"{site_tag} genDlToken[form] HTTP 非 200，尝试 json 体重试")
                        token_resp_json = await client.post(token_url, json={"id": torrent_id})
                        logger.info(
                            f"{site_tag} genDlToken[json] resp status={token_resp_json.status_code} "
                            f"body={token_resp_json.text[:500]!r}"
                        )
                        if token_resp_json.status_code == 200:
                            token_resp = token_resp_json
                        else:
                            logger.error(f"{site_tag} genDlToken 两种请求体均失败，放弃")
                            return None

                    try:
                        token_data = token_resp.json()
                    except Exception as je:
                        logger.error(
                            f"{site_tag} genDlToken 响应不是合法 JSON: {je}; "
                            f"raw={token_resp.text[:500]!r}"
                        )
                        return None

                    if str(token_data.get("code")) != "0":
                        logger.warning(
                            f"{site_tag} genDlToken 业务码非 0: code={token_data.get('code')!r} "
                            f"message={token_data.get('message')!r} -> 用 json 体再试一次"
                        )
                        token_resp2 = await client.post(token_url, json={"id": str(torrent_id)})
                        logger.info(
                            f"{site_tag} genDlToken[json-retry] status={token_resp2.status_code} "
                            f"body={token_resp2.text[:500]!r}"
                        )
                        try:
                            token_data2 = token_resp2.json() if token_resp2.status_code == 200 else None
                        except Exception:
                            token_data2 = None
                        if token_data2 and str(token_data2.get("code")) == "0":
                            token_data = token_data2
                        else:
                            logger.error(f"{site_tag} genDlToken 业务失败，放弃; data={token_data}")
                            return None

                    download_url = token_data.get("data")
                    if not download_url:
                        logger.error(
                            f"{site_tag} genDlToken 响应缺少 data 字段: {token_data!r}"
                        )
                        return None

                    logger.info(
                        f"{site_tag} 取得真实下载地址: {_redact_url(download_url)}"
                    )
                    file_resp = await client.get(download_url)
                    ctype = file_resp.headers.get("content-type", "")
                    clen = file_resp.headers.get("content-length", "")
                    logger.warning(
                        f"{site_tag} 下载实体响应 status={file_resp.status_code} "
                        f"content-length={clen!r} content-type={ctype!r} "
                        f"body_bytes={len(file_resp.content or b'')}"
                    )

                    if file_resp.status_code != 200:
                        logger.error(
                            f"{site_tag} 下载实体 HTTP 非 200: {file_resp.status_code} "
                            f"body_preview={_preview_bytes(file_resp.content)!r}"
                        )
                        return None
                    if not file_resp.content:
                        logger.error(f"{site_tag} 下载实体响应体为空 (Content-Length={clen!r})")
                        return None
                    # 简单校验：BitTorrent v1 文件以 'd' 开头 (bencoded dict)
                    head = file_resp.content[:1]
                    if head != b"d":
                        logger.warning(
                            f"{site_tag} 实体首字节非 bencoded dict ({head!r})，可能拿到的是 HTML/JSON。"
                            f" preview={_preview_bytes(file_resp.content)!r}"
                        )
                    else:
                        logger.info(f"{site_tag} 下载完成，大小={len(file_resp.content)} bytes")
                    return file_resp.content

                # 无法提取 id：当作 RSS 直链 / HTML 下载链接处理
                logger.warning(f"{site_tag} 未能提取 torrent_id，回退直链下载: {safe_input}")
                file_resp = await client.get(url)
                ctype = file_resp.headers.get("content-type", "")
                clen = file_resp.headers.get("content-length", "")
                logger.warning(
                    f"{site_tag} 直链响应 status={file_resp.status_code} "
                    f"content-length={clen!r} content-type={ctype!r} "
                    f"body_bytes={len(file_resp.content or b'')}"
                )
                if file_resp.status_code != 200 or not file_resp.content:
                    logger.error(
                        f"{site_tag} 直链下载失败: status={file_resp.status_code} "
                        f"body_preview={_preview_bytes(file_resp.content)!r}"
                    )
                    return None
                head = file_resp.content[:1]
                if head != b"d":
                    logger.warning(
                        f"{site_tag} 直链返回首字节非 bencoded dict ({head!r})，可能是登录页/JSON。"
                        f" preview={_preview_bytes(file_resp.content)!r}"
                    )
                return file_resp.content

        except Exception as e:
            logger.exception(f"{site_tag} 下载种子异常: {e}")

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
