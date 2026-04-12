import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON
from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Status tracking
    # queued → transcribing → generating → cutting → complete
    # any step can go to: failed
    status = Column(String, default="queued")
    progress = Column(Integer, default=0)   # 0-100
    step_label = Column(String, default="Queued")

    # Input
    original_filename = Column(String)
    video_path = Column(String)             # storage key (relative path or R2 key)
    video_duration = Column(Float, nullable=True)

    # Transcript: [{text, start_ms, end_ms}, ...]
    transcript = Column(JSON, nullable=True)

    # Generated posts
    twitter_post = Column(Text, nullable=True)
    linkedin_post = Column(Text, nullable=True)
    blog_post = Column(Text, nullable=True)

    # Shorts: [{id, title, hook, path, url, duration_s, score}, ...]
    shorts = Column(JSON, nullable=True)

    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "step_label": self.step_label,
            "original_filename": self.original_filename,
            "video_duration": self.video_duration,
            "transcript": self.transcript,
            "twitter_post": self.twitter_post,
            "linkedin_post": self.linkedin_post,
            "blog_post": self.blog_post,
            "shorts": self.shorts,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
