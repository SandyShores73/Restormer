from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import select

from ..core.config import settings
from ..models import AllowedUser


async def get_allowed_user(email: str) -> AllowedUser | None:
    async with settings.database.session() as session:
        result = await session.exec(select(AllowedUser).where(AllowedUser.email == email))
        return result.first()


async def ensure_allowed(email: str) -> AllowedUser:
    allowed = await get_allowed_user(email)
    if allowed is None or not allowed.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not authorised for this service.",
        )
    await _touch_verification(allowed)
    return allowed


async def _touch_verification(allowed: AllowedUser) -> None:
    allowed.last_verified_at = datetime.utcnow()
    allowed.updated_at = datetime.utcnow()
    async with settings.database.session() as session:
        session.add(allowed)
        await session.commit()
