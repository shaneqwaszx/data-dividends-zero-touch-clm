# Integration security checklist

Load the sections relevant to the changed boundary.

## ACRA and external HTTP

- Require HTTPS, certificate verification, deliberately controlled redirects, bounded
  connect/read timeouts, and safe endpoint configuration without userinfo or secret
  query data.
- Add authorization only at the adapter boundary and exclude it from logs/errors.
- Validate response status, content type, body size, JSON shape, required nonblank
  fields, and UTC provenance before canonical mapping.
- Do not persist or log raw response bodies or sensitive request metadata.

## IDP and document upload

- Allow only explicitly approved document types and fields; do not infer sponsor scope.
- Enforce upload size/page/count limits, safe filenames, content-based type validation,
  parser isolation, and rejection of malformed, encrypted, or unsupported documents.
- Treat OCR/IDP text and metadata as untrusted; validate output and route low confidence
  or inconsistency to human review.
- Define retention, deletion, and access boundaries before using real KYC documents.
  Use synthetic, sanitized repository fixtures.

## GoldTier and PingFed

- Keep tokens and client secrets backend-only in approved secret storage; never place
  them in source, `.env`, tests, docs, frontend variables, logs, or error payloads.
- Do not use the quarantined authentication collection. Require approved replacement
  material and fresh credentials before real integration.
- Enforce TLS 1.3 for sponsor sandbox connectivity. Verify certificates and confirmed
  mTLS/private-CA requirements without bypass switches.
- Apply least-privilege scopes, bounded token lifetime, safe refresh/retry behavior, and
  operation-appropriate headers/idempotency without logging their values.

## API, UI, persistence, and logs

- Expose only browser-required source system, environment, timestamps, statuses, and
  safe identifiers. Keep internal registry references and target payloads server-side.
- Persist safe terminal errors before projecting sanitized 5xx responses; stop
  downstream connector calls after required-stage failure.
- Exclude KYC/PII, documents, payloads, exception text, credentials, and authorization
  material from normal logs, history, and telemetry.
- Keep mock/live labels prominent and prevent `COMPLETED` from implying the unresolved
  Ready-for-Approval transition.

## Sponsor artefacts and repository hygiene

- Keep raw sponsor files only under ignored `private/sponsor-artifacts/`.
- Confirm no secret, key, certificate, token, raw live payload, or confidential document
  is tracked, staged, included in build artifacts, or copied into fixtures/examples.
- Run configured secret/scanner tests and report known scanner coverage limitations.
