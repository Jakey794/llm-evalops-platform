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

## Expected outcome

| Prompt | Gate expectation |
|---|---|
| `rag_qa_baseline` | Passes CI thresholds under the mock provider (exact expected outputs) and should remain high quality with real Gemini |
| `rag_qa_degraded` | Fails quality thresholds once real model behavior omits/invalidates citations; in mock demos, use a lowered-output fixture or live run to show the block |

CI on pull requests uses `--mock` / `EVAL_GATE_MOCK=1` so normal PR checks never call Gemini or OpenAI. The gate still validates wiring, thresholds, exit codes, and JSON reporting.

## Reproducing locally

```bash
cd backend
uv run alembic upgrade head
uv run python -m app.seed.load_seed_data

# Baseline should pass under mock:
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
  --report-path /tmp/baseline-gate.json

# Live regression comparison (requires GEMINI_API_KEY):
# Run baseline and degraded prompt versions through POST /eval-runs,
# then compare them in the dashboard Compare view.
```

## Why this matters

The platform treats evaluation as a regression test suite for LLM behavior: versioned prompts, fixed datasets, deterministic graders for structural truth, optional LLM judge for semantics, and a CI gate with stable exit codes. That is the EvalOps loop needed before prompt or model changes reach production.
