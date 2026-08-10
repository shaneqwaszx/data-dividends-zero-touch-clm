---
name: integration-security-review
description: "Review security for this project's ACRA, IDP/document-upload, GoldTier/PingFed, and other external HTTP integration boundaries. Use when changes touch credentials, TLS, authorization, external payloads, KYC/PII, sponsor artefacts, logging, API/browser error projection, uploads, or mock/live configuration."
---

# Integration Security Review

Default to review-only. Implement remediation only when the task explicitly authorizes
changes. Read AGENTS.md, project context, the active planner, relevant decisions/open
questions, and the changed integration path before assessing it.

## Trace the data and trust boundaries

1. Trace configuration and data from external input through transport, decoder/source
   DTO, canonical model, target mapper, persistence/history/logs, API response, and
   frontend. Inspect both success and failure paths.
2. Identify trust transitions for ACRA, uploaded documents/IDP output, PingFed tokens,
   GoldTier EDS/XPI calls, sponsor artefacts, and any other external HTTP client.
3. Use references/review-checklist.md for the detailed project checklist.

## Enforce project-specific invariants

- Never track, log, persist in normal case history, render in the frontend, or include in
  errors: passwords, client secrets, tokens, authorization headers, private keys,
  certificates, sponsor credentials, or raw confidential sponsor artefacts.
- Keep private configuration backend-only and fail closed when required auth/config is
  missing. Do not inspect or reuse the quarantined PingFed/Postman collection.
- Require HTTPS and certificate verification. Never add a TLS bypass. Enforce GoldTier
  TLS 1.3 when real sponsor connectivity is implemented; record unknown ACRA TLS/mTLS/
  private-CA requirements as sponsor dependencies rather than guessing.
- Treat registry responses, HTTP errors, filenames, MIME declarations, uploaded PDFs,
  OCR/IDP output, and target responses as untrusted. Validate type, schema, semantic
  minimums, size/count limits, and allowed formats before canonical mapping or use.
- Project errors through stable trusted codes/messages. Do not expose raw bodies,
  validation internals, endpoints containing secrets, stack traces, or underlying
  exception text.
- Minimize payloads, retention, browser fields, fixtures, events, and logs. Use safe
  identifiers, status, correlation IDs, and sanitized summaries; keep KYC/PII out of
  normal logs.
- Keep mock/sandbox/live modes explicit. Synthetic success must not be represented as a
  live call or real interoperability proof.

## Report

Rank findings by severity with tight file/line evidence, affected boundary, exploit or
failure consequence, remediation guidance, and verification steps. Separate active
defects from accepted phase limitations and later sponsor dependencies. Never reproduce a
secret value in the report; identify only the safe filename/type and containment action.
