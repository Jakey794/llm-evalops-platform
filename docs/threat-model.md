# Threat model

Last reviewed: 2026-08-16

## Scope and security objective

This model covers the public Vercel dashboard, its same-origin Next.js gateway, the FastAPI service on Cloud Run, PostgreSQL, provider APIs, deployment secrets, and platform logs. The intended deployment contains synthetic demonstration data and a small, invited audience. Its primary objectives are to prevent anonymous API access, keep service/provider credentials out of browsers, limit unintended writes and model spend, and preserve useful security evidence.

This is not approval for confidential, regulated, or customer data. Shared viewer/operator passwords do not provide per-person identity, MFA, joiner/leaver controls, or attribution.

## Assets and trust boundaries

- Assets: evaluation datasets and results, provider API keys, database credentials, backend service tokens, dashboard passwords, session-signing key, audit records, and model-spend budget.
- Internet to Vercel: untrusted requests cross into the public login and Next.js gateway.
- Vercel to Cloud Run: the gateway attaches a server-only role token; the browser never receives that token.
- Cloud Run to PostgreSQL and model providers: database and provider credentials remain server-side.
- GitHub to deployment platforms: source and CI are public; deployment secrets must remain in platform secret stores.

## Principal threats and controls

| Threat | Primary controls | Residual risk / required operation |
|---|---|---|
| Anonymous data access | HMAC-signed, HTTP-only, Secure, SameSite session; bearer token required on non-health backend routes | A stolen shared password grants its shared role until rotated |
| Unauthorized writes or model spend | Viewer/operator separation enforced in both gateway and API; write rate limit | Compromised operator access can still spend within limits; configure provider budgets and alerts |
| Credential disclosure to browser | Same-origin gateway; only server-only environment variables carry tokens; response headers are filtered | Operators must inspect builds and never use `NEXT_PUBLIC_` for secrets |
| Password guessing | Constant-time comparison, generic errors, bounded login attempts, strong high-entropy passwords | Vercel function limits are per warm instance; use edge/distributed protection for broad public access |
| API flooding | Separate read/write sliding-window limits, request body cap, bounded query limits | Backend limiter is per instance; cap autoscaling/concurrency or add managed edge enforcement |
| CSRF | Strict SameSite session and same-origin checks on state-changing gateway/login requests | Logout permits a request without Origin for normal form compatibility; impact is logout only |
| SSRF or open proxy abuse | Gateway allowlists API prefixes and safe path characters; backend origin comes only from server configuration | Review the allowlist when adding new proxy paths |
| Log or error leakage | Structured metadata-only audit events; request bodies, passwords, tokens, and provider responses are excluded | Platform access, retention, export, and alert rules require operator configuration |
| Session forgery/replay | SHA-256 HMAC, 32+ character secret, eight-hour expiry, Secure/HTTP-only cookie | No server-side revocation list; rotate the signing secret to invalidate every session |
| Supply-chain compromise | Locked Python/Node dependencies, CI checks, Dependabot, secret scanning, push protection | Review dependency PRs and pin deployment provenance before high-sensitivity use |
| Database/provider compromise | Secrets stay server-side; least-data audit records; synthetic-data boundary | Database IAM, encryption, backups, provider budget limits, and egress policy are platform responsibilities |

## Abuse cases reviewed

1. A caller requests backend data without a token: the API returns `401` before database work.
2. A viewer attempts a dataset import or evaluation run: the gateway and backend each return `403`.
3. A caller repeats reads or writes: the corresponding subject-scoped limit returns `429` with `Retry-After`.
4. A caller submits a large gateway body or a crafted proxy path: the request is rejected before forwarding.
5. A malicious site submits a write with the user's cookie: the Strict cookie and Origin check prevent the request.
6. The backend token is omitted or both tokens are identical: protected routes fail closed with `503`.
7. A log consumer inspects security events: it receives request IDs, routes, roles, outcomes, and timing—not bodies or credentials.

## Public-release gate

- Use only synthetic, non-sensitive data and mocked or tightly budgeted provider accounts.
- Store five independent high-entropy secrets in Vercel/Cloud Run; verify none are public environment variables.
- Verify authentication and authorization from both the browser gateway and direct backend requests.
- Verify login and backend rate-limit failure paths, audit event delivery, log access controls, retention, and alerts.
- Bound Cloud Run concurrency, instance count, request timeout, and provider spend.
- Confirm database encryption, backups, least-privilege access, patching, and recovery ownership.
- Rotate any setup credential that was exposed outside the approved secret store.
- Re-review this model whenever identity, tenancy, data sensitivity, proxy routes, providers, or deployment topology changes.
