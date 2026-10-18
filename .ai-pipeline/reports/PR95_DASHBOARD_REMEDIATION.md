# PR95 independent-gate remediation

Outcome: the three required findings in PR95_DASHBOARD_QUALITY_GATE.md are corrected;
independent re-gate and final clean-commit pre-PR verification remain required.

Identity: local task branch codex/pr95-dashboard-remediation-20261018; remediation
starts from integrated aa8b9a4333f8858262fe5c15cdccd1e1272ace36, whose merge parents
are published PR95 1c1fd9fbf1a68f79137d150ac8609cf811b10938 and accepted main
cc10a2b626ef92d2dd44600d488c1f15cc4f04f8. The final independent report records the
new frozen commit/tree. The first FAIL report remains immutable.

- F1: DashboardService first resolves authorized/date-selected cases. Creator-only
  counts/lists remain separate from resolver aggregation. Mine exposes only the
  requesting actor's workload row, including that actor's successful fixes on
  authorized teammate cases. Other-team/excluded-date fixes remain excluded.
- F2: timing prose describes recorded processing-attempt durations and retained
  workflow-start-to-completion duration. No timing formula, persistence field,
  orchestration owner or waiting-time measurement is invented.
- F3: the selectable category badge now says Available. Provider classifications
  and their existing backend disclosures are unchanged.

F1 was reproduced with a failing teammate-only-resolver test before correction.
F2/F3 had failing rendering assertions before label correction. Focused backend
checks include different creation/start/completion times and a 2-hour retained
blocker with a 12ms processing sample. Physical parity covers both team/mine views
and date ranges after reconstructing adapters from retained data; creator lists
remain empty for the resolver-only actor. The enhanced actual-browser regression
creates and confirms a synthetic Mock case through the normal UI, then asserts a
visible nonzero Singapore segment and no invented Australia segment from the
backend weekly response, alongside filters, reload and history navigation.

The original independent gate executed all 24 guarded physical suites:156 passed,
zero failed/errors/skips. Its ordinary full backend run was interrupted, not passed;
the final full run must explicitly load AnyIO when unrelated plugin autoload is
disabled. The earlier HTTP seeder timeout passed its isolated rerun; final broad
execution must include it. No test is weakened or skipped to obtain acceptance.

API/type additions retain original historical_trend schema/calculation and omitted-
date all-history totals. Browser initialization explicitly requests30d. Memory/Mongo
creator projections and filters are parity-tested. Durable schema, CAS/create/update/
delete semantics, connectors, mappings, config, dependencies, authorization grants,
architecture owners and provider classifications remain unchanged. Dashboard runtime,
read projections, descriptive metrics and presentation are the assigned changes.

The coordinator owns Git mutations. Local commits are explicitly authorized; no
push, PR creation/replacement, shared-history rewrite, PR96 change or merge is allowed.
Next authorized action: fresh independent re-gate on the frozen corrected content,
then clean committed pre-PR verification and owner handoff.

Round 2 F4 remediation: canonical backend `project_case_timing` now supplies additive
case_elapsed_ms for each dashboard case and oldest-open workload value, sharing the
single data_as_of observation. Both manager/mine table display, sort and age predicates
consume that duration. Completed durations remain fixed. Dashboard timing/persistence
read failures use sanitized503 without raw facts/errors. Two backend tests and both
interactive table regressions failed first; source corrections preserve the existing
view/filter layout and all scope decisions. Physical restart parity now includes
active and completed case durations. No schema/write or connector change is involved.
Round 2 full backend before this fix:2780passed/162skipped (156physical+6Tesseract),
3expected malformed-input warnings,1061.01s. It is baseline evidence only. The immutable
round2 report records FAIL for F4; a fresh corrected-content gate remains required.

Round 3 corrections (F5/F6/F7): the service reads authorized cases and its existing
automation input once each before sampling one clock. The saved automation list is
reused; no query, authorization or persistence owner is added. Date cohorts, the
legacy trend, case ages and workload share that final observation. Exact timedelta
floor division and integer means preserve recorded milliseconds and floor only
sub-millisecond fractions. Three new regression tests failed first: overlapping
reads, calendar/trend observation boundaries and1001ms resolution precision.
The physical completed-case fixture now retains the full canonical stage prefix,
start and meaningful stage metrics; canonical validation runs before create. Existing
decode and timing/parity assertions remain strict, and physical fractional-resolution
parity is added. The prior155/1 physical failure reproduced serially from the invalid
fixture; it is not attributed to resource contention. The separate full-backend HTTP
seeder body-read timeout remains an observed failed attempt requiring fresh complete
serial execution; the isolated8.35s PASS does not clear it. Fresh independent gate
and clean committed pre-PR verification remain required on the new frozen content.
