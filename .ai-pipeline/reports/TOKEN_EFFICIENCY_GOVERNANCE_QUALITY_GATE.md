# Token-Efficiency Governance — Independent Quality Gate

## Executive Result

**FAIL.** The reviewed change genuinely reduces the measured routine canonical
read-set, preserves the source/contract/decision hierarchy and all valid high-risk
expansions, and passes its configured focused and broad governance suites. However,
the selector does not fail closed for a whitespace-only `--change-class` value. It
silently removes that malformed value, returns a narrow task-scoped manifest with exit
code 0, and labels the class set `FULL`. This violates the explicit malformed-input
criterion and can cause safety-relevant under-reading. Publication is not eligible.

This is a governance/publication verdict only. It makes no product-phase readiness
claim and does not authorize Phase 22.

## Reviewed Identity and Independence

- Review role: fresh independent quality-gate reviewer; no implementation,
  remediation, acceptance-criteria, Git-state, or publication mutation was performed.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `chore/token-efficiency-governance`
- `BASE_SHA`, current `HEAD`, and frozen local `origin/main`:
  `83f46e20a9ad36ae61aacb0f470c1404c4732d64`
- Initial accepted tree: `3a7fa0a1f99a97bbade13d3c1434896000660125`
- Reviewed content: 14 task-owned implementation/instruction files, all unstaged or
  untracked, with staged count 0.
- Canonical aggregate serialization: paths sorted by PowerShell `Sort-Object`; one
  `<relative path><TAB><lowercase raw-file SHA-256>` record per file; UTF-8, LF between
  records, no terminal LF.
- Aggregate before substantive review:
  `6c1dd7c55ef9e97923f6afe5fde0d436c7b6530a0d9554d87386826e9eadda20`.
- Aggregate immediately before writing this report:
  `6c1dd7c55ef9e97923f6afe5fde0d436c7b6530a0d9554d87386826e9eadda20`.
- The initially supplied aggregate discrepancy was only a path-order serialization
  difference. All 14 per-file raw SHA-256 values matched the frozen handoff exactly;
  no reviewed content changed.

| Reviewed path | Raw SHA-256 |
|---|---|
| `.agents/skills/fyp-phase-execution/SKILL.md` | `01b11c15658f1fc52d9356adc94a19714ee1302dab9c154baba4f63576610caa` |
| `.ai-pipeline/001_planner/TOKEN_EFFICIENCY_GOVERNANCE.md` | `c85a5a0cb36b7732e9a3c1ab6ee03454adf29b607394079ce5e3233937c3d6ef` |
| `.ai-pipeline/003_builder/ROLE.md` | `f6ba58f177980fac4d24f47250b18767c72b9226239ef43027c79971a6e70bb8` |
| `.ai-pipeline/005_reviewer/ROLE.md` | `110d7ef4e56b6704773a9d497360c1eb8a169b34af764c6d10302037386a9cbb` |
| `.ai-pipeline/README.md` | `e014ec8b1ee15e78df29cddfff47768f90fb0948f84f5706cfe5a910e40f1071` |
| `.ai-pipeline/reports/TOKEN_EFFICIENCY_GOVERNANCE_IMPLEMENTATION.md` | `4b6f87967d4db69fdc13e436ff74d284f7539b6c8715e18496b124abc053d976` |
| `AGENTS.md` | `687294de0e4880eebe0667292e038c32453f18295418d6ae68c74389127c2a88` |
| `docs/aegis/work/2026-09-23-token-efficiency-governance/10-intent.md` | `9f211ecd0691d5b906981bd90fa7e57226403506fb13a0f710667ea21efbf9f9` |
| `docs/aegis/work/2026-09-23-token-efficiency-governance/20-checkpoint.md` | `d6aa9d96dceac97e68a0717864e30fce8aa92d6b3056626eb8ca21cc5b3f708e` |
| `docs/aegis/work/2026-09-23-token-efficiency-governance/90-evidence.md` | `1875be3a7d73210082dbbabd8c8fd76224d5d397a4cdfa71355b5b5d54d3d9e5` |
| `docs/CODEX_WORKFLOW.md` | `3bbc5a396608955c921410f2b25faae66260aedf3d843891c7498f3196d9598b` |
| `docs/DEVELOPMENT_WORKFLOW.md` | `4b8368f1dd44af354a2faa3069c538b81f209150a8e50920d2ceca8313df9909` |
| `scripts/dev_context.py` | `727eec193ff7f699b8b2e0c19d6025d33605d7865eb917c2671774f61be1e26e` |
| `tests/test_dev_context.py` | `c9920b97ac9b3c782379cb781ca5d0372ad09cdd32736657e5daf4e31d659d44` |

The compact handoff and implementation report were used only as navigation and claims
to falsify. The complete diff, all 14 current files, the current script/tests, and the
applicable canonical sections were inspected directly.

## Governance Acceptance Checklist

| Criterion | Result | Independent evidence |
|---|---|---|
| QG-TEG-01 genuine, non-gamed routine reduction | PASS | The frozen base was independently recomputed as 84,999 LF-normalized UTF-8 bytes, 84,891 characters, 1,366 lines, and 67 headings. Current built-in results reproduce `DOCS_ONLY` 44,178 bytes (48.0%), `FRONTEND_UI` 55,315 (34.9%), and `CI_TOOLING` 45,950 (45.9%), for a 43.0% mean. The reduction comes from selected current sections while `AGENTS.md` remains full; required task-variable planners, source/tests, skills, and actual referenced content remain mandatory. |
| QG-TEG-02 source-truth hierarchy | PASS | `AGENTS.md` retains the complete source/contract/configuration/decision priority. The selector is explicitly only a navigation manifest and cannot replace actual content or authority. |
| QG-TEG-03 sponsor, security, and provider authority | PASS | Full constitutional sponsor/protected-data/provider rules remain Tier 0. Selected architecture/project-state sections retain Mock/Local/Sandbox/Partial/Dormant truth and open sponsor blockers. Six direct governance/security checks passed. |
| QG-TEG-04 high-risk expansion | PASS | Valid `AUTH_RBAC_SECURITY`, `PERSISTENCE`, and `EXTERNAL_PROVIDER` inputs each select the full four-document canonical set plus full supporting authority/skill references; each measured 88,701 bytes / 1,420 lines / 68 headings. |
| QG-TEG-05 unknown and malformed inputs fail closed | **FAIL** | Unknown `NOT_A_CHANGE_CLASS` exits 1 correctly, but `python scripts/dev_context.py --change-class " "` exits 0 and returns a narrow task-scoped manifest mislabeled `Change classes: FULL`. |
| QG-TEG-06 actual-content review | PASS | Reviewer instructions require direct inspection; this gate independently inspected actual content and executed checks rather than accepting the implementation report. |
| QG-TEG-07 exact-PASS publication | PASS | Pipeline, workflow, and publication rules continue to require exact independent `PASS`; `PASS WITH MINOR FIXES` is not eligible. This `FAIL` therefore blocks publication. |
| QG-TEG-08 tests not weakened | PASS | The nine prior `test_dev_context` behaviors remain and eight selector/benchmark tests were added. Focused 17/17 and affected governance 135/135 passed on the frozen content. The missing malformed-empty regression is part of the blocking finding, not evidence that existing tests were removed. |
| QG-TEG-09 Git/worktree/secret/KYC protections | PASS | Full constitution remains Tier 0; compact-handoff rules prohibit secrets and raw KYC/provider data; context output omits untracked content; direct secret scan and exact five-new-file hygiene passed; staged count remained 0. |
| QG-TEG-10 least-expensive capable routing without weaker evidence | PASS | Routing detail was consolidated into one canonical workflow owner while explicitly preserving evidence and independence obligations for every model route. |
| QG-TEG-11 history on demand | PASS | Tier 2 history is conditional on a named current question, never current truth by recency; phase/remediation/QG still loads the nearest relevant accepted gate/report. |
| QG-TEG-12 no RAG/vector DB/agent framework | PASS | The only RAG/vector/framework additions are explicit prohibitions and a conditional decision gate; no dependency, framework, store, or runtime was added. |
| QG-TEG-13 no product/runtime behavior | PASS | The 14-path scope is governance prose, pipeline/Aegis records, the existing context tool, and its tests. No backend/frontend/provider/API/schema/persistence/auth/business-rule runtime file changed. |
| QG-TEG-14 no Phase 22 | PASS | Planner, implementation evidence, and Aegis records explicitly hold Phase 22; no Phase 22 artifact or behavior was introduced. |
| QG-TEG-15 focused/broad governance checks on exact content | PASS | Focused 17/17, affected governance 135/135, Ruff, six direct checks, tracked diff whitespace, five-new-file hygiene, secret scan, deterministic ordering, output bounds, and benchmark reproduction passed on the aggregate above. The independent malformed-input probe separately fails QG-TEG-05. |

## Contract and Integration Findings

### High severity

No provider/API contract, mapping, schema, or integration behavior changed.

### Medium and low severity

None.

The change preserves current sponsor authority and provider classifications. There is
no external smoke-test claim and no Live readiness inference. Existing open sponsor
questions remain later dependencies only; they do not block this governance scope.

## Tester and Adversarial Findings

### High — whitespace-only change class fails open

`scripts/dev_context.py:275-280` removes every blank/whitespace-only supplied class
before validation. An all-blank supplied list therefore becomes an empty normalized
tuple, follows the selective branch, and returns the common narrow read-set. At
`scripts/dev_context.py:498-508`, the same empty normalized tuple is rendered as
`Change classes: FULL` even though `Selection mode` is `task scoped` and the emitted
references are not the full diagnostic set.

Reproduction:

```text
python scripts/dev_context.py --change-class " "
...
Selection mode: task scoped
Change classes: FULL
...
EXIT=0
```

This is not cosmetic. A malformed or empty interpolated class can bypass the required
high-risk widening and present a false-success/full-context label. The authored negative
test at `tests/test_dev_context.py:188-201` covers a non-empty unknown value but not an
empty or whitespace-only supplied value.

### Passing execution evidence

| Command/evidence | Result |
|---|---|
| `python -m unittest tests.test_dev_context -v` | Initial sandbox run: 8 tests reached PASS and 9 fixture setups errored because sandboxed `git init` was denied. This was missing infrastructure, not an assertion failure. Managed rerun: **17/17 PASS**, 6.111s. |
| Eight-module affected governance suite (`test_dev_context`, project-state, architecture, tooling-config, policy-authority, external-provider-readiness, secrets, pre-PR) | **135/135 PASS**, 59.864s. |
| `python -m ruff check scripts/dev_context.py tests/test_dev_context.py` | **PASS**. A bare `ruff` command was unavailable on `PATH`; the installed Python module was used successfully. |
| `python scripts/check_project_state.py` | **PASS**. |
| `python scripts/check_architecture.py` | **PASS**. |
| `python scripts/check_tooling_config.py` | **PASS**. |
| `python scripts/check_policy_authority.py` | **PASS**. |
| `python scripts/check_external_provider_readiness.py` | **PASS**. |
| `python scripts/check_secrets.py` | **PASS**; no supported secret pattern found. |
| `git diff --check` | **PASS** for the nine tracked modifications. |
| Explicit hygiene over the five task-owned new files | **PASS**; no trailing whitespace, missing final LF, or NUL. |
| Unknown-class probe | **PASS**; sanitized error and exit 1. |
| Two-class order probe (`DOCS_ONLY` + `CI_TOOLING` in both orders) | **PASS**; byte-identical output and deterministic sorted union. |
| Current selector output measurement | **PASS**; 43–50 lines and 3,181–3,458 LF-normalized UTF-8 bytes across the six representative routine/high-risk classes. |
| Benchmark repeated in one process | **PASS**; byte-identical output. |
| Shallow-CI dependency probe | **PASS**; benchmark execution succeeds with repository-root resolution supplied and all other Git access forbidden, proving it does not read the base object. |

The fixed baseline was independently reconstructed from Git object
`83f46e20a9ad36ae61aacb0f470c1404c4732d64`; bytes, characters, lines, and headings
match the frozen constants. The benchmark measures the current canonical four-document
union only, as declared. The internal `Footprint` also calculates document and character
counts even though the rendered table emphasizes bytes, lines, sections, and reduction.

## Code and Architecture Review

### High severity

- The malformed-empty normalization defect above is a fail-open governance behavior.

### Medium and low severity

None.

Apart from that defect, the implementation is bounded and maintainable: it extends the
existing read-only context owner, uses explicit path/section manifests, validates missing
headings, sorts paths/reasons/merged sections deterministically, and keeps high-risk
classes non-selective. It creates no new service, provider, persistence owner, state
owner, framework, dependency direction, or product architecture boundary. No ADR is
required for the reviewed design.

## Security Review

### High severity

- The whitespace-only class defect is safety-relevant because it can suppress the
  high-risk full read-set and triggered security/provider skills. No secret disclosure,
  protected-data access, or runtime security change was observed.

### Medium and low severity

None.

The tool reads only named tracked canonical files and Git metadata, uses
`GIT_OPTIONAL_LOCKS=0`, omits untracked content from status, sanitizes exceptions, and
does not read `.env` or environment secret values. Current tests confirm no repository
mutation or untracked-content output for the ordinary context path. The direct secret
scanner passed on the exact reviewed candidate.

## Required Fixes

1. Reject any explicitly supplied `--change-class` element whose stripped value is
   empty; do not silently discard it. The CLI and `select_context` API must return the
   sanitized fail-closed error/exit behavior.
2. Add focused API and CLI regressions for empty and whitespace-only supplied values,
   including an assertion that a malformed value can never produce the misleading
   `Change classes: FULL` task-scoped output.
3. Rerun the focused 17-test-equivalent suite (with the new dynamic count), the affected
   governance suite, representative multi-class/high-risk/bounded-output probes, Ruff,
   direct governance/security checks, hygiene, and secrets on the remediated frozen
   content; then obtain a fresh independent re-quality gate.

No other implementation fix is required by this review.

## Limitations and Later Dependencies

- Exact proprietary model tokens, billing, cache behavior, and model-side compression
  are not measured. The documented LF-normalized repository-text proxy is reproducible
  and sufficient for the current 30% acceptance target.
- Product/backend/frontend/browser/lifecycle/physical-Mongo/provider suites were not
  run because no such runtime surface changed. No claim depending on them is made.
- The full `pre_pr_check.py` is intentionally a clean committed-tree gate and was not
  run against this uncommitted review candidate. Its affected unit tests passed 135/135;
  the publisher must run the real checker only after accepted content is committed and
  latest-main is assessed.
- Git enumeration emitted pre-existing permission warnings for unrelated test-cache
  directories. The exact 14-file review set and five task-owned new files were inspected
  directly; those unrelated cache contents were not inspected or changed.
- Current open sponsor questions and Live provider evidence remain later product
  dependencies. They are neither resolved nor changed here.

## Readiness

- Governance acceptance: **not ready** until the fail-open malformed-input behavior is
  remediated and independently rechecked.
- Publication readiness: **not eligible** because the exact independent verdict is not
  `PASS`.
- Phase 22: remains on hold; this gate does not authorize or assess it.

## Git Status

At the last pre-report check:

- branch: `chore/token-efficiency-governance`
- `HEAD` / local `origin/main`:
  `83f46e20a9ad36ae61aacb0f470c1404c4732d64`
- staged files: 0
- tracked reviewed modifications: 9
- task-owned untracked implementation/evidence files: 5
- reviewed implementation aggregate: unchanged at
  `6c1dd7c55ef9e97923f6afe5fde0d436c7b6530a0d9554d87386826e9eadda20`
- this quality-gate report is the reviewer's only repository write
- no implementation fix, acceptance change, commit, stage, push, PR, merge, branch
  switch, publication action, or Phase 22 work occurred

## Final Verdict

FAIL
