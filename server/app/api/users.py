from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.dependencies import get_current_active_user
from ..schemas.users import (
    UserCreate,
    UserRead,
    WhitelistCheckRequest,
    WhitelistCheckResponse,
)
from ..services import auth, whitelist

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate) -> UserRead:
    return await auth.create_user(user_in)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: UserRead = Depends(get_current_active_user)) -> UserRead:
    return current_user


@router.post("/verify", response_model=WhitelistCheckResponse)
async def verify_whitelist(request: WhitelistCheckRequest) -> WhitelistCheckResponse:
    allowed = await whitelist.get_allowed_user(request.email)
    if allowed is None or not allowed.is_active:
        return WhitelistCheckResponse(
            allowed=False,
            display_name=None,
            message="This account is not on the access list yet. Contact your administrator.",
        )
    await whitelist.ensure_allowed(request.email)
    return WhitelistCheckResponse(
        allowed=True,
        display_name=allowed.display_name,
        message="Access verified. Continue with registration.",
    )
