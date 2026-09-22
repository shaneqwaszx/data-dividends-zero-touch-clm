# Pre-Phase 22 Manual-UAT Stabilization — Round 2

## Scope and revision boundary

- Repository: `data-dividends-zero-touch-clm`.
- Branch: `fix/pre-phase22-manual-uat-stabilization`.
- Accepted main / merge base: `ef338c9b7926a298e8987acb975fd93c96ed2bfb`.
- First stabilization commit and task-start HEAD:
  `fd613a89cab58ebf3044f49a272e7f8cd76b67fd`.
- Task-start state: clean, ahead 1 / behind 0, no active Git operation, no running
  launcher-owned demo, and no concurrent writer.
- Change classes: `FRONTEND_UI`, `AUTH_RBAC_SECURITY` verification, and `DOCS_ONLY`.
  Backend API/runtime and persistence schema behavior are unchanged.
- This task does not start Phase 22.

The current session exposed PowerShell, Git, Python 3.12.10, Node 22.23.2, npm 10.9.8,
the repository Python virtual environment, local Playwright/Chromium, loopback process
lifecycle tooling, and read/write access to this checkout. MongoDB was reachable through
the existing untracked local configuration. Ports 8000/5173 had no launcher-owned demo
at task start. No external provider or Live credential was used.

## Cases table alignment

Root cause: `apps/frontend/src/styles.css` retained an obsolete grid-era `.case-table`
owner even though the current Cases view is a native HTML table. Its `display: grid`
overrode native table layout, so headers and body cells no longer shared the table
column algorithm.

The dead grid/header/row rules were retired. The current table now uses a 12-column
`colgroup`, fixed intentional widths, native fixed table layout, safe wrapping, and the
existing locally contained horizontal scroller. Action controls retain a dedicated
column. Onboarded keeps its separate existing sizing.

Browser evidence uses bounding boxes rather than screenshot judgment. At representative
768px and 1440px widths it checks all 12 corresponding header/body left positions and
widths within one CSS pixel, root containment, and functional local horizontal scrolling.
The focused guarded memory-only Chromium lane passed 1/1 after reproducing and closing
the obsolete-CSS conflict.

## Mongo mode restoration

The ignored local `.env` setting was changed only from
`CLM_PERSISTENCE_MODE=memory` to `CLM_PERSISTENCE_MODE=mongo`. Existing Mongo connection,
database, collection, credential/hash, and provider settings were preserved and were not
printed. `.env` remains untracked.

Before demo startup, a read-only ping/count/full-envelope decode probe reported:

- cases: 14;
- teams: 2;
- profiles: 6;
- policies: 1; and
- decoded case envelopes: 14.

The probe performed no write, delete, drop, migration, repair, index change, or cleanup.
The case created during the earlier memory-mode UAT session is process-local and is not
migrated; its disappearance after the old memory backend stops is expected.

## Priority compatibility model

The user-visible ordering vocabulary is now `Unset`, `Low`, `Medium`, and `High`.
One frontend helper is the presentation/mapping owner:

| Stored/API value | Visible tier | Canonical tier write |
|---|---|---:|
| `null` | Unset / Unprioritised | `null` |
| `1–3` | Low | `1` |
| `4–7` | Medium | `5` |
| `8–10` | High | `10` |

The nullable integer API and Mongo field, backend ordering, legacy clients, and existing
durable records remain compatible. Exact numeric options were removed from ordinary New
onboarding, case mutation, and list controls. Dashboard numeric buckets are aggregated
once into Low/Medium/High/Unset and retain the exact total. Priority badges used by
Cases, Case Detail, Dashboard, Onboarded, and Audit share the same mapping.

This is `PROJECT_DEFINED_PROVISIONAL` under D-045 pending Q-016. It is ordering-only and
has no risk, SLA, routing, escalation, notification, approval, or regulatory meaning.
No persistence migration, API field removal, risk model, or workflow effect was added.

## Policy mutation verification

Current source retains this capability matrix:

| Role | View | Create showcase | Update editable | Reset one/all |
|---|---:|---:|---:|---:|
| Relationship Manager | Yes | Yes | Yes | Yes |
| Director | Yes | Yes | Yes | Yes |
| Client Onboarder | Yes | No (`403`) | No (`403`) | No (`403`) |
| HR | Yes | No (`403`) | No (`403`) | No (`403`) |

Fresh isolated in-memory API tests exercise every row. Created rules are asserted
`DISPLAY_SHOWCASE_ONLY`. Existing `NOT_EDITABLE` behavior is unchanged. Runtime rule
edits remain limited to the existing contract, and immutable per-case snapshots mean
successful changes affect future cases only. The guarded browser lane confirms RM and
Director see Add/Edit/Reset controls while Client Onboarder and HR do not. No policy
mutation was performed against the user's `clm_poc` catalogue.

## Files changed

Frontend runtime and tests:

- `apps/frontend/src/priority.ts`
- `apps/frontend/src/pages/PriorityControl.tsx`
- `apps/frontend/src/pages/HomeOnboarding.tsx`
- `apps/frontend/src/pages/Dashboard.tsx`
- `apps/frontend/src/pages/CaseQueue.tsx`
- `apps/frontend/src/design-system.css`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/PriorityTier.test.ts`
- `apps/frontend/src/Phase13AuthPriority.test.tsx`
- `apps/frontend/src/Dashboard.test.tsx`
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `apps/frontend/e2e/responsive-layout.e2e.ts`

Backend verification:

- `apps/backend/tests/test_phase14_5_policy.py`

Governance and demo truth:

- `docs/PROJECT_CONTEXT.md`
- `docs/PROJECT_STATE.md`
- `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`
- `docs/contracts/POLICY_AUTHORITY_MATRIX.md`
- `docs/contracts/policy_authority_registry.json`
- `docs/decisions/DECISION_LOG.md`
- `docs/demo/DEMO_RUNBOOK.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `docs/sponsor-questions/PHASE_20_POLICY_DECISION_PACKET.md`
- this report.

Local ignored configuration:

- `.env`: only `CLM_PERSISTENCE_MODE=memory` -> `mongo`; not tracked or staged.

## Verification completed before independent review

- Focused frontend: 4 files, 56/56 passed.
- Full frontend Vitest: 20 files, 272/272 passed.
- Frontend typecheck: PASS.
- Frontend production build: PASS, 112 modules transformed.
- Focused backend priority/policy/persistence: 105/105 passed.
- Guarded responsive/policy/alignment Chromium lane: 1/1 passed in an isolated
  `_env_file=None`, `CLM_PERSISTENCE_MODE=memory` lifecycle.
- Exact unfiltered guarded Chromium suite: 7/7 configured tests passed in seven fresh
  isolated memory-only lifecycles.
- Read-only Mongo ping/count/decode: PASS; 14/14 case envelopes decoded.
- Project-state, architecture, tooling-config, policy-authority,
  external-provider-readiness, and secret checks: PASS.
- Ruff for the changed backend test: PASS.
- `git diff --check`: PASS, with only existing Git line-ending conversion notices.

The first focused Vitest attempt was blocked by sandbox `spawn EPERM`; the unchanged
permitted run passed. The first browser run intentionally exposed the stale
`display:grid` owner; after retiring that dead internal CSS, the unchanged focused lane
passed. The first unfiltered run exposed the stale raw-`7` browser mutation expectation;
that test now writes canonical Medium (`5`) and asserts the tier badge. An isolated rerun
then encountered one transient seeded-row lookup miss; it passed unchanged on rerun. A
later full run exposed the same row-discovery fragility in the responsive lane, so that
lane now uses its existing Cases search control to find the exact known case before
following the real SPA link. The final focused responsive run and exact unfiltered 7/7
run passed. None of these runs accessed `clm_poc`; the browser runner constructs an
explicit memory-only backend with `_env_file=None`.

## Self-review and explicit non-changes

- Headers and body cells now share the native table column algorithm and measured boxes.
- The Cases table scrolls locally and does not widen the page.
- Long company/exception content wraps and the Action column remains available.
- Onboarded retains its separate table contract.
- No raw 1–10 selector remains in normal operational UI.
- Legacy priorities 2/3/4/6/7/8/9 map safely without rewriting stored cases.
- Higher canonical values still sort before lower values; unset remains last under the
  existing backend contract.
- Q-016 remains open and the vocabulary remains provisional.
- No case or policy catalogue was migrated or rewritten in `clm_poc`.
- RM/Director capability was verified; Client Onboarder/HR mutation remains forbidden.
- Showcase creation remains display-only and current cases keep immutable snapshots.
- No ACRA, GoldTier, PingFed, IDP, ownership, connector, mapping, target-ledger,
  persistence schema, React Query, or architecture-owner code changed.
- The accepted first stabilization behavior remains intact.
- Phase 22 did not begin.

Independent quality-gate verdict, second local commit/tree, clean status, post-start
Mongo count, and running-demo evidence are recorded only after those steps complete.
