# LLM Reliability + EvalOps Platform

A production-shaped platform for managing and evaluating the reliability of LLM-powered applications.

## Week 1 Status

Week 1 establishes the application foundation:

- Next.js frontend dashboard shell
- FastAPI backend with health checks
- PostgreSQL local development service
- Backend container image
- Backend and frontend continuous integration

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

cd ../frontend
npm ci
```

## Backend

Run these commands from `backend/`:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

The health endpoint is available at `http://localhost:8000/health`.

## Frontend

Run these commands from `frontend/`:

```bash
npm run dev
npm run check
npm run build
```

The frontend is available at `http://localhost:3000`.

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

## Week 2 Next Steps

- Define the database schema.
- Add Alembic migrations.
- Add JSONL dataset import.
- Seed incident and support datasets.
