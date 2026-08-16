# LLM Reliability + EvalOps Platform

A full-stack reference implementation for measuring the reliability of LLM-powered applications. It combines versioned evaluation data and prompts, deterministic graders, optional LLM-as-judge scoring, quality gates, and cost-latency analytics.

> [!IMPORTANT]
> The project includes synthetic seed data and is intended for local development, demonstrations, and portfolio review. It is not a multi-tenant hosted service: do not connect it to untrusted production data or expose write endpoints without adding authentication, authorization, rate limits, audit logging, and a threat-model review.

## Architecture

```text
┌────────────────────┐       ┌──────────────────────────────┐
│  Next.js dashboard │──────▶│  FastAPI eval API            │
│  (Vercel)          │       │  (Cloud Run)                 │
│                    │       │                              │
│  runs / compare /   │       │  datasets · prompts · runs   │
│  datasets / prompts│       │  graders · metrics · gate CLI│
└────────────────────┘       └──────────────┬───────────────┘
                                            │
                                            ▼
                                 ┌──────────────────────┐
                                 │ PostgreSQL           │
                                 │ datasets, runs,      │
                                 │ results, graders     │
                                 └──────────────────────┘

Providers (optional at runtime, mocked in CI):
  Gemini generation + LLM judge · OpenAI generation
```

## Capabilities

- Dataset ingestion (JSONL) with validation and seed datasets
- Prompt/model versioning with baseline and intentionally degraded prompts
- Synchronous eval runner with cost and latency tracking
- Deterministic graders: exact match, JSON schema, text similarity, citation/grounding
- Optional Gemini LLM-as-judge with composite scoring
- Dashboard analytics: run history, failed examples, breakdowns, cost/latency-quality charts
- Dashboard **New evaluation** launcher (`/runs/new`) for dataset/prompt/model selection
- CI eval gate CLI with thresholds, stable exit codes, JSON reports, and seeded GitHub Actions Postgres
- RAG QA workflow using supplied documents (no vector database)
- Cloud Run + Vercel deployment packaging and portfolio docs

## Project status and security

- The backend uses an allowlist CORS configuration; set `BACKEND_CORS_ORIGINS` to exact approved origins.
- Provider keys stay in ignored environment files. Never commit `.env`, `.env.local`, or real datasets.
- The included dashboard is deliberately not an authentication layer. Treat any public deployment as a demo only unless you add the controls listed above.
- See [SECURITY.md](SECURITY.md) for reporting guidance and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution expectations.

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
cp .env.example .env.local
npm ci
```

## Backend

```bash
cd backend
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

### Eval gate

```bash
uv run python -m app.cli.eval_gate \
  --dataset-name "Support Classification Seed" \
  --prompt-name support_classification_baseline \
  --model-name gemini-3.1-flash-lite \
  --min-pass-rate 0.9 \
  --min-avg-score 0.85 \
  --max-cost-usd 1.0 \
  --max-p95-latency-ms 5000 \
  --mock \
  --mock-profile expected \
  --report-path /tmp/eval-gate-report.json
```

Prove the threshold-failure path without live APIs:

```bash
uv run python -m app.cli.eval_gate \
  --dataset-name "Support Classification Seed" \
  --prompt-name support_classification_baseline \
  --model-name gemini-3.1-flash-lite \
  --min-pass-rate 0.9 \
  --min-avg-score 0.85 \
  --max-cost-usd 1.0 \
  --max-p95-latency-ms 5000 \
  --mock \
  --mock-profile degraded \
  --report-path /tmp/eval-gate-regression.json
echo $?   # expected: 1
```

Exit codes: `0` pass, `1` threshold failure, `2` config error, `3` runtime error.

GitHub Actions workflow `.github/workflows/eval-gate.yml` starts Postgres, migrates, seeds, runs the real CLI, uploads JSON report artifacts, and asserts the degraded profile exits `1`.

### Judge configuration

Set these in the ignored root `.env` file:

```dotenv
LLM_JUDGE_PROVIDER=gemini
LLM_JUDGE_ENABLED=true
GEMINI_API_KEY=replace-with-your-key
LLM_JUDGE_MODEL=gemini-3.1-flash-lite
LLM_JUDGE_TIMEOUT_SECONDS=30
OPENAI_API_KEY=
BACKEND_CORS_ORIGINS=http://localhost:3000
```

`OPENAI_API_KEY` is only required when a `ModelConfig` uses the OpenAI provider. Tests never require it.

## Frontend

```bash
cd frontend
npm run dev
npm run check
npm run build
```

Open `http://localhost:3000` for the dashboard.

For a production Vercel deployment, set `NEXT_PUBLIC_API_BASE_URL` to the approved backend URL and `NEXT_PUBLIC_SITE_URL` to the canonical public URL. The latter keeps canonical, sitemap, robots, and social metadata consistent.

- `/runs/new` — launch a synchronous evaluation (datasets, prompt versions, model configs)
- `/runs` — run history
- `/compare` — multi-run cost/latency vs quality
- API helpers: `GET /datasets`, `GET /prompt-versions`, `GET /model-configs`, `POST /eval-runs`

## Documentation

- [Deployment](docs/deployment.md)
- [Case study](docs/case-study.md)
- [Demo script](docs/demo-script.md)
- [Resume bullets](docs/resume-bullets.md)
- [Agent conventions](AGENTS.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [License](LICENSE)

## Verification

```bash
cd backend
uv run alembic upgrade head
uv run pytest -q
uv run ruff format --check .
uv run ruff check .

cd ../frontend
npm run check
npm run build

git diff --check
git check-ignore -v .env
git status
```
