from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]

# bcrypt silently truncates at 72 bytes; reject longer inputs explicitly so two
# different long passwords can never collide.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes long")
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_context.verify(password, password_hash)
    except ValueError:
        return False


def _create_token(
    user_id: uuid.UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    token_version: int,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "ver": token_version,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    settings = get_settings()
    return _create_token(
        user_id, "access", timedelta(minutes=settings.access_token_expire_minutes), token_version
    )


def create_refresh_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    settings = get_settings()
    return _create_token(
        user_id, "refresh", timedelta(days=settings.refresh_token_expire_days), token_version
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict:
    """Decode and validate a token. Raises ``jose`` errors on failure."""

    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.JWTError(f"expected a {expected_type} token")
    return payload


def access_token_ttl_seconds() -> int:
    return get_settings().access_token_expire_minutes * 60
