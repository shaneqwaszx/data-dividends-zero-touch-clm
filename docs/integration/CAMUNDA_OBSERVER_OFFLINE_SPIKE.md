# Camunda Observer Offline Contract Spike

## Evidence boundary

This document records a test-only reference contract derived from the source handoff
`CAMUNDA READ-ONLY OBSERVATION CONTRACT DRAFTED` at pinned baseline
`cab05d7dc98d4c50c8fc096835fe49802d5896e2`. The implementation and evidence are
offline: fake HTTP and fake engine clients only. There is no worker process, network
transport, server, database, credential, Camunda SDK, BPMN deployment, backend call, or
runtime composition.

The only successful claim is **OFFLINE CONTRACT VERIFIED** after the listed checks and
an exact independent `PASS`. It must not be described as Camunda integrated, runtime
ready, authenticated-worker ready, production ready, or end-to-end orchestration.

## Exact offline contract

- Job type: `clm.observe-case.v1`.
- Business variables: exactly one canonical UUID string named `caseRef`. Job key and
  retry metadata remain outside business variables. Variables cannot select a host,
  endpoint, method, header, tenant, credential, or transport option.
- Read boundary represented by the fake port:
  `GET /api/clm/zero-touch/cases/{case_id}`.
- One invocation performs at most two reads and has no polling, sleep, background task,
  or internal retry-until-stable loop.
- The read port exposes only `read_case`; the reference handler has no path for create,
  start, resume, review, replace, resolve, refresh, evaluate, submit, delete, provider,
  or repository-mutation operations.

An observed completion constructs a fresh `clmObservation` containing only:

```json
{
  "schemaVersion": 1,
  "caseRef": "00000000-0000-4000-8000-000000000123",
  "availability": "OBSERVED",
  "automationStatus": "RUNNING",
  "currentStage": "DOCUMENT",
  "automationVersion": 7,
  "clmVersion": 3
}
```

A safe unavailable completion constructs only:

```json
{
  "schemaVersion": 1,
  "caseRef": "00000000-0000-4000-8000-000000000123",
  "availability": "NOT_AVAILABLE"
}
```

Input variables and broad response objects are never merged into the result. Synthetic
fixtures deliberately contain a UEN, legal name, team, document body, reconciliation
detail, target identifier, and authorization marker; tests prove those values do not
enter output or captured failure diagnostics.

## Mapping to the pinned public response

The pinned `ZeroTouchCaseSummaryResponse` supplies the selected fields at these exact
locations:

| Observation field | Public response location | Pinned authority |
|---|---|---|
| `caseRef` | `case.case_id` | `OnboardingCaseResponse` nested by `ZeroTouchCaseSummaryResponse` |
| `automationStatus` | `status` | `AutomationStatus` |
| `currentStage` | `current_stage` | `AutomationStage` |
| `automationVersion` | `version` | `ZeroTouchAutomationRecord.version` |
| `clmVersion` | `clm.version` | `ClmOrchestrationRecord.version` |

The handler imports the existing automation enums for validation and creates no new
business-enum authority. Expected extra browser-response fields are ignored. The
production route, response models, authorization, and services are unchanged.

The current route is case-scoped. Absent and inaccessible cases share the safe `404`
projection. `401` and unexpected `403` are identity/configuration failures and are
never mapped to case absence. Current production authentication remains repository-backed
browser login plus an opaque process-local session; it does not provide an approved
machine identity, service account, bearer-token contract, or client-credentials flow.

## Three execution clarifications

1. Two matching reads mean only that `caseRef`, automation status/stage/version, and CLM
   version matched in those two observations. They do not prove an atomic multi-record
   snapshot, no intervening change, consistency of unobserved fields, continued
   stability until completion, or authority for a later mutation. A test changes an
   unobserved field between matching selected projections to make this limit explicit.
2. A first valid observation followed by safe `404` discards every first-read
   status/version value and completes only with `NOT_AVAILABLE`.
3. A lost completion acknowledgement remains ambiguous. The same invocation sends no
   immediate second completion and no contradictory fail command, and it performs no
   compensating CLM mutation. A later redelivery is a new invocation and observes again.

The fake engine's winner/loser behavior is only a protocol simulation. It is not proof
of Camunda delivery, activation-timeout, retry-decrement, or exactly-once behavior.

## Failure and completion dispositions

| Condition | Offline reference disposition |
|---|---|
| Invalid job type/input or extra business variable | Zero reads; one sanitized failure command; no success variables |
| First safe `404` | One read; fresh `NOT_AVAILABLE` completion |
| Two matching selected projections | Two reads; fresh allowlisted `OBSERVED` completion |
| Valid `200`, then safe `404` | Two reads; discard the first projection; fresh `NOT_AVAILABLE` completion |
| Selected-field mismatch | Two reads; sanitized `CASE_CHANGED_DURING_OBSERVATION`; no completion |
| `401` or `403` on either read | Sanitized authentication/configuration failure; no completion |
| Timeout, fake transport failure, or `5xx` | Sanitized backend-unavailable failure; no internal retry |
| Malformed, wrong-case, invalid enum/type, missing field, or oversized body | Fail closed without response/exception text |
| Completion rejected | Record rejection; do not send a fail command from the same invocation |
| Completion acknowledgement lost | Record ambiguity; do not repeat completion or send a fail command |
| Redelivery | Fresh reads; no inherited `clmObservation` |

Retry count and backoff are finite injected values on the fake fail command. No elapsed
time or global delivery-attempt guarantee is modeled. Body size is enforced before JSON
parsing of fake bytes; any future real transport would need its own streaming/body limit.

## Deterministic evidence

At the implementation checkpoint, the focused module was discovered and executed by
the repository-pinned pytest:

```text
python -m pytest apps/backend/tests/test_camunda_observer_contract.py -q
58 passed
```

The focused files also passed Ruff lint/format and strict mypy. Broader repository and
governance results are recorded by the final implementation handoff and independent
recheck, because counts and revision identity must remain tied to the exact tested tree.

The final implementation-tree backend run completed with `1059 passed, 17 skipped`;
the skips were the repository's environment-gated suites, not observer-contract cases.
Project-state, architecture, tooling-configuration, and supported secret checks passed.
Full Ruff lint and production-app mypy passed. Ruff's repository-wide format check is
not a baseline gate and reported 30 pre-existing files that would be reformatted; the
three task-owned files themselves pass Ruff format checking.

Tests cover matching observations, every selected-field mismatch, wrong returned case
identity, invalid automation enum/stage and scalar types, missing fields, prohibited or
malformed inputs, non-enumerating `404` cases, `200` then `404`, authentication failures,
timeout/transport/`5xx` on either read, malformed/oversized bodies, redelivery,
overlapping completions, lost acknowledgement, rejected completion, exact read/engine
call counts, data minimization, bounded failure parameters, and zero observer-attributable
forbidden calls.

## Limitations and real-experiment prerequisites

This test-only code does not exercise real authentication or its process-local session
housekeeping. The source handoff's qualification therefore remains: the production GET
is case/workflow/provider read-only, but current session validation can remove expired or
stale session state, so no unconditional zero-application-memory-mutation claim is made.
Fake zero-mutation evidence is not proof that the live endpoint has zero effects.

Before any real experiment, a separately authorized task would need:

- approved non-human identity, least-privilege case scope, credential lifecycle, and
  audit decisions;
- a decision on whether the current broad browser response is acceptable or a separate
  minimized read boundary is required;
- the actual Camunda version, deployment model, tenant, endpoint, SDK, authorization,
  licence, TLS/network path, and verified permissions;
- an approved non-production case/environment and explicit deployment, execution,
  stop, cleanup, and credential-revocation authority;
- a real transport with bounded connection/read timeouts and streaming/body limits.

None of those prerequisites is implemented or inferred here. Mutating Camunda/CLM
commands and the later thin-supervisor proposal remain deferred.
