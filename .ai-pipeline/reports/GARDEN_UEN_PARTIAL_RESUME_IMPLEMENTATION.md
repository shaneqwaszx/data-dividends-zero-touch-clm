# Garden UEN PARTIAL resume - implementation handoff

## Outcome and identity

Candidate hotfix on `fix/garden-uen-partial-resume`, worktree
`C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.garden-hotfix`.
BASE_SHA / current source HEAD / latest fetched origin/main:
`40c530dde5edc0c714beae764fc760c741a5fdbf` (no main drift).
Frozen15-path content SHA256:
`c951c08a93c0d98024c1184e76fd955d05528056a9d313f493dc5d19d1728880`.
Manifest records exact bytes separately from future commit identity. Independent
review/publication are separate stages and not inferred from implementer checks.

## Reproduced failure and proven cause

Strict offline official-Mock Garden partnership contract + normal XPI Sandbox
name-only candidate + local PDF extraction: wrong11111998B -> corrected11111999A
returned HTTP200, PARTIAL acquisition and correct case identity, but canonical state
REVIEW_REQUIRED and automation WAITING_FOR_REVIEW/REGISTRY retained obsolete
ACRA_ENTITY_NOT_FOUND. Three intended-result tests failed before repair.
NO_MATCH tests passed on the baseline, excluding selection/stale versions/PARTIAL
contract rejection as the reproduced cause. Actual external session UAT was not accessed.

Correction acquired verified registry evidence before Search; review/failure Search
then replaced aggregate state and skipped normal retained-registry rebind. Existing
orchestration correctly required usable canonical state to retire blockers. The final
repair is at OnboardingService, reusing its existing acquisition/validation path after
Search for a verified correction, with zero additional provider fetches. The temporary
orchestrator predicate was removed completely; that file is unchanged. A second failing
assertion proved CLM refresh exposed MATCH_FOUND as an identity blocker code. The final
checkpoint uses GT_SEARCH_IDENTITY_REVIEW_REQUIRED while retaining provider outcome.
UI label regression failed before original/current/document distinction was added.

## Exact behavior and files

Same case and original document ID/extraction/provenance survive correction. Registry
remains PARTIAL with COMPLETE profile/officers and UNSUPPORTED ownership/relationships;
no fabricated edges/percentages or COMPLETE binding. Superseded registry blockers become
CANCELLED history; no-match continues to readiness, while incomplete target identity
retains the existing creator-confirmation action. Use entered selects current retained
identity; manual and document choices remain verified/version-bound. No implicit target
confirmation, Shell/Policy/Amend, new intent or replay occurs.

INTENDED: apps/backend/app/services/onboarding.py;
apps/backend/app/services/clm_orchestration.py;
apps/frontend/src/pages/CaseDetail.tsx;
apps/frontend/src/pages/IdentityCorrectionForm.tsx.
SUPPORTING: IdentityCorrectionForm.test.tsx; Garden regression and physical Mongo test
files; Garden browser test; scripts/slice_b_registry_fixture.py;
scripts/e2e_backend_server.py; scripts/run_physical_mongo_tests.py;
tests/test_run_e2e.py; .github/workflows/ci.yml (count comment only); bounded planner;
docs/integration/GARDEN_UEN_PARTIAL_RESUME.md. Exact paths/hashes are in the manifest.
Report/manifest files are evidence support, excluded from product-content hash.

API/shared types, schema, connector interfaces, configuration, business/ownership rule,
mapping, auth/security, architecture and provider status: unchanged. Runtime correction
ordering, safe review-code projection and UI presentation: changed. CI commands,
deadlines and job inventory unchanged; browser count92/46+46 and new physical-test
inventory are maintained. No dependency/lockfile or global configuration change.

## Verification summary

- Focused Garden13 + current identity/stage-recovery/SliceB49:62 PASS.
- Physical Garden2: PASS on new owned mongo:7 container, loopback19417, fresh generated
  allowlisted p12 databases; strict cleanup assertions pass; no protected database access.
- Configured Playwright2 actual authenticated UI/HTTP journeys: PASS9.2s, owned
  ports18865/14873, strict offline transports, zero external calls/target mutations.
- Full frontend:50 files/583 tests PASS10.46s; types/build/npm dependency integrity PASS.
  Existing React act/SSR warnings and unchanged installed dependency advisory remain.
- Full backend: RUNNING at receipt preparation; final evidence to be appended.
- Ruff backend and touched scripts/tests PASS. Mypy `app` from apps/backend: PASS127
  source files. `pip check`: PASS. An initial root-directory mypy invocation lacked the
  configured plugin and was discarded; configured rerun passes without source repair.
- Contract unittest44 PASS; secret scan PASS; scanner unittest8 PASS; asset unittest4 PASS.
- Browser harness unittest48 PASS; physical harness unittest19 PASS. Added browser file
  initially failed pinned91 count (actual92); exact inventory assertion/comment corrected,
  preserving maximum shard46 and8340-second bound, no deadline reduction.
- check_project_state, check_architecture, check_tooling_config,
  check_policy_authority, check_external_provider_readiness: PASS.
- Complete final diff self-reviewed; tracked whitespace and explicit task-owned new-file
  whitespace PASS. New tracked/staged files receive the secret scan at publication.
- Full passing independent QG and clean committed pre-PR are required before push/PR.

## Resources, authority and remaining action

Task-owned Python3.12.10 .venv / pinned dependencies and Node22.23.3 / pinned npm.
Shared environment lacked PDFium and sandbox restricted local worker/socket execution;
checks ran with approved process/network permissions and offline providers. No private
.env read, external provider HTTP/write, VirtualBox/runner action or prior billing
investigation. Original measured-evidence checkout/head and all existing worktrees and
untracked evaluation/output folders are preserved. New nested isolated worktree is the
only additional untracked path in the original checkout. Host-managed creation failed
on Windows long-path checkout before registration; explicit fallback used long-path Git.

Owner authorizes normal commit/push/hotfix PR only after independent exact PASS and
committed pre-PR PASS. No merge authority. Container is task-owned and will be removed
only after independent physical verification; hotfix worktree remains for human review.

## Final broad evidence - supersedes RUNNING at receipt preparation

`../../.venv/Scripts/python.exe -m pytest` from `.garden-hotfix/apps/backend`:
**2668 passed,151 skipped,4 warnings, exit0,1246.68s**. Production bytes and ordinary-test semantics exercised match the frozen candidate
(the subsequent only test change removes an extra terminal blank line). Collection began before the new
physical2 file and later test-inventory/comment support additions; physical2 and
browser/physical harness67 have separate fresh PASS execution.151 skipped tests are not
reported as executed or passing. Current relevant physical Garden evidence is the
separately executed2 real-driver tests. Warnings are existing Starlette TestClient
deprecation and deliberate malformed-Pydantic conformance fixtures.
Full frontend exact command `npm test -- --reporter=dot`:583 passed/50 files, exit0;
`npm run typecheck`, `npm run build`, `npm ls --all`: exit0.
Independent verdict remains owned exclusively by the fresh assigned QG report.

## Publication hygiene delta

The staged whitespace check detected an extra blank line at EOF in the new Garden
regression test, missed by the initial trailing-space-only scan. The sole remediation
removed that terminal whitespace. All other fourteen frozen paths are unchanged.
The manifest above records the updated raw-byte identity. Independent re-gate owns
the final exact acceptance and separately binds normalized staged blobs. Full staged
whitespace and secret scans now pass. No runtime, test assertion or safeguard changed.
