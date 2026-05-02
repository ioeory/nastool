"""
认证 API — 登录、刷新 Token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, create_access_token, get_current_user
from app.db import get_db
from app.db.models.user import User
from app.schemas import Token, Response, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    使用用户名 + 密码获取 JWT Access Token。
    """
    result = await db.execute(select(User).where(User.name == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="账号已被禁用")

    token = create_access_token(data={"sub": user.name})
    return Token(access_token=token)


@router.get("/me", response_model=Response, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return Response(data=UserOut.model_validate(current_user))
