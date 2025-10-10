from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext
from sqlmodel import select

from ..core.config import settings
from ..models import User
from ..schemas.users import UserCreate, UserRead
from ..utils.database import DatabaseManager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"exp": datetime.utcnow() + expires_delta, "sub": str(subject)}
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


async def authenticate_user(email: str, password: str) -> UserRead | None:
    user = await get_user_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return UserRead.from_orm(user)


async def get_user_by_email(email: str) -> User | None:
    async with settings.database.session() as session:
        result = await session.exec(select(User).where(User.email == email))
        return result.first()


async def get_user_by_id(user_id: int) -> UserRead | None:
    async with settings.database.session() as session:
        user = await session.get(User, user_id)
        if user:
            return UserRead.from_orm(user)
        return None


async def create_user(user_in: UserCreate) -> UserRead:
    async with settings.database.session() as session:
        existing = await session.exec(select(User).where(User.email == user_in.email))
        if existing.first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            password_hash=get_password_hash(user_in.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return UserRead.from_orm(user)


async def upsert_google_user(sub: str, email: str, full_name: str) -> UserRead:
    async with settings.database.session() as session:
        result = await session.exec(select(User).where(User.google_sub == sub))
        user = result.first()
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=get_password_hash(sub),
                google_sub=sub,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            user.email = email
            user.full_name = full_name
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return UserRead.from_orm(user)
