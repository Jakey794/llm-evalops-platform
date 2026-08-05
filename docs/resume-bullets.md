# Resume Bullets

Use or adapt these bullets for a resume / portfolio write-up:

- Built an end-to-end LLM EvalOps platform (FastAPI, PostgreSQL, Next.js) for dataset management, prompt/model versioning, synchronous eval runs, and reliability dashboards.
- Implemented deterministic graders (exact match, JSON schema, text similarity, citation/grounding) plus an optional Gemini LLM-as-judge path with composite scoring and failure-mode analytics.
- Designed a document-grounded RAG QA workflow without a vector database, using supplied documents, required citation IDs, and graders for `missing_citation`, `invalid_citation`, and `unsupported_claim`.
- Shipped a CI eval gate CLI with pass-rate/score/cost/p95 thresholds, stable exit codes, JSON reports, and GitHub Actions jobs that mock providers so PRs never call external LLM APIs.
- Added dashboard analytics for run history, failed examples, tag/difficulty/workflow breakdowns, and cost-quality / latency-quality comparison charts.
- Packaged the system for Cloud Run + Vercel deployment with production CORS guidance, migration startup, seed commands, and portfolio documentation (case study, demo script, architecture).
