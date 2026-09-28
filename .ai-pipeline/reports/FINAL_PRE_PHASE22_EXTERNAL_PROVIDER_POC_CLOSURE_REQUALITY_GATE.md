# Final pre-Phase 22 external-provider POC closure re-Quality Gate

## Executive Result

**FAIL.** The frozen candidate is locally sound for the reviewed scope, and the three
prior local Quality Gate findings are closed. However, the assigned acceptance contract
requires all 14 criteria and an exact independent `PASS`. The retained external evidence
still contains only two real read-only XPI Searches (`NO_MATCH / 0`) and the truthful
official ACRA Marketplace Mock Garden result (`REVIEW_REQUIRED / PARTIAL`, zero
shareholders and relationships). It contains no safely created or reused sandbox
customer, Shell/Policy/Amend result, ledger-retained target ID, same-ID read-back, or
portal-visible customer. Criteria 5-9 and therefore criterion 14 fail.

The present blocker is external/authority-bound, not a newly found implementation bug:
the sole implemented onboarding route is Singapore/UEN while the supplied bounded
GoldTier registration vocabulary is Australian `ABN`. Inventing a UEN-to-ABN mapping
or introducing a second jurisdiction would violate current project authority. The
candidate is not ready to close this POC or advance on the strength of this gate.

### Findings first

1. **Acceptance blocker — external lifecycle remains incomplete.** No authorized
   customer mutation occurred, so the required create/reuse, operation, ID, read-back,
   and portal evidence does not exist.
2. **Authority blocker — no lawful identifier mapping is available.** Current contracts
   permit SG/UEN only; the supplied target vocabulary permits `ABN`. The implementation
   correctly stopped rather than fabricate a mapping or a second registry route.
3. **No open local Quality Gate defect found.** QG-01, QG-02, and QG-03 are fixed on the
   frozen candidate. Fresh focused, adversarial, full-backend, full-frontend, static,
   governance, and security checks passed.

## Phase Acceptance Checklist

| # | Acceptance requirement | Result | Direct evidence |
|---:|---|---|---|
| 1 | Official ACRA API Marketplace Mock is the registry environment | PASS | Retained Garden evidence identifies ACRA `MARKETPLACE_MOCK`; fresh projection preserved that environment and did not substitute local fixtures. |
| 2 | GoldTier uses the authorized sandbox environment | PASS | Current configuration/contracts and retained sanitized evidence identify sandbox `anz-nutmeg`; no Production or Live claim is made. |
| 3 | Real GoldTier Search succeeds through the application connector | PASS | Work evidence records two application-service/XPI connector Searches on 2026-09-27, both `NO_MATCH` with zero candidates and no Mock fallback. This gate performed no external call. |
| 4 | No local GoldTier Mock substitutes for the real sandbox path | PASS | The XPI path is an explicit `SANDBOX_PARTIAL` provider behind the controlled connector boundary. Tests force Mock only for ordinary isolated regression lanes; retained external evidence states no fallback. |
| 5 | Create one bounded sandbox customer, or safely reuse an exact prior customer | **FAIL** | Both duplicate Searches returned no match, and authority stopped execution before target-ledger reservation or mutation. No customer was created or reused. |
| 6 | Observe Shell/Policy/Amend results as applicable | **FAIL** | No Shell, Policy, or Amend request was sent; no external operation result exists. |
| 7 | Retain the GoldTier customer ID in the target ledger | **FAIL** | There is no created/reused target customer and no retained target-ledger ID. |
| 8 | Run real read-back Search and find the same customer/ID | **FAIL** | With no customer or retained ID, same-ID read-back evidence cannot exist. |
| 9 | Show the sandbox customer in the portal if technically available | **FAIL** | No customer existed to locate, and no portal-visible customer evidence was retained. |
| 10 | The local decision tree and sponsor-facing pipeline work correctly | PASS | QG-01/02/03 and ID provenance are closed; fresh adversarial projection, 76 focused backend tests, 4 focused frontend tests, 1,351 full backend tests, 287 full frontend tests, Ruff, mypy, and TypeScript typecheck passed. This local PASS does not override the external failures. |
| 11 | Garden remains truthful | PASS | Official-Mock evidence remains `REVIEW_REQUIRED / PARTIAL`, with zero shareholders and relationships. Fresh projection mapped both empty operations to `EMPTY`, the registry parent to `REVIEW_REQUIRED`, and did not inject local synthetic ownership. |
| 12 | No silent provider fallback occurs | PASS | Connector/configuration inspection, XPI tests, readiness checks, and retained evidence preserve explicit provider modes and fail closed. No ACRA or GoldTier fallback was observed or added. |
| 13 | Candidate contains no newly tracked secret or protected provider payload | PASS | `check_secrets.py` passed. DTOs and projections retain bounded safe fields; Search tests prove raw target data is not retained. No `.env`, credential, authorization header, confidential sponsor artefact, or raw payload was accessed by this gate. |
| 14 | Fresh independent Quality Gate returns exact `PASS` | **FAIL** | This independent closure re-gate returns **FAIL** because criteria 5-9 remain unsatisfied. |

## QG-01, QG-02, QG-03, and ID disposition

### QG-01 — historical v1/v2 order: FIXED

- Stage-order v1 keeps Search inside the legacy GoldTier target subtree and does not
  project a premature top-level Search.
- Stage-order v2 projects Search once, before document/reconciliation/ownership, and
  excludes a duplicate Search child from the target subtree.
- Fresh unit and adversarial checks passed for both versions.

### QG-02 — active checkpoint-absent Search status: FIXED

When Search has started but no checkpoint exists and operation evidence is still
`NOT_ATTEMPTED`, the automation stage owns the presentation status. Fresh parameterized
regression and an independent probe confirmed:

| Automation status | Projected Search status |
|---|---|
| `RUNNING` | `IN_PROGRESS` |
| `WAITING_FOR_REVIEW` | `REVIEW_REQUIRED` |
| `RECOVERY_PENDING` | `BLOCKED` |
| `TECHNICAL_FAILURE` | `FAILED` |

### QG-03 — complete checkpoint-absent Search view: FIXED

For all four states above, fresh inspection and adversarial execution confirmed that:

- status is automation-owned;
- timestamp is the latest retained `GOLDTIER_SEARCH_*` CLM event;
- safe text matches the status (`Search in progress`, `Search requires review`,
  `Search blocked`, or `Search failed`);
- an active Search-stage exception supplies the blocker code;
- record count and retained GoldTier ID remain absent without a checkpoint; and
- exact-match, no-match, and ambiguous branches all remain `NOT_REACHED`, with no
  invented timestamp, count, blocker, safe result, or ID.

### GoldTier ID provenance: FIXED

- A no-match Search plus a later Shell-owned ID leaves the Search node and every Search
  branch without an ID; the target path may retain the created/reused ID.
- An exact-match checkpoint may expose the ledger-owned matched ID on Search and its
  exact-match branch.
- Review-required Search does not acquire a target-path ID.
- The service passes the checkpoint's selected exact-match ID into the ledger-owned
  incremental target path; the browser response sources retained IDs from the target
  ledger/outcome, not from an unrelated presentation field.

## Contract and Integration Findings

### Current authority and integration result

The candidate preserves the required boundary:

`untrusted provider DTO -> canonical evidence/model -> target mapper -> controlled connector`

GoldTier remains explicitly `SANDBOX_PARTIAL`; XPI request/response models are strict,
connector paths are bounded, and optional `accountEntityType` / `productType` values are
sent only when usable authority is `SPONSOR_SUPPLIED` or `SANDBOX_OBSERVED`. Unconfirmed
optional values serialize empty rather than becoming invented defaults. The remaining
required enrichment fields continue to block request construction when absent.

Search resolution is fail closed: no match permits the new-customer branch, exact match
permits the existing-customer branch, and multiple/probable/hard-conflict evidence
requires review with zero Shell calls. Target writes remain ledger-owned and ordered;
post-dispatch uncertainty is non-replayable, recorded outcome finalization is retryable,
and later operations stop after failure or uncertainty.

The official ACRA Marketplace Mock Garden evidence remains partial and empty for
shareholders/relationships. It does not borrow the local Garden/SIM fixture, does not
claim complete ownership, and cannot reach target mutation.

### Quarantines and source precedence

No contradictory GoldTier example was promoted into a fixture, enum, DTO, mapper, or
assertion. The current contract/decision/mapping set remains authoritative over examples.
No direct ACRA-to-GoldTier mapping, route-to-Mongo access, alternate ownership engine,
second jurisdiction, or runtime composition of a dormant provider was introduced.

## Tester and Adversarial Findings

Fresh commands and exact results:

- Focused backend:
  `python -m pytest -p no:cacheprovider apps/backend/tests/test_goldtier_xpi_sandbox.py apps/backend/tests/test_garden_business_fixture.py`
  — **76 passed**, one deprecation warning.
- Full backend canonical suite:
  `python -m pytest -p no:cacheprovider apps/backend/tests`
  — **1,351 passed, 35 skipped**, four warnings.
- Focused frontend: `npm.cmd test -- --run src/GoldTierSandbox.test.tsx` — **4 passed**.
- Full frontend: `npm.cmd test -- --run` — **287 passed in 23 files**; existing React
  SSR/`act(...)` warnings were emitted, with no test failure.
- Frontend typecheck: `npm.cmd run typecheck` — **PASS**.
- Ruff: `python -m ruff check --no-cache apps/backend/app apps/backend/tests scripts tests`
  — **PASS**.
- mypy: `python -m mypy --no-incremental apps/backend/app` — **PASS**, 108 files.
- `check_project_state.py`, `check_architecture.py`,
  `check_external_provider_readiness.py`, and `check_policy_authority.py` — **PASS**.
- `check_secrets.py` — **PASS**.
- `git diff --check HEAD` — **PASS**; task-owned work Markdown also has no trailing
  whitespace and ends with LF.

The first sandboxed focused frontend attempt could not start esbuild (`spawn EPERM`). It
was rerun with approval outside the process sandbox and passed 4/4. This is an execution
environment limitation, not a product failure.

An over-broad repository-root `pytest -p no:cacheprovider` invocation was also attempted.
It collected 1,699 items but stopped on two contract-test import errors because
`phase13_contract_credentials` is not importable from that root invocation. The defined
canonical backend command targets `apps/backend/tests`; it subsequently passed 1,351/35.
The collection error is reported here and is not misrepresented as passing evidence.

Fresh adversarial execution additionally covered:

- checkpoint-absent Search status/text/timestamp/blocker/count/ID/branch coherence for
  `RUNNING`, `WAITING_FOR_REVIEW`, `RECOVERY_PENDING`, and `TECHNICAL_FAILURE`;
- no-match, exact-match, and review-required Search dispositions;
- no-match and exact-match ID provenance;
- Garden `PARTIAL` parent with two `EMPTY / 0` operations;
- target `IN_PROGRESS` (uncertain/non-replayable representation) and `FAILED` parent/
  child states; and
- historical v1 versus v2 ordering.

No network, portal, external provider, or physical Mongo check was run in this independent
gate. Prior retained external evidence was assessed; it was not replayed. Physical Mongo
was not required for this presentation/connector slice, and no disposable database was
authorized or provisioned.

## Code and Architecture Review

No current correctness, architecture, or maintainability defect was found in the frozen
candidate.

- The backend owns the bounded recursive workflow projection; the frontend renders the
  authoritative order and does not infer authorization, provider truth, or workflow
  state.
- Browser processing nodes forbid extra fields, bound strings/counts/children, and expose
  only safe summaries.
- Target operation ordering, call stopping, ID retention, and no-replay recovery remain
  ledger-owned.
- The existing deterministic Decimal ownership engine remains the sole UBO owner.
- Frontend workflow markup is semantic, collapsed by default, accessible by text and
  `aria` status, responsive, and reduced-motion aware.
- Documentation, decision, mapping, project-state, architecture, and task work records
  agree on the provider classifications and external blocker.

Accepted debt/later work is listed separately below and is not evidence for this POC.

## Security Review

No current security finding was found in the reviewed delta.

- No secret-bearing file was read; `.env` was not accessed.
- No credentials, tokens, headers, private keys/certificates, KYC/PII, document bodies,
  raw provider payloads, or private exception details were emitted or retained by this
  gate.
- Connector error mapping and browser DTOs expose controlled safe messages and bounded
  fields; raw XPI candidate payloads are not retained.
- Mutation remains opt-in, ledger-owned, and non-replayable after uncertain dispatch.
- Provider/context mismatch, malformed responses, missing authority, and unsupported
  paths fail closed.
- The fresh supported secret scan passed; repository status shows no newly tracked secret
  artefact.

Deferred hardening such as production credential lifecycle, TLS/mTLS posture, production
allowlisting, observability, and operational runbooks remains outside this sandbox POC
and must not be described as complete.

## Required Fixes

There is no local implementation fix required by this gate.

The current acceptance blocker requires new external/sponsor authority, not code guessed
from examples: provide an authorized Singapore/UEN-compatible GoldTier registration
contract/mapping (or explicitly authorize and design a separate jurisdiction route), then
rerun the bounded ledger-owned customer flow. Only after that authority exists may an
authorized run prove create/reuse, Shell -> Policy -> Amend as applicable, retained ID,
same-ID read-back, and portal visibility with sanitized evidence.

Later dependencies, not current fixes, remain: related-party child-ID and relationship
semantics; multi-level hierarchy; Ready-for-Approval behavior; Production/Live security
and interoperability; full MIS; and a full Exception Workbench.

## Readiness

- **Local criterion 10 / candidate implementation:** PASS for the reviewed scope.
- **Official ACRA Marketplace Mock truthfulness:** PASS as Mock/Partial evidence only;
  this is not Live ACRA verification.
- **Real GoldTier Search readiness:** demonstrated for bounded read-only Search in the
  authorized sandbox, with two `NO_MATCH / 0` results.
- **GoldTier customer mutation/read-back/portal proof:** NOT PROVED.
- **Overall final pre-Phase 22 POC closure:** **NOT READY**.
- **Next-phase readiness:** **NO**. This report authorizes no next phase, publication,
  commit, push, PR, or merge.

## Git Status and reviewed identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `BASE_SHA = HEAD = origin/main = 463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged changes: none.
- Reviewed tracked delta: 22 modified files; frozen binary diff hash, excluding all gate
  reports: `a36105932929e5a7a8cd12d5557206c076908d7b`.
- Reviewed work-record hashes:
  - `10-intent.md`: `DC9568BA6645C13D2C4E55B960A350C9EB67CFC4D5E62C2610B92BE8AE6828EC`
  - `20-checkpoint.md`: `712678A7DD2E3EF930210561634677CB9AB452CD8E03CEEF6B05B29754F1F8EF`
  - `90-evidence.md`: `6FE4B8099E4F51EFA280338E310BDDE63ADE83DBBA6D4C8556B4FEDE4FAB0AD4`
  - `99-reflection.md`: `F40AFA2F6F08135EF7293A82504AAD034B85407905988D723206A249136AF9AD`
- Existing untracked content before this gate: the four work records/directories and the
  three prior Quality Gate reports.
- Sole write by this independent run: this untracked closure re-Quality Gate report.
- No implementation, configuration, test, contract, decision, work-record, or other
  documentation file was edited. No stage, commit, branch/switch/rebase, push, PR, merge,
  provider mutation, portal action, or next phase occurred.
