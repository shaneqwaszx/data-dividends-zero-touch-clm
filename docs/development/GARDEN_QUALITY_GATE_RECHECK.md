# Garden independent quality gate — recheck

## Result and identity

**FAIL** on 2026-10-01. The first gate's registry-status, processing-type and physical
test-coverage findings are remediated. Both offline Garden journeys still pass. Two
operator presentation defects remain, and required physical execution remains pending.
This is not exact PASS, publication readiness, or permission to begin another phase.

The first FAIL report, GARDEN_QUALITY_GATE.md, remains untouched. This fresh review had
no implementation/remediation role and wrote only this assigned report. The source
candidate was frozen throughout; all 44 manifest hashes matched before and after review.

| Identity | Value |
|---|---|
| Branch | fix/demo-happy-path-stabilization |
| Base / HEAD / local origin/main | efc31f450f0103766fa812bc0aa80754f801dbe9 |
| Candidate digest | 3ed727911f490b880ef80c1f60d34be9a608e2d9eb0e5b2fb6c7783ecb2092d2 |
| Manifest | tmp/GARDEN_REVIEW_MANIFEST.json; 44 paths |
| First candidate | tmp/GARDEN_REVIEW_MANIFEST_V1.json; original report retains its identity |
| Remediation delta | API projection; physical/orchestration tests; Garden browser test; CaseStatePanels source/test; styles; frontend types |
| Git state | Task-owned unstaged modified/new content; no publication |

## Original findings re-evaluated

| Finding | Recheck |
|---|---|
| GQ-01 stale registry review | RESOLVED: validated completed REGISTRY projects COMPLETE at readiness/completion; retained acquisition stays PARTIAL with EMPTY/UNSUPPORTED children; no current registry-review panel |
| GQ-02 document cards and zoom overflow | PARTLY RESOLVED: document field values are readable at all five widths and CSS 200%; actual root/body scroll assertions pass. Corporate particulars still collapses values into character columns at CSS 200% |
| GQ-03 omitted UNSUPPORTED processing type | RESOLVED: shared frontend union, label and symbol maps now represent Unsupported explicitly; focused rendering regression passes |
| GQ-04 physical status test coverage | COVERAGE RESOLVED BY INSPECTION: typed unsupported relationship operation performs no counted dispatch; exact UNSUPPORTED/null-provenance dictionary is asserted across both restarts. Physical execution is still REQUIRED/PENDING |

Aggregate identity completion does not fabricate complete source ownership. Normal
evidence retains the original collections, provenance and missing-source issue. The
backend owns the current identity/ownership/readiness states and UI actions. Unsupported
is neither an observed empty collection nor a provider failure.

## Remaining local findings

### GQR-01 — P2: confirmation action contradicts a red “No action available” message

At ready Review and Send, the Action required panel retains only
TARGET_CONFIRMATION_REQUIRED and correctly says the operator must confirm the frozen
destination, warnings and digest. Its decision metadata explicitly lists **Confirm frozen
target submission**, and the enabled normal **Confirm and send to Mock GoldTier** button
successfully completes the case. Nevertheless the same panel displays a red **No action
available** banner with **No safe resolution action is authorized for this retained
blocker. The workflow remains fail-closed.**

This is a reproducible false description of the functioning next action, visible in all
six screenshots. `project_human_interventions` in apps/backend/app/api_models.py defaults
no_action to the hard-stop message; the generic READINESS branch leaves it unchanged,
and available exception-resolution actions are empty because confirmation has its own
owner. Project the actual authorized confirmation route and inputs instead of the
generic no-action reason, without adding a second action or bypass. Add readiness
projection/UI regression and preserve the existing confirmation guard.

### GQR-02 — P2: Corporate particulars does not reflow at 200% content magnification

The reviewed document cards and overall scroll extent now pass. However the **Corporate
particulars** section immediately below Operational timing still maintains narrow
label/value columns at CSS 200%, causing company name, registration identifier and other
retained identity values to wrap into individual characters. This is visible in
a77f1b61da1583d61e7c7a6edc368373275c0894.png. Reflow this affected read-only evidence
section against its actual available width and verify useful value width/readability,
as already done for the document cards. No source or authorization change is needed.

## Independent execution and visual evidence

| Recheck | Result |
|---|---|
| Frozen manifest | PASS: 44 unchanged path hashes before/after |
| Backend orchestration/protocol/acquisition focused suites | PASS: 142 tests, 40.95 seconds; one Starlette deprecation warning |
| Frontend CaseStatePanels/manual evidence/performance | PASS: 33 tests / 3 files |
| Guarded ordinary Garden browser paths | PASS: 2 tests, 15.6 seconds |
| Five widths / document value width | PASS assertions and independent screenshot inspection: 360, 768, 1280, 1440, 1920 |
| CSS 200% zoom root/body scroll and document width | PASS; native browser chrome zoom untested; Corporate particulars defect separately retained |
| Focus-only navigation | PASS: registry focus changes focus with zero API requests |
| Confirmation / completion / Cases / Onboarded | PASS: no completion before explicit UI confirmation; completed case has no active exceptions and registry aggregate COMPLETE |
| Discrepancy path | PASS: four field acceptances, four audited Keep registry decisions, retained canonical identity, ownership review and readiness |
| Whitespace | PASS: tracked diff check |
| Physical Mongo | NOT RUN: user-prohibited normal Atlas/application database; no authorized disposable local service |

One scoped Garden run retained synthetic screenshots through an in-memory harness HTML
reporter override into OS temp. Candidate files were unchanged; owned loopback memory
services were cleaned up. No ambient app import, dotenv resolution or Mongo/DNS attempt
was repeated during this recheck. No external provider requests or target writes occurred;
the final target was local Mock. All current evidence remains synthetic offline protocol
input through the real decoder, never a current official observation.

Screenshots, all independently viewed, are under
`C:/Users/shane/AppData/Local/Temp/garden-qg-recheck-716mso90/data/`:

| View | File | Dimensions |
|---|---|---|
| 360 | 39428e4b33700e29fc6b01b6523a79296adadd88.png | 360 x 24634 |
| 768 | d33a359afb8c55e87ad10f6f9af30d7be2ea22cb.png | 768 x 16140 |
| 1280 | 053139e2f592d00560e31e63ef0fb07f01e891c9.png | 1280 x 14408 |
| 1440 | 42f1204352db0df08c5756a289259c8fc0165399.png | 1440 x 13479 |
| 1920 | d9626e5ad0d62e1963cac1def8a65038f98a1408.png | 1920 x 12643 |
| CSS 200% at 1440 | a77f1b61da1583d61e7c7a6edc368373275c0894.png | 1440 x 45319 |

Implementer-reported new broad evidence is 1491 backend pass/38 skip, 378 frontend pass,
22 canonical browser pass, 44 guarded contracts and Ruff/mypy/type/build/scanner pass.
Those reports are corroborating evidence, not independently reexecuted counts. First-gate
contract/security/architecture findings and limitations remain in the original report;
only the frozen remediation delta was changed and rechecked here.

## Safety, authority and readiness

No new canonical owner, dependency, target mapping, UBO threshold, schema envelope
version, provider endpoint/authentication, authorization policy or Live status was added
by this remediation. Backend presentation and frontend type/layout/runtime display
changed. New physical coverage exercises the already-added stored enum without weakening
CAS, document/version binding, confirmation or no-replay. No secret/confidential source
was introduced in the reviewed delta. No Git mutation, provider dispatch, database cleanup,
unrelated process termination or candidate fix occurred in this review.

Required physical Mongo evidence remains unavailable and independently prevents exact
PASS under fyp-quality-gate. An authored restart test cannot substitute for execution.
Current official ACRA coverage remains unobserved in this run; explicit synthetic protocol
labels are truthful but cannot satisfy official-observation acceptance. External reads
require separate bounded authorization. GoldTier Sandbox remains PARTIAL; child identity,
name-only match authority, final approval and Live interoperability remain later sponsor
dependencies. The pre-existing project-state baseline conflict and occupied Windows
lifecycle port remain distinct limitations from the two current UI defects.

**Next authorized action:** remediate GQR-01 and GQR-02 within the assigned owners, obtain
focused regression/visual evidence, freeze new content and assign fresh independent
re-QG. Obtain required physical evidence only through a separately authorized disposable
service/publication-CI route. This report does not authorize publication or waive any
acceptance criterion. Exact independent verdict remains **FAIL**.
