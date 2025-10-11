from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class ProcessingJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="pending", index=True)
    stage: str = Field(default="queued", index=True)
    input_path: str
    output_path: str | None = None
    input_manifest: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="JSON manifest describing uploaded files.",
    )
    output_manifest: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="JSON manifest describing generated files.",
    )
    mode: str = Field(default="denoise", index=True)
    passes: int = Field(default=1, ge=1, le=5)
    file_count: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None
    progress: float = Field(default=0.0)
    debug_log: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Chronological debug log entries separated by newlines.",
    )
