# Demo Script (5–7 minutes)

## 0. Prep (before recording)

1. Start Postgres: `docker compose up -d postgres`
2. Backend:
   ```bash
   cd backend
   uv sync --locked --extra dev
   uv run alembic upgrade head
   uv run python -m app.seed.load_seed_data
   uv run uvicorn app.main:app --reload --port 8000
   ```
3. Frontend:
   ```bash
   cd frontend
   npm ci
   npm run dev
   ```
4. Optional live judge: set `LLM_JUDGE_ENABLED=true` and `GEMINI_API_KEY` in root `.env` (never show the key on screen).

## 1. Architecture (45s)

Open the README architecture diagram. Say:

- Next.js dashboard
- FastAPI eval runner
- PostgreSQL persistence
- Deterministic graders + optional Gemini judge
- CI eval gate with mocked providers on PRs

## 2. Datasets (60s)

Open `/datasets`.

- Show Support Classification, Incident Triage, and RAG QA seeds.
- Open RAG QA and highlight supplied `documents`, `required_citations`, and tags/difficulty.

## 3. Run an evaluation (90s)

Create a run via API (terminal):

```bash
# Replace IDs from GET /datasets, prompt-versions, or seed output.
curl -s http://localhost:8000/prompt-versions | jq '.[0]'
curl --fail-with-body -X POST http://localhost:8000/eval-runs \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"...","prompt_version_id":"...","model_config_id":"..."}'
```

Open `/runs`, click into the new run, and show:

- Pass rate, average score, cost, avg/p95 latency
- Failed examples + grader feedback
- Tag / difficulty / workflow breakdowns

## 4. Compare prompts (60s)

Open `/compare`, select baseline vs another completed run, and show cost-quality and latency-quality charts.

## 5. CI eval gate (60s)

```bash
cd backend
uv run python -m app.cli.eval_gate \
  --dataset-name "Support Classification Seed" \
  --prompt-name support_classification_baseline \
  --model-name gemini-3.1-flash-lite \
  --min-pass-rate 0.9 \
  --max-cost-usd 1.0 \
  --max-p95-latency-ms 5000 \
  --mock \
  --report-path /tmp/eval-gate-report.json
echo $?
jq . /tmp/eval-gate-report.json
```

Mention GitHub Actions `eval-gate.yml` runs mocked tests only—no real API calls on normal PRs.

## 6. Closing (30s)

Restate the portfolio value: reproducible evals, regression detection, cost/latency visibility, and a CI gate that can block degraded prompt versions.
