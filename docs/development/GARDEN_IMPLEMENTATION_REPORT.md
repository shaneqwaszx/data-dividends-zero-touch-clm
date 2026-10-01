# Garden Happy Path & Operator Experience — Final Report

## 1. Executive Summary

STATUS: PARTIAL. Both normal-UI Garden journeys pass with explicitly synthetic offline
Marketplace protocol input, local extraction/manual ownership and Mock GoldTier.
Required physical Mongo acceptance remains pending for CI's disposable mongo:7 service.
Fresh official-provider observations have not been authorized or executed. This is an
uncommitted implementation handoff, not publication readiness or sponsor acceptance.

## 2. Repository

| Item | Evidence |
|---|---|
| Repository | C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm |
| Branch | fix/demo-happy-path-stabilization |
| Base / HEAD / local origin/main / merge-base | efc31f450f0103766fa812bc0aa80754f801dbe9 |
| Initial tree/index | clean; mandatory read-only preflight passed |
| Final implementation | task-owned changes, unstaged and uncommitted |
| Git/network operations | no fetch, switch, worktree, reset, stash, clean or publication |
| Safe preflight | Settings(_env_file=None), test/memory/Mock; no external calls |

## 3. ACRA

Entity Profile, Officers and Shareholders retain existing strict supported contracts.
LLP Highlights, Capital Details and Relationships remain unsupported. Relationships now
has UNSUPPORTED, zero records, no call and no invented endpoint/timestamp/provenance.
EMPTY still means an actual decoded empty response. PARTIAL acquisition keeps its
ownership gap while valid canonical identity proceeds to the existing ownership owner.
FAILED acquisition and invalid canonical identity still stop dependent work.
The registry pipeline reports completion of validated identity separately from retained
PARTIAL source acquisition. Historical missing ownership is informational once the
registry stage completes; the current ownership/readiness owner supplies the actual action.

The browser fixture exercises the production Marketplace adapter and token decoder
through injected allowlisted synthetic transports, with simulated empty shareholders.
Its banner explicitly states synthetic offline test evidence. No current official
response, address, officer or interoperability result is claimed.

## 4. GoldTier

Primary completion uses local Mock GoldTier, with explicit durable target confirmation
and the existing ordered ledger. Sandbox remains PARTIAL and read-only/preview evidence.
Name-only candidate 143878 is not promoted to an exact match. ADR-007 does not authorize
an operator-attested target identity. Related-party calls remain BLOCKED_CONTRACT /
BLOCKED_CHILD_ID_LIFECYCLE; no child ID, relationship or hierarchy rule is invented.
Console help covers criteria, classification, constants, dry-run and required sponsor
child lifecycle authority. Preview validation does not imply dispatch or acceptance.

## 5. Cases and Onboarded

Completed accessible cases already remain in Cases; Onboarded is an overlapping view.
No status predicate or deduplication change was needed. UI copy makes this clear.
The happy browser journey verifies the same completed Garden case in both views;
backend regression retains each separate accessible completed case.

## 6. Clean Journey

Ordinary UI: login → Singapore/Garden intake → clean synthetic client PDF → validated
identity/PARTIAL acquisition → reviewed matching local document → classification →
structured reviewed 60/40 declaration → ready Review and Send → explicit confirmation →
Mock target completion → Cases and Onboarded. Ownership remains client-supplied LOCAL /
MANUAL_DECLARATION_POC, calculated by the existing Decimal engine. The actual registry
ownership collections remain empty. Confirmation is the remaining actionable checkpoint
before target writes; all active blockers clear only after successful completion.

The late-loading document regression demonstrated a silent submit failure before the
fix. The form now submits the same current reviewed document it visibly selects, retaining
server-side evidence version validation. The focused regression passes after the fix.

## 7. Human Intervention

The conflicting synthetic PDF produces four field discrepancies. Four normal document
acceptance actions retain the document observations; four explicit Keep registry value
decisions reconcile them without canonical overwrite. The final reconciliation returns
to the retained ownership blocker, then structured ownership submission reaches readiness.
No discrepancy test performs an external target write. Pending current document fields
remain reviewable during bounded pre-confirmation ownership review; completed/submitted
mutation guards, lock authorization and CAS remain authoritative.

## 8. Blockers

| Item | Classification | State |
|---|---|---|
| Ownership absence misreported as invalid registry identity | local defect | fixed, focused/full/browser evidence |
| Relationships absence fabricated as provider EMPTY | provenance defect | fixed; unsupported/no call |
| Reconciliation shows stale DOCUMENT stage | local defect | fixed; current remaining stage retained |
| Ownership selection empty after async documents load | local UI defect | reproduced, fixed, regression/browser pass |
| Duplicate intake / intelligence refresh | local performance defect | guarded intake; intelligence dispatch 2→1 |
| Retained registry gap still demanded review after recovery | independent GQ-01 | fixed; current-stage projection and readiness/completed regressions |
| Document/corporate character columns / magnified overflow | independent GQ-02/GQR-02 | fixed; scoped document/header/retained-card/corporate reflow; stronger browser checks pass |
| False no-action banner beside enabled confirmation | independent GQR-01 | backend projects existing confirmation control; UI uses backend no-action reason; failing regression repaired |
| Shared processing UNSUPPORTED maps missing | independent GQ-03 | fixed; typed union/label/symbol aligned |
| Physical UNSUPPORTED roundtrip absent | independent GQ-04 | authored explicit persisted status/null-provenance assertions over both restarts; execution pending |
| Physical Mongo | missing infrastructure | required, pending CI mongo:7; Atlas prohibited |
| Windows lifecycle | occupied shared resource | port 8000 occupied; preserve unrelated process |
| Project-state baseline | pre-existing baseline conflict | accepted HEAD already names unreachable d23d7b7; checker fails |
| Official Mock/current Sandbox observations | external authority/evidence | not executed; no inferred interoperability |
| Sandbox child identity / name-only candidates | sponsor dependency | fail-closed retained |

## 9. Performance

Reproduce memory/Mock before/after measurements with
`.venv/Scripts/python.exe scripts/profile_garden_local.py --iterations 5`.
The baseline is a read-only archive of accepted base source, not a Git worktree.
Both children refuse external connects and omit dotenv. Post-remediation sample medians:

| Action | Before ms | After ms | Samples per side | Browser calls in final Garden run |
|---|---:|---:|---:|---|
| Create/start | 6.06 | 5.42 | 5 | 3; offline UI interval 146–160 ms |
| Open detail | 15.68 | 15.03 | 25 | 6; UI interval 153–159 ms |
| Accept document field | 25.68 | 24.28 | 15 | 1 POST + 4 GET; 218–279 ms |
| Reconciliation decision | 46.32 | 31.89 | 5 | 4; 155–316 ms |
| Manual ownership | 23.28 | 18.16 | 5 | 4; 262–314 ms |
| Policy rebind | 27.97 | 21.22 | 5 | backend benchmark only |
| Classification save | 28.66 | 24.16 | 5 | 1 PUT; 90–105 ms |

Backend benchmark and browser intervals measure different boundaries and are not directly
comparable. Host variance is substantial; no provider/projection latency improvement is
established. The demonstrated request reduction is intelligence invalidation 2→1 with a
real QueryObserver, retaining dependent refreshes. Registry-focus navigation makes zero
requests. Browser action progress is immediately visible. Every external provider count
is zero; simulated dispatch counts are separate evidence. Mongo latency was not measured.

## 10. Files and Change Surfaces

- Backend: existing registry connector/errors/adapter/domain/API, registry ownership,
  onboarding and orchestration owners; create_app test injection/profile label.
- Frontend: intake guard, existing cache effects, case status/progress/manual form,
  Cases copy, ACRA and GoldTier console help, scoped document/header/evidence reflow;
  corresponding types/tests.
- Verification: focused backend/cache/physical test, two synthetic PDFs and generator,
  strict offline transport, guarded E2E launcher/Garden tests, performance profiler,
  delivery fixture inventory.
- Documentation: ACRA profile and dated ADR-007 amendment; task plan, operator guide,
  this report and independent gate report.

API/type: additive UNSUPPORTED and test-only profile presentation value. Durable schema:
no envelope version bump or repository owner change; additive stored operation enum
requires physical read/restart evidence. Connector: unsupported no-call behavior changed;
no endpoint/auth expansion. Configuration: runtime modes unchanged; explicit isolated
test launch flag added. Business rule: valid identity separated from ownership gap within
existing reviewed manual workflow; no ownership threshold/precedence/approval change.
Mapping/auth/security: no target mapping or policy authority change; existing safeguards
preserved. Architecture: existing owners retained, injected test transport only. Provider
classification: no Live promotion. Runtime: corrected bounded progression, async form
selection, request deduplication and action feedback.

## 11. Verification

| Check | Latest result |
|---|---|
| Full backend pytest | PASS: 1491 passed, 38 skipped, 4 warnings; physical skips not evidence |
| Ruff backend and changed scripts/tests | PASS |
| Strict mypy app | PASS: 112 source files |
| Full frontend | PASS: 379 tests / 32 files; existing act/SSR warnings |
| Frontend typecheck/build/dependency graph | PASS; optional platform packages absent |
| Canonical browser | PASS: 22 isolated lifecycles on second candidate; final presentation delta rechecked by both Garden paths (13.7s) |
| Responsive/accessibility | widths 360/768/1280/1440/1920; CSS content zoom 200%; existing keyboard/focus/hover suites |
| Contracts | PASS: 44 tests |
| Focused harness/delivery checks | PASS: 52 tests |
| Applicable governance/security/harness tests | PASS: 193 tests |
| Architecture/tooling/policy/provider-readiness/secret checks | PASS |
| Project-state checker/current-baseline unit | FAIL: pre-existing unreachable verified_main_sha |
| GoldTier example validator | completed: 19 VALID, 19 INVALID_QUARANTINED, 48 NOT_VALIDATED; no promotion |
| pip check | PASS |
| Whitespace/new task-owned text hygiene | PASS |
| Windows lifecycle | 3 date tests pass; 20 runtime tests blocked by occupied port 8000 |
| Physical Mongo | PENDING locally, required CI service evidence after authorized publication |
| pre_pr_check publication gate | NOT RUN: intentional uncommitted handoff |

The initial broad backend run exposed the superseded cache expectation; the updated
22-test cache suite and fresh full run pass. Initial root blanket discovery was unsuitable
for contract import layout and hit sandbox temp prerequisites, occupied port and the new
fixture inventory; proper configured contract/harness commands passed after inventory
update. Generated legacy screenshots were preserved under ignored tmp and restored to
accepted bytes without index/Git metadata mutation, avoiding unrelated artifact churn.

## 12. Independent Quality Gate

First independent verdict: FAIL, recorded in GARDEN_QUALITY_GATE.md on frozen digest
5efb38952c96d941ae814d22f145daa9454a060fdb52b1444d377bfad00011d2 (42 paths).
Second independent verdict: FAIL in GARDEN_QUALITY_GATE_RECHECK.md on
3ed727911f490b880ef80c1f60d34be9a608e2d9eb0e5b2fb6c7783ecb2092d2 (44 paths).
GQ-01 through GQ-04 and GQR-01/GQR-02 led to bounded remediation above. The last
confirmation unit/browser assertions reproduced the misleading banner before both its
backend projection and frontend unconditional fallback were repaired. Corporate values
now have useful width at CSS 200% content magnification; native chrome zoom is untested.

Final frozen candidate: 3cc6d9bd753b825450e9618a4e9f7b44604cc0bc12debf1ea6079a2bfed17a5b
(46 paths). Fresh independent final recheck: **FAIL** in
[GARDEN_QUALITY_GATE_FINAL_RECHECK.md](GARDEN_QUALITY_GATE_FINAL_RECHECK.md), solely
for unverified required physical Mongo/current official-provider evidence. All local
findings are resolved; no reproducible local defect remains. Independent execution:
142 backend (42.67s), 74 frontend, both Garden paths (14.3s), six inspected screenshots
including readable Corporate particulars at CSS 200%; all 46 frozen hashes unchanged. Current focused backend 142, frontend 379,
both Garden paths, configured strict mypy, type/build and whitespace pass. The full
1491-backend/38-skip and 22-browser runs preceded this final presentation-only delta;
they are corroborating evidence rather than executions of the final frozen bytes.

[fyp-quality-gate](../../.agents/skills/fyp-quality-gate/SKILL.md) requires **FAIL** when
an "unverified required criterion" remains. Required physical Mongo and current official
observations remain unverified; neither authored tests nor synthetic inputs waive them.

## 13. Provider Activity

Actual external ACRA reads: 0. Actual GoldTier reads: 0. Actual external writes: 0.
Implementation uses explicit guarded test settings and does not inspect dotenv,
MONGO_URI, credentials or protected payloads. During first independent review, one
unguarded contract-import command implicitly resolved normal settings (possibly dotenv)
and attempted Mongo DNS resolution. It timed out before an established database
client/server connection, with no database mutation or URI disclosure. This was an
unsafe verification path; it was stopped. Guarded discovery applied the repository
ordinary-test environment before app imports and passed. Do not repeat that command.
No normal application database cleanup or physical use occurred.
Inert test credentials are generated in process and never reported. No target state replay.

## 14. Sponsor and External Dependencies

Official network observations require a separate bounded approval: token ×1,
entityBasicInformation ×2, coShareholdersDetails ×1; Relationships ×0, GoldTier ×0,
external writes ×0. This four-request budget is documented, not dispatched.
GoldTier childId lifecycle and name-only target identity remain sponsor controlled.
Normal Atlas persistence is not disposable physical test infrastructure. CI must prove
the exact published candidate's guarded physical suite before final acceptance.

## 15. Final Verdict and Next Authorized Action

Local offline clean path: PASS. Local discrepancy/human progression: PASS. Current
official API coverage: strict implemented profile/officer/shareholder contracts, no
fresh network evidence. GoldTier Sandbox: PARTIAL. External submission: NOT EXECUTED.
Publication: NOT YET REQUESTED. Overall completion: PARTIAL. Independent final gate is FAIL solely for required
physical evidence and current official observations; local implementation findings
are resolved. The physical acceptance requirement remains intact.

Implementation and fresh independent local review are finished. Required physical Mongo
execution remains pending locally; use the existing GitHub CI mongo:7 suite on the exact
candidate after separately authorized publication, unless an approved disposable service
becomes available first. Current official observations likewise require bounded authority.
No commit, fetch, push, PR, merge or Git-state repair is authorized by this handoff.
Preserve the port occupant and the user's normal Atlas database.

## 2026-10-01 official evidence continuation

Current official networked ACRA Marketplace Mock acquisition is now independently
VERIFIED: OAuth1, entity/basic2 and shareholders1 all returned HTTP 200 within the
new explicit authorization. Source candidate 3cc6d9bd753b825450e9618a4e9f7b44604cc0bc12debf1ea6079a2bfed17a5b
is unchanged. PARTNERSHIP and the actual returned business address differ from the
offline fixture; SG remains a project-derived default, entity status remains null,
shareholders EMPTY and Relationships UNSUPPORTED/no-call.

The original network-backed browser case did not complete because the temporary
harness missed asynchronously rendered document review controls. Corrected captured-
company-data replay completed locally with officer personal data omitted; no source
fix was required. Actual-composition HR zero-call configuration/unsupported checks pass.
Overall exact gate remains FAIL for the unverified original full journey and physical
Mongo, which remains required through CI mongo:7 after authorized publication.
See [official verification report](OFFICIAL_ACRA_GARDEN_VERIFICATION_REPORT.md) and
[independent evidence gate](OFFICIAL_GARDEN_EVIDENCE_QUALITY_GATE.md) for current counts,
safety chronology, limitations and frozen evidence. No publication occurred.
