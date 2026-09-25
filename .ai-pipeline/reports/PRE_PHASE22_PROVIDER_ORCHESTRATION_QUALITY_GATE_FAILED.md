# Pre-Phase 22 Provider Orchestration and Sandbox Testing — Independent Quality Gate

Date: 2026-09-24
Reviewer role: fresh, review-only combined quality gate
Branch: `feature/pre-phase22-provider-orchestration`
Current source revision: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`
Tested candidate: uncommitted 85-path working-tree candidate described below
Independent verdict: **FAIL**

## Executive result

The candidate is not ready for publication or human PR preparation. A fresh
falsification found that the generic resume/advance helpers skip the newly required
`GOLDTIER_SEARCH` stage and move a registry-complete record directly to `DOCUMENT`.
This violates the sponsor-directed early-Search order and makes the schema-v5 legacy
compatibility claim unsafe for persisted in-progress records. Two further bounded
acceptance defects affect provider truth and the HR Sandbox console: Mock mode is
labeled `SANDBOX_PARTIAL`, and Search always reports entity resolution as
`NOT_ASSESSED` instead of producing the required result.

The reviewer did not implement a workaround. Candidate publication remains blocked
pending bounded remediation, affected and broad verification, and a fresh independent
gate over a newly frozen candidate.

## Candidate identity and review boundary

Before review, immediately before writing, and again after writing this report (always
excluding only this report), the reviewer independently obtained:

- branch: `feature/pre-phase22-provider-orchestration`;
- `HEAD`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`;
- `origin/main`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`;
- merge base with `origin/main`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`;
- 72 tracked working-tree modifications, 13 nonignored untracked candidate files,
  and zero staged paths;
- 85 candidate paths total, excluding only this quality-gate report;
- ordinal, case-sensitive `path<TAB>git-hash-object`, LF-joined with no terminal LF,
  SHA-256:
  `70ee1102996ba8b9db26e7442e174c141e0b0518c9bf5ebd96cb5ab70ec41858`.

The review was local and read-only except for this report. No external provider was
called, no provider mutation was attempted, no Docker daemon was started, no database
URI was read or used, and no product, test, contract, decision, or implementation-report
content was changed.

## Blocking findings

### PP22-QG-001 — High — Legacy/restart advancement bypasses early GoldTier Search

`apps/backend/app/services/zero_touch_orchestration.py:2121-2130` implements
`_next_stage`, but its ordered sequence omits `AutomationStage.GOLDTIER_SEARCH` and
places `DOCUMENT` immediately after `REGISTRY`. The companion transition map at
`apps/backend/app/services/zero_touch_orchestration.py:2134-2141` likewise maps
`REGISTRY` directly to `DOCUMENT`.

A fresh direct invariant check produced:

```text
next_after_registry=DOCUMENT
stage_after_registry=DOCUMENT
AssertionError: next-stage bypasses early Search
```

The main creation path special-cases Search, so new happy-path tests can pass. That does
not protect a persisted pre-feature/in-progress record whose completed stages contain
only `REGISTRY`, nor any path that uses the generic transition helpers. Such a record
can resume at Document before Search. The persistence fixtures now commonly include
both `REGISTRY` and `GOLDTIER_SEARCH`, which does not falsify this adverse legacy state.

Required outcome: make the canonical stage-order helpers include the early Search
checkpoint, add a regression for a registry-complete legacy/restart record without the
new field/stage, and rerun orchestration plus memory/Mongo compatibility evidence. The
reviewer does not prescribe an implementation beyond preserving the single workflow
owner and fail-closed semantics.

### PP22-QG-002 — Medium — Mock GoldTier status is classified as Sandbox Partial

`apps/backend/app/api_provider_sandbox.py:48-60` hard-codes the status response
classification to `SANDBOX_PARTIAL`. The endpoint at lines 147-171 correctly emits
`mode="MOCK"` when the Sandbox connector is not configured, but it cannot emit the
canonical Mock classification. A fresh in-process request using default test settings
and an HR actor returned:

```text
200 MOCK SANDBOX_PARTIAL False GOLDTIER_SANDBOX_NOT_CONFIGURED
```

This conflicts with the canonical target entry in `docs/PROJECT_STATE.md:23`, where
GoldTier mode `mock` is classified `MOCK`, and it makes the HR provider-status display
internally inconsistent. Provider capability classification must be derived truthfully
from the active mode without implying Sandbox behavior while Mock is active.

Required outcome: return a mode-consistent classification, cover at least Mock and
configured Sandbox status, and keep the host/credential projection safe.

### PP22-QG-003 — Medium — HR Sandbox Search does not produce entity-resolution result

The assigned console contract explicitly requires an entity-resolution result after
bounded Customer Search. `apps/backend/app/api_provider_sandbox.py:73-80` constrains
the field to the sole literal `NOT_ASSESSED`, and the Search route at lines 173-218
returns candidates without invoking the existing resolution owner. The frontend then
displays that placeholder as the result
(`apps/frontend/src/pages/GoldTierSandbox.tsx:219`). The focused backend and frontend
tests encode `NOT_ASSESSED`, so their passing result confirms the omission rather than
falsifying it.

Required outcome: satisfy the assigned result contract through the existing entity
resolver (not a second resolver), with bounded inputs and tests for meaningful result
states, or obtain an explicit scope/authority change before claiming this console
requirement complete.

## Required-category assessment

| Required category | Result | Independent assessment |
|---|---|---|
| GoldTier workflow/order | **FAIL** | New-case source paths preserve Search before Document and target mutation, but the canonical resume helpers bypass Search (PP22-QG-001). |
| No duplicate customer / exact-existing behavior | Pass in reviewed paths | Exact existing-customer disposition retains the proved ID and skips Shell; focused tests cover no duplicate Shell dispatch. This does not cure the resume-order defect. |
| Early Search | **FAIL** | Creation is early, read-only, identity-bound, and persisted; legacy/restart advancement is not (PP22-QG-001). |
| Incremental target ledger / no replay | Pass in reviewed paths | Shell, Policy, and Amend remain separate ledger operations; stopping, `IN_PROGRESS` uncertainty, retained outcome, and no-replay behavior remain ledger-owned. No parallel mutation owner was found. |
| Sandbox writes | Pass with explicit blocked limitation | No GoldTier mutation is currently possible through the console: seven mandatory policy fields remain `TBD_SPONSOR`, and the standalone write endpoint is blocked by the mandatory case ledger. RP dispatch remains blocked on the unresolved `childId` lifecycle. These are truthful blockers, not successful write evidence. |
| ACRA official Mock contract/auth | Pass at the authorized boundary | `api_marketplace_mock` is distinct from local Mock and generic Sandbox, is labeled non-production Mock, and composition fails closed while the auth scheme is unresolved. The recorded no-auth HTTP 401 proves only reachability/auth requirement. This reviewer made no ACRA call. |
| Provider truth | **FAIL** | GoldTier Mock status is labeled `SANDBOX_PARTIAL` (PP22-QG-002). No Live claim or silent provider fallback was found elsewhere. |
| COI profile | Pass | The POC profile requires legal name, registration identifier, and country; address is optional and compared only when supplied. The legacy profile remains unchanged. |
| HR RBAC / no case access / no browser credentials | Pass | `PROVIDER_SANDBOX_TEST` is backend-authoritative and HR-only; direct non-HR calls are denied. HR does not receive `CASE_ACCESS`, and the browser projection contains only safe host identity and no credentials. |
| HR Sandbox console function | **FAIL** | Bounded Search and dry-run surfaces exist, but the required entity-resolution result is never assessed (PP22-QG-003). |
| Progress UI / backend authority / cache scope | Pass | The UI consumes backend-authored stages and target states. Added Sandbox and case query keys remain authenticated-user scoped; existing logout/session/401 clearing patterns are retained. |
| Entity-resolution / UBO / risk regressions | Pass, bounded | The orchestration path uses the existing resolver; no second UBO engine or regulatory-risk owner was introduced. UBO remains deterministic Decimal/advisory and mock risk remains advisory. The separate console omission is PP22-QG-003. |
| Persistence / restart / legacy compatibility | **FAIL** | Additive schema-v5 fields and target receipts are present, but a registry-only legacy/in-progress record can resume past Search (PP22-QG-001). Fresh physical Mongo evidence is unavailable because the Docker Desktop Linux daemon is absent; no unknown/shared database was used. |
| Security | Pass for reviewed boundary | Backend capability enforcement, bounded criteria/body settings, safe connector errors, redacted host-only status, no browser credentials, and blocked standalone writes were verified in source and focused tests. No secret was exposed by the review. |
| Audit | Pass with stated limitation | Case activity/exception owners remain intact. Provider-console diagnostics are bounded, sanitized, and process-local; they are not represented as a durable enterprise audit archive. |
| Test evidence / dynamic counts | **FAIL overall** | Fresh focused tests and checkers pass, but they omit or encode the three defects above. Counts are recorded as observed, not treated as permanent constants. |
| Authority labels | Pass | Sponsor-confirmed, user-authorized POC, provisional, official-documentation, Mock/Sandbox Partial, and `TBD_SPONSOR` boundaries remain distinguishable. No observed status was promoted to sponsor confirmation. |
| Q-016 | Pass | Assignment/note/SLA mutation scope remains unchanged and deferred. |
| Phase 22 | Pass | Phase 22 remains explicitly held; no activation claim was found. |

## Fresh verification evidence

The reviewer ran risk-focused, non-provider checks against the frozen content:

- backend focused pytest across provider Sandbox API, ACRA modes, CLM/zero-touch
  orchestration, document processing, and Phase 12 persistence:
  **222 passed**;
- frontend focused `GoldTierSandbox.test.tsx`: **1 file / 3 tests passed**;
- frontend TypeScript typecheck: **passed**;
- direct project-state, architecture, policy-authority, external-provider-readiness,
  and secret checks: **passed**;
- `git diff --check`: **passed** (line-ending conversion warnings only);
- all 13 nonignored untracked candidate files: no trailing whitespace and final-newline
  check **passed**;
- direct stage-order invariant: **failed** with both helpers returning `DOCUMENT` after
  `REGISTRY` (PP22-QG-001);
- direct default-mode provider status check: returned `MOCK` with
  `SANDBOX_PARTIAL` (PP22-QG-002).

The implementation report additionally records, for this same candidate fingerprint,
`1320 passed / 35 expected physical-only skipped`, frontend `23 files / 285 tests`,
contract `44/44`, governance/security `159/159`, Playwright `14/14`, and the other
listed static/dynamic checks. Those broader implementer results were inspected and
cross-checked against source and focused tests, but are not relabeled as independent
reruns.

One earlier Windows lifecycle run recorded a pre-header loopback timeout (`22/23`),
followed by an exact-test pass (`1/1`) and an unchanged complete pass (`23/23`). The
failure history is properly retained. Given the exact recovery and subsequent unchanged
full pass, it is not by itself classified as a product blocker; it also does not offset
the deterministic blockers above.

Fresh physical Mongo verification was not possible: the Docker client exists, but the
Docker Desktop Linux daemon pipe is absent. This is recorded as missing infrastructure,
not as passing current physical evidence and not as permission to use an unknown URI.

## Architecture and complexity assessment

The intended owner boundaries are mostly preserved: orchestration owns the read
checkpoint, the existing resolver owns match decisions, the target ledger owns mutation
ordering/no-replay, repositories own reconstruction, backend capabilities own access,
and React Query owns browser cache lifecycle. No direct ACRA-to-GoldTier mapping,
second ledger, second ownership engine, frontend authorization owner, or live-provider
fallback was found.

However, PP22-QG-001 demonstrates duplicated stage-order knowledge: the domain order and
new creation behavior include `GOLDTIER_SEARCH`, while two service helpers retain the
old order. That divergence is a concrete architecture/legacy defect, not merely a
future decomposition opportunity. Remediation should restore one consistent workflow
order without adding another owner or compatibility fallback.

## Known limitations and readiness

- GoldTier customer mutation remains blocked by seven `TBD_SPONSOR` policy fields and
  by the mandatory case-bound target ledger. No write evidence exists.
- Related-party creation remains blocked on the sponsor-defined `childId` lifecycle.
- ACRA Marketplace Mock authentication remains unresolved. The recorded unauthenticated
  401 is not an auth scheme and not interoperability proof.
- Physical Mongo behavior is not freshly proved on this host because the Linux daemon
  is absent.
- Q-016 remains open and unchanged.
- Phase 22 remains on hold.
- Production ACRA, GoldTier/PingFed, vendor OCR, SSO, Camunda, regulatory-risk, and
  autonomous approval claims remain out of scope and unproved.

## Required next action

Preserve this failed report. Remediate PP22-QG-001 through PP22-QG-003 in a bounded
implementation run, add adverse regression coverage, rerun every affected and broad
verification surface, freeze a new candidate identity, and request a fresh independent
combined quality gate. A repository-owner human retains all merge authority.

FAIL
