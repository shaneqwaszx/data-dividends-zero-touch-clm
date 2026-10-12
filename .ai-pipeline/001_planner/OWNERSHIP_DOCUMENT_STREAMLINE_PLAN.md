# Ownership UX and document continuation hotfix

Owner request: pasted assignment, 2026-10-12. Scope is the four requested UX/process
changes; no other phase or provider work. Publication requires a separate owner approval after independent
exact PASS, as reserved by the superseding brief. Human owner merges.

## Task start and boundaries

- Checkout: task-owned `.ownership-hotfix`; branch
  `feat/ownership-ubo-doc-review-streamline`.
- BASE_SHA / initial HEAD / freshly fetched origin/main:
  `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`; tracked state clean.
- Managed worktree creation failed on Windows filename length; ordinary worktree
  created with invocation-local `core.longpaths=true`. Other checkouts untouched.
- Capabilities: shell/Python3.12, Node22/npm10, Playwright harness, UI browser tool,
  independent subagent review and GitHub tools. Existing Python environment reused;
  isolated frontend lockfile install. No `.env`, protected database or provider access.
- Browser ports reserved for this run: backend8875/frontend4273. Memory/Mock/Local
  synthetic evidence only. Physical Mongo is conditional on affected persistence
  semantics, not assumed available or needed for a mere orchestration change.
- Classes: FRONTEND_UI, BACKEND_DOMAIN, BACKEND_API. Existing frontend mutation
  settlement, authenticated query keys, cancellation and cache invalidation are reused;
  no shared cache semantics change (FRONTEND_STATE_CACHE inspected conservatively).

## Cause, necessity and minimum change

Observed source: apply_review_decisions returns PENDING_INPUTS immediately after saving
document receipts. CaseDetail therefore still offers Continue evidence review. Pending
documents cannot use the existing replacement action; failed intake retry extracts but
does not continue. During ordinary document/final review replace_document already
retains supersession and invokes dependent refresh/advance.

Decision: code-change. Non-code instructions cannot remove the redundant handoff.
Canonical owner is ZeroTouchOrchestrator; reuse start, existing document replacement,
reconciliation checkpoint and target ledger. No new continuation/cache/persistence owner.
Patch shape: owner-level continuation wiring and read-only presentation. Preserve
initial multi-file intake completion, source choices, low/missing-evidence blockers,
creator/lock/CAS authorization, lineage and final target confirmation. Highest-risk
counterexamples are incomplete/stale review, failed sibling replacement, and target replay.
TDD Mode: off; diagnostic reproduction plus targeted regression. No strict TDD claim.
Architecture review/ADR: not required; no owner/interface direction replaced. Large
CaseDetail/ReviewAndSend edits are wiring only; extract focused presentation components.

## Atomic implementation slices

1. Reproduce pending-confirm and pending-replacement through authenticated browser/HTTP.
2. Primary bounded hierarchy from retained relationships; no percentage arithmetic.
   Native holder buttons and shared candidate selection, type/country/direct/effective,
   selected path-to-root. Repeated holders/cycles/orphans/limits remain explicit.
   Keep exact retained calculations in a secondary disclosure.
3. Reuse one read-only UBO summary in ownership and final review. List only natural
   persons with backend MET and PROVISIONAL_UBO_CANDIDATE; display exact percentage,
   comparator, threshold and reason. Other results remain review/below/indeterminate.
4. Confirm complete current document decisions and invoke existing continuation once.
   Missing decisions fail before writes. Replacement supersedes active slot, extracts,
   and advances to actual blocker; failed retries preserve history and failed siblings.

## Evidence and completion

Focused backend HTTP/service and frontend rendering tests; configured guarded browser
journeys for confirm, source choice, replacement, truthful failure and no extra resume.
Then full backend/frontend tests, Ruff/mypy, typecheck/build, affected contracts/security/
regression/governance and full diff/whitespace including new Markdown. No massive unrelated
browser inventory required. Current source, tested bytes and frozen reviewed bytes are
recorded separately. Fresh independent QG writes only its assigned report. Remediate
findings separately and re-review changed content. Integration-safe-development and
clean committed pre_pr_check precede push/PR. Inspect latest main drift; never merge PR.

Unchanged: durable schema/repositories, connectors/configuration/provider status,
ownership calculations/threshold business rules, target mappings and auth grants.
Changed: presentation and workflow progression/API errors for incomplete confirmation.


## Superseding principal-engineering brief — 2026-10-12

Continue the same worktree; no duplicate implementation. Two slices are independently
validated by their focused checks and the final independent combined gate. Slice A adds
collapsible levels, source legend, path calculation, supporting paths and direct/indirect
summary, desktop/360px/text scaling/reload evidence. Slice B adds four-field reject/replace,
failed/conflicting replacement and generated-database Mongo restart evidence (B08).
Disposable Mongo7: task-owned clm-ownership-hotfix-20261012, loopback27429, image-created
anonymous volumes only; no host data mounts, no protected database, no external providers.
Publication authority: the superseding brief reserves commit/push/PR for a separate owner
approval. Finish concrete implementation/test/review, then request that approval. No
commit or pre-PR clean-committed claim before authorization.

Current contracts retain D-062's confirmed bounded numeric comparator separately from
unresolved legal UBO policy. All UI candidates remain provisional. Existing ADR-011
section checkpoints and reconciliation UoW provide their existing atomicity; there is
no new cross-document/case transaction and no cross-owner atomicity claim. Additional
uploads remain separate from explicit replacement slots.

Risk/test map: A01-07 Garden offline hierarchy and COMPLETE fixture, exact backend
values/source, qualifiers, multi-path/cycle/unknown cases, native controls, mobile/reload;
B01-06 four-field grouped review and replacement with receipt/one-extraction call evidence;
B07 existing tamper/concurrent/creator/freeze/session/case-switch regressions; B08 physical
restart plus cleanup; B09/B12 target confirmation/no-replay assertions; B10 retained Garden
PARTIAL correction and distinct COMPLETE synthetic regression; B11 typed failure checkpoint.
Before/after screenshots are synthetic evidence, never sponsor/customer artefacts.

## One bounded remediation — ODS-QG-01

The first independent frozen gate was FAIL: pending replacement advanced while an
independent current FAILED document remained, terminalizing the case and disabling
targeted retry. Grouped pending confirmation also attempted continuation across this
same blocker. Failing-first regressions reproduce both outcomes.

Reuse the existing failed-document predicate and pending-input checkpoint. Grouped
confirmation retains saved receipts and returns PENDING when an independent failed
document remains. Normal replacement and version-bound dependent-refresh recovery
share the same owning continuation, which returns to the reupload checkpoint rather
than advancing across failed evidence. The domain's existing document-reupload exception
also accepts RESUMING only at DOCUMENT with the original completed prefix and required
DOCUMENT_REUPLOAD_REQUIRED event; the general transition table and statuses are unchanged.
No source/threshold/approval business rule or schema changes. Tests challenge wrong
stage, event and prefix, and prove final targeted retry continues without target writes.
The physical restart variant preserves failed sibling/history/receipts and retryability.

The previous full backend run is incomplete/stale for remediation, not a passing result.
Freeze the remediated path set, run a fresh full backend suite and affected physical and
browser lanes, then request a new independent reviewer. Exactly one bounded remediation
round is authorized; no publication approval is inferred.

## Final owner-authorized remediation — ODS-RQG-02

The owner explicitly authorized one additional FINAL round for the independent retry
API projection defect. A failing-first HTTP regression reproduced generic 500 after
accepted replacement and retained TECHNICAL_FAILURE / OWNERSHIP. The retry helper now
catches ZeroTouchInfrastructureError through the existing safe 503 projection, preserving
the error owner and DTO/status semantics. Focused HTTP coverage checks accepted lineage,
historical events, current terminal checkpoint and rejected replay without target writes.
Frontend adverse coverage checks that the existing 503 path reloads accepted history and
terminal evidence exactly once, without resume or another mutation. No frontend runtime
policy changes, automatic retry, schema, authorization or target-ledger changes.

Run required BACKEND_API checks, freeze corrected content and obtain a NEW independent
combined gate covering both original slices plus this correction. If it fails, stop with
the root cause; no further remediation is authorized. If it passes, stop at the separate
integration/publication authorization boundary. No commit, push, main change or merge.

## Overnight release closure authorization - 2026-10-12

The owner supersedes the exhausted remediation limit for this task and authorizes initial
ODS-FQG-03 repair plus up to two further demonstrated in-scope remediation cycles. Each
changed candidate requires a fresh independent combined gate. Normal scoped commit,
committed-state pre-PR check, push and one main-targeted PR are authorized conditionally
on exact independent PASS, mandatory local verification and latest-main integration.
No main implementation, merge, protection bypass or real external mutation is authorized.

Task start: existing isolated branch/base/HEAD/main a6c80d2; 24 frozen hashes match
874ac717f8c20f37720729110bbc16d4a4922167dad49e82221a48d6fd2ba0e2. Historical FAIL reports
and evidence are immutable. No other writer is active. One coordinator owns implementation
and Git; each independent reviewer owns only its assigned report. Current shell/Python,
frontend runtime and guarded Playwright are available; normal isolated process execution
is required after demonstrated sandbox subprocess/temp limitations. Browser ports8798/4198
are reserved for sequential coordinator checks; reviewer uses distinct owned ports.

Change class for this recovery: FRONTEND_UI. ArchitectureReviewRequired: no new owner,
framework, dependency, canonical model or durable boundary. Change necessity: valid root
relationship duplicates the client key and displays the wrong holder. Replace only the
presentation occurrence identity with disjoint structured client/path/unlinked keys;
use the same identity for React rows, selection, collapse and graph reconciliation.
Preserve backend IDs, Decimal results, provenance, UBO policy and all document fixes.

Verification: unchanged valid-source probe RED then GREEN; permanent discovered regression
for valid sentinel/delimiter IDs, repeated paths, root/unlinked rows, refresh/removal,
selection, collapse, keyboard and no duplicate keys. Full frontend/types/build, targeted
actual authenticated browser, owning backend/contract/security/governance checks and
required E2E inventory/relevant selectors. Backend full2680/155 evidence is attributed
only to exact unchanged backend bytes; never relabeled fresh. Fresh physical databases
only where required by changed dependency surface. Freeze before independent review.

Durable progress remains delta-only in tmp/ownership-hotfix-evidence/OVERNIGHT_CHECKPOINT.md.
Stages: repair -> independent gate -> final verification -> latest-main assessment ->
scoped commit -> clean committed pre-PR PASS -> normal push -> PR -> actual CI observation.
If mandatory gates fail beyond two extra cycles or a material authority/conflict/tooling
boundary is encountered, stop with evidence. Remote billing refusal is NOT EXECUTED;
never repeatedly dispatch blocked jobs or fabricate PASS. Human owner alone merges.

## Overnight additional cycle 1 - browser compatibility

Stage D exposed two retained browser locators for the former technical-summary label.
The canonical second shard timed out at the clean Singapore scenario; stronger visible
assertions reproduced the missing old label in that scenario and both identity choices.
Use the accepted `Technical calculations and retained paths` control in those two
existing tests, preserving every behavior, currentness/history, network/storage and
layout assertion. Keep the stronger visibility checks. No product/backend/DTO/provider,
deadline, skip, dependency or configuration change is authorized by this correction.
This consumes the first of two additional source-remediation cycles; one remains.
Freeze the changed supporting tests and obtain a fresh implementation-independent
combined verdict covering A01-A07/B01-B12 and the three earlier findings. The preceding
PASS remains immutable historical evidence, not acceptance of these changed test bytes.
Full frontend/type/build, corrected canonical browser groups, inventory/governance and
hygiene precede the new freeze. Final affected checks and both canonical shards follow
exact PASS before latest-main integration or publication. First scanned-OCR shard failure
was separately resolved by exposing already-installed Tesseract in child-only PATH;
the unchanged scanned browser and six real OCR cases passed without any source/host change.

## PR83 post-publication P1 remediation - 2026-10-12

Owner brief506865eb authorizes one evidence-justified remediation of review comment
4243047623, consuming the remaining overnight source cycle. Published/task HEAD169a5db
and freshly fetched main/basea6c80d2 match the clean branch and PR83. Historical reports
and evidence remain immutable. One implementation/Git writer; fresh independent reviewer
writes only the separately assigned P1 report. If that gate fails, stop without another
source remediation; if exact PASS and mandatory gates pass, normal commit/push updates
PR83, followed by the authorized inline reply/resolution and new-finding check. No merge,
main/protection/billing/provider changes or extra phase is authorized.

Actual API reproduction: partial initial intake plus current grouped decisions advances
without count-bound completion. Initial replacement and successful failed-upload retry
reproduce the same bypass. The first probe had a harness-only absent DTO-field error;
the corrected probe reads started_at from its existing service owner and produces three
real status failures against unchanged product bytes. Original diagnostics are retained.

Change Necessity: retain explicit initial completion; documentation alone cannot prevent
the reproduced owner mutation. Decision code-change in existing orchestration only.
Canonical owner and common generator: document actions permit unstarted PENDING_INPUTS
to continue without initial completion. Existing started_at is null before explicit
count-validated start and retained across recognized replacement/reupload recovery;
existing start/recovery events prove that interpretation. No new completion flag/schema.
Highest-risk counterexample: valid PENDING_INPUTS after a previously started interrupted
document workflow must still continue when sufficiently repaired. Initial interrupted
uploads must instead remain intake until explicit count-bound completion.

Patch/ripple: shared owner guard; test canonical API/service consumers, legitimate recovery,
persisted restart and actual browser action. Single-root/multiple manifestation scope;
guard producer eligibility, never browser heuristics. Existing start/count/failure and
target-ledger safeguards remain. Large owning service receives only a local fix without
new responsibility; reuse one small predicate in existing document/start entry points.
ArchitectureReviewRequired no: no new owner, module/dependency, schema or provider.
TDD Route strict, explicit owner failing-first authority; current published source is RED.

Plan:
1. Preserve clean publication identity and exact review thread; inspect current owners.
2. Permanent adverse API tests: partial confirmation/replacement/retry and count-free resume;
   wrong count rejects, correct complete advances once; single-document compatibility.
3. Small owner correction, keeping document receipts/lineage and true recovery semantics.
4. Correct only prior fixture setup that modeled uncompleted intake as legitimate recovery;
   preserve assertions and establish completion/recovery through existing owners. Add
   initial restart/currentness/authorization and real browser remaining-intake coverage.
5. Required BACKEND_DOMAIN/BACKEND_API, affected FRONTEND_UI and supporting CI_TOOLING
   verification: focused then fresh full backend, frontend/types/build, contracts,
   configured lint/types, security/governance, guarded physical Mongo and canonical E2E.
6. Freeze full PR candidate plus remediation delta; fresh independent A01-A07/B01-B12
   and P1 acceptance/finding review. FAIL stops; exact PASS continues automatically.
7. Fresh main assessment, specific staging/content proof, normal commit, clean committed
   pre-PR/checklist, normal push to existing PR83, exact remote identity, authorized inline
   reply and resolution, fresh findings/actual CI evidence. Billing refusal NOT EXECUTED.

Current resources: PowerShell/Python/npm/GitHub CLI and guarded browser execution available;
task PYTHONPATH required because reused editable environment points at primary checkout.
No .env read. Existing Tesseract only child PATH; new allowlisted disposable Mongo service
and databases required for physical evidence. Coordinator ports8798/4198; reviewer distinct.
Never overlap resource-heavy suites, database or browser lifecycles. Delta checkpoints in
tmp/pr83-p1-evidence; prior overnight handoff remains unchanged historical publication evidence.
