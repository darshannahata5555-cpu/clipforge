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

## Pipeline

```
Upload → Transcribe (AssemblyAI) → Generate posts (Claude Haiku) → Score + cut shorts (FFmpeg)
```

Each step runs in a Celery worker. The frontend polls `/api/jobs/{id}` every 2.5s for status.
