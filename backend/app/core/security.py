from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = settings.ALGORITHM


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire, "iat": now, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:2] + "*" * 10 + value[-4:]


def encode_fernet_key_from_secret(secret: str) -> bytes:
    """Derive a stable 32-byte key from the app secret for reversible encryption."""
    import hashlib

    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a secret (e.g. an LLM API key) using a key derived from SECRET_KEY."""
    if not value:
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(encode_fernet_key_from_secret(JWT_SECRET)).encrypt(value.encode("utf-8")).decode("utf-8")
    except ImportError:  # pragma: no cover - cryptography is a dependency
        return value


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a secret previously encrypted with :func:`encrypt_secret`."""
    if not value:
        return None
    try:
        from cryptography.fernet import Fernet, InvalidToken

        return (
            Fernet(encode_fernet_key_from_secret(JWT_SECRET))
            .decrypt(value.encode("utf-8"))
            .decode("utf-8")
        )
    except (ImportError, InvalidToken, ValueError):  # pragma: no cover
        return value
