# Phase 13 Demo Completeness — Implementation Part 1

## 1. Executive summary

Part 1 completes the memory-mode Phase 13 sponsor-demo surface without performing the
independent Quality Gate or physical MongoDB validation. The application now creates
strict optional priority atomically, presents it in normal New Onboarding, and seeds a
deterministic two-team portfolio of ten genuinely completed synthetic cases through
authenticated application APIs and the existing `STRAIGHT_THROUGH` workflow.

## 2. Baseline

- Branch: `fix/phase13-demo-login-identities`
- Original `BASE_SHA`: `dcb52937d46882a5b1b6ba7f2d545829e6fda662`
- Current `HEAD`, local `origin/main`, and merge base at closeout:
  `dcb52937d46882a5b1b6ba7f2d545829e6fda662`
- Persistence mode for Part 1 verification: `memory`
- The host's `PHASE12_MONGO_URI` was a non-routable `<cluster>` placeholder, not a
  physical Mongo endpoint. Part 1 commands blanked it locally so genuine-Mongo tests
  skipped rather than performing network validation.

## 3. Existing auth/identity remediation preserved

The intentional prior uncommitted Vite-origin repair, person-like synthetic identities,
renamed hash settings, DBS/OCBC display metadata, signed-in identity presentation,
generator, lifecycle regression, documentation, and tests were preserved. This Part 1
work extends that same working tree; it does not reconstruct it from `main`.

## 4. RBAC showcase portfolio

The seed portfolio contains five cases for `TEAM_A` / DBS Corporate Onboarding and five
for `TEAM_B` / OCBC Corporate Onboarding. Each team receives priorities
`10, 8, 5, 1, null` in canonical backend order. The selected safe synthetic UENs are
`202400001A`, `202400007G`, `202400008H`, `202400009I`, and `202400010J`.

## 5. Team ownership model

Cases remain team-owned. No user-specific owner, reassignment, sharing, or distinct
Onboarder/Relationship Manager permission was added. Maya Lim and Ethan Tan see the
same `TEAM_A` portfolio; Sophia Ng and Ryan Lee see the same `TEAM_B` portfolio; Olivia
Koh sees both. Persisted identifiers remain `TEAM_A` and `TEAM_B`.

## 6. Successful-case workflow

For every missing seed case, the seeder creates the case through
`POST /api/demo/clm/zero-touch/cases`, then attaches a bounded fictional PDF through the
existing demo document endpoint. Existing demo providers execute the normal
Registry → Document → Reconciliation → Ownership → Readiness → Mock GoldTier flow. A
case is accepted only when the response is `COMPLETED` and the existing CLM outcome is
`MOCK_GOLDTIER_SUBMITTED`. No status or repository is mutated directly and no fake
completion endpoint was added.

The original candidate UEN `202400002B` was rejected during implementation because its
existing synthetic registry record correctly stops at `CANONICAL_DATA_INCOMPLETE`.
`202400010J`, an existing complete safe synthetic fixture, replaced it rather than
weakening workflow truth.

## 7. Seeder implementation

`scripts/seed_phase13_demo.py` authenticates as `olivia-koh`, obtains the credential by
hidden prompt, keeps cookies/CSRF in process, and uses only supported HTTP APIs. New
cases include priority in the create body. Reused cases retain their team and use the
existing priority PATCH only when the stored value differs. The script never emits the
password, hash, cookie, CSRF value, or provider payload.

## 8. Seeder idempotence

The live loopback memory-backend test observed:

- first run: `10 created, 0 reused, 10 priorities reconciled`;
- second run in the same backend process: `0 created, 10 reused, 10 priorities reconciled`;
- unique team/UEN pairs after both runs: 10;
- final successful states: 10 `COMPLETED` cases.

Final verification fails nonzero for a missing/duplicate expected identity, null/invalid
team, wrong priority, or non-completed case. A dedicated test proves verification
failure returns exit code 1 without printing the runtime credential.

## 9. New Onboarding priority contract

The zero-touch create body accepts optional `priority`. Omitted and explicit JSON null
produce null. Strict JSON integers 1–10 are accepted. `0`, `11`, negative integers,
floats, booleans, numeric strings, and arbitrary strings are rejected with `422` before
case creation. Existing clients that omit the field remain compatible.

## 10. Atomic priority-at-create

Priority travels through the existing zero-touch → CLM → onboarding service chain and
is assigned when the initial `OnboardingCase` is constructed and first persisted. The
create response immediately contains it and has no `CASE_PRIORITY_UPDATED` event. The
normal frontend performs one create POST and no follow-up priority PATCH.

## 11. Frontend changes

Normal New Onboarding retains UI V2 and now shows:

- the backend-authored canonical team display name for team actors;
- the existing backend-authored explicit team selector for Director;
- `Case priority` with helper `Optional. 10 = highest, 1 = lowest.`;
- `Unset`, `10 — Highest`, integers 9 through 2, and `1 — Lowest`;
- Unset by default for both team actors and Director;
- the returned priority badge immediately after successful creation.

The API client includes priority only in the one create body. It remains a consumer of
backend ordering and does not use local/session storage as an authorization owner.

## 12. Shared-store RBAC tests

One application/store is populated with both teams. Tests prove all five identities'
portfolio views, same-team priority mutations for Ethan and Ryan, Director global
visibility, and bidirectional cross-team direct-ID non-enumeration. For both directions,
GET and representative PATCH requests return the identical fixed 404 body used for a
nonexistent case.

## 13. Memory-mode demo evidence

A real loopback Uvicorn server hosted the memory application while `HttpSeedApi` ran
twice. The first/second counts were 10/0 and 0/10 as above, and every new case passed the
real document/orchestration APIs to canonical completion. A second in-process
shared-application test logged in as Maya, Ethan, Sophia, Ryan, and Olivia and verified
the expected five/five/ten visibility plus priority order. Separately, the Windows
lifecycle suite started the actual backend/frontend launchers and verified login through
the Vite proxy. Memory state is process-local and resets on backend restart.

## 14. Persistence schema compatibility

Phase 12's canonical `DurableCaseSnapshot` already embeds `OnboardingCase`, whose schema
v2 shape contains `team_id` and `priority`. Accepting priority during initial creation
does not change stored shape. `CASE_SNAPSHOT_SCHEMA_VERSION` remains 2; no migration or
second persistence abstraction was added. Exact schema-v1 reads still map only in memory
to null team/null priority without read-time rewrite.

## 15. Mongo-oriented test updates

The Phase 13 physical-Mongo test now supplies priority in the initial create request for
prioritised cases and retains a later PATCH-clear assertion. It continues to check schema
2, persisted team/priority, team immutability, restart visibility/order, and provider-free
reads using the new synthetic identities.

## 16. Physical Mongo status

Physical MongoDB validation:
NOT PERFORMED — PART 2 REQUIRED

The genuine-Mongo tests skipped because no usable `PHASE12_MONGO_URI` was configured.
No Mongo process was installed, started, contacted, or modified in Part 1.

## 17. Test table

| Check | Result |
|---|---|
| Strict RED evidence | Create-priority and UI/request tests failed for the missing behavior; first memory seed rejected a truthfully incomplete UEN |
| Focused Phase 13/backend regression | `119 passed, 1 skipped` (the physical Phase 13 Mongo test) |
| Live HTTP memory seeder | PASS; first 10 created/0 reused, second 0 created/10 reused |
| Full backend | `842 passed, 12 skipped, 3 warnings` |
| Frontend typecheck | PASS |
| Frontend Vitest | `108 passed` |
| Frontend production build | PASS; 45 modules transformed |
| Contract tests | `44 passed` with `PYTHONPATH=apps/backend;tests/contract` |
| Windows lifecycle | `17 passed in 207.95s` |
| Ruff | PASS; protected pre-existing cache directories produced access warnings only |
| Mypy | PASS; 78 source files |
| `pip check` | PASS |
| Secret scanner unit tests only | `5 passed` |
| `git diff --check` | PASS |

The three backend warnings remain the existing intentional malformed-provider Pydantic
serializer warnings. The 12 skips are physical Mongo tests, not Mongo passes.

## 18. Security/invariant review

- Authentication remains backend-only, opaque-session, host-cookie, and CSRF protected.
- Team/role authority remains server-authored; request headers, query values, bodies,
  localStorage, and sessionStorage cannot elevate it.
- Cross-team and absent IDs retain identical safe 404 projection.
- The seeder sends a bounded fictional valid PDF and retains no document bytes; demo and
  Mock labels remain explicit.
- No connector, TLS, ACRA, GoldTier, UBO, approval, or production-IAM behavior changed.
- No plaintext credential, hash, token, cookie, CSRF value, raw provider payload, or
  KYC/PII was added to tracked source, tests, docs, browser storage, or normal logs.
- Only `tests/test_check_secrets.py` was executed for secret checking in this continuation;
  the broad scanner was not invoked. The earlier scanner incident remains disclosed in
  the preserved authentication remediation report.
- The protected unrelated untracked artifact and `pytest-cache-files-*` entries were not
  opened, modified, renamed, deleted, staged, or cleaned during this continuation.
- POC regression catalogue behavior was preserved; no catalogue scenario was rewritten.

## 19. Files changed

Part 1 adds or changes these surfaces on top of the preserved remediation delta:

- creation chain: `apps/backend/app/main.py`, `services/zero_touch_orchestration.py`,
  `services/clm_orchestration.py`, `services/onboarding.py`;
- backend tests: Phase 13 priority, auth/RBAC, demo scripts, and physical-Mongo test;
- frontend: `App.tsx`, `api.ts`, `pages/HomeOnboarding.tsx`, and Phase 13 frontend tests;
- seeder: `scripts/seed_phase13_demo.py`;
- documentation: project context, architecture, contract, decision D-036, demo runbook,
  and this report.

The complete tracked working-tree delta contains 31 modified files because it also
includes the intentionally preserved prior auth/identity remediation. The earlier
remediation report and this report are task-owned untracked files.

## 20. Git status

The branch remains `fix/phase13-demo-login-identities`. Nothing is staged. Nothing was
committed, pushed, merged, rebased, reset, cleaned, or branch-switched. There are no
unresolved paths. The unrelated pre-existing untracked entries remain untracked and
untouched. Repository cleanliness is intentionally not claimed.

## 21. Remaining limitations

This remains synthetic Mock/process-local POC behavior. It is not PingFed/SSO,
production RBAC, assignment, notifications/SLA, Ready-for-Approval, live ACRA/GoldTier
interoperability, production persistence, or physical Mongo evidence. Memory portfolios
must be reseeded after every backend restart. Q-012, Q-015, and Q-016 remain applicable.

## 22. Part 2 handoff requirements

Part 2 must be started only by explicit owner instruction. It should configure a genuine
approved `PHASE12_MONGO_URI`, execute the Phase 12/13 physical restart and adverse-case
tests against that database, capture exact pass/fail evidence, and update the Mongo
status without treating memory tests as a substitute. The independent Phase 13 Quality
Gate remains a separate owner-controlled action and was not performed here.
