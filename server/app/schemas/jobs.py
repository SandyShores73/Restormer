from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    filename: str


class JobRead(BaseModel):
    id: int
    status: str
    input_path: str
    output_path: str | None
    created_at: datetime
    updated_at: datetime
    error_message: str | None

    class Config:
        orm_mode = True


class JobStatusUpdate(BaseModel):
    status: str
    output_path: str | None = None
    error_message: str | None = None
