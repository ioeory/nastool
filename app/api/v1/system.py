"""
系统信息 API
"""
import platform
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import APIRouter, Depends
from datetime import datetime, time

from app.core.config import settings
from app.core.security import get_current_user
from app.db import get_db
from app.schemas import Response

router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/info", response_model=Response, summary="获取系统信息")
async def system_info(_=Depends(get_current_user)):
    return Response(data={
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "python_version": sys.version,
        "platform": platform.platform(),
        "db_type": settings.DB_TYPE,
        "debug": settings.DEBUG,
    })
    

@router.get("/stats", response_model=Response, summary="获取系统实时统计数据")
async def get_system_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """返回仪表盘所需的统计指标"""
    from app.db.models.site import Site
    from app.db.models.subscribe import Subscribe
    from app.db.models.history import TransferHistory, DownloadHistory
    
    # 1. 活跃站点数
    active_sites = await db.scalar(select(func.count()).select_from(Site).where(Site.is_active == True))
    
    # 2. 订阅规则总数
    total_subs = await db.scalar(select(func.count()).select_from(Subscribe))
    
    # 3. 累计搬运成功总数
    total_transfers = await db.scalar(select(func.count()).select_from(TransferHistory).where(TransferHistory.success == True))
    
    # 4. 总下载历史
    total_downloads = await db.scalar(select(func.count()).select_from(DownloadHistory))
    
    # 5. 今日整理成功数
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_transfers = await db.scalar(
        select(func.count())
        .select_from(TransferHistory)
        .where(TransferHistory.success == True)
        .where(TransferHistory.created_at >= today_start)
    )
    
    return Response(data={
        "active_sites": active_sites or 0,
        "total_subscribes": total_subs or 0,
        "total_transfers": total_transfers or 0,
        "total_downloads": total_downloads or 0,
        "today_transfers": today_transfers or 0
    })


@router.get("/settings", response_model=Response, summary="获取系统配置")
async def get_settings(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """获取所有动态配置的系统变量"""
    from sqlalchemy import select
    from app.db.models.system_setting import SystemSetting
    
    # 允许动态配置的键白名单
    allowed_keys = [
        "QB_HOST", "QB_USERNAME", "QB_PASSWORD", "QB_CATEGORY", "LIBRARY_PATH",
        "PROXY_HOST", "USE_PROXY", "TMDB_API_KEY", "EMBY_HOST", "EMBY_API_KEY",
        "JELLYFIN_HOST", "JELLYFIN_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "WECHAT_CORP_ID", "WECHAT_CORP_SECRET", "WECHAT_AGENT_ID", "COOKIECLOUD_HOST",
        "COOKIECLOUD_KEY", "COOKIECLOUD_PASSWORD"
    ]
    
    # 默认值回退到 settings 中的 fallback
    result_data = {k: getattr(settings, k) for k in allowed_keys if hasattr(settings, k)}
    
    # 从数据库中叠加覆盖
    stmt = select(SystemSetting).where(SystemSetting.key.in_(allowed_keys))
    db_items = (await db.scalars(stmt)).all()
    for item in db_items:
        # 类型简单的还原
        if item.value is not None:
            if item.value in ["true", "True", "1"]:
                result_data[item.key] = True
            elif item.value in ["false", "False", "0"]:
                result_data[item.key] = False
            else:
                try:
                    # 尝试转换回数字（如果原封不动就是数字格式）
                    result_data[item.key] = int(item.value) if item.value.isdigit() else item.value
                except ValueError:
                    result_data[item.key] = item.value

    return Response(data=result_data)


@router.post("/settings", response_model=Response, summary="修改系统配置并在内存生效")
async def update_settings(data: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """保存配置到 SQLite DB 并热更新 settings 实例"""
    from sqlalchemy import select
    from app.db.models.system_setting import SystemSetting
    
    for k, v in data.items():
        if not hasattr(settings, k):
            continue
            
        val_str = str(v) if v is not None else ""
        bool_conversion = val_str.lower() in ["true", "1", "yes"] if isinstance(v, bool) else val_str
        mapped_val_str = "True" if isinstance(v, bool) and v else ("False" if isinstance(v, bool) else val_str)
        
        # 写入数据库 (Upsert 逻辑)
        stmt = select(SystemSetting).where(SystemSetting.key == k)
        existing = await db.scalar(stmt)
        if existing:
            existing.value = mapped_val_str
        else:
            new_set = SystemSetting(key=k, value=mapped_val_str, description="")
            db.add(new_set)
            
        # 根据类型转换并热更新单例（简单类型处理）
        current_val = getattr(settings, k)
        if isinstance(current_val, bool):
            setattr(settings, k, v)
        elif isinstance(current_val, int):
            setattr(settings, k, int(v) if v else 0)
        else:
            setattr(settings, k, val_str)
            
    await db.commit()
    return Response(message="配置已保存并生效")


@router.post("/test_qb", response_model=Response, summary="测试 qBittorrent 连接")
async def test_qbittorrent(data: dict, _=Depends(get_current_user)):
    """测试下载器连接"""
    import httpx
    
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    
    if not host:
        return Response(code=1, message="未填写 qBittorrent 地址")
        
    url = f"{host.rstrip('/')}/api/v2/auth/login"
    login_data = {"username": username, "password": password}
    
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            res = await client.post(url, data=login_data)
            
        if "Ok" in res.text:
            return Response(message="连接 qBittorrent 成功")
        else:
            return Response(code=1, message=f"连接失败：用户名或密码错误")
    except Exception as e:
        return Response(code=1, message=f"连接异常：{str(e)}")


@router.post("/test_notification", response_model=Response, summary="测试通知连通性")
async def test_notification(data: dict, _=Depends(get_current_user)):
    """测试 Telegram / 企业微信配置"""
    from app.modules.notification import NotificationManager
    
    channel = data.get("channel")
    config = data.get("config", {})
    
    if not channel:
        return Response(code=1, message="未指定通知通道")
        
    success = await NotificationManager.test_notification(channel, config)
    if success:
        return Response(message=f"{channel.capitalize()} 测试消息发送成功，请检查手机！")
    else:
        return Response(code=1, message=f"{channel.capitalize()} 测试发送失败，请检查配置或日志。")


@router.get("/health", summary="健康检查（无需认证）")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
