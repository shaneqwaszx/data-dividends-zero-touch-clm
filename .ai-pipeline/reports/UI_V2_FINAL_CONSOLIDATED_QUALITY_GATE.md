# UI V2 Final Consolidated Independent Quality Gate

Date: 2026-09-02
Gate type: independent, review-only

## 1. Executive summary

**PASS.** The integrated UI V2 branch contains the intended Autoboard UI and the
bounded RQG-01 responsive correction, while the RQG-02 ordering and RQG-03 Windows
lifecycle fixes are inherited unchanged from authoritative `origin/main`. Fresh source
inspection, targeted checks, the complete backend suite, frontend verification,
contract/static/security checks, a 17-test Windows lifecycle suite, a supported live
Start → Status → Stop, and browser review found no Critical, High, Medium, or Low
finding.

All required final-zero metrics are zero. This report is the only repository file
created by this gate. No implementation, test, configuration, historical report, or
unrelated file was modified.

## 2. Branch / HEAD / origin-main baseline

| Item | Expected | Observed | Result |
| --- | --- | --- | --- |
| Repository | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` | exact path | PASS |
| Branch | `integration/ui-v2-finalization` | `integration/ui-v2-finalization` | PASS |
| HEAD | `5ec5b31` | `5ec5b31016c0159795976018adb52ee5f320b805` | PASS |
| `origin/main` | `eff81761a8dc355a56792aae4a1e8a738675b964` | exact SHA | PASS |
| RQG-01 ancestor | `71d62d2` | ancestor of HEAD | PASS |
| RQG-02 ancestor | `8309486` | ancestor of HEAD through `origin/main` | PASS |
| RQG-03/main ancestor | `eff8176` | ancestor of HEAD | PASS |

`git log --oneline --decorate -10` showed the expected integration, responsive,
ordering, and lifecycle history. The merge base of HEAD and `origin/main` is the
authoritative `eff81761...` commit.

## 3. Git inventory

The initial working tree had no tracked or staged changes. It contained only these
pre-existing untracked artefacts:

- `.ai-pipeline/reports/UI_V2_FINAL_REQUALITY_GATE.md`;
- `.ai-pipeline/reports/UI_V2_MAIN_SYNCHRONIZATION.md`;
- the protected unrelated filename beginning `e workspace and multi-document intake`.

The protected unrelated file was not opened, changed, staged, renamed, deleted, or
cleaned. Inaccessible historical pytest-cache directories produced status/search
warnings but were not changed. `git diff --check` and `git diff --cached --check`
passed. Nothing was staged.

## 4. UI V2 integration review

The integrated application renders the Autoboard shell and the exact visible
navigation order: New onboarding, Cases, Onboarded, Audit, Policy. New onboarding,
completed, review-required, registry-stop, case list/detail, client detail, Audit, and
Policy states were inspected against current backend behavior.

The UI remains a presentation/orchestration client. It does not calculate ownership,
choose a source of truth, replay target operations, invent approval, or create a second
workflow-state owner. Supported case/document/reconciliation/recovery operations remain
bound to existing backend routes.

## 5. RQG-01 verification

`OnboardedActionColumnHeader` renders `<th aria-label="Open" />`. The intended table
wrapper still provides contained horizontal scrolling and the table retains its 1100px
minimum width. Runtime inspection found zero `.sr-only` descendants within the
Onboarded scroll wrapper, while the action column retained the accessible name `Open`.

Onboarded search, jurisdiction filtering, row keyboard activation, and the Open button
remained functional. The 1280px desktop layout remained visually acceptable. No
document-level horizontal expansion was reproduced.

RQG-01 regressions: **0**.

## 6. Responsive viewport evidence

Fresh browser measurements for Onboarded:

| Requested viewport | Document scroll/client | Wrapper scroll/client | Table width | Result |
| ---: | ---: | ---: | ---: | --- |
| 1280 | 1280/1280 | 1223/1223 | 1222.81 | PASS |
| 1024 | 1024/1024 | 1100/967 | 1100 | PASS |
| 760 | 760/760 | 1100/722 | 1100 | PASS |
| 480 | 480/480 | 1100/450 | 1100 | PASS |

The wide table scrolls only inside its intended container at 1024, 760, and 480.
Cases also remained document-contained at all four widths, with its 980px table
scrolling inside 967px, 722px, and 450px narrow containers. Audit, Client detail, Case
detail, and Policy measurements likewise remained bounded by their document client
widths at every target.

Responsive regressions outside Onboarded: **0**.

## 7. RQG-02 verification

Independent source inspection confirmed the shared canonical helper sorts automation
records by `(item.updated_at, str(item.case_id))` with `reverse=True`. Both
`InMemoryZeroTouchAutomationRepository.list_records()` and
`MongoZeroTouchAutomationRepository.list_records()` delegate to that helper after
constructing defensive copies. Mongo envelope ordering remains separate and does not
govern the automation/API case list.

The retained contract is therefore:

1. automation `updated_at` descending;
2. exact timestamp ties by canonical `str(case_id)` descending.

RQG-02 regressions: **0**.

## 8. Ordering test evidence

The focused selection passed **4/4**:

- historical deterministic newer-first ordering and defensive copies;
- exact equal-timestamp case-ID tie behavior;
- automation ordering independent of opposite envelope ordering;
- equal-timestamp in-memory/Mongo-adapter parity.

The complete backend suite also passed with these tests included. No intermittent
historical ordering failure recurred.

## 9. RQG-03 verification

Source inspection confirmed `ConvertTo-UtcCreationInstant` normalizes typed
`DateTimeOffset`, timezone-aware `DateTime`, and offset-bearing ISO strings to UTC.
Null, unsupported, malformed, zone-less, and unspecified-kind values fail closed.
`Test-SameCreationTime` retains the narrow 1ms comparison tolerance. Launcher and
listener ownership pass typed values without the earlier lossy string cast.

Stop still precomputes launcher/listener ownership and refuses termination on unsafe
mismatch. No PID-only fallback or tolerance widening was found.

RQG-03 regressions: **0**.

## 10. Lifecycle evidence

`python -m unittest discover -s tests -p "test_demo_lifecycle_windows.py" -v`
passed **17/17** in 183.402s. Coverage included:

- UTC and UTC+08 representations of the same instant;
- invalid and zone-less creation times;
- valid launcher/listener ownership;
- wrong creation time and wrong executable;
- Stop refusal for mismatched or incomplete ownership;
- occupied-port non-termination and reset/start/stop sequences.

Ports 8000 and 5173 were free for the separate supported smoke:

- Start: exit 0;
- Status: backend `OWNED`, frontend `OWNED`, exit 0;
- backend `/health`: HTTP 200;
- frontend `/`: HTTP 200;
- Stop: exit 0;
- listener residue: 0;
- `.runtime/demo-processes.json` after Stop: absent.

## 11. F01-F05 status

| Prior finding | Fresh status | Evidence |
| --- | --- | --- |
| F-01 registry stop | CLOSED; regression 0 | Retained `WAITING_FOR_REVIEW`/`REGISTRY` case rendered `Registry unavailable`; no impossible targeted-retry text; attention and not-selected semantics were present. Controller tests passed in the 96-test suite. |
| F-02 scanner weakening | CLOSED; regression 0 | Scanner and its five tests passed; production branch has backend/security parity with `origin/main`. |
| F-03 stale new-case progress | CLOSED; regression 0 | Reset implementation and regression coverage passed within the frontend suite. |
| F-04 misleading registry icons | CLOSED; regression 0 | Runtime conflict showed `Jurisdiction status: attention`; absent route showed `Registry route status: not selected`; neither used a success check. |
| F-05 Policy classifications | CLOSED; regression 0 | Runtime rendered REAL, DERIVED, PENDING SPONSOR CONFIRMATION, and UNAVAILABLE; Q-012/Q-015 remained pending, not REAL. |

F01-F05 regressions: **0**.

## 12. UI truthfulness / API contract

- The account disclosure says `Local POC operator`, authentication is not connected,
  and no identity, role, or sign-out capability is claimed.
- Policy is visible and read-only; no mutation control or endpoint is present.
- Pipeline bands map Registry, Document, Ownership, Readiness/Mock target, and Complete
  from backend stages. No fake Screening/Risk/Approval stage is represented as real.
- Unsupported actor, loop, risk, review schedule, production client, and related values
  render as `—`, `Not available in current POC`, or an explicit pending classification.
- Client export, Start review, Audit CSV, document download, reviewer assignment, and
  return-for-rework mutations remain disabled when backend support is unavailable.
- The identifier label is exactly `Mock GoldTier party ID`.
- Onboarded includes only `COMPLETED` backend cases and carries a permanent Mock/POC
  disclaimer.
- Audit renders backend timeline events only; actor and loop are `—`.
- The fresh production bundle contained no prohibited `/api/cases`, `/api/clients`,
  `/api/audit`, `/api/reviewers`, `/api/policy`, assign, return-for-rework, or resubmit
  route and no operational browser mock/local-storage fallback.
- Runtime review-dialog interactions produced no forbidden route call and no browser
  console warning/error. The supported ownership GET returned 404 only when ownership
  evidence was not yet available; the client deliberately maps that response to null.

Truthfulness regressions: **0**. Unsupported API behavior: **0**.

## 13. Frontend tests / typecheck / build

| Check | Fresh result |
| --- | --- |
| `npm run typecheck` | PASS |
| `npm test` | PASS — 96/96 tests, 2/2 files (58 App, 38 UI V2 integration) |
| `npm run build` with output directed outside the repository | PASS — 42 modules; CSS 55.28kB; JS 231.77kB |

Frontend failures: **0**.

## 14. Backend regression

The complete backend suite passed once as required:

`714 passed, 11 skipped, 4 warnings in 19.40s`

The skips are the environment-gated genuine-Mongo tests. The warnings were the known
Starlette deprecation warning and deliberate malformed-provider serializer warnings.
No test failure or backend regression occurred.

Backend regressions: **0**.

## 15. Contracts / static / security

| Check | Fresh result |
| --- | --- |
| Contract tests | PASS — 44/44 |
| Ruff `--no-cache` | PASS |
| Strict mypy with external cache | PASS — 73 source files |
| `pip check` | PASS — no broken requirements |
| GoldTier validator unit tests | PASS — 5/5 |
| GoldTier example validator | PASS — 19 valid, 19 invalid/quarantined, 48 not validated |
| Secret-scanner unit tests | PASS — 5/5 |
| Standalone secret scan | PASS — no supported patterns found |

Contract regressions: **0**. Security regressions: **0**.

## 16. Runtime / browser review

The supported local workflow was run with ACRA Mock, local POC IDP, Mock Ownership,
Mock GoldTier, and process-local persistence. Browser review covered:

- New onboarding and bounded document input;
- Cases filters, search presentation, keyboard row navigation, and exact detail load;
- a completed straight-through case;
- a low-confidence `DOCUMENT_LOW_CONFIDENCE` review case;
- disabled Assign reviewer and Return for rework dialogs;
- Onboarded and Client detail;
- Audit filters/timeline-only evidence;
- read-only Policy;
- a retained jurisdiction-conflict Registry unavailable case;
- desktop, tablet, and mobile layouts.

No overlap, clipping, document-level overflow, broken enabled control, stale success,
fake data, unsupported mutation, or browser console/API failure was found. The in-app
file-chooser bridge timed out before attaching a local fixture; this was a browser-tool
limitation, not a product response. The same synthetic fixture was submitted through
the supported local backend endpoint and the browser then verified the resulting
backend-authored state.

## 17. Security / integration boundaries

The UI branch has zero material diff from `origin/main` under `apps/backend`,
`scripts`, root `tests`, `docs/architecture`, and `.github`. Consequently the accepted
ACRA guardrail, dormant/uncomposed live binding, secret scanner, Mongo persistence,
GoldTier contract, source-neutral reconciliation, jurisdiction gateway, and
deterministic/provisional UBO owners are inherited unchanged.

Fresh backend, contract, scanner, static, and runtime evidence remained green. Q-012
is still OPEN; the UI says live ACRA binding remains pending. No production-readiness
claim for real ACRA, PingFed, GoldTier, legal UBO, approval, or compliance was observed.

## 18. Real Mongo status

`PHASE12_MONGO_URI` was unavailable. The 11 genuine-Mongo tests were skipped by their
configured environment gate.

**REAL MONGO VERIFICATION WAS NOT EXECUTED LOCALLY.** Adapter/unit and full-suite
results are not represented as a genuine Mongo service pass. The external Mongo CI
gate remains required.

## 19. GoldTier private-data status

The optional GoldTier example validator executed successfully against the locally
available contract/example evidence and reported **19 VALID, 19 INVALID / QUARANTINED,
48 NOT VALIDATED**. The established quarantine classifications were unchanged. No
credential/authentication collection was inspected or used, and no private content was
copied into this report.

Real GoldTier/PingFed verification was not performed and is not implied.

## 20. Diff / scope audit

`git diff --name-status origin/main...HEAD` contains the intended UI V2 reports and
frontend integration files, including the focused RQG-01 component/test correction.
There is no branch diff in backend implementation, lifecycle scripts, root tests,
architecture, CI, ACRA, GoldTier contracts, persistence, or security tooling.

RQG-02 and RQG-03 are legitimate authoritative-main changes introduced by the final
merge; they are not UI scope creep. Unexpected backend divergence introduced by the UI
branch: **0**.

## 21. Findings

| Severity | Count | Finding |
| --- | ---: | --- |
| CRITICAL | 0 | None. |
| HIGH | 0 | None. |
| MEDIUM | 0 | None. |
| LOW | 0 | None. |
| INFO | 3 | Real Mongo unavailable locally; browser file-chooser bridge limitation; real external ACRA/GoldTier environments remain unavailable/unapproved. |

Required fixes: **none**.

## 22. Remaining sponsor / environment limitations

- Q-012 remains OPEN for the authoritative subscribed ACRA contract, authentication,
  endpoint, sandbox, and TLS details.
- Q-015 remains OPEN for source precedence, disagreement, reviewer/audit authority,
  retention, and production restart policy.
- Sponsor-approved document, confidence, UBO, reviewer/RBAC, related-party, and
  Ready-for-Approval policy remain unresolved as previously documented.
- Real Mongo was not available locally.
- Real ACRA, PingFed, and GoldTier sandbox interoperability was not executed.

These limitations constrain production/live readiness but do not block integration of
the truthful Mock/POC UI V2 finalization.

## 23. Final metrics

| Metric | Result |
| --- | ---: |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| Low findings | 0 |
| RQG-01 regressions | 0 |
| RQG-02 regressions | 0 |
| RQG-03 regressions | 0 |
| F01-F05 regressions | 0 |
| Truthfulness regressions | 0 |
| Unsupported API behavior | 0 |
| Frontend failures | 0 |
| Backend regressions | 0 |
| Contract regressions | 0 |
| Security regressions | 0 |
| Responsive target failures | 0 |
| Horizontal document overflow failures | 0 |
| Ordering regressions | 0 |
| Lifecycle regressions | 0 |
| Document-level responsive overflow defects | 0 |
| Browser console/runtime failures | 0 |
| Unexpected backend divergence caused by UI branch | 0 |
| Unrelated implementation changes created by gate | 0 |

All mandatory PASS metrics are zero.

## 24. Final verdict

The branch is ready to integrate as the final truthful Mock/POC UI V2 finalization.
This verdict does not authorize a commit, push, merge, rebase, or next phase, and it
does not imply production or live ACRA/GoldTier readiness.

PASS — READY TO INTEGRATE UI V2 FINALIZATION
