from __future__ import annotations

from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests

from ..core.config import settings
from ..services import auth
from ..schemas.tokens import Token

router = APIRouter()


@router.post("/google", response_model=Token)
async def login_google(token: str) -> Token:
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.google_client_id)
        user = await auth.upsert_google_user(
            sub=idinfo["sub"],
            email=idinfo.get("email", f"user-{idinfo['sub']}@example.com"),
            full_name=idinfo.get("name", "Google User"),
        )
        access_token = auth.create_access_token(subject=user.id)
        return Token(access_token=access_token)
    except ValueError as exc:  # pragma: no cover - network errors
        raise HTTPException(status_code=400, detail="Invalid Google token") from exc
