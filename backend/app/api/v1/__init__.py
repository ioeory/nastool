"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1 import auth, site, system, search, downloader, subscribe, tmdb, automation, history

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(site.router)
api_router.include_router(system.router)
api_router.include_router(search.router)
api_router.include_router(downloader.router)
api_router.include_router(subscribe.router)
api_router.include_router(tmdb.router)
api_router.include_router(automation.router)
api_router.include_router(history.router)
