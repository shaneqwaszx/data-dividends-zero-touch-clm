# Phase 06 — Zero-Touch Orchestration

## Outcome

Phase 06 adds one sponsor-facing onboarding path:

`UEN + one PDF -> registry -> document policy -> ownership -> readiness -> Mock GoldTier`

The browser starts the case once and thereafter reads server-owned status. Deterministic
work continues without buttons until the case completes, reaches a typed business
exception, or records a technical failure. The accepted Phase 01–05 APIs remain
available only as historical/development boundaries; their UI controls are nested under
an explicitly environment-gated **Demo/Test Controls** section.

## Boundaries and ownership

- `ZeroTouchOrchestrator` owns stage order, checkpoints, status, events, metrics, loop
  limits, exception lifecycle, and automatic resume.
- Existing onboarding, document, ownership, readiness, and target services remain the
  owners of their records and domain rules. The orchestrator composes them; it does not
  duplicate their mapping or target-write logic.
- Provider selection is injected at composition or the demo boundary. The automation
  record retains only an opaque provider-binding ID; a process-local resolver recreates
  the same adapter at ownership resume. Provider objects and scenario names never enter
  persisted or browser-visible records.
- The process-local automation repository uses expected-version writes. A shared
  per-case lock serializes attach/start/resolve so duplicate or concurrent requests
  cannot advance the same checkpoint twice.
- Phase 05's pre-receipt target outcome ledger remains the authority for target-side
  replay protection and recovery. Phase 06 does not introduce another target ledger.
- The process-local document repository assigns an immutable monotonic insertion
  sequence on the first save of each document. Case document enumeration uses that
  sequence, so equal timestamps cannot make random UUIDs determine blocker order.

## State model

| Status | Meaning | Browser behavior |
|---|---|---|
| `PENDING_INPUTS` | Registry case exists; required PDF is not attached | Wait for sponsor input |
| `RUNNING` | Server is executing deterministic stages | Poll read-only status |
| `WAITING_FOR_REVIEW` | A typed business exception blocks progress | Render only server-authorized actions |
| `RESUMING` | A version-bound exception was resolved | Poll; no second start click |
| `RECOVERY_PENDING` | Phase 05 retained a target outcome but finalization remains retryable | Stop ordinary polling; a later start/recovery re-enters Phase 05 without replay |
| `COMPLETED` | Mock target sequence completed | Stop polling; show claim boundary |
| `TECHNICAL_FAILURE` | Infrastructure/provider/target/loop failure occurred | Stop polling; do not present as review or success |

Stage order is monotonic: `REGISTRY`, `DOCUMENT`, `OWNERSHIP`, `READINESS`,
`MOCK_GOLDTIER`, `COMPLETE`. A bounded transition loop fails safely with
`AUTOMATION_LOOP_GUARD` if ordinary stage progression cannot converge. Explicit
`CLM_FINALIZATION_RETRY_REQUIRED` is different: after a small local retry bound it
persists `RECOVERY_PENDING`, outside the progression loop guard.

Every repository write enforces the legal status transition and a completed-stage
ordered-prefix invariant. Unexpected exceptions around progression are converted to
one sanitized `ZERO_TOUCH_UNEXPECTED_FAILURE` terminal record at the active stage;
private exception text is discarded and later calls stop.

## Document decision and source authority

The Phase 06 auto-confirm rule is intentionally narrow and provisional. Every required
field must be present, pending, equal to the current canonical registry value under the
existing comparison rules, and at or above the configured threshold. The resulting
completion method is recorded as `AUTO_CONFIRMED`; Phase 03 manual completion remains
`HUMAN_REVIEWED` and its historical `ALL_FIELDS_MATCH` scenario remains manual.

Lifecycle `REVIEWED` means review finished; it is not semantic clearance. The checkpoint
re-evaluates every pending and reviewed case document against current canonical values,
reviewed/corrected values, confidence, missing fields, and explicit journey resolutions,
regardless of insertion order. Every blocked document is retained deterministically.

Mismatch, low-confidence, missing, or invalid review state creates a typed exception
that retains all detected blocker codes. `KEEP_REGISTRY_VALUE` is advertised only for
a source conflict. It appends a separate field-bound resolution record for this journey;
it does not rewrite extraction, reviewed value, or canonical-at-processing evidence. If
low confidence or another blocker remains, the server raises the next typed exception.
Low-confidence-only and missing-field exceptions expose no invented action. Resolution
binds to the automation/document versions and a server-only SHA-256 fingerprint of the
current canonical case and complete document set, recomputed while the case lock is
held. Canonical mutation without a document event therefore fails stale before any
review mutation or target call. Accepting a conflicting document as master data is not
implemented because Q-005/Q-014 remain open.

The document checkpoint evaluates every case-owned document, not only the newest.
Progression requires all of them to be reviewed under the integrated rule. Blockers are
presented in repository insertion order; document UUIDs remain identities only and have
no semantic ordering role.

Ownership cycle/incomplete exceptions and existing-party/partial-target outcomes expose
no approval action. Corrected replacement evidence or sponsor semantics are required;
Phase 06 cannot click through them.

## Idempotency, retry, and recovery

- Duplicate/concurrent start and resume requests are idempotent at completed, failed,
  or review checkpoints.
- Resolution requires matching case, active exception, automation version, evidence
  version, and an action from `available_actions`; stale/cross-case requests fail closed.
- No blind automatic provider retry is performed. The current provider protocols do not
  expose a sponsor-confirmed transient classification, and replaying target writes would
  be unsafe. The one narrow exception is `CLM_FINALIZATION_RETRY_REQUIRED`: Phase 06
  re-enters the same Phase 05 `submit` authority. Repeated recoverable failures persist
  `RECOVERY_PENDING`; a later start re-enters only finalization, preserving submission,
  correlation, and idempotency identity without repeating search, shell, policy, or amend.
- Repositories, locks, events, and ledgers are process-local. This POC does not claim
  durable restart recovery, distributed locking, or exactly-once delivery.

## Security and observability

PDF bytes are size/signature bounded, used synchronously, and not stored or returned.
Events and API errors contain fixed codes/messages, safe identifiers, stage/status, and
bounded evidence summaries; no raw provider payload, credential, token, file path, or
private exception text is projected. Metrics record automated stages, interventions,
exceptions, durations, and final outcome. They are operational POC evidence—not
business approval or production telemetry.

## Claim boundary

`COMPLETED` means the accepted Mock GoldTier path reached
`MOCK_GOLDTIER_SUBMITTED`. It does not mean legal/compliance approval, live ACRA or
GoldTier acceptance, or Ready-for-Approval. Live ACRA, sponsor document/UBO policy,
related-party writes, PingFed/GoldTier, reviewer authorization, retention, and final
approval semantics remain blocked by the existing sponsor questions.
