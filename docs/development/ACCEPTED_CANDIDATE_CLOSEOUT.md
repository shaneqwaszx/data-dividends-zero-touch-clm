# Accepted candidate closeout and publication authorization checkpoint

2026-10-01. This is a proposed, uncommitted integration unit; no publication occurred.
Branch `fix/demo-happy-path-stabilization`; HEAD/base/local origin/main/merge-base
`efc31f450f0103766fa812bc0aa80754f801dbe9`. Index empty. Existing worktrees,
accepted source, historical reports, failed gates and retained evidence were preserved.
No model escalation; exact configured model identifier is unavailable through the tools.

## Project-state diagnosis and correction

Classification: **B — HISTORICAL_REFERENCE_REQUIRES_PRESERVATION**.

`docs/PROJECT_STATE.md` stores `verified_main_sha` and defines it as the main behavioral
baseline inspected for that snapshot. Subsequent documentation-only commits do not
replace it; feature HEAD need not equal it. `scripts/check_project_state.py` verifies
that the object exists and is an ancestor of local `origin/main`.

Read-only history proves the stored `d23d7b7335ba402b071191821c35e4f5e879ed7c`
is the operator blocker UX main commit (#62, 2026-09-29). Main documentation refresh
`3d6e7b560b8062daeb93c31cf91b0df957797e9c` (#63) introduced that reference.
Both are ancestors of the accepted #64 base. `git cat-file -t` returns commit;
`git merge-base --is-ancestor` returns 0. There is no observed missing object or
history rewrite. No fetch was required to establish these local facts.

The disclosed ancestry FAIL was a **checker environment defect**: its Git subprocess
received only `GIT_OPTIONAL_LOCKS=0`, discarding inherited Git configuration. In this
sandbox that removes the already configured repository trust context, so Git exits 128
for dubious ownership. The checker then reports the generic unreachable-baseline error.
It does not establish a provenance gap.

The minimal correction preserves the inherited process environment while still setting
`GIT_OPTIONAL_LOCKS=0`. No wildcard trust exception, global/local Git configuration,
history, SHA, date, provider metadata or authority was changed. A failing-first actual
Git test verifies inherited process configuration without writing repository config.
The existing genuine non-ancestor test still rejects unrelated main history.

Prior reports truthfully retain their then-observed FAIL; this diagnosis supplements
them rather than rewriting history. `tmp/CANDIDATE_CLOSEOUT_PROVENANCE_PROOF.json`
records the exact read-only history and classification. Post-merge snapshot refresh
remains a separate operation after resulting main is known and inspected.

## Entire accumulated candidate and proposed partition

Exact proposed publication set: **112 files**, in
`docs/development/ACCEPTED_CANDIDATE_PUBLICATION_MANIFEST.json`. Each path is classified
INTENDED or SUPPORTING with its owner. The set includes 107 existing changed/new
task paths, the checker and its regression test, and three closeout/manifest/gate files.
There are no unexplained content paths, dependency or lockfile changes.

Propose **one commit**: `Stabilize demo onboarding, ownership recovery and provider safety`.
Garden stabilization, bounded provider contract/safety corrections, exception-driven
processing and ownership presentation share orchestration, API and frontend owners.
Separating them would require reconstructed intermediate file contents that are not
independently accepted integration units. Preserve the prior chronological reports
inside this single reviewed accumulated commit; do not squash their evidence claims
into a blanket external acceptance claim.

The stat/status entry `apps/frontend/src/pages/BlockerDecisionDetails.tsx` is excluded:
its bytes exactly equal the HEAD blob and it has no content diff. It is an index/stat
or normalization artifact, not another implementation change. It was not rewritten
or staged. Publication must reconcile any such status entry safely before the later
clean committed pre-PR check; this run does not refresh index metadata.

The complete semantic tracked diff is retained locally at
`tmp/CANDIDATE_CLOSEOUT_SEMANTIC.diff`; raw line-ending effects are preserved rather
than reformatted. Prior accepted manifest paths were checked for current content;
this continuation changes only the checker and its test plus the three new closeout
artifacts. No accepted Garden/Golden runtime code was changed.

Accumulated changes include API/type projections, registry unsupported/partial handling,
conditional GoldTier mapping/no-replay safety, document/reconciliation/progression
behavior, policy-authority documentation and browser cache/UI behavior. This closeout
adds only CI_TOOLING/DOCS_ONLY changes. No new runtime owner, environment/toolchain,
dependency, config key, auth/RBAC change, Mongo/CAS owner or envelope version was added.

## Security and excluded artifacts

The exact named publication set excludes tmp evidence/manifests/runtime logs, all local
credentials/environment files, private sponsor originals, raw provider responses,
browser/session artifacts, caches, build output, virtual environments and node_modules.
No `.env` or credential values were read, dumped or copied. Historical provider reports
are sanitized evidence summaries; provider/customer IDs do not imply approval.

Supported `scripts/check_secrets.py:scan_file` is applied directly to the exact proposed
paths, with matched values suppressed. The normal supported repository scan also passes.
The two PDF fixtures match their deterministic synthetic generator exactly, 2/2; no
private provider/client document is included. Exact path hashes and the supported
scanner result are retained in the current closeout freeze/evidence. The independent
gate is scanned after its report is written, before the final seal.

## Proportional verification

| Current closeout lane | Result |
|---|---|
| Project-state checker | PASS; historical SHA unchanged |
| Focused project-state tests | 19 PASS, including real inherited Git config and non-ancestor rejection |
| Architecture checker | PASS |
| Static provider readiness | PASS; does not dispatch a provider |
| Policy authority | PASS |
| Supported secret scan | PASS; exact proposed set additionally checked |
| Ruff changed Python | PASS |
| Strict mypy changed script | PASS, one source |
| Secret and physical-runner unit tests | 25 PASS; no physical DB dispatch |
| Tracked whitespace plus task-owned new text | PASS |

Initial runner-unit execution had five collection failures because its temporary path
under Windows AppData was inaccessible to the sandbox child. Rerunning the unchanged
tests with a task-owned temporary directory passes all 25. This is launcher infrastructure,
not a runner source change, physical acceptance or weakened test.

Runtime evidence is explicitly reused because all tested runtime paths are unchanged:
the Garden ownership gate has independent PASS on its exact freeze; current full backend
1531 PASS/38 SKIP/4 warnings, frontend392 PASS, contracts44 PASS, Garden clean/conflict2
PASS and Golden1 PASS. Ruff/mypy112/typecheck/build and held/stale publication checks
remain bound to unchanged source. Golden retains zero exception interventions, one
explicit confirmation and COMPLETED. Garden retains upstream EMPTY, LOCAL 60/40,
existing Decimal engine, immediate resolution/history and automatic resume.

## Physical CI, provider chronology and readiness limits

The existing `.github/workflows/ci.yml` has push and pull_request triggers and the
unconditional `phase12-mongo` job: disposable `mongo:7`, health check, Python3.12,
explicit PHASE12 test URI and `scripts/run_physical_mongo_tests.py`. The runner selects
its owned suites, fails on unavailable/empty/skipped execution, isolates child settings
and relies on allowlisted disposable databases. Workflow/runner configuration is capable
of providing physical acceptance after publication, subject to actual remote execution.

No physical Mongo suite was run here. Earlier physical receipts are historical evidence,
not a fresh result on this accumulated publication candidate. Required current physical
acceptance remains pending the authorized CI lane; ordinary 38 skips are not PASS.
Retained Atlas/Mongo is never a substitute. Remote CI has not been inspected or claimed
green. Full external GoldTier lifecycle acceptance remains blocked: Policy/Amend were
not executed. Local/recovery PASS does not erase preserved external acceptance FAIL.

External ACRA, GoldTier, PingFed and Production calls in this continuation: **0**.
No retained Mongo read/write/cleanup was needed or dispatched. Prior unchanged sanitized
fresh-process proof preserves ID143880, PROVIDER_VERIFIED_RECOVERY, original Shell
uncertain, replayed=false and no Policy/Amend. The retained service was not stopped.
Service evidence file and latest ledger proof are unchanged; no replay/reconstruction.

This run prepares an **authorization checkpoint**, not PR-ready/merge-safe certification.
No fetch, staging, commit, push, PR, branch deletion or merge. A later separately
authorized publication run must verify exact reviewed content, assess freshly fetched
main, stage only named paths, obtain clean committed pre_pr_check/checklist evidence and
observe applicable CI including physical Mongo. Human owner alone merges.

## Independent closeout gate

Separate reviewer writes only `ACCEPTED_CANDIDATE_CLOSEOUT_QUALITY_GATE.md` and answers
the ten assigned closeout questions. Exact accumulated freeze is
`tmp/CANDIDATE_CLOSEOUT_REVIEW_MANIFEST.json`; gate is outside the implementation freeze
and its final hash is separately sealed. P0/P1/P2 means FAIL. Maximum two bounded
remediation rounds; preserve each failed report. This implementation report does not
supply an independent verdict or publication authority.
