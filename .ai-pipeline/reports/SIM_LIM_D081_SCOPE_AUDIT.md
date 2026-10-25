# D-081 scope audit (owner correction, 2026-10-24)

Status: OWNER SCOPE REVIEW PENDING. Nothing was committed, pushed, reset, reverted,
cherry-picked or deleted. No product code changed after this correction.

## How the AI Assistant entered testing

A message titled "UI Enhancement V1 — Visual Smoke Test and Owner Approval Gate" arrived in
this session as a user message. It:
- named candidate HEAD `52b631da…` (tree `73c8b62e…`) on `integration/ui-enhancement-v1-stage2`;
- listed, in its section 4D, "AI Assistant guidance and navigation to an existing case-page
  section" and "GoldTier Details & Status".

Starting a separate session was refused because the session runs over Remote Control, so the
smoke test ran here. It was **test-only**:
- it ran against main `ceefe1e`, not the D-081 worktree;
- it used separate processes (a backend from a `git archive` export of `ceefe1e`, Vite from
  the primary checkout's main source, and the AI Assistant service with its model disabled);
- it changed no code anywhere.

It stopped on receipt of this correction. The V1, assistant and backend smoke processes on
8100, 8811 and 5811 are stopped. The D-081 smoke servers on 8791 and 5791 are untouched.

## Commit `52b631da`

| Item | Value |
|---|---|
| Commit | `52b631da19e2889643895f034d3885039ca71bf4`, author "Claude", 2026-10-22 08:43 UTC |
| Parent | `dbfb170c80345e9a5d3bee76f57182f37595df1d` |
| Tree | `73c8b62e44ebe88373f67c3d08e485f2609e55ce` |
| Branch | **None.** It is an unreferenced object in the shared repository; no local or remote branch contains it |
| Purpose | "fix(assistant): point guidance at the case page's GoldTier Details & Status section" |
| Files | `apps/assistant/ai_assistant/guide.py`, `.../knowledge/guidance/environments.md`, `.../knowledge/guidance/review-and-send.md`, `apps/assistant/tests/test_required_p2.py`, `.../tests/test_ai_assistant_main_integration.py` (5 files, +28/−11) |
| Belongs to | An earlier UI Enhancement V1 stage-2 integration task (2026-10-22). It is not part of this worktree and not an ancestor of main or of `feat/sim-lim-acra-ownership-followthrough-20261024` |
| Where its content is now | Main already contains identical `apps/assistant` content: `git diff 52b631da 2f45324 -- apps/assistant` is empty. It arrived through the V1 squash merge `2f45324` (PR #103). This session did not create, modify or apply it |

## Current D-081 candidate

| Item | Value |
|---|---|
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024` / `feat/sim-lim-acra-ownership-followthrough-20261024` |
| HEAD = BASE = `origin/main` | `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. No commits; nothing staged. The reflog shows only the worktree creation |
| Candidate tree (recomputed now) | `f79e3192303bbec6759924e35317ecb0e3b312e6`, **identical** to the frozen UI-correction candidate |
| Last independently accepted D-081 tree | `ff8f7ab5cbadb6349e3561a48fd030bd76567bfc` (re-QG PASS) |

**Delta `ff8f7ab` → `f79e319`, all within the approved U1–U4 scope.** 12 files:
- `types.ts`;
- `ownershipDisplay.ts`;
- `UboSummary.tsx`;
- `OwnershipPathExplorer.tsx`;
- `OwnershipStructure.tsx`;
- the new `UboSummary.test.tsx` and `ownershipAssumedBasisFixture.ts`;
- the `ReviewAndSend.test.tsx` and `five-layer-hybrid.e2e.ts` assertions;
- `OWNERSHIP_UBO_PROFILE.md`, `DECISION_LOG.md` (D-081 presentation bullet) and
  `FIVE_LAYER_ACRA_HYBRID_DEMO.md`.

**Unauthorized product changes: none.** The whole candidate against BASE has no file under
`apps/assistant` and no AI Assistant or GoldTier code. Backend, `scripts` and backend tests
are unchanged against `ff8f7ab`.

## Out-of-scope activity (test-only, recorded, not remediated)

- The UI Enhancement V1 visual smoke test and the AI Assistant navigation probe on main.
- Artifacts, kept as evidence; delete only on owner decision:
  - scratchpad `ui_v1_smoke\` (scripts, screenshots, video, results, `main_export\` copy of
    `ceefe1e`, logs, runtime password file);
  - the primary checkout's gitignored `.playwright-mcp\v1\` and `.playwright-mcp\console-*`;
  - Vite's `node_modules\.vite-temp` in the primary checkout (ignored).
- Deferred findings (main/V1 UI, not D-081; details in `ui_v1_smoke\V1_VISUAL_SMOKE_REPORT.md`):
  1. at 390 px the pipeline rail clips the Registry verification and Risk assessment labels;
  2. the sticky section header overlaps its status line;
  3. the GoldTier Details & Status pill reads "Complete" while its line says "Attention
     required";
  4. "0 active blockers" appears beside Blocked stages;
  5. the UEN conflict says to confirm in Registry verification, but the decisions live under
     Document verification;
  6. the floating assistant button overlaps content.

  For the AI Assistant: section links worked in deterministic mode. A first automated check
  wrongly reported navigation; it had clicked the section's own header. That was corrected.
  Nothing about the assistant was changed or remediated.

## Evidence validity

- **D-081 UI correction (`f79e319`), still valid** because the tree is unchanged:
  - typecheck PASS, full Vitest 64 files / 1058 PASS, build PASS;
  - focused E2E 7/7, full browser E2E 115/115;
  - CI lanes and checkers PASS, benchmark 30.047%.
- The fresh independent QG for `f79e319` has **not yet been commissioned**.
- The `ff8f7ab` re-QG PASS remains historical evidence for that tree.
- The V1 smoke results concern main `ceefe1e`. They are not D-081 evidence and are not used
  as such.

## Recommended steps to restore scope

1. Done: stopped all V1 and AI Assistant test processes.
2. No product rollback is needed: the candidate contains only approved files.
3. Owner decision: keep or dispose of the out-of-scope V1 smoke artifacts listed above, and
   whether the deferred V1 findings become a separate task.
4. On owner go-ahead: resume the authorized D-081 workflow only.
   - Commission the fresh independent read-only QG on `f79e319`; the brief is prepared,
     with no assistant scope.
   - Then the owner visual review of the Ownership & UBO and Review & Send presentation on
     the running D-081 servers (8791/5791).
   - Stop at OWNER VISUAL REVIEW / PUBLICATION AUTHORIZATION PENDING.
