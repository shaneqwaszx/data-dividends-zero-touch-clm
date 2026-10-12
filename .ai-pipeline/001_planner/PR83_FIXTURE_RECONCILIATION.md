# PR83 fixture reconciliation and release closure

Owner authority: brief fe7c11fb, 2026-10-12. This new bounded task supersedes the
exhausted limit only for the fifteen ODS-P1QG-04 canonical test setups. Production,
contract, assertion, timeout and skip policy changes are outside this assignment.
One further fixture-only refinement is conditional on an independent demonstrated
in-scope finding. A production defect or scope expansion requires STOP. Publication
to existing PR83 is authorized after exact fresh PASS and all local publication gates;
human owner alone decides merge and any remote-CI release exception.

TaskStartSnapshot: existing .ownership-hotfix, branch
feat/ownership-ubo-doc-review-streamline, HEAD169a5db0348c0ae6384289215410ed4d69fb23ad,
base/fresh maina6c80d2f20048ce64b3f6184df34c098f8fff4ab. All35 preserved candidate
hashes match687430e24c88770993b0863033f905234d885510c7b40685f40511d5f1447cdf;
prior P1 gate remains byte-identical39d281066dc9497db1b5d25966dce62acf06e4dc4084239f8b05f0fd98084d6f.
One writer owns tests/Git; fresh independent reviewer owns only its assigned report.

Change Necessity: test arrangements must reach their original assertions through the
count-bound owner. Decision: test-code-change, two files/twelve initial call sites,
fifteen expanded cases. Keep the existing service guard and every other test statement.
Canonical owner: existing ZeroTouchOrchestrator.start with expected_document_count.
Counts below express each authored scenario, never successful-upload count inference.
TDD Route strict: exact fifteen cases reproduced15FAIL before edits. Architecture review
not required: no new owner, dependency, schema, interface or production semantics.

The legacy-profile test seeds a persisted PROVISIONAL_CORPORATE profile to verify
required address; it does not exercise the single-document attach/upload route. Keep
that original profile seed; explicit initial count1 does not fabricate completion.
The supported single-document route is separately retained and tested by the current P1
compatibility regression. Both concurrent workers complete the same intended one-file
intake after the original barrier; no pre-race start is inserted. Subsequent completed
duplicate and resume calls remain count-free and unchanged. Both100-run loops remain.

| Failed case | Old setup | Corrected initial setup | Preserved assertion/purpose |
|---|---|---|---|
| matching_document_auto_confirms_even_after_readiness_created_reconciliation | One clean intake document; reconcile; count-free start | start(expected_document_count=1), same prior reconcile | AUTO_CONFIRMED, no pending fields/intervention/document blocker; Search-only |
| frozen_threshold_is_inclusive[0.85-True] | One exact-confidence document; count-free start | explicit count1 | Inclusive threshold acceptance, original confidence and field statuses |
| frozen_threshold_is_inclusive[0.849999-False] | One below-threshold document; count-free start | explicit count1 | Below-boundary fields remain pending; no intervention relabel |
| partial_machine_confirmation_does_not_clear_missing_or_low_confidence[LOW_CONFIDENCE] | One low-confidence document; count-free start | explicit count1 | REVIEW_REQUIRED, exactly one pending field, real DOCUMENT exception |
| partial_machine_confirmation_does_not_clear_missing_or_low_confidence[MISSING_FIELD] | One required-missing document; count-free start | explicit count1 | Same missing value/confidence and blocking assertions |
| changed_canonical_value_and_operator_rejection_do_not_auto_clear | One document with operator rejection; count-free start | explicit count1 | Changed-canonical assessment false; rejection/history retained |
| legacy_document_profile_still_requires_registered_address | One legacy-profile/missing-address document; count-free start | explicit count1, existing legacy seed unchanged | Required-address discrepancy and document_required true; Search-only |
| duplicate_and_concurrent_start_do_not_repeat_completed_work | One document; two barrier-synchronized starts | Both racing calls explicit count1 | Two COMPLETED results, same duplicate/resume version and exact target calls |
| P06_QG_005_REVIEWED_CONFLICT_EARLIER_DOCUMENT | Reviewed conflict then clean document; count-free start | explicit count2 | Genuine DOCUMENT conflict and earlier reviewed reference; Search-only |
| P06_QG_005_REVIEWED_CONFLICT_LATER_DOCUMENT | Clean then reviewed conflict document; count-free start | explicit count2 | Later reviewed conflict reference; Search-only |
| P11_ONE_CURRENT_FIELD_DISCREPANCY_RETAINS_BOTH_CONFLICT_DOCUMENTS | Two reviewed conflicts; count-free start | explicit count2 | One discrepancy, both observations in insertion order; Search-only |
| P06_QG_013_EQUAL_TIMESTAMPS_PRESERVE_INSERTION_ORDER_100_RUNS | Two equal-time conflicts per iteration; count-free start | explicit count2 in same100-iteration loop | Equal timestamps, stable insertion and observation order,100 Search calls |
| P06_QG_013_FORMER_FLAKY_TEST_IS_STABLE_100_RUNS | Calls preceding two-conflict scenario100 times | Uses reconciled scenario; wrapper unchanged | All original two-conflict assertions repeated100 times |
| P06_QG_005_REVIEWED_CONFLICT_RESOLVED_BY_KEEP_REGISTRY | One reviewed conflict; count-free initial start | explicit count1; original resolution unchanged | Completion, original/reviewed values, reconciliation decision, exact target calls |
| P06_QG_005_REVIEWED_LOW_CONFIDENCE_REMAINS_BLOCKED | One reviewed low-confidence document; count-free start | explicit count1 | WAITING, low-confidence exception, no available action; Search-only |

Verification order: exact fifteen RED -> reconciled fifteen GREEN with original bodies
and loops -> initial/recovery P1 owners -> affected backend/contract/security/governance
-> fresh full backend -> full frontend/types/build -> fresh generated-database Mongo
-> guarded browser and full canonical shards at60seconds -> freeze full candidate ->
fresh independent gate at OWNERSHIP_DOCUMENT_STREAMLINE_FIXTURE_QUALITY_GATE.md.
Only exact PASS continues latest-main assessment, explicit reviewed staging, commit,
clean committed prePR/checklist, normal push/update PR83, precise inline reply/resolution
and actual new push/PR CI observation. Never bypass billing/protection or merge.

Resources: task Python environment/PYTHONPATH, explicit AnyIO, installed Tesseract in
child-only PATH; existing frontend/runtime. Serialize heavy lanes and Mongo/browser
resources. New disposable Mongo service requires preflight and fresh allowlisted DBs;
never protected databases or providers. No .env reads. Ports8798/4198 coordinator;
reviewer uses distinct owned ports. Checkpoints/evidence in tmp/pr83-fixture-evidence;
all earlier reports and logs remain immutable. Current change class is CI_TOOLING;
the complete retained candidate still requires BACKEND_DOMAIN/BACKEND_API/FRONTEND_UI
verification under the owner brief. API/type, schema, connector, configuration,
business-rule, mapping, auth/security, architecture and provider status unchanged by
this fixture slice; no production runtime edit.
