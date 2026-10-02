# Phase 24 implementation handoff

Uncommitted implementation candidate; independent verdict is not supplied by this
handoff. The assigned Phase 24 request is authoritative. No other phase, publication,
target external operation, retained target-state access or autonomous approval occurred.

## Revision and ownership

- Branch: `feat/phase24-registry-identity-ownership-ubo`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/phase24-registry-identity-ownership-ubo/data-dividends-zero-touch-clm`.
- `BASE_SHA`, current `HEAD` and inspected/fetched `origin/main`:
  `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`.
- Original checkout preserved clean on `codex/post-pr65-project-state`, HEAD
  `4125ece34ed9e4c3a306e5f7a989b146356b3479`.
- Root coordinated all Git and implementation writes. Earlier read-only specialists
  traced owners and challenged implementation; they did not supply a gate verdict.
- Exact tested source is the final dirty candidate at the above HEAD. The manifest
  records every changed/new candidate path and byte digest after this handoff is saved.
  Its own file and the assigned independent report are excluded from recursive hashing.
  Independently reviewed identity and verdict belong only to the fresh gate report.
- Nothing staged; no commit, push, PR, merge, branch deletion or worktree cleanup.

## Result and owner boundaries

Registry correction verifies the proposed UEN through the existing canonical registry
path before Search or state mutation. Entered, current document and other-UEN choices
are explicit. Document choice binds the current document ID and event version;
reauthorization and revision checks stay inside the owning lock. Confirmed, submitted
and completed identity is frozen. Previous normalized entity/registry evidence,
correction receipts and ownership analyses remain in bounded backend history. Browser
audit projection excludes old private graph/provider bundles.

Same-UEN registry reacquisition and changed-UEN corrections invalidate only dependent
ownership/readiness state through update-only identity-bound repository CAS. Parent
canonical UEN and correction generation are checked inside Mongo mutation boundaries.
Independent non-registry evidence with the same UEN remains valid only if no intervening
different/unknown identity retired it. A-to-B-to-A cannot resurrect old independent
evidence; a newer identity-generation replacement retains the prior analysis.
Service and physical Mongo continuation now share the repository-owned currentness
predicate under the existing parent lock/CAS. Independent same-UEN evidence continues
without replacement; registry-derived evidence remains strictly generation-bound.
Historical unknown source binding cannot authorize stale reuse after a later correction. The existing
resume sequence is reused; unrelated document/reconciliation blockers remain active.

One strict scalar evidence model retains original bounded values, Decimal amounts,
units, class, provenance, time, confidence, basis and evidence version. One deterministic
semantic tagger supplies labels, reasons and references; it is not a predictive model.
The sole ownership owner derives percentages only from explicit compatible,
authoritative, positive denominators and unique same-entity numerators. It rejects
row-sum inference, floats, cross-UEN/class/unit/time/environment/provenance synthesis,
duplicates, ambiguous interests, unsupported groups and unresolved status semantics.
The existing >=25 comparator is unchanged. Candidate flags do not establish legal
controller, final approval or production compliance outcomes.

Scalar percentages retain actual owned-parent bindings and distinct edge references
for repeated/nested parties. Unknown bindings remain null and unquantified. Graph and
scalar diagnostics are combined before candidate classification; review issues make
affected candidates indeterminate while retaining valid numeric/path evidence.
Unresolved group, unknown, control, membership/economic-interest and unmatched
owner/partner/member/shareholder roles require review beside valid graph evidence.
Unknown/withdrawn scalar activity remains unresolved even with a matching edge;
director/officer labels alone neither create ownership nor block supported evidence.

Both identity histories are capped at 16. Capacity rejection occurs under the owning
lock before registry verification, Search or state mutation. Case repositories and
the durable codec reconstruct/validate full model values before writes, including
existing backend-only provider bindings; a mutated invalid model cannot poison storage.

Official composition declines company-shareholder acquisition for non-company legal
forms, including its dependent relationship call. Synthetic local Garden fixtures
retain their established behavior. A present
official entity lacking the supported shareholder collection is rejected, rather than
presented as empty membership. No new partner/member/group/capital provider is composed.

Seven ordered accessible disclosures expose current stage, progress, active issues and
next action. Stage-local human interventions have expandable details and retained
history. Ownership uses one primary intervention with evidence-specific reasons.
Read-only Search and target diagnostic panels remain in their owning stages. Focus
actions reveal their disclosure before focusing. Review & Send is last, with an always
visible unavailable-state explanation until ready. Completion is 100%, zero active
issues, and final submission still requires explicit confirmation.
Visual and ARIA completion use the same percentage, explicitly separating 100% POC
submission from unresolved final human approval. Normal, hover and keyboard-focus
disclosure contrast is checked in actual Chromium. Registry correction advances the
CaseDetail action generation and cancels/resets dependent documents, ownership and
intelligence through the existing query owner before publishing the new summary.
Null/lower-version new evidence cannot preserve the old identity's cache baseline;
late old requests cannot overwrite the rebound analysis.

## Explicit change classes

| Surface | Changed | Boundary |
|---|---|---|
| API/types | Yes | Additive registry-identity and ownership/audit fields; unknown scalar entity binding is nullable, known nested identifiers remain bounded |
| Durable schema | Yes | Optional fields within existing v7 records; no envelope bump, index or migration |
| Connector | Yes | Scalar retention, legal-form dispatch and unsupported-shape rejection |
| Configuration | No | No setting, dependency, lockfile or default mode change |
| Business rule | Yes | Bounded compatible-unit derivation and specific evidence outcomes; threshold unchanged |
| Mapping | Yes, source only | Canonical scalar evidence; target GoldTier mapping unchanged |
| Auth/security | Yes | New route uses existing policy; locked identity CAS and minimized browser audit; no RBAC rule change |
| Architecture | Yes | Proposed ADR-008 semantic tagger; no second math, persistence, cache or authorization owner |
| Provider status | No | Mock stays Mock; no Sandbox/Partial/Dormant/Live promotion |
| Runtime behavior | Yes | Same-case correction, dependency recomputation and ordered disclosure UX |

## Executed verification

Python: 3.12.10 using the original checkout's existing virtual environment, with
worktree `apps/backend` on PYTHONPATH. Node: 22.23.3; npm: 10.9.9. No package upgrades.
Latest affected commands below ran on the revised source after remediation round 2.
Subsequent edits updated documentation and the manifest only. Earlier candidate/gate
evidence remains explicitly historical. Unchanged root harness/dependency checks from
round 1 are identified separately. Counts are specific to this candidate.

| Lane | Command/result |
|---|---|
| Focused new backend | Phase 24 identity/evidence pytest modules: 87 passed (17 identity, 70 ownership/evidence) |
| Full backend | `python -m pytest apps/backend/tests -o addopts= -q -p no:cacheprovider --tb=short`: 1,622 passed, 43 skipped, four warnings, 206.34 seconds; skips are guarded physical cases |
| Physical Mongo | `python scripts/run_physical_mongo_tests.py --timeout-seconds 900`: nine suites, all 43 passed; generated allowlisted disposable databases cleaned; includes cap-17 rejection/restart, independent A-to-B-to-A replacement, same-UEN independent continuation and strict registry-generation rejection/restart |
| Backend static | `python -m ruff check . --no-cache` from backend; strict `python -m mypy app` using external cache: pass, 115 source files |
| Task script | Ruff on explicit Phase 24 discovery script: pass |
| Dependencies | Round-1 unchanged dependency evidence: `python -m pip check`, `npm ls --all`: pass; no dependency/lock changes since |
| Frontend | Configured Vitest: 34 files, 401 passed; typecheck and production build pass |
| Browser | Final round-2 `python ../../scripts/run_e2e.py --timeout-seconds 60` from frontend: all 29 configured selectors / 31 instances passed in isolated local Mock lifecycles; 317.187 seconds |
| Browser coverage | Golden zero interventions and one confirmation plus ARIA100%; Garden clean/conflict automatic resume and delayed current-document rendering; all identity choices including actual rendered new-UEN scalar/candidate evidence; current-document/focus/stale responses; representative roles, routes, responsive, keyboard and computed contrast coverage |
| Contracts | CI-style unittest discovery under `tests/contract`: 44 passed |
| Root governance/harness | Unchanged round-1 harness evidence: CI-style unittest discovery per non-lifecycle module: 260 passed, plus three pytest-style preflight tests passed; delivery subset four already within 260 |
| Governance | Project-state, architecture, tooling/config, policy-authority and external-provider-readiness checkers: pass |
| Hygiene | Secrets checker, full effective diff inspection, `git diff --check`, explicit new Markdown whitespace check: pass before freeze; rerun after handoff/manifest creation |

Ordinary frontend warnings include existing React act/layout-effect warnings. Physical
tests were supplemented with an actual task-owned mongo:7.0 container, no volumes,
loopback port 27024. No test touched `clm_poc`; no Mongo URI was printed or persisted.
Container `clm-phase24-mongo-20261001-2135` remains available for the independent reviewer
and is to be stopped by root after that review. No unrelated process will be stopped.

The root Windows lifecycle lane was unavailable: an existing unrelated listener owned
port 8000, producing 20 setup failures in the attempted run. It was left untouched.
Startup/process composition was not changed; no passing lifecycle claim is made.
An initial incorrect root unittest discovery treated contract files as package imports;
the subsequent CI-style contract command passed all 44 cases. Private GoldTier sponsor
archives are absent, so example validation reports NOT VALIDATED, not PASS.
`pre_pr_check.py` was deliberately not run on this required uncommitted handoff.

Post-remediation root discovery initially selected the pytest-only preflight module
with unittest (zero tests, not PASS); pytest subsequently passed all three. One unchanged
pytest-parser probe initially failed with Windows ancestor collection from system
temporary storage. All 17 parser tests passed with TEMP/TMP confined to a verified
task-owned directory inside the candidate. That directory was removed after execution.
These harness limitations are retained; no product/test assertion was weakened.

Round-1 full backend regression exposed invalid constructed-policy insertion now
rejected earlier by full-value validation. Its fixture now separately asserts that
early rejection and injects a corrupted read after a valid create to preserve all
original fail-closed preview/dispatch assertions. Empty ownership asserts both retained
graph and missing-evidence issues. Two manual fixtures now use UTC dates to avoid a
demonstrated local/UTC midnight mismatch; runtime date rules did not change.

## Actual external evidence and limitations

See `docs/development/PHASE_24_ACRA_DISCOVERY.md`. Actual bounded official ACRA Mock
session totals: 24 attempts (six OAuth, 18 GET), 22 HTTP responses (six OAuth,
16 GET), two initial read TLS failures before HTTP response. Successful reads used the
composition's verified platform TLS context; no certificate verification bypass.
The public resource-centre search added zero provider API calls.

Garden `11111999A` is a partnership. Its fresh canonical acquisition retained four
ROLE observations, tagged four OWNER_ROLE values and returned REVIEW_REQUIRED with
INCOMPLETE_LEGAL_ENTITY and UBO_REVIEW_REQUIRED, zero candidates. These are semantic
evidence, without numeric numerator/denominator or legal/control authority. Unbound
`111111111M` shareholder inspection found four parties and shareAllotted, but its basic
identity read was empty and no authoritative compatible denominator was supplied.
`333333333C` and `222222222C` representations require unsupported member/group schemas.
No capital call occurred. No other-UEN numerator/denominator combination was attempted.
Consequently no coherent official quantitative fallback, derived network percentage,
network UBO or false STP demonstration is claimed.

The user supplied the private local sample source on October 2. The matching seven-page
catalogue was inspected in memory only for candidate UEN discovery. Six documented
additional basic UENs were read: five verified basic identities had no applicable
supported quantitative ownership route; capital sample `111111111K` returned basic
EMPTY. Catalogue availability is resolved and the provider demonstration is not
deferred. No supported documented sample supplied sufficient coherent same-entity
quantitative/control evidence; the user explicitly permits that truthful result.
Q-012 still controls partner/member/group/capital schemas and denominator authority.
Offline fixtures exercise 60/40, exact 25 and adverse arithmetic without provider claims.

No approved predictive artifact/runtime exists for the new semantic tagger:
`ML_RUNTIME_NOT_AVAILABLE` is explicit; its experimental protocol is unwired. The
existing separate `ubo-advisory-linear-v1` review aid is unchanged. Sixteen exact semantic fixture cases exercise
the deterministic rule baseline and its reason/provenance outputs. No fabricated
training, holdout, precision, recall or predictive metric is reported.

No GoldTier, PingFed, production or target mutation call occurred. The ledger's ordering,
call stopping and replay recovery remain owned by the existing ledger. Retained target
ID 143880 and all retained recovery state were never opened or modified.

## Independent review and next authorized action

The initial fresh independent gate returned FAIL with four findings: history capacity/
full-value validation, stale independent A-to-B-to-A evidence, premature candidate
classification/lost diagnostics, and incorrect nested scalar entity attribution.
The exact report and original manifest are preserved as
`PHASE_24_QUALITY_GATE_ROUND_1.md` and `PHASE_24_CANDIDATE_MANIFEST_ROUND_1.json`.
Remediation round 1 changed only their owning boundaries and adverse regressions.
It also stopped the inapplicable dependent relationship read exposed during the
fresh canonical Garden demonstration. No independent PASS is asserted here.

The fresh gate after round 1 returned FAIL with five findings. Its exact report and
reviewed manifest are preserved as `PHASE_24_QUALITY_GATE_ROUND_2.md` and
`PHASE_24_CANDIDATE_MANIFEST_ROUND_2.json`. Remediation round 2 is the final permitted
round and addresses only those owning boundaries:

- R2-F1: registry correction retires supporting query data/action generations; four
  production-client component regressions cover three non-polling outcomes, null
  current ownership and late old GETs. Browser assertions check rendered new evidence.
- R2-F2: 14 adverse mixed-graph semantic/status cases now retain valid numeric evidence
  with indeterminate candidates and a specific review issue; a director-only case
  remains analyzed. All 14 reproduced the defect before the fix.
- R2-F3: one shared currentness predicate permits independent same-UEN continuation
  under physical Mongo CAS while retaining registry generation rejection. Physical
  independent continuation failed before the fix; both paired cases now pass.
- R2-F4: scoped disclosure hover/focus colors preserve readable contrast. Actual
  Chromium reproduced 1.264:1 before the fix; normal/hover/focus now satisfy >=4.5:1.
- R2-F5: visual and accessible POC percentage share one value; completed progress100%
  keeps the unresolved human approval boundary explicit. The new component assertion
  failed before the fix, and Golden checks the actual browser ARIA values.

Freeze and independently review this exact candidate, including new files. Any P0/P1/P2
means FAIL. Only root may remediate after preserving a failed report; at most two rounds,
each followed by affected verification, a new freeze and a fresh independent reviewer.
Both rounds have now been used; a further material failure must be reported without
starting a third remediation round absent separate user authorization.
The independent gate decides whether current criteria are met and distinguishes missing
evidence from later authority dependencies. This implementation handoff is not an
independent PASS or permission to publish. No commit, push, PR, merge or next phase is
authorized. Retain the task worktree for review and stop only its disposable container
after the final gate run.
