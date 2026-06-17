 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/api/jobs.py
index 0000000000000000000000000000000000000000..a7e17b3503c4aed112326cc3aac9dece575a9cd9 100644
--- a//dev/null
+++ b/server/app/api/jobs.py
@@ -0,0 +1,113 @@
+from __future__ import annotations
+
+import asyncio
+from datetime import datetime
+import mimetypes
+from pathlib import Path
+from typing import AsyncIterator, List
+
+from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
+from fastapi.responses import FileResponse, StreamingResponse
+from sqlmodel import select
+
+from ..auth.dependencies import get_current_active_user
+from ..core.config import settings
+from ..models import ProcessingJob
+from ..schemas.jobs import JobRead
+from ..schemas.users import UserRead
+from ..services.pipeline import pipeline
+from ..utils.database import DatabaseManager
+
+router = APIRouter()
+
+db: DatabaseManager = settings.database
+
+
+async def _update_job(job: ProcessingJob) -> ProcessingJob:
+    job.updated_at = datetime.utcnow()
+    async with db.session() as session:
+        session.add(job)
+        await session.commit()
+        await session.refresh(job)
+        return job
+
+
+async def _process_job(job_id: int, input_path: Path, output_path: Path) -> None:
+    async with db.session() as session:
+        job = await session.get(ProcessingJob, job_id)
+        if not job:
+            return
+        try:
+            job.status = "processing"
+            await _update_job(job)
+            await pipeline.process(input_path, output_path)
+            job.status = "completed"
+            job.output_path = str(output_path)
+            await _update_job(job)
+        except Exception as exc:  # noqa: BLE001
+            job.status = "failed"
+            job.error_message = str(exc)
+            await _update_job(job)
+
+
+@router.post("/", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
+async def create_job(
+    background_tasks: BackgroundTasks,
+    file: UploadFile = File(...),
+    current_user: UserRead = Depends(get_current_active_user),
+) -> JobRead:
+    if not file.content_type.startswith("image/"):
+        raise HTTPException(status_code=400, detail="Unsupported file type")
+
+    destination = Path(settings.upload_dir) / f"{current_user.id}_{file.filename}"
+    output_path = Path(settings.processed_dir) / f"{current_user.id}_{file.filename}"
+    destination.parent.mkdir(parents=True, exist_ok=True)
+    output_path.parent.mkdir(parents=True, exist_ok=True)
+    content = await file.read()
+    destination.write_bytes(content)
+
+    async with db.session() as session:
+        job = ProcessingJob(
+            user_id=current_user.id,
+            status="queued",
+            input_path=str(destination),
+            output_path=str(output_path),
+        )
+        session.add(job)
+        await session.commit()
+        await session.refresh(job)
+
+    background_tasks.add_task(_process_job, job.id, destination, output_path)
+    return JobRead.from_orm(job)
+
+
+@router.get("/", response_model=List[JobRead])
+async def list_jobs(current_user: UserRead = Depends(get_current_active_user)) -> List[JobRead]:
+    async with db.session() as session:
+        result = await session.exec(
+            select(ProcessingJob).where(ProcessingJob.user_id == current_user.id)
+        )
+        jobs = result.all()
+    return [JobRead.from_orm(job) for job in jobs]
+
+
+@router.get("/{job_id}", response_model=JobRead)
+async def get_job(job_id: int, current_user: UserRead = Depends(get_current_active_user)) -> JobRead:
+    async with db.session() as session:
+        job = await session.get(ProcessingJob, job_id)
+        if not job or job.user_id != current_user.id:
+            raise HTTPException(status_code=404, detail="Job not found")
+    return JobRead.from_orm(job)
+
+
+async def _iter_file_chunks(
+    request: Request,
+    output_path: Path,
+    chunk_size: int,
+    chunk_delay_seconds: float,
+) -> AsyncIterator[bytes]:
+    try:
+        with output_path.open("rb") as output_file:
+            while chunk := output_file.read(chunk_size):
+                if await request.is_disconnected():
+                    break
+                yield chunk
+                if chunk_delay_seconds > 0:
+                    await asyncio.sleep(chunk_delay_seconds)
+    except asyncio.CancelledError:
+        raise
+    except OSError as exc:
+        raise HTTPException(status_code=500, detail="Unable to stream processed file") from exc
+
+
+@router.get("/{job_id}/download")
+async def download_job(
+    job_id: int,
+    request: Request,
+    stream: bool = Query(False, description="Stream the processed file in low-latency chunks."),
+    chunk_ms: int = Query(0, ge=0, le=1000, description="Optional delay between streamed chunks in milliseconds."),
+    current_user: UserRead = Depends(get_current_active_user),
+) -> FileResponse | StreamingResponse:
+    async with db.session() as session:
+        job = await session.get(ProcessingJob, job_id)
+        if not job or job.user_id != current_user.id:
+            raise HTTPException(status_code=404, detail="Job not found")
+        if job.status != "completed" or not job.output_path:
+            raise HTTPException(status_code=400, detail="Job not completed")
+    output_path = Path(job.output_path)
+    if not output_path.exists():
+        raise HTTPException(status_code=404, detail="Processed file missing")
+    if not stream:
+        return FileResponse(output_path, filename=output_path.name)
+
+    media_type, _ = mimetypes.guess_type(output_path.name)
+    media_type = media_type or "application/octet-stream"
+    headers = {
+        "Content-Disposition": f'attachment; filename="{output_path.name}"',
+        "X-Content-Type-Options": "nosniff",
+        "X-Stream-Chunk-Ms": str(chunk_ms),
+    }
+    if media_type.startswith("image/"):
+        headers["X-Image-Filename"] = output_path.name
+
+    return StreamingResponse(
+        _iter_file_chunks(request, output_path, chunk_size=64 * 1024, chunk_delay_seconds=chunk_ms / 1000),
+        media_type=media_type,
+        headers=headers,
+    )
 
EOF
)
