from __future__ import annotations

from contextlib import asynccontextmanager

from typing import Iterable

from sqlalchemy import text
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

    async def ensure_columns(self) -> None:
        """Add newly introduced columns to existing SQLite databases if required."""

        async with self.engine.begin() as conn:
            await self._ensure_processing_job_columns(conn)

    async def _ensure_processing_job_columns(self, conn) -> None:  # type: ignore[no-untyped-def]
        result = await conn.execute(text("PRAGMA table_info(processingjob);"))
        columns: Iterable[str] = (row[1] for row in result)  # type: ignore[index]
        column_set = {column.lower() for column in columns}

        async def add_column(sql: str) -> None:
            await conn.execute(text(sql))

        if "progress" not in column_set:
            await add_column("ALTER TABLE processingjob ADD COLUMN progress FLOAT DEFAULT 0.0")
        if "stage" not in column_set:
            await add_column("ALTER TABLE processingjob ADD COLUMN stage VARCHAR(255) DEFAULT 'queued'")
        if "debug_log" not in column_set:
            await add_column("ALTER TABLE processingjob ADD COLUMN debug_log TEXT")
