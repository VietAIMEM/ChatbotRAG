from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.admin import Admin
from app.services.rate_limit import admin_login_rate_limiter, chat_rate_limiter

bearer_scheme = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Admin:
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)
    if not token:
        # Allow Authorization header as fallback.
        credentials: HTTPAuthorizationCredentials | None = await bearer_scheme(request)
        if credentials:
            token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    subject = payload.get("sub")
    try:
        import uuid

        subject_uuid = uuid.UUID(subject)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    result = await db.execute(select(Admin).where(Admin.id == subject_uuid))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    return admin


async def check_chat_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    allowed, retry_after = await chat_rate_limiter.check(
        ip, settings.CHAT_RATE_LIMIT_PER_MINUTE, settings.CHAT_RATE_LIMIT_WINDOW_SECONDS
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please wait {retry_after} seconds and try again.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_admin_login_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    allowed, retry_after = await admin_login_rate_limiter.check(
        ip, settings.ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE, settings.CHAT_RATE_LIMIT_WINDOW_SECONDS
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait and try again.",
            headers={"Retry-After": str(retry_after)},
        )
