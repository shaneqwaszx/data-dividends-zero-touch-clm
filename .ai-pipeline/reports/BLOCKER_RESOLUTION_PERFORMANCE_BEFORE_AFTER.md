# Blocker review performance before and after

Status: final comparable measurements and required local regressions PASS; independent acceptance pending.

Baseline production source: e799d74063678bb0eccbea445d5ab3c8628dd2c0, exact ignored Git
archive. Only the common measurement test/helpers and pinned runtime were supplied to
the archive; baseline production behavior was unchanged. Candidate: uncommitted branch
feat/blocker-resolution-idp-ux-optimization. The final manifest identifies exact bytes.
Measurements ran sequentially on the same Windows host with identical inputs within each
lane. Browser groups use 1280x900; the separate mobile check restores this viewport.

## API: 30 four-decision groups per revision

Workload: four low-confidence synthetic identity observations ACCEPTED through actual
in-process HTTP TestClient. Each confirmation is followed by the same four supporting
GETs. The low-confidence evidence remains blocked and target calls stay zero. This
compares confirmation and authoritative refresh, not a browser or production SLA.

| Measure | Baseline | Candidate |
|---|---:|---:|
| POSTs per four decisions | 4 | 1 |
| Supporting GETs | 16 | 4 |
| Reconciliation evaluations | 4 | 1 |
| Authorized continuation calls (blocked workload) | 0 | 0 |
| Document section saves | 5 | 1 |
| Median request plus refresh (ms) | 74.48 | 69.94 |
| p95 request plus refresh (ms) | 96.10 | 93.60 |
| Median complete four decisions (ms) | 293.77 | 69.94 |
| p95 complete four decisions (ms) | 330.47 | 93.62 |

Request/refresh baseline has 120 observations versus candidate30; total-group comparisons
have 30 each. p95 uses sorted index floor(0.95*(n-1)), as the executable script specifies.
Elapsed times include local service/persistence/projection work and fluctuate with the host.
The deterministic request/save reduction, not a fixed timing threshold, is acceptance.

Receipts: [baseline API](BLOCKER_REVIEW_BASELINE_METRICS.json),
[candidate API](BLOCKER_REVIEW_CANDIDATE_METRICS.json).
Reproduce with scripts/benchmark_blocker_review.py, --samples30, and candidate --batch.

## Physical Mongo: one diagnostic group per revision

Workload: four missing native-PDF fields REJECTED, with the same supporting refresh waves.
CommandListener counts only command names during confirmation/refresh. Each revision uses
a newly generated allowlisted disposable database on the owned local Mongo7 server,
verified removed afterward. No URI, command payload or protected database is recorded.

| Server commands | Baseline | Candidate |
|---|---:|---:|
| find | 497 | 147 |
| update | 21 | 5 |
| Total observed | 518 | 152 |
| Target calls | 0 | 0 |
| Final state | WAITING_FOR_REVIEW | WAITING_FOR_REVIEW |

These are one-group counts, not a latency distribution or percentiles. They include
supporting reads, so they are distinct from the instrumented document section-save count.
Receipts: [baseline Mongo](BLOCKER_REVIEW_BROWSER_EVIDENCE/baseline-mongo-commands.json),
[candidate Mongo](BLOCKER_REVIEW_BROWSER_EVIDENCE/candidate-mongo-commands.json).
Reproduce with scripts/benchmark_blocker_review_mongo.py and explicit --root/--batch.

## Browser: 30 groups / 120 choices per revision

The identical ambiguity TXT workload is REJECTED through actual rendered controls and
authenticated local HTTP/process lifecycles. The baseline starts its single-field request
on each choice; the candidate stores choices locally, then confirms once. Measurement
excludes setup, screenshots and the separate mobile viewport check. Each candidate SELECT
must stay enabled/focused and pass an actual center-point DOM hit-test. Choices issue no
GET or mutation. After confirmation, missing evidence stays blocked and no target write
occurs. The candidate primary action has AA contrast and passes the mobile viewport check.

All three baseline and candidate sample groups passed (30 groups / 120 choices each).
Candidate measurements come from the current two-shard run, whose disjoint41/40 union
passed all81 selectors / 104 tests. The earlier complete unfiltered product run also
passed. Backend2617/physical136 pass on unchanged backend/persistence bytes; final root373 and
frontend574/typecheck/build also pass. Independent acceptance remains pending.

| Browser measure | Baseline | Candidate |
|---|---:|---:|
| Median individual choice (ms) | 234 | 17.5 |
| p95 individual choice (ms) | 265 | 22 |
| Median all-four selection (ms) | 954.5 | 70 |
| p95 all-four selection (ms) | 986 | 87 |
| Median separate group confirmation (ms) | 0 (already applied per choice) | 226 |
| p95 separate group confirmation (ms) | 0 (already applied per choice) | 250 |
| Median total four decisions (ms) | 954.5 | 296.5 |
| p95 total four decisions (ms) | 986 | 327 |
| Requests while selecting | 20 in every group | 0 in every group |
| Full group POST / GET count | 4 / 16 in every group | 1 / 4 in every group |

The measured median full-group elapsed time decreased about69%; request count decreased
75%. A baseline choice already commits to the server, so its zero separate-confirmation
time is not a zero-cost save. The candidate total includes its actual single confirmation.
This is a single-host, synthetic four-field result, not a universal speed guarantee.
Receipts: [browser aggregate](BLOCKER_REVIEW_BROWSER_EVIDENCE/performance-browser-summary.json),
baseline-group-1..3.json and candidate-group-1..3.json in the same evidence directory.
Earlier timings with different first-group viewport/instrumentation are superseded.

The browser, API and Mongo workloads differ across lanes. Only before/after within the
same lane is comparable; their distributions are never combined. There is no production
load-test, multi-process concurrency or real external-provider timing claim.

Representative screenshots are in BLOCKER_REVIEW_BROWSER_EVIDENCE: baseline navigation,
candidate actual focused SELECT, four local draft choices, mobile confirmation and the
remaining blocker after confirmation. The normal-layout footer does not obscure later
decision fields. Draft storage remains limited to the current open case in the tab.

The final candidate browser receipts and screenshots were regenerated after BR-QG-01
compact-summary remediation. All30 groups independently compare four retained backend
intervention IDs with four details records, one visible warning and the related count.
That setup-only comparison precedes the unchanged measured selection/confirmation window.
The original API/Mongo production sources and exact benchmark receipts are unchanged.
