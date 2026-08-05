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
- CI eval gate with seeded Postgres + deterministic mock providers on PRs

## 2. Datasets (60s)

Open `/datasets`.

- Show Support Classification, Incident Triage, and RAG QA seeds.
- Open RAG QA and highlight supplied `documents`, `required_citations`, and tags/difficulty.

## 3. Run an evaluation (90s)

Open `/runs/new` (also linked from Dashboard and Runs).

1. Select **Support Classification Seed** (or RAG QA Seed for the citation story).
2. Confirm the prompt list only shows workflow-compatible versions (baseline / degraded).
3. Choose `gemini-3.1-flash-lite` (or another seeded model with a configured key).
4. Click **Start evaluation** and wait for the synchronous run to finish.
5. Land on `/runs/{id}` and show:
   - Pass rate, average score, cost, avg/p95 latency
   - Failed examples + grader feedback
   - Tag / difficulty / workflow breakdowns

If you need a second run for Compare, launch the matching degraded prompt from the same page.

## 4. Compare prompts (60s)

Open `/compare`, select baseline vs degraded completed runs, and show cost-quality and latency-quality charts.

## 5. CI eval gate (60s)

```bash
cd backend
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
echo $?
jq . /tmp/eval-gate-report.json
```

Mention GitHub Actions `eval-gate.yml` starts Postgres, seeds data, runs the real CLI with `--mock`, uploads JSON reports, and also proves the degraded mock profile returns exit code `1`—without calling Gemini or OpenAI on normal PRs.

## 6. Closing (30s)

Restate the portfolio value: reproducible evals, dashboard-launched runs, regression detection, cost/latency visibility, and a CI gate that can block degraded prompt or model behavior.
