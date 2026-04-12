import os
import uuid
import tempfile
from celery import Celery
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import Job
from services import assemblyai_service, claude_service, ffmpeg_service, shotstack_service
from services.storage import storage

celery_app = Celery(
    "pipeline",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


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
        tmp = tempfile.mktemp(suffix=suffix)
        storage.download_to_tmp(job.video_path, tmp)
        return tmp, True
    return storage.local_path(job.video_path), False


# ── Main task ─────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=0)
def process_video(self, job_id: str):
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

        duration = ffmpeg_service.get_duration(local_path)
        _update(db, job, video_duration=duration)

        transcript = assemblyai_service.transcribe(local_path)
        _update(db, job, transcript=transcript, progress=40, step_label="Transcription complete")

        # ── Step 2: Generate posts + extract metadata ─────────────────────────
        _update(db, job, status="generating", step_label="Writing posts with AI…", progress=45)

        # Run metadata extraction first (small fast call) so speaker name
        # is available for Shotstack overlays later.
        meta = claude_service.extract_metadata(transcript)
        speaker_name  = meta.get("speaker_name", "Guest Speaker")
        episode_title = meta.get("episode_title", "Scaler Podcast")

        posts = claude_service.generate_posts(transcript)
        _update(
            db, job,
            twitter_post=posts.get("twitter"),
            linkedin_post=posts.get("linkedin"),
            blog_post=posts.get("blog"),
            progress=65,
            step_label="Posts generated",
        )

        # ── Step 3: Design + cut shorts ───────────────────────────────────────
        _update(db, job, status="cutting", step_label="Designing best shorts…", progress=68)

        designs = claude_service.design_shorts(transcript, max_shorts=settings.max_shorts)
        if not designs:
            _update(db, job, shorts=[], status="complete", step_label="Done!", progress=100)
            return

        _update(db, job, step_label="Cutting & stitching clips…", progress=75)

        shorts_out    = []
        use_shotstack = bool(settings.shotstack_api_key) and settings.storage_type in {"r2", "s3"}

        for i, design in enumerate(designs):
            short_id  = str(uuid.uuid4())[:8]
            short_key = f"shorts/{job_id}/{short_id}.mp4"
            dur       = design.get("duration_s", 60)
            enhanced  = False

            if settings.storage_type == "local":
                # ── Local: concat → burn overlays with FFmpeg ─────────────────
                raw_path = storage.local_path(short_key)
                ffmpeg_service.concat_segments(
                    input_path=local_path,
                    segments=design["segments"],
                    output_path=raw_path,
                )
                # Burn overlays in-place (write to temp, then replace)
                tmp_enhanced = raw_path + ".enhanced.mp4"
                try:
                    ffmpeg_service.burn_overlays(
                        input_path=raw_path,
                        output_path=tmp_enhanced,
                        hook_text=design.get("hook_text", ""),
                        speaker_name=speaker_name,
                        duration_s=dur,
                    )
                    os.replace(tmp_enhanced, raw_path)
                    enhanced = True
                except Exception as exc:
                    print(f"[ffmpeg overlays] clip {short_id} failed: {exc}")
                    if os.path.exists(tmp_enhanced):
                        os.remove(tmp_enhanced)

                final_url = storage.public_url(short_key)

            else:
                # ── R2: concat → upload → Shotstack enhance ──────────────────
                tmp_raw = tempfile.mktemp(suffix=".mp4")
                try:
                    ffmpeg_service.concat_segments(
                        input_path=local_path,
                        segments=design["segments"],
                        output_path=tmp_raw,
                    )
                    storage.upload_file(short_key, tmp_raw)
                    raw_url = storage.public_url(short_key)

                    if use_shotstack:
                        try:
                            final_url = shotstack_service.enhance_clip(
                                public_url=raw_url,
                                duration_s=dur,
                                title=design.get("title", episode_title),
                                hook_text=design.get("hook_text", ""),
                                speaker_name=speaker_name,
                            )
                            enhanced = True
                        except Exception as exc:
                            print(f"[shotstack] clip {short_id} failed, using R2 fallback: {exc}")
                            final_url = raw_url
                    else:
                        final_url = raw_url
                finally:
                    if os.path.exists(tmp_raw):
                        os.remove(tmp_raw)

            shorts_out.append(
                {
                    "id": short_id,
                    "title": design.get("title", f"Clip {i + 1}"),
                    "hook_text": design.get("hook_text", ""),
                    "score": design.get("score", 0),
                    "duration_s": dur,
                    "rationale": design.get("rationale", ""),
                    "url": final_url,
                    "path": short_key,
                    "enhanced": enhanced,
                }
            )

            progress = 75 + int((i + 1) / len(designs) * 22)
            _update(db, job, progress=progress)

        _update(
            db, job,
            shorts=shorts_out,
            status="complete",
            step_label="Done!",
            progress=100,
        )

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
