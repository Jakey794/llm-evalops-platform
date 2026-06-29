# LLM Reliability + EvalOps Platform

A production-shaped platform for managing and evaluating the reliability of LLM-powered applications.

## Week 2 Status

Week 2 adds dataset management to the application foundation:

- Next.js frontend dashboard shell
- FastAPI backend with health checks
- PostgreSQL local development service
- Backend container image
- Backend and frontend continuous integration
- Dataset and test-case schema with Alembic migrations
- Atomic JSONL dataset imports with per-line validation
- Dataset list, detail, and test-case APIs
- Bundled support-classification and incident-triage seed datasets
- Frontend dataset browser

## Architecture

```text
Next.js frontend -> FastAPI backend -> PostgreSQL
```

## Local Setup

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 22+, npm, and Docker.

```bash
cp .env.example .env
docker compose up -d postgres

cd backend
uv sync --locked --extra dev
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data

cd ../frontend
npm ci
```

## Backend

Run these commands from `backend/`:

```bash
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

The health endpoint is available at `http://localhost:8000/health`.

### Dataset API

With the backend running, list datasets and inspect one by replacing `<dataset-id>` with an ID
from the list response:

```bash
curl http://localhost:8000/datasets
curl http://localhost:8000/datasets/<dataset-id>
curl http://localhost:8000/datasets/<dataset-id>/test-cases
```

Import a JSONL file atomically (requires `jq`):

```bash
jq -Rs \
  '{name: "Support Classification Copy", workflow_type: "support_classification", source_filename: "support_classification.jsonl", jsonl_content: .}' \
  backend/app/seed/support_classification.jsonl \
  | curl --fail-with-body -X POST http://localhost:8000/datasets/import-jsonl \
      -H 'Content-Type: application/json' --data-binary @-
```

An invalid line or duplicate test-case ID rejects the entire import without creating a dataset.

## Frontend

Run these commands from `frontend/`:

```bash
npm run dev
npm run check
npm run build
```

The frontend is available at `http://localhost:3000`. Open the dataset browser at
`http://localhost:3000/datasets` after starting the backend and loading seed data.

## Backend Docker Image

From the repository root:

```bash
cd backend
docker build -t llm-evalops-backend .
docker run -p 8000:8000 --env-file ../.env.example llm-evalops-backend
curl http://localhost:8000/health
```

The standalone container health check reports a degraded status until PostgreSQL is reachable from inside the container. For local development, run PostgreSQL with Docker Compose and provide a container-reachable `DATABASE_URL`.

## Deployment Notes

- Vercel will deploy `frontend/`.
- Cloud Run will deploy the backend container later.
- No deployment automation is included yet.
