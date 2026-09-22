# External Provider Secret and Transport Security Runbook

This runbook applies when a future provider activation is separately authorized. It
does not activate a connector or create a secret-manager dependency.

1. The integration owner confirms the authority, scope, environment, and rotation /
   revocation status. Quarantined material is never opened, tested, copied, or reused.
2. The owner delivers fresh least-privilege secrets, tokens, certificates, or private
   CA references through the approved out-of-repository mechanism. No secret appears in
   Git, docs, issue, PR, log, screenshot, browser field, fixture, or normal evidence.
3. The backend alone consumes secret references. Frontend configuration, case history,
   provider DTOs, and normal logs contain no token, password, authorization header,
   private key, certificate private key, or secret-bearing URL.
4. HTTPS and certificate verification remain enabled. There is no TLS-disable flag,
   wildcard certificate bypass, or uncontrolled redirect. Redirects are disabled or
   explicitly controlled according to an authoritative provider contract.
5. GoldTier real transport requires TLS 1.3. mTLS/private CA is configured only when
   the sponsor contract explicitly requires and supplies its safe trust material.
6. Timeouts, rate limits, retries, idempotency and error mapping are implemented only
   from authoritative provider rules. An uncertain target outcome stops closed; it is
   not replayed and is never hidden by a Mock fallback.
7. Failures project to stable sanitized categories. Logs may retain safe provider ID,
   operation, state, correlation identifier and redaction result only.
8. A future authorized sandbox run produces the strict sanitized evidence profile. The
   evidence validator rejects unknown fields, credential/header/body/payload-shaped
   material, non-UTC timestamps, provider mismatch and unsupported promotion claims.

The current repository remains Mock/Local/Partial/Dormant as recorded in
`external_provider_readiness_registry.json`. Placeholder environment names in
`.env.example` are not consumed settings and are not readiness evidence.
