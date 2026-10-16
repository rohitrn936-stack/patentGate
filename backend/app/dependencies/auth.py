from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
_EXPIRED_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token, expected_type="access")
        subject = payload.get("sub")
        if not subject:
            raise _CREDENTIALS_ERROR
        user_id = UUID(subject)
        token_version = int(payload.get("ver", 0))
    except ExpiredSignatureError as exc:
        raise _EXPIRED_ERROR from exc
    except (JWTError, ValueError) as exc:
        raise _CREDENTIALS_ERROR from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.token_version != token_version:
        raise _CREDENTIALS_ERROR
    return user


CurrentUser = Depends(get_current_user)
