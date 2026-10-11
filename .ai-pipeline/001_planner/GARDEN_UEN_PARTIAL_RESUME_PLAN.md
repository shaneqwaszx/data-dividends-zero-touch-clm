# Garden UEN PARTIAL resume hotfix - bounded plan

- Worktree: `.garden-hotfix`; branch `fix/garden-uen-partial-resume`.
- BASE_SHA / fetched main / initial HEAD: `40c530dde5edc0c714beae764fc760c741a5fdbf`.
- Scope: wrong UEN -> retained Garden document -> corrected `11111999A`, both UI choices, truthful PARTIAL acquisition, retire superseded registry blocker, retain real target/evidence blockers. No external writes, dotenv access or unrelated work.
- Owners: existing ZeroTouchOrchestrator repair path and IdentityCorrectionForm presentation. No new owner/schema/rule/provider/mapping/authorization/cache semantics. Classes FRONTEND_UI, BACKEND_DOMAIN, BACKEND_API (safe contract consumers checked; no API model change planned).
- Reproduction: normal Marketplace Mock adapter + offline strict Garden partnership decoder + XPI Sandbox name-only candidate + local PDF. HTTP200, canonical REVIEW_REQUIRED, automation WAITING_FOR_REVIEW/REGISTRY, active obsolete ACRA_ENTITY_NOT_FOUND despite corrected UEN and PARTIAL acquisition. Same three regressions pass with target NO_MATCH; stale versions and wrong-value selection are excluded for the reproduced path.
- Cause: registry completion/cancellation wrongly depends on aggregate VALIDATED, which target Search review changes. Fix owner-local predicate from verified usable current registry evidence; keep target identity review and all guards. No change to accepted partial contract.
- Change Necessity: code-change; configuration cannot correct stage/blocker ownership. Patch shape: existing owner predicate, no fallback/forced transition. Reuse current stage/exception/continuation APIs. Edit-in-place, local fix without new responsibility in the large orchestrator.
- TDD Route: strict, explicit user failing-first authority. Backend three intended-result failures captured before edits; UI original/corrected provenance regression before edits.
- Atomic work: (1) frozen reproduction and guards, (2) registry completion predicate + UI provenance, (3) focused/full affected checks/browser/memory-Mongo boundaries, (4) independent QG, one bounded remediation/re-gate if needed, (5) authorized commit/pre-PR/push/PR after exact PASS. Human merge only.
- Capabilities: Python3.12.10 and Node22.23.3; task-owned pinned .venv and npm dependencies provisioned. Native browser via Playwright; no private config. Owned browser ports will be selected; physical Mongo checked only if required and available, allowlisted disposable database only. Shared resources/worktrees preserved.
- Required evidence: focused correction/authorization/currentness/freeze, complete backend/frontend suites, Ruff/mypy/types/build/contracts/secret checks, focused Garden actual browser HTTP and relevant persistence roundtrip/adverse tests. No provider transport or persistence-schema change, so no new external authority or mandatory physical-schema evidence implied.
- Stop: material ambiguity, required unavailable evidence, unresolved independent finding, latest-main conflict, or human-only merge. Publication authorization is explicit in the owner request.

Final diagnosis and patch boundary: the recurrence generator is OnboardingService
acquisition ordering. After verified correction, REVIEW_REQUIRED/FAILED Search omitted
the normal retained-registry rebind. The existing confirmation guard correctly requires
usable VALIDATED canonical evidence; broadening that guard would be a misfix. The final
patch restores the existing acquisition/validation ordering with the retained bundle;
ZeroTouchOrchestrator remains unchanged. A second independently failing assertion proved
CLM refresh's provider-outcome-as-blocker-code projection; it now uses the same typed
identity-review code as ordinary Search. Current provider outcome remains unchanged.
CaseDetail exposes retained document candidates while registry evidence is absent;
IdentityCorrectionForm distinguishes original/current/document values. The fixture-only
wrong-UEN allowlist supports browser reproduction. No new runtime branch/provider owner.
Physical evidence was added on owned Docker mongo:7 / loopback19417, generated p12
allowlisted databases only. Browser ports18865/14873 are task-owned and harness-cleaned.

Verification support delta (CI_TOOLING): the added Garden browser file raises discovery
from91 to92, still46 per shard; exact test assertion and workflow comment were updated,
with no changed deadline/job command. New Garden physical tests are listed in the existing
physical runner so CI executes them. First causal check failure was92!=91;48 harness
tests and19 physical-runner tests now pass. Source owners/behavior remain unchanged.
