from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import init_db
from config import settings
from routes import upload, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(f"{settings.local_storage_path}/uploads", exist_ok=True)
    os.makedirs(f"{settings.local_storage_path}/shorts", exist_ok=True)
    os.makedirs(f"{settings.local_storage_path}/tmp", exist_ok=True)
    yield


app = FastAPI(title="Video Pipeline API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")

# Serve local shorts/files in dev (in prod, R2 handles this)
if settings.storage_type == "local":
    app.mount(
        "/storage",
        StaticFiles(directory=settings.local_storage_path),
        name="storage",
    )
