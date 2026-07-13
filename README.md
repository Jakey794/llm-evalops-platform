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

## Week 5: LLM-as-judge

The eval runner can optionally send model output to Gemini after deterministic grading. Exact
match, JSON schema, and text similarity remain first-class because they are fast, repeatable, and
reliable for structural checks; the judge adds semantic assessment without becoming a single
point of failure. Judge errors are stored in `grader_results`, the run continues, and the
deterministic result is retained.

Final deterministic/judge weights are 70/30 for support classification, 40/60 for incident
triage, and 50/50 otherwise. The validated `LLMJudgeOutput` is:

```text
score: float (0.0-1.0)
passed: bool
reason: short user-visible string
failure_modes: list[string]
rubric_scores: map[string, float (0.0-1.0)]
```

Allowed failure modes are `incorrect_label`, `invalid_json`, `missing_required_field`,
`wrong_severity`, `incomplete_reasoning`, `unsupported_claim`, `missing_citation`,
`hallucination`, and `irrelevant_answer`. Citation checking for `rag_qa` is not implemented yet.
See [an example judge result](docs/examples/judge-result.json).

### Local judge configuration

Set these in the ignored root `.env` file:

```dotenv
LLM_JUDGE_PROVIDER=gemini
LLM_JUDGE_ENABLED=true
GEMINI_API_KEY=replace-with-your-key
LLM_JUDGE_MODEL=gemini-2.5-flash-lite
LLM_JUDGE_TIMEOUT_SECONDS=30
```

`OPENAI_API_KEY` is not used by the judge. It is still required when the selected primary
`ModelConfig` uses the existing OpenAI generation provider.

To run a small existing dataset, start the backend with these settings and submit existing,
workflow-compatible dataset, prompt-version, and model-config IDs:

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

curl --fail-with-body -X POST http://localhost:8000/eval-runs \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"<dataset-id>","prompt_version_id":"<prompt-version-id>","model_config_id":"<model-config-id>"}'
```

Inspect `GET /eval-runs/<run-id>/results` or `GET /eval-runs/<run-id>/failed-examples`.

### Week 5 verification

```bash
cd backend
uv run pytest
uv run ruff format --check .
uv run ruff check .

cd ../frontend
npm run check
npm run build
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
