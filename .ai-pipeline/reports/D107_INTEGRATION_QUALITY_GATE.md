# D-107 Latest-Main Integration - Independent Quality Gate

- Date: 2026-10-30
- Reviewer: a fresh, independent QG agent. It did not author, remediate, integrate or review D-107 in round 1 or round 2.
- Scope: the staged merge of origin/main `c6b37f2` (PR #142, D-101) into `feat/assistant-claude-hr-enablement-int` at HEAD `5a766fa` (D-107, PR #141).
- Verdict: **PASS**

## Frozen identity (recomputed at start and at end, identical)

| Item | Start | End |
| --- | --- | --- |
| Branch | `feat/assistant-claude-hr-enablement-int` | same |
| HEAD | `5a766facfd0769844d6b1eea9425cab1ac382360` | same |
| MERGE_HEAD = origin/main | `c6b37f2284dcd2c2e421fcc24f86a35962c29e9e` | same |
| `git write-tree` | `85b4f0a774138ec69eb768535cfd644ed6c48ac5` | same |
| `git diff --cached --binary origin/main \| git hash-object --stdin` | `60aa2add46a2c4648da4e7d0fcd9ba23ee4ce83b` | same |
| The same, excluding `.ai-pipeline` | `c2a472f575dafa5cd2a3f4ee52670ed4b3d68e51` | same |
| Unstaged `git diff` | empty (0 bytes) | empty |
| Untracked or modified files outside the index | none | none, apart from this report |

The reviewer wrote only this report. It made no change to the index, MERGE_HEAD or the tracked tree. Probes and `git archive` exports went only to the session scratchpad. No `.env` file was read, and there were no network calls and no paid calls.

## Integration correctness

| Claim | Method | Result |
| --- | --- | --- |
| Nothing of D-107 is lost | For each of the 15 delta paths, the staged patch over `c6b37f2` was compared with D-107's patch `7e5653d..5a766fa` (with the `index` and `@@` lines removed), and the staged blobs were compared with the `5a766fa` blobs. | The same 15 paths are in both deltas. 12 blobs are byte-identical to `5a766fa`: the 7 Python files, 3 frontend files and 2 QG reports. 13 patches are identical, including `synthetic_boundary.json`. The boundary blob differs only because main's base differs; D-107's patch (`+disable`, `+monthly`, `+ro`, `+setup`, no removals) applies unchanged. The only content differences are the two documentation lines below. |
| Nothing of D-101 is lost | Every one of the 93 paths in `git diff --name-only 7e5653d c6b37f2` was compared, staged blob against `c6b37f2` blob, with absent counted as absent. | 90 of 93 are identical. The 3 that differ are the stated overlap files: the boundary and the 2 docs. `demo-government-scanned.pdf` is absent both on main and in the staged tree; D-101 deletes it, so it is not part of the delta. |
| Boundary is generated and current | `apps/assistant/scripts/build_synthetic_boundary.py --check` | `synthetic boundary is current` (rc 0). Over main, it adds only `disable`, `monthly`, `ro` and `setup`, and removes nothing. |
| Eligibility manifest is current | `apps/assistant/scripts/build_synthetic_eligibility.py --check` | `synthetic eligibility is current` (rc 0). Its blob is unchanged from main. |
| Docs are main's bytes plus D-107's block | Byte-prefix hash: the first N bytes of the staged doc, where N is main's size, were hashed against main's blob. | `PROJECT_STATE.md`: main's 1468 lines and 866 CRs are an exact prefix (`c4799f5c…` = `c4799f5c…`); the 18 appended lines are all CRLF (884 − 866 = 18). `DECISION_LOG.md`: main is an exact prefix (`d4e7adae…`); the 27 appended lines are LF (0 CR). There is no EOL churn. |
| Only the basis lines changed versus `5a766fa` | The added lines of each doc patch were diffed against each other. | `PROJECT_STATE.md` differs in the heading ("uncommitted" became "integrated onto main `c6b37f2` as `…-int`") and the basis bullet. `DECISION_LOG.md` differs only in the Q1 row. Nothing else changed. |
| Whitespace | `git diff --cached --check origin/main` | clean (rc 0) |

## Qualification basis (computed by the reviewer)

The values come from `model_qualification.qualification_basis()`, run under `PYTHONPATH` set to each tree's `apps/assistant`. Each export was made with `git archive <rev> apps/assistant | tar -x` into the scratchpad.

| Tree | Basis | Documented |
| --- | --- | --- |
| Integrated worktree (staged = working tree) | `5dc26b296026251c…` | yes: PROJECT_STATE:1482 and DECISION_LOG:1799 (Q1) |
| `git archive origin/main` (`c6b37f2`) | `5adfe7ec2c5852cc…` | yes: same lines |
| `git archive 7e5653d` | `7e386b8a69e127b1…` | yes |
| `git archive 5a766fa` | `80448c6d7d61d500…` | yes |

All four statements are correct. Main's own D-101 entries do not record D-101's basis move (`7e386b8a…` to `5adfe7ec…`). The integrated D-107 text now records it implicitly (see I2).

## D-095 eligibility with D-101's manifest and fixtures

- **Manifest contents.** The manifest, unchanged from main, approves by digest `demo-gamma-partnership-agreement.pdf` (`e45feb3a…`, 358866 bytes) and `demo-parks-government-status.pdf` (`ed3bb29e…`, 236014 bytes). `sha256sum` and `wc -c` on the fixture files match. The retired `demo-government-scanned.pdf` digest (`1dccb019…`) is absent from the manifest.
- **Provider-neutral check.** `synthetic_eligibility.check` is unchanged by D-107 and shared by both providers. It reads the same manifest. `data_access.verification_mode` routes Claude to `anthropic_runtime.synthetic_mode`, which is HR-record-aware, and GPT-OSS to `synthetic_eligibility.mode`, which is unchanged.
- **Reviewer probe.** The scratchpad file is `probe_d101.py`. The results:
  - D-101 Parks `T99FY0105G`, demo Gamma `209990103C` and retired `209990105E` each return `SYNTHETIC_CASE_NOT_APPROVED`.
  - Sim Lim with environment `LIVE` returns `SYNTHETIC_CASE_NOT_APPROVED`.
  - The identifier screen `_UEN` matches the T-format `T99FY0105G`.
- **Conclusion.** The integration fails closed for both providers, and behaviour is identical to main (see I1).
- **Test coverage.** `test_synthetic_eligibility.py`, `test_data_access_policy.py` and `test_claude_hr_enablement.py`, including `test_every_d095_check_still_applies_to_hr_enabled_claude`, pass against D-101's manifest.

## Claude readiness and workspace identity

`anthropic_runtime.py`, `model_admin.py`, `model_admin_store.py`, `anthropic_profiles.py`, `model_catalog.py` and `data_access.py` are byte-identical to the R2-reviewed content (`5562ba59…` = `9c36e63`). D-101 touches no file under `apps/assistant` other than the two generated JSON files, so the readiness ordering is unaffected by the merge. That ordering is:

1. `ANTHROPIC_ENABLEMENT_UNREADABLE`
2. `ANTHROPIC_NOT_ENABLED`
3. `MODEL_DISABLED_BY_ENVIRONMENT`
4. `NOT_DEVELOPMENT_ENVIRONMENT`
5. the attestation and workspace checks
6. `WORKSPACE_MISMATCH`
7. the limit checks

The workspace pin, `WORKSPACE_CHANGE_REFUSED` and `WORKSPACE_MISMATCH` are likewise unaffected, as is the qualification gate (the basis now `5dc26b29…`). The Claude and readiness suites below exercise these paths on the integrated tree. Readiness is evidenced as offline Mock/Local only; no Live claim is made.

## Evidence (executed in this session against the frozen content)

| Check | Command | Result |
| --- | --- | --- |
| Targeted assistant suites (13 files): claude_hr_enablement, claude_console, claude_hr_spending, claude_multi_turn, claude_runtime, credentials, session_credentials, data_access_policy, model_management, d098_recovery, remote_test, model_factory, synthetic_eligibility | `python -m pytest -p no:cacheprovider -q` from `apps/assistant`, with `PYTHONPATH` set to the worktree's `apps/assistant` | **648 passed**, 0 failed, 0 skipped (rc 0) |
| Backend sample | `pytest -p no:cacheprovider tests/test_entity_types_persistence.py tests/test_document_digests.py` from `apps/backend` | **24 passed** |
| Root delivery assets | `pytest -p no:cacheprovider -q tests/test_phase_07_delivery_assets.py` | **4 passed** |
| ruff | `ruff check --no-cache` and `ruff format --check --no-cache` on D-107's 7 Python files | All checks passed; 7 already formatted |
| mypy strict | `mypy --cache-dir <scratchpad> ai_assistant` | Success: no issues found in 47 source files |
| Frontend typecheck | `npm run typecheck` | clean |
| Frontend tests | `npx vitest run` | **71 files, 1284/1284 passed** |
| Generators | boundary and eligibility `--check` | both current |
| Repository hygiene after runs | `git status --untracked-files=all` and `git diff` | no stray files; unstaged diff empty |

Not executed by this reviewer:

- **The full backend suite.** The integrator reports D-101's 37 backend test files at 1199 passed and 105 skipped. Those skips are real-Mongo tests, and no disposable Mongo was available. The backend tree is byte-identical to main's, and D-107 changes no backend file, so this lane belongs to D-101 and is not a D-107 integration risk.
- **The full assistant suite.** The integrator is running it separately; there is a known Windows Errno 24 under load.
- **Playwright E2E and physical Mongo.** Both are classified as missing infrastructure, and neither is required by the integration delta.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| I1 | Info (pre-existing, D-101/D-095 scope) | `apps/assistant/ai_assistant/synthetic_eligibility.json` (`companies`); `apps/assistant/scripts/build_synthetic_eligibility.py:38-42` | D-101's two new documents are approved by digest. Their cases cannot be D-095-admitted, though, because the zero-touch demo companies are not approved companies in the manifest: Parks `T99FY0105G`, and Gamma and the others `2099901xxX`. Those companies come from local seeds, not `MOCK_ACRA_SOURCES`, so `check` returns `SYNTHETIC_CASE_NOT_APPROVED` for Claude and for GPT-OSS. This fails closed, and main behaves identically. It is not caused by D-107 and needs no fix here. If the owner wants remote models on those cases, that is a separate decision. |
| I2 | Info (docs) | `docs/PROJECT_STATE.md:1482`; `docs/decisions/DECISION_LOG.md:1799` | Main's D-101 entries never stated D-101's own basis move (`7e386b8a…` to `5adfe7ec…`). The integrated D-107 text states both basis pairs correctly, so the record is now complete. No action is required. |
| I3 | Info (carried over) | R2 I1 to I3 | The round 2 informational UX and scope items still apply unchanged, because the code is byte-identical. |

There are no Critical, High, Medium or Low findings. No secret, key, credential or protected data is newly tracked; the delta contains no `.env` files, keys or raw payloads.

## Change classification (integrated delta over main `c6b37f2`)

| Area | Changed? | Detail |
| --- | --- | --- |
| API/type | yes | D-107: `PUT /provider/anthropic`, `POST .../workspace-read`, `anthropic_setup`, and the `AnthropicSetup` TS type. Unchanged since R2. |
| Schema | yes | The SQLite `anthropic_enablement` table (D-107). |
| Configuration | no | |
| Connector or mapping | no | |
| Auth/security | yes | D-107's HR-only, Origin-checked, rate-limited and lock-rechecked enablement. Unchanged. |
| Business rule | yes | D-107's enablement source. |
| Architecture | no | |
| Provider status | no | Claude is Local/Mock-evidenced, with no Live claim. |
| Runtime behaviour | yes | Claude readiness and the D-095 mode under HR enablement. |
| Qualification basis | yes | The integrated basis is `5dc26b296026…`. Claude Balanced needs re-qualification after merge, within the owner's existing authorisation. |

## Readiness

The frozen integrated content (`write-tree 85b4f0a7…`, delta `60aa2add…`) is acceptable for the next lifecycle stage. That stage needs:

- the merge commit, with its tree equal to `85b4f0a7…`;
- `pre_pr_check.py` on the committed state;
- explicit owner authorisation to publish to PR #141.

The owner merges. Hosted CI status is not assessed here. After merge, Claude Balanced re-qualification on basis `5dc26b296026…` remains an owner-authorised operational step.
