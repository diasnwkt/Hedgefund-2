from typing import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import decode_token, oauth2_scheme
from config import Settings, get_settings
from db.session import get_async_session

log = structlog.get_logger(__name__)


async def get_db(settings: Settings = Depends(get_settings)) -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session


async def get_redis(settings: Settings = Depends(get_settings)) -> aioredis.Redis:
    client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=settings.redis_timeout_sec,
    )
    return client


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, settings)
        username: str = payload.get("sub", "")
        if not username:
            raise credentials_exc
    except JWTError:
        raise credentials_exc
    return username
