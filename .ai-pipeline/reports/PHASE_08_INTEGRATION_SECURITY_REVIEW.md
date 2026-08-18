# Phase 08 Integration Security Review

## Scope reviewed

The input-driven PDF upload path, `LocalPdfTextIdpProvider`, document projection,
replacement/supersession endpoint, ZeroTouch re-evaluation, UEN-keyed Mock providers,
and Developer/Test control separation.

## Findings

No Critical, High, Medium, or required-fix Low finding remains in the Phase 08 changed
path.

- Upload metadata remains case-bound, strict `application/pdf`, safe display-name
  validated, stream-size bounded, and signature/EOF checked before provider invocation.
- The local parser is in-process but network-free, strict, rejects encrypted/malformed
  PDFs through a stable sanitized failure, and bounds page count (10) plus extracted
  text (64,000 characters). It does not follow PDF references or claim malware/CDR.
- No-text PDF returns derived `DOCUMENT_TEXT_UNAVAILABLE`; it does not fabricate OCR
  evidence. Parser output is reconstructed through the existing strict four-field DTO.
- PDF bytes and full raw text remain transient and absent from repositories, events,
  broad responses, export, and normal logs. Browser receives only accepted safe fields,
  comparisons, confidence, and safe constant provenance.
- Replacement validates the case/document relationship, current unsuperseded state,
  expected event count, active document-review stage, and nonterminal automation state.
  Historical extraction is retained; stale, superseded, cross-case, and terminal paths
  fail safely. Superseded evidence is excluded from readiness while unrelated current
  evidence remains authoritative.
- Normal sponsor start uses no scenario parameter. Gated Developer/Test scenario routes
  are separate and create their own case; they cannot alter an already-created sponsor
  case. Mock/local labels remain explicit.

## Accepted POC limitations

This is not production PDF isolation, malware/CDR, authenticated review, encrypted
durable evidence storage, retention implementation, OCR/IDP service, or live ACRA/
GoldTier security verification. Q-003, Q-005, Q-013, and Q-014 remain open. No raw
sponsor artefact or credential was accessed.

## Verification

Initial implementation evidence recorded 500 backend tests. The remediation rerun passed
502 tests, strict mypy passed (56 files), Ruff passed, secret tests passed (5), and the
expanded Phase 08 PDF/replacement tests passed (8).

## Remediation follow-up — 2026-08-18

### Result

**No current Critical or High integration-security finding in the remediated Phase 08
boundary.**

- The normal Windows launcher now selects `IDP_CONNECTOR_MODE=local_pdf_text`; its
  console mode and `/api/system/execution-profile` report `LOCAL_PDF_TEXT` / `LOCAL`.
  Developer Mock IDP use remains behind the existing demo-only route boundary.
- The local parser remains in-memory, network-free, and bounded by the existing upload,
  page, and extracted-text limits. No raw PDF bytes or complete extracted text were
  added to state, logs, API responses, or the browser.
- Sponsor evidence refresh uses the authoritative zero-touch summary case ID, version,
  and update timestamp. Document and ownership requests are scoped to that same
  server-authored case ID; no cross-case identifier or client-derived evidence is sent.
- The added ownership and Mock GoldTier UI sections consume existing minimized models or
  a new server-authored operation-status projection only. They do not expose provider
  payloads, request bodies, credentials, headers, endpoints, idempotency bindings, or
  fingerprints.
- Windows startup normalizes only the launcher process environment before child launch,
  preventing a case-insensitive `Path`/`PATH` collision without modifying machine
  variables. The launcher checks bindability before launch and continues to refuse broad
  image-name or blind port termination.

### Remaining limitations

Production parser sandboxing/CDR, authenticated review/RBAC, durable encrypted storage,
and live ACRA/GoldTier/PingFed/TLS verification remain unimplemented phase non-goals.
The Windows launcher was subsequently verified through a clean start/health/stop cycle;
the bindability preflight continues to preserve unrelated occupied-port owners.
