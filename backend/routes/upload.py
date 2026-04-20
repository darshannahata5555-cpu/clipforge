import uuid
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import Job
from services.storage import storage
from config import settings
from workers.pipeline import process_video

router = APIRouter()

ALLOWED_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/webm", "video/mpeg",
}


@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Upload MP4, MOV, AVI, MKV, or WebM.",
        )

    # Read and check file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.0f} MB). Max is {settings.max_file_size_mb} MB.",
        )

    job_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    storage_key = f"uploads/{job_id}{ext}"

    # Save to storage
    await storage.save(storage_key, contents)

    # Create DB job
    job = Job(
        id=job_id,
        original_filename=file.filename,
        video_path=storage_key,
        status="queued",
        step_label="Queued",
    )
    db.add(job)
    db.commit()

    # Run pipeline as a background task (same process, no Redis/Celery needed)
    background_tasks.add_task(process_video, job_id)

    return {"job_id": job_id}
