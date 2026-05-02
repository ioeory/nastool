import re

def parse_cookie_string(cookie_str: str) -> str:
    """
    将各种格式的 Cookie 转换为标准的 name=value; name2=value2 格式
    支持：
    1. 标准 Cookie 字符串
    2. Netscape HTTP Cookie File (txt 格式)
    """
    if not cookie_str:
        return ""
        
    cookie_str = cookie_str.strip()
    
    # 检查是否是 Netscape 格式
    if cookie_str.startswith("# Netscape") or "\t" in cookie_str:
        return parse_netscape_cookie(cookie_str)
        
    return cookie_str

def parse_netscape_cookie(content: str) -> str:
    """解析 Netscape 格式的 Cookie 内容"""
    cookies = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith("#"):
            continue
            
        parts = line.split("\t")
        # Netscape 格式通常有 7 列: 
        # domain, subdomains, path, secure, expiry, name, value
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            cookies.append(f"{name}={value}")
            
    return "; ".join(cookies)
