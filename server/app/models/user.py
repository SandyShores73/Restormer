from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: str
    password_hash: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    google_sub: str | None = Field(default=None, index=True)
