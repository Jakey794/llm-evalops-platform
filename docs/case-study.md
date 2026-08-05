# Case Study: Catching a Prompt Regression with EvalOps

## Problem

A “helpful” prompt rewrite for document-grounded RAG QA improved fluency in anecdotal review but silently dropped citation discipline. Without an automated gate, the change could ship with missing citations, invented document IDs, and unsupported claims.

## Setup

Seeded assets:

- Dataset: `RAG QA Seed` (`rag_qa` workflow, 20 cases with supplied documents)
- Baseline prompt: `rag_qa_baseline` / `v1`
- Degraded prompt: `rag_qa_degraded` / `v1-degraded`
- Model config: `gemini-3.1-flash-lite` (or the mocked expected-output provider in CI)
- Deterministic graders: JSON schema + text similarity + citation/grounding

The degraded prompt explicitly tells the model that citations are optional and that inventing details is allowed. That is the controlled failure mode for this study.

## Measurement

Primary metrics:

- Pass rate
- Average composite score
- Total estimated cost
- P95 latency

Failure modes of interest:

- `missing_citation`
- `invalid_citation`
- `unsupported_claim`

## How to produce baseline and degraded runs

### A. Dashboard (preferred for demos)

1. Seed the database (`uv run python -m app.seed.load_seed_data`).
2. Open `/runs/new`.
3. **Baseline:** dataset `RAG QA Seed`, prompt `rag_qa_baseline` / `v1`, model `gemini-3.1-flash-lite`.
4. **Degraded:** same dataset and model, prompt `rag_qa_degraded` / `v1-degraded`.
5. Open each completed run detail page and note pass rate, avg score, cost, and p95 latency.
6. Optionally open `/compare` and select both runs.

Requires a configured `GEMINI_API_KEY` (or OpenAI key for the OpenAI model config). Never commit secrets.

### B. Deterministic mock gate (CI / offline)

Baseline (expected to **pass**, exit `0`):

```bash
cd backend
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data

uv run python -m app.cli.eval_gate \
  --dataset-name "RAG QA Seed" \
  --prompt-name rag_qa_baseline \
  --prompt-version-label v1 \
  --model-name gemini-3.1-flash-lite \
  --min-pass-rate 0.9 \
  --min-avg-score 0.85 \
  --max-cost-usd 1.0 \
  --max-p95-latency-ms 5000 \
  --mock \
  --mock-profile expected \
  --report-path /tmp/baseline-gate.json
```

Controlled regression without live APIs (expected to **fail thresholds**, exit `1`):

```bash
uv run python -m app.cli.eval_gate \
  --dataset-name "RAG QA Seed" \
  --prompt-name rag_qa_baseline \
  --prompt-version-label v1 \
  --model-name gemini-3.1-flash-lite \
  --min-pass-rate 0.9 \
  --min-avg-score 0.85 \
  --max-cost-usd 1.0 \
  --max-p95-latency-ms 5000 \
  --mock \
  --mock-profile degraded \
  --report-path /tmp/degraded-gate.json
```

`--mock-profile degraded` returns schema-shaped but incorrect outputs (empty citations / wrong labels) so the gate can prove exit code `1` without calling Gemini or OpenAI.

### C. Export / record metrics

From a gate report:

```bash
jq '{passed, exit_code, eval_run_id, metrics, violations, dataset_id, prompt_version_id, model_config_id, mock_profile}' \
  /tmp/baseline-gate.json
```

From the API / dashboard after live runs:

- Run detail: `/runs/{id}` (pass rate, avg score, cost, latency)
- Compare: `/compare?` via UI selection
- Raw JSON: `GET /eval-runs/{id}`

Save the measured values into the template below. **Do not invent numbers.**

## Expected outcome (qualitative)

| Prompt / profile | Gate expectation |
|---|---|
| `rag_qa_baseline` + `--mock-profile expected` | Passes CI thresholds (mirrors expected outputs) |
| `--mock-profile degraded` | Fails quality thresholds with exit code `1` |
| `rag_qa_degraded` with live Gemini | Typically lower citation quality than baseline; record measured metrics below |

CI on pull requests starts Postgres, migrates, seeds, runs the real CLI with `--mock`, uploads JSON artifacts, and asserts the degraded profile returns exit code `1`. Normal PR checks never call Gemini or OpenAI.

## Measured production results

Both runs used the same `RAG QA Seed` dataset, containing 20
document-grounded test cases, and the same `gemini-3.1-flash-lite`
model configuration. The intentional experimental variable was the
prompt version.

| Run | Prompt | Pass rate | Avg score | Final failed cases | Total cost (USD) | Avg latency (ms) | P95 latency (ms) | Run ID |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Baseline | `rag_qa_baseline` / `v1` | 95.0% | 0.987 | 1 | $0.02939670 | 745.5 | 867 | `647d4df7-9029-48d6-b39f-875def2671a8` |
| Regression | `rag_qa_degraded` / `v1-degraded` | 85.0% | 0.953 | 3 | $0.06300110 | 808.15 | 908 | `6fa61dcb-8a5a-4224-8523-8606fee31cc7` |

### Observed regression

Relative to the baseline prompt, the degraded prompt:

- reduced pass rate from **95.0% to 85.0%**
- reduced average composite score from **0.987 to 0.953**
- increased final failed cases from **1 to 3**
- increased estimated cost from **$0.0294 to $0.0630**
- increased average latency from **745.5 ms to 808.15 ms**
- increased p95 latency from **867 ms to 908 ms**
- produced zero provider errors in both runs, confirming that the measured
  difference came from evaluated model behaviour rather than an API failure

The platform therefore detected a measurable quality regression while also
showing its operational cost and latency effects. A prompt change that might
appear acceptable during a few manual spot checks performed materially worse
across the fixed evaluation suite.

### Failure-mode analysis

The failed-example inspection endpoint includes cases with any grader-level
failure signal, even when the final composite score still passes. Therefore,
the 12 inspection rows returned for each run should not be interpreted as
12 final failures.

Final composite failures increased from **1 case in the baseline to 3 cases
in the degraded run**.

| Grader failure signal | Baseline | Degraded |
|---|---:|---:|
| `missing_required_phrase` | 1 | 3 |
| `low_text_similarity` | 1 | 3 |
| `unsupported_claim` | 1 | 3 |
| `missing_citation` | 1 | 0 |

The degraded prompt tripled the frequency of missing required content,
low semantic similarity, and unsupported claims. This supports the aggregate
regression shown by the lower pass rate and average score.

The baseline-only `missing_citation` signal does not contradict the overall
result: the final decision uses a weighted composite of multiple graders,
and the degraded prompt produced more repeated failures across required
content, semantic-similarity, and grounding checks.

### Operational observation

The degraded evaluation completed successfully in the backend, processed all
20 test cases, and persisted its results. However, the browser request that
initiated the synchronous evaluation disconnected before receiving the final
response because the run lasted approximately 16 minutes.

The completed run remained available through run history and the run-detail
API. A production-scale version would move evaluation execution to an
asynchronous worker and have the frontend poll the run-status endpoint rather
than holding one browser request open.

### Environment

- Date: `2026-08-05`
- Environment: production
- Database: Neon PostgreSQL
- Backend: Google Cloud Run
- Frontend: Vercel
- Dataset: `RAG QA Seed`
- Test cases: 20
- Model: `gemini-3.1-flash-lite`
- LLM judge enabled: yes
- Baseline run: `647d4df7-9029-48d6-b39f-875def2671a8`
- Degraded run: `6fa61dcb-8a5a-4224-8523-8606fee31cc7`

## Why this matters

The platform treats evaluation as a regression test suite for LLM behavior: versioned prompts, fixed datasets, deterministic graders for structural truth, optional LLM judge for semantics, dashboard-launched runs, and a CI gate with stable exit codes. That is the EvalOps loop needed before prompt or model changes reach production.
