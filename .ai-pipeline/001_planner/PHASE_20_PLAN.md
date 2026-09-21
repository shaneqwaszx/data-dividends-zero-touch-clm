# Phase 20 — Sponsor Policy Authority Gate Plan

## Identity and preflight

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Feature branch: `phase/20-policy-authority-gate`
- `BASE_SHA`: `c2929043968ab540f873ccffa69142380c2da056`
- Base tree: `e68a5e19b2a362162eb2b7b8362b40194b09b529`
- Released predecessor branch/head inspected:
  `fix/phase19-postmerge-clock-determinism` at
  `bde4943e3aaaad9fbe199eaef4614fca31f7b6b2`
- Post-merge evidence: GitHub Actions run `35603202350`, event `push`, head SHA
  `c2929043968ab540f873ccffa69142380c2da056`, `completed / success`.
- Start state: tracked and untracked tree clean; no merge, rebase, cherry-pick, or
  bisect active; Phase 20 branch absent locally and remotely before creation; only the
  coordinator is using this worktree.
- Available capabilities: PowerShell, Git 2.55.0, Python 3.12.10, GitHub CLI 2.101.0,
  repository write access, remote Git/GitHub read and publication access subject to
  approval, and one fresh independent reviewer slot. No app connector or external
  provider is required.
- Resource boundary: documentation and deterministic governance checks only. No
  browser, MongoDB, lifecycle process, disposable database, external provider, or
  reserved port is required.

## Change classification and scope

Primary change class: `DOCS_ONLY`.

Bounded supporting change class: `CI_TOOLING / GOVERNANCE`, limited to one strict
policy-authority registry checker, its unit tests, and wiring into the existing CI and
pre-PR governance lanes.

No runtime change class is authorized or expected. Product code, persistence schema,
provider composition, APIs/types, mappings, business rules, RBAC, and frontend behavior
remain unchanged.

## Authority sources inspected

The controlling read set is:

1. `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, and
   `docs/DEVELOPMENT_WORKFLOW.md`;
2. `docs/sponsor-questions/OPEN_QUESTIONS.md`;
3. `docs/decisions/DECISION_LOG.md`;
4. `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md` and
   `docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`;
5. current project/contract indexes and the existing governance checker, tests, CI,
   and pre-PR owners;
6. Phase 19 implementation and independent gate evidence, the accepted `73bbf223...`
   Phase 19 main commit, the `c292904...` deterministic-clock remediation diff, and
   successful post-merge run `35603202350`.

No private sponsor artefact, quarantined authentication collection, `.env`, credential,
or raw KYC/provider payload is needed or authorized.

## Authority classification

Every runtime-sensitive assertion uses exactly one status:

- `OBSERVED`: current source/tests/configuration prove only the implementation fact.
- `PROJECT_DEFINED_PROVISIONAL`: current POC behavior exists without sponsor authority.
- `SPONSOR_CONFIRMED`: durable repository evidence explicitly authorizes the exact
  behavior.
- `UNKNOWN_BLOCKED`: authority is insufficient to implement or claim the behavior.

The machine gate treats `runtime_enabled` as sponsor/production-policy activation, not
as an inventory of existing POC mechanics. `UNKNOWN_BLOCKED` and
`PROJECT_DEFINED_PROVISIONAL` can never have `runtime_enabled: true`. An open blocking
sponsor question also prevents `SPONSOR_CONFIRMED` and runtime activation.

## Current authority findings

- Sponsor-confirmed: D-009 permits/expects human exception review and confirms that
  “zero touch” does not mean no human exceptions. It does not identify the reviewer,
  permissions, separation of duties, dispositions, retention, or approval owner.
- Observed/project-defined provisional: current bounded review/rework actions, local
  identities/capabilities, P1–P10 ordering-only priority, conservative validation and
  source-conflict behavior, provisional `>= 25%` UBO candidate threshold, and Mock
  target completion.
- Unknown/blocked: Q-001, Q-003, Q-004, Q-005, Q-013, Q-014, Q-015, Q-016, Q-017,
  and Q-018, plus Q-002/Q-006/Q-007/Q-009/Q-010/Q-011 where they affect approval or
  handoff.

No current evidence authorizes Ready-for-Approval, calculated or supplied-risk workflow
effects, production reviewer/assignment/RBAC policy, four-eyes enforcement, source
precedence, final legal UBO policy, retention policy, priority 1–3 semantics, SLA,
escalation, approval/rejection, or production Zero-Touch/GoldTier handoff behavior.

## Expected files and owners

- Decision-ready contracts and traceability under `docs/contracts/`.
- Sponsor-readable question packet under `docs/sponsor-questions/`.
- Narrow Phase 19 current-state refresh in `docs/PROJECT_STATE.md`.
- Contract index update in `docs/contracts/README.md`.
- One machine-readable registry at
  `docs/contracts/policy_authority_registry.json`.
- One focused checker at `scripts/check_policy_authority.py`, with unit tests and
  existing CI/pre-PR wiring.
- Phase implementation and independent gate reports under `.ai-pipeline/reports/`.

The independent reviewer alone may write
`.ai-pipeline/reports/PHASE_20_QUALITY_GATE.md`.

## Governance invariants and adverse cases

The checker must reject:

- an unsupported status or malformed registry entry;
- `UNKNOWN_BLOCKED` or `PROJECT_DEFINED_PROVISIONAL` with runtime activation enabled;
- an open blocking question paired with `SPONSOR_CONFIRMED` or runtime activation;
- unresolved Q-017 supplied risk represented as confirmed or active;
- unresolved Q-001 Ready-for-Approval represented as confirmed or active;
- unresolved Q-014/Q-015 review or source authority represented as confirmed or active;
- unresolved Q-016 production identity, assignment, or priority policy represented as
  confirmed or active;
- missing required Phase 20 policy gates or duplicate policy identifiers.

Existing `check_project_state.py` remains the owner for Mock/Local/Partial/Dormant
provider truth; the new checker does not duplicate it.

## Verification

Run, at minimum:

- focused policy-authority checker unit tests;
- complete affected pre-PR/governance test inventory;
- `python scripts/check_policy_authority.py`;
- `python scripts/dev_context.py`;
- `python scripts/check_project_state.py`;
- `python scripts/check_architecture.py`;
- `python scripts/check_tooling_config.py`;
- `python scripts/check_secrets.py`;
- Markdown/JSON/file hygiene for every task-owned new file;
- `git diff --check`.

After implementation self-review, one fresh independent reviewer owns the exact Phase 20
gate report and must return exact `PASS` before publication. On the clean committed tree,
run `python scripts/pre_pr_check.py`, then verify latest-main and local/remote/CI identity.

## Stop conditions

Stop the dependent work if sponsor evidence unexpectedly authorizes a runtime change,
if the base or post-merge CI identity changes, if the worktree contains unowned changes,
if the checker cannot remain narrow and deterministic, if a required check fails, if
the independent verdict is not exact `PASS`, or if latest main introduces unreconciled
intent. Do not implement runtime policy, start Phase 21, rebase/reset/force-push, or
merge the pull request.
