# Sponsor demo performance delta

Fresh measurements for the expanded candidate, 2026-10-10. These are local workloads,
not service-level guarantees. The original accepted report and its receipts remain intact.

| Browser: 30 groups, four choices | Original baseline | Prior accepted candidate | Expanded candidate |
|---|---|---|---|
| Median choice time (ms) | 954.5 | 70 | 76.0 |
| Median confirmation/refresh (ms) | Included in choices | 226 | 245.0 |
| Median total (ms) | 954.5 | 296.5 | 331.5 |
| Current p95 total (ms) | Historical receipt | Historical receipt | 374 |
| Mutations / supporting GETs | 4 / 16 | 1 / 4 | 1 / 4 |

All 30 current groups sent zero requests while selecting drafts. Confirmation produced
one POST and four supporting GETs. Current total median is
65.3% below the original baseline. The three
current ten-row receipts are in SPONSOR_DEMO_REGRESSION_EVIDENCE/group-1..3.json.
Current browser p95 uses nearest rank, ceil(0.95*n)-1 (index28 for30). The original
API benchmark retains floor(0.95*(n-1)) (index27 for30). These estimators differ;
no browser/API p95 comparison or old/current browser p95 reduction is claimed.

The separate 30-sample in-process HTTP workload measured median
81.719 ms and p95 101.321 ms for
four decisions and the refresh wave. Historical original median/p95 were 293.772/330.471 ms;
the prior accepted candidate was 69.940/93.620 ms. Each current sample has one mutation,
four GETs, one reconciliation and one document save. Receipts are current-api-30.json.

Physical Mongo is one descriptive workload per revision, not a timing distribution:
original find/update 497/21; prior accepted candidate 147/5; expanded candidate
197/5. Current reads are higher than
the prior candidate; writes remain five. No read-count improvement over that candidate
is claimed. Target calls remain zero and final state WAITING_FOR_REVIEW. Receipts are
current-mongo-commands.json. Baseline receipts stay in BLOCKER_REVIEW_BROWSER_EVIDENCE.

This passing benchmark does not close the required browser regression gap. See
SPONSOR_DEMO_VERIFICATION.json and the independent gate for acceptance status.
