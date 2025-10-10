from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    google_sub: str | None = None

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
