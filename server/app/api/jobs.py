from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import select

from ..auth.dependencies import get_current_active_user
from ..core.config import settings
from ..models import ProcessingJob
from ..schemas.jobs import JobRead
from ..schemas.users import UserRead
from ..services.pipeline import pipeline
from ..utils.database import DatabaseManager

router = APIRouter()

db: DatabaseManager = settings.database


async def _update_job(job: ProcessingJob) -> ProcessingJob:
    job.updated_at = datetime.utcnow()
    async with db.session() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def _process_job(job_id: int, input_path: Path, output_path: Path) -> None:
    async with db.session() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job:
            return
        try:
            job.status = "processing"
            await _update_job(job)
            await pipeline.process(input_path, output_path)
            job.status = "completed"
            job.output_path = str(output_path)
            await _update_job(job)
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_message = str(exc)
            await _update_job(job)


@router.post("/", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_active_user),
) -> JobRead:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    destination = Path(settings.upload_dir) / f"{current_user.id}_{file.filename}"
    output_path = Path(settings.processed_dir) / f"{current_user.id}_{file.filename}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    destination.write_bytes(content)

    async with db.session() as session:
        job = ProcessingJob(
            user_id=current_user.id,
            status="queued",
            input_path=str(destination),
            output_path=str(output_path),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    background_tasks.add_task(_process_job, job.id, destination, output_path)
    return JobRead.from_orm(job)


@router.get("/", response_model=List[JobRead])
async def list_jobs(current_user: UserRead = Depends(get_current_active_user)) -> List[JobRead]:
    async with db.session() as session:
        result = await session.exec(
            select(ProcessingJob).where(ProcessingJob.user_id == current_user.id)
        )
        jobs = result.all()
    return [JobRead.from_orm(job) for job in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, current_user: UserRead = Depends(get_current_active_user)) -> JobRead:
    async with db.session() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job or job.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.from_orm(job)


@router.get("/{job_id}/download")
async def download_job(job_id: int, current_user: UserRead = Depends(get_current_active_user)) -> FileResponse:
    async with db.session() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job or job.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "completed" or not job.output_path:
            raise HTTPException(status_code=400, detail="Job not completed")
    output_path = Path(job.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Processed file missing")
    return FileResponse(output_path, filename=output_path.name)
