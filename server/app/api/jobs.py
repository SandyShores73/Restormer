from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import List
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import select

from ..auth.dependencies import get_current_active_user
from ..core.config import settings
from ..models import ProcessingJob
from ..schemas.jobs import JobRead
from ..schemas.users import UserRead
from ..services.pipeline import MODE_LABELS, SUPPORTED_MODES, pipeline
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


def _extract_filename(path_str: str) -> str:
    posix_name = Path(path_str).name
    if posix_name and posix_name != path_str:
        return posix_name
    windows_name = PureWindowsPath(path_str).name
    if windows_name and windows_name != path_str:
        return windows_name
    return path_str.split("/")[-1].split("\\")[-1]


def _parse_manifest(manifest: str | None) -> list[dict[str, str]]:
    if not manifest:
        return []
    try:
        data = json.loads(manifest)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    parsed: list[dict[str, str]] = []
    for entry in data:
        if isinstance(entry, dict):
            filename = str(entry.get("filename", ""))
            path = str(entry.get("path", ""))
            parsed.append({"filename": filename, "path": path})
    return parsed


def _build_job_read(job: ProcessingJob) -> JobRead:
    filename = _extract_filename(job.output_path or job.input_path)
    downloadable = False
    download_path: str | None = None
    download_url: str | None = None
    if job.status == "completed" and job.output_path and Path(job.output_path).exists():
        downloadable = True
        download_path = f"/jobs/{job.id}/download"
        base_url = settings.normalised_public_base_url
        if base_url:
            download_url = urljoin(f"{base_url}/", download_path.lstrip("/"))
    debug_lines = job.debug_log.splitlines() if job.debug_log else []
    progress = job.progress or 0.0
    stage = job.stage or "queued"
    input_manifest = _parse_manifest(job.input_manifest)
    output_manifest = _parse_manifest(job.output_manifest)
    mode = job.mode or "denoise"
    mode_label = MODE_LABELS.get(mode, mode.replace("_", " ").title())
    return JobRead(
        id=job.id,
        status=job.status,
        stage=stage,
        filename=filename,
        mode=mode,
        mode_label=mode_label,
        passes=job.passes,
        file_count=job.file_count,
        input_files=[entry["filename"] for entry in input_manifest if entry["filename"]],
        output_files=[entry["filename"] for entry in output_manifest if entry["filename"]],
        created_at=job.created_at,
        updated_at=job.updated_at,
        error_message=job.error_message,
        downloadable=downloadable,
        download_path=download_path,
        download_url=download_url,
        progress=progress,
        debug_lines=debug_lines,
    )


async def _record_progress(
    job: ProcessingJob,
    *,
    message: str,
    status: str | None = None,
    stage: str | None = None,
    progress: float | None = None,
) -> ProcessingJob:
    if status:
        job.status = status
    if stage:
        job.stage = stage
    if progress is not None:
        job.progress = max(0.0, min(progress, 1.0))
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    entry = f"[{timestamp}] {message}"
    if job.debug_log:
        job.debug_log = f"{job.debug_log.rstrip()}\n{entry}"
    else:
        job.debug_log = entry
    return await _update_job(job)


async def _process_job(job_id: int) -> None:
    async with db.session() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job:
            return
        try:
            await _record_progress(
                job,
                message="Job picked up by worker",
                status="processing",
                stage="initialising",
                progress=0.05,
            )

            async def emit(stage: str, progress: float, message: str) -> None:
                await _record_progress(job, message=message, stage=stage, progress=progress)

            input_manifest = _parse_manifest(job.input_manifest)
            input_paths = [Path(entry["path"]) for entry in input_manifest if entry.get("path")]
            if not input_paths:
                raise RuntimeError("No input files recorded for job")

            archive_path = Path(job.output_path) if job.output_path else None
            if archive_path is None:
                archive_root = Path(settings.processed_dir) / f"job_{job.id}"
                archive_root.mkdir(parents=True, exist_ok=True)
                archive_path = archive_root / "restormer_outputs.zip"

            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_result, manifest = await pipeline.process_batch(
                input_paths,
                archive_path.parent,
                mode=job.mode,
                passes=job.passes,
                progress_callback=emit,
            )
            job.output_path = str(archive_result)
            job.output_manifest = json.dumps(manifest)
            await _record_progress(
                job,
                message="Processing completed and output stored",
                status="completed",
                stage="completed",
                progress=1.0,
            )
        except Exception as exc:  # noqa: BLE001
            job.error_message = str(exc)
            await _record_progress(
                job,
                message=f"Processing failed: {exc}",
                status="failed",
                stage="failed",
                progress=1.0,
            )


@router.post("/", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: str = Form("denoise"),
    passes: int = Form(1),
    current_user: UserRead = Depends(get_current_active_user),
) -> JobRead:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one image")
    if len(files) > 25:
        raise HTTPException(status_code=400, detail="You can upload at most 25 images per job")

    normalised_mode = mode.lower().strip()
    if normalised_mode not in SUPPORTED_MODES:
        raise HTTPException(status_code=400, detail=f"Unsupported mode '{mode}'")

    passes = int(passes)
    passes = max(1, min(5, passes))

    batch_id = uuid4().hex
    input_dir = Path(settings.upload_dir) / f"user_{current_user.id}" / f"job_{batch_id}"
    output_dir = Path(settings.processed_dir) / f"user_{current_user.id}" / f"job_{batch_id}"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    input_manifest: list[dict[str, str]] = []

    for index, upload in enumerate(files):
        content_type = (upload.content_type or "").lower()
        if content_type and not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"{upload.filename} is not an image upload")
        original_name = Path(upload.filename or f"image_{index}.png").name or f"image_{index}.png"
        stem = Path(original_name).stem or f"image_{index}"
        suffix = Path(original_name).suffix or ".png"
        candidate = original_name
        counter = 1
        while candidate in used_names:
            candidate = f"{stem}_{counter}{suffix}"
            counter += 1
        used_names.add(candidate)

        data = await upload.read()
        destination = input_dir / candidate
        destination.write_bytes(data)
        input_manifest.append({"filename": candidate, "path": str(destination)})
        await upload.close()

    archive_path = output_dir / "restormer_outputs.zip"

    async with db.session() as session:
        job = ProcessingJob(
            user_id=current_user.id,
            status="queued",
            stage="queued",
            input_path=str(input_dir),
            output_path=str(archive_path),
            input_manifest=json.dumps(input_manifest),
            mode=normalised_mode,
            passes=passes,
            file_count=len(input_manifest),
            progress=0.03,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    background_tasks.add_task(_process_job, job.id)
    await _record_progress(
        job,
        message=f"Queued {len(input_manifest)} image(s) for {MODE_LABELS.get(normalised_mode, normalised_mode)}",
        stage="queued",
        status="queued",
        progress=0.03,
    )
    return _build_job_read(job)


@router.get("/", response_model=List[JobRead])
async def list_jobs(current_user: UserRead = Depends(get_current_active_user)) -> List[JobRead]:
    async with db.session() as session:
        result = await session.exec(
            select(ProcessingJob).where(ProcessingJob.user_id == current_user.id)
        )
        jobs = result.all()
    return [_build_job_read(job) for job in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, current_user: UserRead = Depends(get_current_active_user)) -> JobRead:
    async with db.session() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job or job.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")
    return _build_job_read(job)


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
