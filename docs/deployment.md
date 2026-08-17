# Deployment

This project deploys as two independently managed services:

- **Backend**: FastAPI container on Google Cloud Run
- **Frontend**: Next.js app on Vercel
- **Database**: Managed PostgreSQL (Cloud SQL or equivalent)

The reference deployment uses signed dashboard sessions and two shared demo roles. No Kubernetes, Redis, Celery, or external auth service is required for a small synthetic-data demo. Use a managed identity provider and a distributed limiter before scaling beyond that boundary.

## Environment variables

### Backend (Cloud Run)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://...` SQLAlchemy URL |
| `BACKEND_CORS_ORIGINS` | yes in prod | Comma-separated frontend origins, e.g. `https://your-app.vercel.app` |
| `BACKEND_VIEWER_TOKEN` | yes | Random 32+ character service token; must match Vercel |
| `BACKEND_OPERATOR_TOKEN` | yes | Different random 32+ character service token; must match Vercel |
| `API_DOCS_ENABLED` | no | Default `false`; enable only for an intended environment |
| `RATE_LIMIT_WINDOW_SECONDS` | no | Default `60` |
| `RATE_LIMIT_READ_REQUESTS` | no | Per-instance viewer/operator read limit; default `120` |
| `RATE_LIMIT_WRITE_REQUESTS` | no | Per-instance operator write limit; default `10` |
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
| `BACKEND_API_BASE_URL` | yes | Server-only Cloud Run URL, no trailing slash |
| `BACKEND_VIEWER_TOKEN` | yes | Same viewer token configured in Cloud Run |
| `BACKEND_OPERATOR_TOKEN` | yes | Same operator token configured in Cloud Run |
| `APP_SESSION_SECRET` | yes | Random 32+ character HMAC secret |
| `APP_VIEWER_PASSWORD` | yes | Strong password for read-only dashboard access |
| `APP_OPERATOR_PASSWORD` | yes | Different strong password for evaluation writes |
| `NEXT_PUBLIC_SITE_URL` | yes | Canonical frontend URL; safe to expose publicly |

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
  -e BACKEND_VIEWER_TOKEN='replace-with-random-32-plus-character-token' \
  -e BACKEND_OPERATOR_TOKEN='replace-with-a-different-random-token' \
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
- Server-only env: `BACKEND_API_BASE_URL`, both `BACKEND_*_TOKEN` values, `APP_SESSION_SECRET`, and both `APP_*_PASSWORD` values
- Public env: `NEXT_PUBLIC_SITE_URL=https://llm-evalops-platform.vercel.app`

`frontend/vercel.json` documents the intended Vercel settings. Do not prefix secrets with `NEXT_PUBLIC_`.

## Safe production rollout

1. Generate independent high-entropy session, viewer-token, operator-token, viewer-password, and operator-password values. Never paste them into issues, logs, commits, or build arguments.
2. Add the frontend variables in Vercel for Production (and Preview only if previews should be functional). Keep the existing backend URL as `BACKEND_API_BASE_URL`; remove the obsolete public variable after verification.
3. Deploy the frontend. Confirm `/login` loads, bad passwords fail, viewer access is read-only, and operator access can launch only an intentional synthetic evaluation.
4. Add the matching service tokens to Cloud Run and deploy the backend revision. The frontend gateway already sends these tokens, so this order avoids breaking the dashboard while closing direct unauthenticated API access.
5. Confirm direct `/health` remains public; direct `/datasets` returns `401` without a token, `200` with the viewer token, and write routes return `403` to the viewer token.
6. Retain Cloud Run and Vercel logs, create alerts for repeated `authentication.denied`, `authorization.denied`, `rate_limit.denied`, and 5xx events, then rotate any credential used during setup if it appeared outside an approved secret store.

## Gateway and CORS checklist

1. Deploy the frontend with `BACKEND_API_BASE_URL` pointing at the backend.
2. Confirm browser calls stay on `/api/backend/*`; service tokens must not appear in page source, browser storage, or client bundles.
3. Keep `BACKEND_CORS_ORIGINS` limited to explicit trusted origins as defense in depth.
4. Keep local `http://localhost:3000` only in development configs.

## Operational limits

The bundled limiter is deliberately dependency-free and applies per backend process and per warm Vercel function. Multiple instances can therefore admit more traffic than the configured number. Keep Cloud Run instance counts and concurrency bounded for the reference demo. Use a managed edge/WAF or distributed rate-limit service before opening access to a larger audience. Audit events are written to stdout; retention, alerting, access control, and export are deployment responsibilities.

## Health checks

- Backend: `GET /health`
- Frontend: Vercel default HTTPS check on `/`

Read [Threat model](threat-model.md) before public exposure.
