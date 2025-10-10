from __future__ import annotations

from contextlib import asynccontextmanager

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.ext.asyncio.engine import create_async_engine


class DatabaseManager:
    """Utility wrapper around SQLModel's async engine."""

    def __init__(self, url: str) -> None:
        self.engine = create_async_engine(url, echo=False, future=True)

    @asynccontextmanager
    async def session(self) -> AsyncSession:
        async_session = AsyncSession(self.engine)
        try:
            yield async_session
        finally:
            await async_session.close()

    async def create_db_and_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
