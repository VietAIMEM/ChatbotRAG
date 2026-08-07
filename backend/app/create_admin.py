from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.admin import Admin

logger = get_logger(__name__)


async def create_admin(username: str, password: str, email: str | None = None) -> str:
    if len(password) < 8:
        raise ValueError("Admin password must be at least 8 characters long.")
    async with SessionLocal() as db:
        result = await db.execute(select(Admin).where(Admin.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            existing.password_hash = hash_password(password)
            if email:
                existing.email = email
            await db.commit()
            return f"Admin '{username}' already existed - password updated."

        admin = Admin(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        return f"Admin '{username}' created successfully."


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the initial admin account.")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", ""))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", ""))
    args = parser.parse_args()

    if not args.password:
        logger.error(
            "No admin password provided. Set ADMIN_PASSWORD env var or pass --password. "
            "Credentials are never hard-coded."
        )
        raise SystemExit(1)

    try:
        message = await create_admin(args.username, args.password, args.email or None)
    except ValueError as exc:
        logger.error("create_admin failed: %s", exc)
        raise SystemExit(1) from exc
    logger.info(message)


if __name__ == "__main__":
    asyncio.run(main())
