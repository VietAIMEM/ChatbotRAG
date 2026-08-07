from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_login_rate_limit, get_current_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.admin import Admin
from app.schemas.auth import AdminOut, ChangePasswordRequest, LoginRequest, LoginResponse

router = APIRouter(tags=["admin-auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await check_admin_login_rate_limit(request)
    from sqlalchemy import select

    result = await db.execute(select(Admin).where(Admin.username == payload.username))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(str(admin.id))
    response.set_cookie(
        key=settings.ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
        path="/",
    )
    return LoginResponse(admin=AdminOut.model_validate(admin))


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(settings.ADMIN_COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/auth/me", response_model=AdminOut)
async def me(admin: Admin = Depends(get_current_admin)):
    return AdminOut.model_validate(admin)


@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    admin.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Password updated"}
