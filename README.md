# ClipForge — Video Content Pipeline

Upload a video → get transcript, Twitter thread, LinkedIn post, blog, and auto-cut shorts.

## Run locally (dev)

```bash
# 1. Copy env and fill in your keys
cp .env.example .env

# 2. Start everything
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

Required keys in `.env`:

- `ANTHROPIC_API_KEY` — Claude Haiku
- `ASSEMBLYAI_API_KEY` — transcription (free tier: 100 hours)
- `POSTGRES_PASSWORD` — any string (local only)

## Deploy to a VPS (production)

```bash
# 1. SSH into your VPS (Ubuntu 22.04 recommended)
# 2. Install Docker + Docker Compose
# 3. Clone repo and fill in .env
git clone <repo>
cp .env.example .env
# Edit .env: set real keys, DOMAIN=yourdomain.com, STORAGE_TYPE=r2

# 4. Set your email in traefik/traefik.yml for Let's Encrypt

# 5. Start
docker-compose up -d --build
```

That's it. Traefik auto-issues SSL for your domain.

## Deploy to Render

This repo is ready for Render deployment with production services for the frontend, backend, worker, database, and Redis.

Use the `render.yaml` blueprint in this repo to deploy:

- `clipforge-backend` — FastAPI backend web service
- `clipforge-worker` — Celery worker service
- `clipforge-frontend` — Next.js frontend web service
- `clipforge-db` — Render Postgres database
- `clipforge-redis` — Render Key Value (Redis-compatible) service

During deployment, set these secret environment variables in Render:

- `ANTHROPIC_API_KEY`
- `ASSEMBLYAI_API_KEY`
- `SHOTSTACK_API_KEY`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

For production storage, keep these values:

- `STORAGE_TYPE=r2`
- `R2_BUCKET=video-pipeline`
- `R2_PUBLIC_URL=https://pub-xxx.r2.dev`

On Render, the frontend expects the backend API to be available at:

- `https://clipforge-backend.onrender.com/api`

## Switch to Cloudflare R2 (production storage)

In `.env`:

```
STORAGE_TYPE=r2
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_key
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET=video-pipeline
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

## AWS deployment with S3 storage

If you deploy on AWS, use S3 for file storage by setting:

```
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=video-pipeline
AWS_REGION=us-east-1
AWS_S3_PUBLIC_URL=https://video-pipeline.s3.amazonaws.com
```

`AWS_S3_PUBLIC_URL` is optional when your bucket is publicly accessible.

## Pipeline

```
Upload → Transcribe (AssemblyAI) → Generate posts (Claude Haiku) → Score + cut shorts (FFmpeg)
```

Each step runs in a Celery worker. The frontend polls `/api/jobs/{id}` every 2.5s for status.
