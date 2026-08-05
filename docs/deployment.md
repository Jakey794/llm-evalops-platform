# Deployment

This project deploys as two independently managed services:

- **Backend**: FastAPI container on Google Cloud Run
- **Frontend**: Next.js app on Vercel
- **Database**: Managed PostgreSQL (Cloud SQL or equivalent)

No Kubernetes, Redis, Celery, or auth service is required.

## Environment variables

### Backend (Cloud Run)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://...` SQLAlchemy URL |
| `BACKEND_CORS_ORIGINS` | yes in prod | Comma-separated frontend origins, e.g. `https://your-app.vercel.app` |
| `GEMINI_API_KEY` | for Gemini generation/judge | Keep secret; never commit |
| `LLM_JUDGE_ENABLED` | no | `true`/`false` |
| `LLM_JUDGE_PROVIDER` | no | default `gemini` |
| `LLM_JUDGE_MODEL` | no | default `gemini-3.1-flash-lite` |
| `LLM_JUDGE_TIMEOUT_SECONDS` | no | default `30` |
| `OPENAI_API_KEY` | only if using OpenAI model configs | Optional provider |
| `PORT` | Cloud Run sets this | Container listens on `$PORT` |

### Frontend (Vercel)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | yes | Public Cloud Run URL, no trailing slash |

Root `.env` is for local development only and must stay gitignored.

## Migrations and seed

From `backend/`:

```bash
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data
```

Cloud Run startup (`scripts/start.sh`) runs `alembic upgrade head` before uvicorn. Seed data is intentional and should be run once per environment by an operator, not on every container start.

## Backend container (Cloud Run)

```bash
cd backend
docker build -t llm-evalops-backend .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL='postgresql+psycopg://postgres:postgres@host.docker.internal:5432/evalops' \
  -e BACKEND_CORS_ORIGINS='http://localhost:3000' \
  -e LLM_JUDGE_ENABLED=false \
  llm-evalops-backend
```

Cloud Run notes:

- Set CPU/memory for synchronous eval runs (eval execution is request-scoped).
- Configure Cloud SQL Auth Proxy or a private IP `DATABASE_URL`.
- Set `BACKEND_CORS_ORIGINS` to the exact Vercel production and preview origins you need.
- Do not bake API keys into the image; inject them as secrets.

## Frontend (Vercel)

- Root directory: `frontend`
- Framework preset: Next.js
- Install: `npm ci`
- Build: `npm run build`
- Env: `NEXT_PUBLIC_API_BASE_URL=https://<cloud-run-service-url>`

`frontend/vercel.json` documents the intended Vercel settings.

## CORS checklist

1. Deploy backend with production CORS origins.
2. Deploy frontend with `NEXT_PUBLIC_API_BASE_URL` pointing at that backend.
3. Confirm browser calls to `/health`, `/datasets`, and `/eval-runs` succeed without CORS errors.
4. Keep local `http://localhost:3000` only in development configs.

## Health checks

- Backend: `GET /health`
- Frontend: Vercel default HTTPS check on `/`
