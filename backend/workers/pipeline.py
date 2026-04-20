import os
import uuid
import tempfile
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import Job
from services import assemblyai_service, claude_service
from services.storage import storage


# ── Helpers ──────────────────────────────────────────────────────────────────

def _update(db: Session, job: Job, **kwargs):
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()
    db.refresh(job)


def _get_local_video(job: Job) -> tuple[str, bool]:
    """
    Returns (local_path, is_tmp).
    For R2 storage, downloads to a tmp file (caller must delete it).
    For local storage, returns the direct path.
    """
    if settings.storage_type == "r2":
        suffix = os.path.splitext(job.video_path)[1] or ".mp4"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        storage.download_to_tmp(job.video_path, tmp)
        return tmp, True
    return storage.local_path(job.video_path), False


# ── Main pipeline function (runs as FastAPI background task) ──────────────────

def process_video(job_id: str):
    db = SessionLocal()
    tmp_video = None

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # ── Step 1: Transcribe ───────────────────────────────────────────────
        _update(db, job, status="transcribing", step_label="Transcribing audio…", progress=5)

        local_path, is_tmp = _get_local_video(job)
        if is_tmp:
            tmp_video = local_path

        transcript = assemblyai_service.transcribe(local_path)

        # Derive duration from last sentence end timestamp
        duration = transcript[-1]["end_ms"] / 1000 if transcript else None
        _update(db, job, transcript=transcript, video_duration=duration,
                progress=40, step_label="Transcription complete")

        # ── Step 2: Generate posts ────────────────────────────────────────────
        _update(db, job, status="generating", step_label="Writing posts with AI…", progress=45)

        posts = claude_service.generate_posts(transcript)
        _update(
            db, job,
            twitter_post=posts.get("twitter"),
            linkedin_post=posts.get("linkedin"),
            blog_post=posts.get("blog"),
            progress=70,
            step_label="Posts generated",
        )

        # ── Step 3: Design shorts (timestamps only, no video cutting) ─────────
        _update(db, job, status="cutting", step_label="Finding best clip moments…", progress=75)

        designs = claude_service.design_shorts(transcript, max_shorts=settings.max_shorts)

        shorts_out = []
        for i, design in enumerate(designs):
            shorts_out.append({
                "id": str(uuid.uuid4())[:8],
                "title": design.get("title", f"Clip {i + 1}"),
                "hook_text": design.get("hook_text", ""),
                "score": design.get("score", 0),
                "duration_s": design.get("duration_s", 0),
                "rationale": design.get("rationale", ""),
                "segments": design.get("segments", []),
            })

        _update(db, job, shorts=shorts_out, status="complete", step_label="Done!", progress=100)

    except Exception as exc:
        try:
            _update(db, job, status="failed", step_label="Failed", error=str(exc))
        except Exception:
            pass
        raise

    finally:
        db.close()
        if tmp_video and os.path.exists(tmp_video):
            os.remove(tmp_video)
