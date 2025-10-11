from __future__ import annotations

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import select

from ..core.config import settings
from ..models import ProcessingJob
from ..services.pipeline import pipeline
from ..utils.database import DatabaseManager

router = APIRouter()

db: DatabaseManager = settings.database


async def _require_dashboard_token(x_dashboard_token: str | None = Header(default=None)) -> None:
    token = settings.dashboard_token
    if token is None:
        return
    if x_dashboard_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard token",
        )


@router.get("/summary")
async def diagnostics_summary(
    _: None = Depends(_require_dashboard_token),
) -> dict[str, object]:
    async with db.session() as session:
        result = await session.exec(select(ProcessingJob))
        jobs = result.all()

    total_jobs = len(jobs)
    status_counts = Counter(job.status for job in jobs)
    average_progress = sum(job.progress for job in jobs) / total_jobs if total_jobs else 0.0
    recent_jobs: list[dict[str, object]] = []
    for job in sorted(jobs, key=lambda item: item.updated_at or datetime.utcnow(), reverse=True)[:6]:
        recent_jobs.append(
            {
                "id": job.id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "updated_at": job.updated_at.isoformat(),
                "filename": _extract_filename(job.output_path or job.input_path),
                "last_debug": (job.debug_log.splitlines()[-1] if job.debug_log else None),
            }
        )

    environment = pipeline.describe_environment()

    return {
        "total_jobs": total_jobs,
        "status_counts": dict(status_counts),
        "average_progress": round(average_progress, 3),
        "environment": environment,
        "recent_jobs": recent_jobs,
    }


def _extract_filename(path_str: str) -> str:
    return path_str.split("/")[-1].split("\\")[-1]
