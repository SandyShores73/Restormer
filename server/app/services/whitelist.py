from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlmodel import select

from ..core.config import settings
from ..models import AllowedUser

logger = logging.getLogger(__name__)


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


async def seed_from_file(seed_path: Path | None) -> None:
    resolved = settings.resolve_path(seed_path)
    if resolved is None or not resolved.exists():
        return
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Skipping whitelist seed file %s: %s", resolved, exc)
        return
    if not isinstance(payload, list):
        logger.warning("Whitelist seed file %s must contain a JSON array", resolved)
        return

    async with settings.database.session() as session:
        mutated = False
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            email = entry.get("email")
            if not email:
                continue
            result = await session.exec(select(AllowedUser).where(AllowedUser.email == email))
            existing = result.first()

            if existing:
                updated = False
                for field in ("display_name", "note", "is_active"):
                    if field in entry and getattr(existing, field) != entry[field]:
                        setattr(existing, field, entry[field])
                        updated = True
                if updated:
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    mutated = True
            else:
                allowed = AllowedUser(
                    email=email,
                    display_name=entry.get("display_name"),
                    note=entry.get("note"),
                    is_active=bool(entry.get("is_active", True)),
                )
                session.add(allowed)
                mutated = True

        if mutated:
            await session.commit()
