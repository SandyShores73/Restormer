from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel


class JobCreate(BaseModel):
    filename: str


class JobRead(BaseModel):
    id: int
    status: str
    stage: str
    filename: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None
    downloadable: bool
    download_path: str | None = None
    download_url: AnyHttpUrl | None = None
    progress: float
    debug_lines: list[str]


class JobStatusUpdate(BaseModel):
    status: str
    output_path: str | None = None
    error_message: str | None = None
    progress: float | None = None
    stage: str | None = None
