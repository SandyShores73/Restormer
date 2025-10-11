"""FastAPI server for AI-based denoise, detail refinement, and focus correction.

The server exposes REST endpoints for authenticating users, uploading images,
submitting processing jobs, and retrieving results.  Inference is executed with
ONNX Runtime's DirectML execution provider so that it can utilise the AMD Radeon
RX 7800 XT GPU available on the target Windows 11 host.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from .api import diagnostics, jobs, oauth, users
from .auth.dependencies import get_current_active_user
from .core.config import settings
from .schemas.tokens import Token
from .schemas.users import UserRead
from .services.auth import authenticate_user, create_access_token

app = FastAPI(title="Restormer Remote AI Denoise", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")
app.mount("/dashboard", StaticFiles(directory=settings.dashboard_dir, html=True), name="dashboard")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise core services when the application starts."""
    await settings.init_directories()
    await settings.database.create_db_and_tables()
    await settings.database.ensure_columns()


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@app.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: UserRead = Depends(get_current_active_user),
) -> UserRead:
    return current_user


@app.get("/health", tags=["diagnostics"])
async def health() -> dict[str, str]:
    """Simple readiness probe used by the desktop client during onboarding."""

    return {"status": "ok", "public_base_url": settings.normalised_public_base_url or "unset"}


app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])
