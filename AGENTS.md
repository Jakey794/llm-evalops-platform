# AGENTS.md

Enduring conventions for humans and coding agents working in this repository.

## Scope boundaries

Do **not** add authentication, billing, teams/multi-tenancy, autonomous agents, Redis, Celery, or Kubernetes unless explicitly requested.

Do **not** deploy external infrastructure from agent sessions.

Do **not** print, modify, stage, or commit root `.env` or any live secrets.

## Architecture

- `frontend/`: Next.js App Router dashboard
- `backend/`: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Eval execution is synchronous and request-scoped
- Graders are deterministic first; Gemini judge is optional and non-fatal
- RAG QA uses supplied documents in each test case—no vector database

## Backend conventions

- Python 3.12+, `uv`, Ruff, Pytest
- Prefer simple typed Pydantic schemas and SQLAlchemy models
- Mock all external model/provider calls in automated tests
- Provider implementations must return errors as data when practical so runs can continue
- New workflows should ship with seed JSONL, prompt versions, grader config, and tests
- CLI eval gate exit codes: `0` pass, `1` threshold failure, `2` config error, `3` runtime error

## Frontend conventions

- TypeScript + Biome (`npm run check`)
- Fetch backend via `NEXT_PUBLIC_API_BASE_URL`
- Preserve loading, error, empty, and partial-data states for dashboard views
- Prefer lightweight SVG/CSS visualizations over heavy chart libraries unless needed

## Quality bar before finishing work

Backend:

```bash
cd backend
uv run alembic upgrade head
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

Frontend:

```bash
cd frontend
npm run check
npm run build
```

Repository:

```bash
git diff --check
git check-ignore -v .env
git status
```

## Commits and PRs

- Use conventional commits
- Never force-push shared branches unless explicitly requested
- Never commit `.env`
- Prefer focused commits by feature area (graders, gate, dashboard, docs)
