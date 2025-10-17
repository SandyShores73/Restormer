from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from pydantic import AnyHttpUrl, BaseSettings, Field, validator

from ..utils.database import DatabaseManager


def _default_log_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "RestormerServer" / "logs"
    return Path("server/logs")


class Settings(BaseSettings):
    """Application configuration derived from environment variables."""

    project_root: Path = Path(__file__).resolve().parents[2]
    assets_dir: Path = Field(default_factory=lambda: Path("server/processed"))
    dashboard_dir: Path = Field(default_factory=lambda: Path("server/dashboard"))
    models_dir: Path = Field(default_factory=lambda: Path("server/models_cache"))
    processed_dir: Path = Field(default_factory=lambda: Path("server/processed"))
    upload_dir: Path = Field(default_factory=lambda: Path("server/uploads"))
    database_url: str = Field("sqlite+aiosqlite:///server/restormer.db")
    whitelist_seed_file: Path | None = Field(
        default_factory=lambda: Path("seed_whitelist.json"),
        env="RESTORMER_WHITELIST_SEED",
    )
    secret_key: str = Field("change-me", env="RESTORMER_SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24
    allowed_origins: Iterable[str] = Field(
        default_factory=lambda: ["*"], env="RESTORMER_ALLOWED_ORIGINS"
    )
    public_base_url: AnyHttpUrl | None = Field(
        default=None, env="RESTORMER_PUBLIC_BASE_URL"
    )
    google_client_id: str | None = Field(default=None, env="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(
        default=None, env="GOOGLE_CLIENT_SECRET"
    )
    dashboard_token: str | None = Field(
        default=None, env="RESTORMER_DASHBOARD_TOKEN"
    )
    log_dir: Path = Field(default_factory=_default_log_dir, env="RESTORMER_LOG_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("allowed_origins", pre=True)
    def _split_allowed_origins(cls, value: Any) -> Iterable[str]:  # noqa: D401, N805
        """Support comma separated lists for RESTORMER_ALLOWED_ORIGINS."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def database(self) -> DatabaseManager:
        return DatabaseManager(self.database_url)

    @property
    def normalised_public_base_url(self) -> str | None:
        if not self.public_base_url:
            return None
        return str(self.public_base_url).rstrip("/")

    async def init_directories(self) -> None:
        for directory in (
            self.assets_dir,
            self.dashboard_dir,
            self.models_dir,
            self.processed_dir,
            self.upload_dir,
            self.log_dir,
        ):
            Path(directory).expanduser().mkdir(parents=True, exist_ok=True)

    def export(self) -> dict[str, Any]:
        return json.loads(self.json())

    def resolve_path(self, path: Path | None) -> Path | None:
        if path is None:
            return None
        expanded = Path(path).expanduser()
        return expanded if expanded.is_absolute() else self.project_root / expanded


settings = Settings()
