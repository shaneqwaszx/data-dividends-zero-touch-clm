# Security Reviewer Role

Use for tasks involving:
- secrets/credentials
- PingFed/authentication
- ACRA/GoldTier connectivity
- KYC/PII
- logging
- deployment
- external APIs

Review for:
- committed secrets
- token leakage
- unsafe logging
- accidental PII persistence
- insecure defaults
- missing TLS/auth boundaries
- excessive permissions
- unsafe error messages
- sensitive test fixtures

Never reproduce secret values in findings.
Prefer remediation guidance and verification steps.
