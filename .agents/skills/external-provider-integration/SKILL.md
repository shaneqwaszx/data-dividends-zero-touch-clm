---
name: external-provider-integration
description: "Use when adding or changing ACRA, GoldTier, PingFed, vendor IDP/OCR, ownership services, or any future external HTTP/API provider, sandbox, authentication, contract, adapter, or live-mode behavior."
---

# External Provider Integration

## Trigger

Use for new or changed external endpoints, operations, modes, transport, auth/TLS,
decoders, provider DTOs, mappings, error/retry/timeout behavior, or sandbox/live proof.
Mock-only internal fixture changes use the phase/regression workflow unless they alter
provider parity or claims.

## Purpose

Integrate untrusted external systems through existing ports with authoritative contracts,
truthful mode labels, safe errors/data, deterministic call stopping, and no secret
persistence.

## Inputs

- assigned operation/provider and intended classification;
- authoritative contract plus samples/discrepancy records;
- current port, adapter, mapper, composition and Mock behavior;
- authorized sandbox/account prerequisites and required business outcome.

## Mandatory context

Read `AGENTS.md`, current state/architecture/workflow, the provider contracts,
decisions/open questions, current connector/mapper/composition/tests,
`sponsor-contract-reconciliation`, `architecture-change-review` when an owner changes,
and `integration-security-review` with its checklist.

## Preconditions

- Endpoint/schema/mandatory fields/auth/TLS/error/timeout/rate/idempotency authority is
  sufficient for the assigned operation.
- Credentials are owner-provisioned through approved runtime secret handling, never repo files.
- Current Mock and call-stopping behavior is understood.
- Provider mode and evidence classification are separate and explicitly named.

## Analysis steps

1. Reconcile every material contract/sample difference. Catalogue unresolved conflicts;
   quarantine invalid examples. Stop behavior dependent on missing authority.
2. Perform the architecture existence check. Extend the current provider port/adapter;
   do not create a second router or business owner for convenience.
3. Define strict source DTOs and validation: status/content type/body bounds/schema,
   identity binding, semantic minimums, timestamps and safe provenance.
4. Map `source DTO -> canonical evidence -> target/domain use`. Business logic never
   imports or branches on raw provider payloads.
5. Compare Mock parity operation by operation: request meaning, semantic outcomes,
   errors, partial/not-found behavior, ordering and prohibited claims. Mocks remain
   deterministic and credential-free, not copies of confidential payloads.
6. Review auth/TLS: backend-only injection, least privilege, certificate verification,
   redirect policy, TLS 1.3 for GoldTier, mTLS/private CA only when confirmed, redaction
   and rotation/revocation boundaries.
7. Define bounded connect/read/overall timeout and retry policy. Retry only operations
   whose idempotency and duplicate-call consequences are authoritative; otherwise stop
   with an uncertain outcome and no replay.
8. Map provider failures to stable sanitized codes. Never retain/log raw bodies,
   credentials, URLs with secret data, stack traces or KYC/PII.
9. Define exact call count, ordering and call-stopping assertions for success, absence,
   partial, invalid, timeout, auth and downstream failure.
10. Produce sanitized sandbox evidence: mode, operation, time, safe correlation,
    outcome and checks—never credentials/raw customer/provider content.
11. Run security review, contract/conformance tests, POC regression, checkers and QG.
12. Update state only to the proved classification. Tool or credential availability is
    not Live readiness.

`PARTIAL` permits only explicitly enumerated authority-independent scaffolding such as
an existing-port test seam or documentation of a blocked mode. The report must list
every permitted and blocked slice. It never permits wiring known fields, transport,
fallback, retry, canonical mapping, or runtime composition that depends on a missing
contract/security decision.

## Allowed changes

- Focused adapter/DTO/mapper/port/composition/config/tests and truthful documentation.
- Explicit fail-closed provider modes and sanitized execution evidence.
- Mock updates required to preserve approved semantic parity.

## Forbidden changes

- Raw provider DTOs/payloads in business logic, persistence, normal logs or browser output.
- Direct ACRA-to-GoldTier mapping or provider selection from user-controlled URLs/names.
- Silent Sandbox/Live-to-Mock fallback or false success for demo continuity.
- Hard-coded/repository-stored secrets, TLS disablement or certificate bypass.
- Arbitrary retries, replay after uncertain target activity, or retrying validation/auth failures.
- Treating incomplete samples, credentials, Mock tests, tools or sandbox success as Live.

## Stop conditions

Stop when contract authority is incomplete/contradictory, required auth/TLS/idempotency/
rate behavior is unknown, safe secret provisioning is absent, canonical mapping is
unconfirmed, sanitized evidence is impossible, Mock fallback is demanded, or the change
would bypass an existing port/ledger.

## Required tests

- strict DTO/schema/identity/provenance and canonical mapping tests;
- Mock parity and connector conformance;
- exact call-count/order/call-stopping for every outcome;
- timeout/retry/no-replay/error-redaction tests;
- contract tests, relevant backend/POC regression, secret scanner;
- `python scripts/check_architecture.py` and `check_project_state.py`;
- `integration-security-review` and independent QG;
- sanitized sandbox smoke only when authorized and required.

## Required evidence

- authority/discrepancy classification and quarantines;
- adapter/port and canonical mapping diagram;
- auth/TLS/secret/redaction review;
- timeout/retry/error and call-count matrix;
- Mock parity result, exact tests, sandbox classification and residual blockers.

## Expected report

```text
PROVIDER INTEGRATION: PROCEED | PARTIAL | STOP
Provider / operation:
Mode / classification:
Contract authority / discrepancies:
Port / canonical mapping:
Auth / TLS / secrets:
Timeout / retry / error mapping:
Mock parity / call stopping:
Sanitized sandbox evidence:
Tests / reviews:
Blocked capabilities:
```

## Handoff format

Give the implementer exact authoritative operations, DTO/mapping/port boundaries,
allowed modes, secret injection owner, timeout/retry/error matrix, call assertions and
tests. Give security/QG sanitized evidence and unresolved questions. Give the owner
manual account/OAuth/certificate/token steps. Never hand off raw credentials or claim
Live without the complete evidence chain.
