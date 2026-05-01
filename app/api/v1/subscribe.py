from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db import get_db
from app.db.models.subscribe import Subscribe
from app.schemas import Response

router = APIRouter(prefix="/subscribe", tags=["订阅"])

@router.get("/", response_model=Response, summary="获取订阅列表")
async def list_subscribes(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Subscribe).order_by(Subscribe.created_at.desc()))
    subs = result.scalars().all()
    return Response(data=[
        {
            "id": s.id,
            "name": s.name,
            "keyword": s.keyword,
            "is_active": s.is_active,
            "note": s.note
        } for s in subs
    ])

@router.post("/", response_model=Response, summary="添加订阅")
async def add_subscribe(data: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    if not data.get("name") or not data.get("keyword"):
        return Response(code=1, message="名称和关键字必填")
        
    s = Subscribe(
        name=data["name"],
        keyword=data["keyword"],
        is_active=data.get("is_active", True),
        note=data.get("note")
    )
    db.add(s)
    await db.commit()
    return Response(message="订阅添加成功")

@router.patch("/{id}", response_model=Response, summary="修改订阅")
async def update_subscribe(id: int, data: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    s = await db.scalar(select(Subscribe).where(Subscribe.id == id))
    if not s:
        return Response(code=1, message="订阅不存在")
        
    for k, v in data.items():
        if hasattr(s, k) and k != "id":
            setattr(s, k, v)
    await db.commit()
    return Response(message="订阅修改成功")

@router.delete("/{id}", response_model=Response, summary="删除订阅")
async def delete_subscribe(id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    s = await db.scalar(select(Subscribe).where(Subscribe.id == id))
    if not s:
        return Response(code=1, message="订阅不存在")
    await db.delete(s)
    await db.commit()
    return Response(message="订阅删除成功")
