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

## Measured results (fill in after a real run)

> **Template only — replace placeholders with values from your reports or dashboard. Never invent live metrics.**

| Run | Prompt / profile | Pass rate | Avg score | Total cost (USD) | P95 latency (ms) | Source |
|---|---|---|---|---|---|---|
| Baseline | `rag_qa_baseline` / `v1` or `expected` mock | _TBD_ | _TBD_ | _TBD_ | _TBD_ | report path or run id |
| Degraded | `rag_qa_degraded` / `v1-degraded` or `degraded` mock | _TBD_ | _TBD_ | _TBD_ | _TBD_ | report path or run id |

Notes:

- Date / environment: _TBD_
- Judge enabled: _yes/no_
- Artifact paths: _e.g. `/tmp/baseline-gate.json`_

## Why this matters

The platform treats evaluation as a regression test suite for LLM behavior: versioned prompts, fixed datasets, deterministic graders for structural truth, optional LLM judge for semantics, dashboard-launched runs, and a CI gate with stable exit codes. That is the EvalOps loop needed before prompt or model changes reach production.
