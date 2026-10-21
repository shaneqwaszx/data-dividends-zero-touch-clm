# Five-Stage Workflow Governance Quality Gate

## Outcome

**PASS**

The candidate meets every acceptance criterion in the assignment. No required fix
remains. The seven findings below are optional clarity or consistency improvements;
none blocks publication. The verdict covers only the frozen content identified below.

## Reviewed identity

- Worktree: `claude-worktrees/five-stage-workflow-20261021`. Branch:
  `chore/five-stage-workflow-20261021`.
- `BASE_SHA` = `HEAD` = `origin/main` = `5d9fd145bb7b77f03f2398fd09e728912f3c071c`.
  Ahead/behind is 0/0, so no integration merge was needed.
- Content: `HEAD` plus 13 modified tracked paths. There are no untracked task files.
  - `git diff | sha256sum` = `d1d747f29b21e48b915a974c0461dc148c0d889b571f39b306b378b7935741be`.
  - Per-file sha256 prefixes match the assignment: `0a85db54 e60da1a1 f04c5e06 72a51f98
    15846dc8 e72cbe72 f6d03b41 d6c6fb4d 2a04b3f6 cbe6d8ae 562594ee ac1c29cf d906b83a`.
- I checked this identity at the start and again at the end of the review. It did not
  change.
- Binding procedure: `HEAD:.agents/skills/fyp-quality-gate/SKILL.md` and `HEAD:AGENTS.md`.
- Change class: `DOCS_ONLY`. I confirmed that the diff is prose, templates and skill
  instructions only. No executable, configuration, CI or `.github/workflows/ci.yml`
  change is present. The `.claude/skills` pointers are unchanged.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Five-stage lifecycle is canonical | Met | DEVELOPMENT_WORKFLOW `## Lifecycle`. AGENTS.md:112-119. Skills README. CODEX_WORKFLOW. `.ai-pipeline/README`. BRANCH_MERGE_PROTOCOL intro. |
| Stage 1: scope, isolated branch, smallest change, adverse tests, focused-only iteration, fix known failures, self-review | Met | fyp-phase-execution:13-16, :61-92. Integration skill:22-24 makes "known failures fixed" the Stage 2 entry condition. AGENTS.md still forbids developing on `main`. |
| Stage 2: fetch latest main, reconcile by intent, freeze, run the complete set once, Testing owns evidence, rerun invalidated evidence, broad rerun when impact is unbounded, no stale or incomplete evidence | Met | Integration skill Steps 1-5 (:20-106). DEVELOPMENT_WORKFLOW TESTING row and `### Evidence reuse and invalidation` (:254-272). 004_tester ROLE. |
| Stage 3: independent review of the exact integrated candidate, substantive, reuses valid evidence, three outcomes, bounded remediation, fresh recheck without a new full suite | Met | fyp-quality-gate:11-15, :44-59, :93-97. Workflow QUALITY GATE row. See finding 3 on the explicit RBAC and persistence wording. |
| Stage 4: exact PASS plus authorization, unchanged content, drift check, `pre_pr_check` on a clean tree, checklist, scoped staging, normal push, PR, remote SHA, both push and PR CI, exact billing-blocked token with GitHub evidence, no waiver or bypass | Met | Integration skill Steps 6-8. PRE_PR_CHECKLIST. BRANCH_MERGE_PROTOCOL. 007_publisher ROLE. PR template. The token text is byte-identical in all 6 places it appears. |
| Stage 5: human owner reviews the evidence and squash-merges; no agent merges | Met | BRANCH_MERGE_PROTOCOL Stage 5 paragraph. Workflow OWNER row. PR template footer. |
| Efficiency principles do not override security, contract, physical or change-class duties | Met | The change-class matrix is byte-unchanged. Stage 2 Step 5.2 names browser, Mongo, OCR, lifecycle, contract and security evidence. Shared-resource suites must be serialized or isolated. Non-behavioral artifacts do not invalidate evidence. |
| Constraints: no product change; no weakened mandatory tests; `ci.yml` untouched; QG not reduced to self-review; human authorization kept; Git safety kept; Claude and Codex routing consistent; minimal churn | Met | Diff scope checked. `test_claude_skill_pointers` passes. No other docs were edited. No stale `Stage 5/6/7` heading references remain outside history. |

### Condensation and lost-text check

I checked the implementer's condensation note against the text at HEAD.

- The old DEVELOPMENT_WORKFLOW pre-QG bullet (failure, stale-state, authorization,
  restart and replay paths; reproduce before fixing), the two-cycle bullet and the
  self-review bullet are all present in fyp-phase-execution:61-74. The workflow pointer
  at :226-228 keeps the rule that self-review is "never an independent-QG PASS".
- The detailed publication paragraph survives in three places: BRANCH_MERGE_PROTOCOL
  :152-160, integration-safe-development Steps 6-8, and the 007_publisher ROLE.
- The old "rerun every affected check after the final change" is now split. Stage 1
  reruns focused checks, and Stage 2 runs the complete set, so combined coverage is not
  reduced.
- The new `### Evidence reuse and invalidation` sits inside the level-two section
  `Focused, broad and independent evidence`. `dev_context` splits on level-two headings
  only, so routine context still loads it. I confirmed this from the selector code and
  from `--change-class DOCS_ONLY` output.
- DEVELOPMENT_WORKFLOW line endings: the diff adds no CR characters, and untouched lines
  are not shown as changed.

## Findings

All seven findings are optional. None is required.

1. **Low, optional.** DEVELOPMENT_WORKFLOW.md:260 says "Stages 3 and 4 do not repeat a
   complete suite…", but :272 says the reviewer "may rerun anything". Suggested
   wording: "need not repeat".
2. **Low, optional.** BRANCH_MERGE_PROTOCOL.md:139-143 lists "commit the reviewed work"
   only after PASS. It does not say that an authorized Stage 2 merge normally needs the
   feature work committed first. Without that, someone may merge onto a dirty tree,
   which is hard to back out because stash and reset are banned. DEVELOPMENT_WORKFLOW
   ("make any commit that requires") and integration-safe-development:67-68 already
   imply the commit. Suggest making the sequence explicit.
3. **Low, optional.** fyp-quality-gate/SKILL.md:51-55 does not name RBAC, team-scope
   isolation, or provider and persistence boundaries as review dimensions, although the
   owner's criteria list them. The criterion is still met: the skill classifies
   violations of AGENTS.md invariants as bugs, and AGENTS.md lists those invariants.
4. **Low, optional.** integration-safe-development/SKILL.md:132 uses `<reviewed commit>`.
   When QG reviewed uncommitted content, this means the Step 6 publication commit (the
   reviewed tree plus the report). Naming it that way would remove the ambiguity. The
   patch-id comparison is conservative either way, because context drift produces an
   unequal id and therefore a recheck.
5. **Low, optional.** integration-safe-development/SKILL.md:95 says "complete applicable
   change-class set". It does not repeat that planner or task-added checks are included.
   The matrix legend "Planner/gate may add checks" covers this indirectly.
6. **Low, optional.** fyp-quality-gate/SKILL.md:14 defines `AWAITING_INDEPENDENT_QG`
   only in the reviewer's own skill. The coordinator, who records it when no reviewer
   exists, may never load that skill. Suggest adding it to the DEVELOPMENT_WORKFLOW or
   integration handoff.
7. **Cosmetic, optional.** AGENTS.md:118 is 101 characters, against about 88 for
   neighboring lines. It was likely left long to keep the diff small.

### Informational (not findings on this content)

- Context benchmark margin: the routine mean reduction is 30.5% against the 30% floor in
  `tests/test_dev_context.py`. Future additions to selected sections may trip the test.
- `integration-safe-development/SKILL.md` is LF in the working copy while its neighbors
  are CRLF (`core.autocrlf=true`). The index blob is LF, so a commit is unaffected.
- `.ai-pipeline/005_reviewer/ROLE.md` (unchanged) still says "run the required checks".
  It is stricter than the new reuse model, not weaker.
- `integration-safe-development` frontmatter (unchanged, identical to the Claude pointer)
  does not mention "integrated acceptance". The skills README routing row does.

## Evidence

Every result was reproduced by the reviewer on the frozen identity, with
`PYTHONDONTWRITEBYTECODE=1`, Windows, Python from PATH, in this worktree.

- `python -m unittest tests.test_dev_context tests.test_check_project_state
  tests.test_check_architecture tests.test_claude_skill_pointers
  tests.test_check_policy_authority tests.test_check_external_provider_readiness
  tests.test_check_secrets`: 103 OK. This equals the implementer's 55 + 7 + 14 + 19 + 8.
- `python -m unittest tests.test_pre_pr_check`: 64 OK.
- Scripts `check_project_state`, `check_architecture`, `check_tooling_config`,
  `check_policy_authority`, `check_external_provider_readiness` and `check_secrets` all
  exit 0.
- `git diff --check` is clean. There are no untracked task files to check separately.
- `python scripts/dev_context.py --benchmark` gives a routine mean of 30.5%.
  `--change-class DOCS_ONLY` exits 0.
- The implementer's Stage 2 evidence is therefore confirmed by an independent rerun,
  not reused on trust.
- Not run, and not required for `DOCS_ONLY` with no executable change: backend pytest,
  Ruff, mypy, frontend, E2E, physical Mongo, OCR.
- `pre_pr_check.py` itself was not run. It requires a clean committed tree, which is a
  Stage 4 duty.

## Independence

I am a fresh-context Claude subagent launched by the implementing session as the Stage 3
reviewer. I did not author or remediate any of the reviewed content. I wrote only this
report and edited no reviewed file.

Process note: the binding HEAD workflow does not require a separate Stage 2 run. The
candidate's new rule that Stage 2 "must not be the implementation run" applies only
after publication.

## Governance and publication readiness

The content is eligible for Stage 4 publication once the owner authorizes it. The
publisher must:

1. Confirm the identity above is unchanged.
2. Stage only the 13 paths plus this report.
3. Commit.
4. Reassess `origin/main` drift.
5. Run `python scripts/pre_pr_check.py` on the clean tree.
6. Complete the Pre-PR checklist.

Optional findings 1-7 may be adopted only through a bounded remediation followed by a
fresh independent recheck of the changed delta. This review does not authorize commit,
push, PR or merge. No product-phase readiness is asserted.
