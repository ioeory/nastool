import re
from typing import Optional, Dict, Any

class MediaParser:
    """
    媒体信息解析工具
    从种子标题（Torrent Title）中提取标题、年份、分辨率、季集等元数据
    """

    # 常见分辨率正则
    RES_PATTERNS = {
        "2160p": r"2160p|4k|uhd",
        "1080p": r"1080p|fhd",
        "720p": r"720p|hd",
    }

    # 常见质量/来源正则
    QUALITY_PATTERNS = {
        "BluRay": r"bluray|remux",
        "WEB-DL": r"web-dl|web-rip|webrip",
        "HDTV": r"hdtv",
    }

    # 季号解析 (S01, Season 1)
    SEASON_PATTERN = r"s(?:eason)?\s*(\d{1,2})"
    # 集号解析 (E01, Ep 01)
    EPISODE_PATTERN = r"e(?:pisode)?\s*(\d{1,3})"

    @classmethod
    def parse(cls, title: str) -> Dict[str, Any]:
        """
        解析标题返回元数据字典
        """
        result = {
            "raw": title,
            "title": "",
            "year": None,
            "resolution": None,
            "quality": None,
            "season": None,
            "episode": None,
        }

        # 1. 尝试提取年份 (4位数字，通常在括号内或点分隔符后)
        year_match = re.search(r"[\. \(\[]((?:19|20)\d{2})[\. \)\]]", title)
        if year_match:
            result["year"] = int(year_match.group(1))

        # 2. 提取分辨率
        for res, pattern in cls.RES_PATTERNS.items():
            if re.search(pattern, title, re.IGNORECASE):
                result["resolution"] = res
                break

        # 3. 提取质量
        for q, pattern in cls.QUALITY_PATTERNS.items():
            if re.search(pattern, title, re.IGNORECASE):
                result["quality"] = q
                break

        # 4. 提取季集
        s_match = re.search(cls.SEASON_PATTERN, title, re.IGNORECASE)
        if s_match:
            result["season"] = int(s_match.group(1))

        e_match = re.search(cls.EPISODE_PATTERN, title, re.IGNORECASE)
        if e_match:
            result["episode"] = int(e_match.group(1))

        # 5. 提取纯净标题 (简单处理：截取到第一个年份、分辨率或季集标识之前)
        # 这是一个启发式逻辑，实际可能需要更复杂的正则
        clean_title = title
        # 寻找第一个切断点
        cut_index = len(title)
        
        # 检查年份切断
        if year_match:
            cut_index = min(cut_index, year_match.start())
        
        # 检查季号切断
        if s_match:
            cut_index = min(cut_index, s_match.start())
            
        # 检查分辨率切断
        for pattern in cls.RES_PATTERNS.values():
            m = re.search(pattern, title, re.IGNORECASE)
            if m:
                cut_index = min(cut_index, m.start())
                break

        if cut_index > 0:
            clean_title = title[:cut_index]
            # 替换 . 为 空格，去除尾部符号
            clean_title = clean_title.replace(".", " ").strip()
            # 去除可能残留在结尾的 ( [ 等符号
            clean_title = re.sub(r"[\(\[\s\.-]+$", "", clean_title)

        result["title"] = clean_title

        return result
