# Security policy

## Supported versions

Security fixes are applied to the current `main` branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not include exploit details, secrets, or personally identifiable information in a public issue.

Do not open public issues for suspected vulnerabilities. GitHub private vulnerability reporting is enabled for confidential reports.

## Deployment security

The reference deployment includes signed dashboard sessions, viewer/operator authorization, bearer-protected backend routes, bounded rate limits, and structured audit events. Operators must still provide unique secrets, retain and monitor platform logs, rotate credentials, keep the backend and database patched, and follow the [threat model](docs/threat-model.md).

Shared demo passwords are not an identity provider. Replace them with managed single sign-on and per-user authorization before using confidential, regulated, or customer data.
