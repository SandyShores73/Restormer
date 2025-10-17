from __future__ import annotations

from collections import Counter, deque
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import select

from ..auth.dependencies import get_current_active_user
from ..core.config import settings
from ..models import ProcessingJob
from ..schemas.users import UserRead
from ..services.pipeline import pipeline
from ..utils.database import DatabaseManager
from ..utils.logging import get_log_file_path

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


@router.get("/logs")
async def diagnostics_logs(
    limit: int = 200,
    current_user: UserRead = Depends(get_current_active_user),
) -> dict[str, object]:
    """Return the most recent server log lines for on-device debugging."""

    log_path = get_log_file_path()
    if not log_path or not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not initialised")

    limit = max(1, min(limit, 2000))
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = [line.rstrip("\n") for line in deque(handle, maxlen=limit)]

    return {
        "path": str(log_path),
        "line_count": len(lines),
        "lines": lines,
        "updated_at": datetime.utcnow().isoformat(),
        "viewer": current_user.email,
    }


def _extract_filename(path_str: str) -> str:
    return path_str.split("/")[-1].split("\\")[-1]
