# Phase 24 publication tooling independent Quality Gate - 2026-10-02

## Executive Result

**FAIL.** The immutable historical-patch whitespace exception satisfies the six owner safety properties. One reproducible **P2-1** remains in the accompanying architecture-checker change: a module-level function receives the model-carrier exception merely by carrying a validator decorator. This violates the bounded promise that free functions remain rejected. Publication must wait for bounded remediation and fresh independent review of the changed tooling. The accepted Phase 24C and lifecycle-tooling content remains unchanged.

Reviewer: fresh `patch_publication_gate`, inherited requested GPT-6.1 Sol / High route. Applied this worktree's `fyp-quality-gate` and report template. Read the complete owner request attachment `9034b7ea-6240-459a-a73a-0522f3c1bee7/Pasted text.txt`, root AGENTS, backend guidance for the inspected model, CI_TOOLING dev_context and selected Tier 1 sections, repository skill routing, frozen manifest, historical patch manifests, accepted Phase 24C gate, preceding tooling Round 1 gate, the complete four-file delta and affected owners/tests. No implementation fix was performed.

### Exact current, tested and reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/phase24-registry-identity-ownership-ubo/data-dividends-zero-touch-clm`.
- Branch: `feat/phase24-registry-identity-ownership-ubo`.
- BASE_SHA, HEAD, merge base and inspected origin/main: `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. No reviewer fetch or remote freshness claim.
- Four-file content SHA256: `cc7a5f61bab4afbc509693bc1c74d6a4fcec4dfdf17451d9e073308d3e56b0d2`, computed from sorted UTF-8 path/NUL/file SHA256/LF.
- Manifest: `PHASE_24_PATCH_WHITESPACE_MANIFEST.json`, SHA256 `8c21ac5beb8de8113da07a8cd393a5c0bc6751781694218fb27954b552c20f65`.
- The tested and reviewed content is the frozen uncommitted four-file tree, rather than HEAD alone. All four raw hashes and digest matched before tests and before report writing.

| Reviewed file | Raw SHA256 |
|---|---|
| scripts/check_architecture.py | 28d921e973e64b922e24d044e71db370ed24e6bb175cde06732a7c367d6891a7 |
| scripts/pre_pr_check.py | 854c909e71942c0ce81ce72d57a381384327eea870ca5cf99fbee41e37db339f |
| tests/test_check_architecture.py | 378f6dc329ab6f2ea8c352c7470e42817db52a0d933ba42fdcf748f56ee35a8d |
| tests/test_pre_pr_check.py | d6e3a48b6e3486c7e1b29aa46fc8e25a15d50aea0a02eaeb60ecbbb925cbe56b |

Preservation checks independently matched all 135 accepted Phase 24C entries and digest `6da4e190816e25357d71c2fb61bf8b9493d896097b49e1906ddf8f2d1e88b3a7`, all three accepted lifecycle owners and digest `a2f217b60bcb621df95e597f71d4be170f12e30119fecc8f26f02fcff3837097`, and every raw SHA256 and staged Git object identity for the prior 144 publication paths in `tmp/phase24-closeout/publication_identity.json`. Rechecks retained those bytes. Phase 24C manifest/report SHA256 values remain `b2dcfd06191c66976cc77501af3d1ceddf5fd5ddf4a7d4d0769425aec09e9ad4` / `e9fa711fcc26c8e825a9854713746d2807f1d0c4ab5a749fee59a255da15afe7`. Lifecycle Round 1 manifest remains `eaaf5020570d61ceecfaf954df83bae744c19cd97f2eb2dc6e49ff03df7b5350`; current preserved Round 1 report SHA256 is `4a1f2240a95f6be9f9ef624773c0760d20f37e679d5acf526f726607abb33300`, matching the prior publication identity. Historical and original reports/manifests were not rewritten.

## Publication Tooling Acceptance Checklist

| Criterion | Result and direct evidence |
|---|---|
| Ordinary source trailing whitespace fails | PASS: committed ordinary Python fixture rejected by full checker. |
| Ordinary Markdown trailing whitespace fails | PASS: committed ordinary Markdown fixture rejected by full checker. |
| Arbitrary new patch receives no exception | PASS: `new.patch` context-space finding remains a failure. |
| Changed approved patch byte/hash fails | PASS: changed first byte rejected; changed hash also rejected when Git reports no whitespace error. |
| Extra/unrecognized whitespace fails | PASS: extra whitespace changes hash and fails; unknown line, unknown diagnostic, missing context and two-space context remain failures. |
| Only the exact three accepted artifacts qualify | PASS: exact paths, exact accepted SHA256 and known 20 one-space context lines required; committed fixture and actual staged component pass. |
| Historical artifacts and references immutable/non-runtime | PASS: historical, accepted, raw and staged hashes match; all prior 144 raw/staged identities preserved; references occur in evidence manifests and publication tooling/tests, with no application runtime consumer. |
| Normal staged whitespace/hygiene retained | PASS for current component: 144 paths inspected; raw Git exit 2/20 diagnostics, filtered component zero failures/three hash validations. Four new tooling owners separately pass diff whitespace. Final staging and clean committed official gate remain pending coordinator work. |
| Model-only ownership carrier recognized without admitting free functions | **FAIL, P2-1:** plain free functions reject, but a module-level validator-decorated function passes the full architecture checker. |
| Secret/private publication checks retained | PASS within supported-pattern scope: independent secret scan and eight scanner tests pass; no protected material access or application security modification. |

## Contract and Integration Findings

No contract/provider finding. The owner authorizes only immutable historical evidence whitespace, with normal rules retained, plus genuine bounded closeout/publication defect handling. There was no existing broad patch/glob exclusion to reuse; the publication checker remains the sole exception owner. Its exact three-path/hash/line mechanism does not disable normal whitespace checks or add a baseline suppression. No `.patch` glob, `.ai-pipeline/**` exemption, `--no-verify` or disabled official pre-PR gate is introduced.

The architecture false positive is real: the accepted `ownership_evidence.py` contains bounded BaseModel/StrEnum evidence carriers and Pydantic validators; authoritative math stays in the existing engine. ADR-008 and current architecture distinguish scalar evidence from ownership calculation. Recognizing that exact existing carrier is within genuine publication-defect scope, but the submitted shape guard is too permissive at function scope. P2-1 is a tooling defect; no second engine exists in the actual accepted product source.

Sponsor/Live dependencies remain unchanged and do not block this narrow tooling review. No external provider, retained database, physical Mongo, Atlas, clm_poc or lifecycle action occurred.

### Immutable patch identities and every whitespace finding

All occurrences below have raw line content exactly one ASCII space, representing a unified-diff context prefix for a blank line. Each raw and staged SHA256 equals its original historical manifest entry and accepted Phase 24C entry. None is accidental source trailing whitespace. Headers identify historical remediation before/after paths; these files are evidence, not executable application source.

| Exact path under .ai-pipeline/reports/ | Raw = staged = accepted/historical SHA256 | Count / every context-line number |
|---|---|---|
| PHASE_24B_REMEDIATION_ROUND_1_DELTA.patch | 73fca2299b9038a90968871497e8e181160e44a28141b55018cd26509a8cf1ec | 10: 6, 36, 44, 45, 49, 50, 59, 60, 90, 117 |
| PHASE_24B_REMEDIATION_ROUND_2_DELTA.patch | 763daa74b1225643b676563a696fcd9daec85486c2880ffb72b652583e09523f | 9: 6, 13, 50, 58, 65, 79, 83, 172, 173 |
| PHASE_24B_STAGE_RECOVERY_ROUND_1_ORCHESTRATION_DELTA.patch | 5baa7225bd15c0b5e4e18f20e2fb45b686530eca0f55ef2491372b25b02cff63 | 1: 57 |

## Tester and Adversarial Findings

Available in this session: Windows PowerShell, Git, task `.venv/Scripts/python.exe` with installed dependencies, Ruff and disposable unittest fixtures. Python `-B`, Ruff `--no-cache`, Git `GIT_OPTIONAL_LOCKS=0` in read-only probes. No dependency installation. Narrow approved test execution outside the primary writable root was required; only disposable fixtures were written. No shared ports/processes/databases were reserved or used.

| Fresh independent execution | Exact result |
|---|---|
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_pre_pr_check.py -v` | 50 tests PASS, zero skips, 45.937s. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_check_architecture.py -v` | 17 tests PASS, zero skips, 6.376s. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_check_secrets.py -v` | 8 tests PASS, zero skips, 0.010s. |
| Ruff `check --no-cache apps/backend scripts tests` | PASS. |
| Project state, architecture, tooling config, policy authority, external provider readiness and secrets scripts | All six scanners PASS on the actual candidate. Passing architecture scan does not invalidate the supplemental fixture defect. |
| Four-file `git diff --check` | PASS; report/manifest text whitespace inspected explicitly. |
| Actual staged component using `_scan_git_changes` and `_check_diff_whitespace` | 144 staged paths; Git exit 2; 20 findings; three exact patch validations; zero component failures. No official repository-audit PASS claim. |
| Twelve supplemental whitespace format/error/hash probes | All expected outcomes: one known diagnostic PASS; eleven negatives FAIL. |
| Supplemental complete architecture checker fixture | Reproduces P2-1: no ownership finding for validator-decorated module-level free function. |
| Frozen preservation before/pre-report checks | Four tooling + 135 candidate + three lifecycle hashes/digests retained; all prior 144 raw/staged identities retained. |

The twelve supplemental whitespace probes cover known diagnostic success, error exit 128 with a known diagnostic, stderr-only error with empty stdout, unknown line, missing context, two-space context, unknown diagnostic kind, arbitrary path, CRLF-altered content, removed final LF, UTF-8 BOM and missing content. Error exits retain failures, and hash validation occurs even when Git returns zero. `_git_object_text` reads binary Git objects with strict UTF-8 decode; worktree reads similarly decode raw bytes, so the production hash does not silently normalize CRLF. Changed CRLF/BOM/final-newline bytes are rejected.

An initial read-only identity snippet referred to lifecycle manifest `content_id` rather than its actual `tooling_content_id` and ended with KeyError after completing four-file/135-file checks. The corrected identity execution matched all required identities. This command setup error is not passing evidence or a product defect.

Prior product execution is separately attributed to unchanged accepted gates/coordinator evidence, not rerun here: backend 1774 PASS/70 guarded skips, subsequently 59+11 physical PASS/zero skips; frontend 388 PASS; focused browser 18 and full configured 38 tests/31 selectors; strict mypy 115 files; contracts 44; Windows lifecycle 31 PASS and fresh tooling Round 1 PASS. The reviewer inspected preserved acceptance reports; this narrow gate relies on byte preservation for product regression continuity and independently executes the affected tooling lanes above. Official pre-PR on clean committed state and remote CI are not yet executed/claimed by this reviewer.

## Code and Architecture Review

### P2-1: model-carrier exception accepts validator-decorated free functions

Owner: `scripts/check_architecture.py:71-79`, `_is_scalar_ownership_evidence_model`. The AST walk checks class bases and whether every function has a syntactically named `field_validator`/`model_validator` decorator. It never checks that a function is a method of a permitted model class. Consequently this exact-path fixture is accepted without `OWNERSHIP_CANONICAL_OWNER`:

```python
from pydantic import BaseModel, model_validator

class Carrier(BaseModel):
    scalar: int

@model_validator(mode="after")
def calculate_ubo(value):
    return value
```

Independent reproduction imported the existing architecture unittest fixture helper and called `_rules_after("apps/backend/app/domain/ownership_evidence.py", source)`. Result: empty rule set. The plain module function and non-validator method reject, and invalid syntax rejects, but adding the decorator crosses the intended scope boundary. Existing new tests cover only undecorated free functions, an ordinary class and a non-validator method, so all 17 pass despite this gap.

Required bounded correction: verify function scope as well as decorator shape; module-level free functions must reject regardless of validator decoration, and accepted validators must belong to the supported model classes. Add a failing-first regression for the reproduced decorated free-function case and retain valid actual carrier, ordinary second-owner and other engine/method rejection coverage. This reviewer has made no fix. The current scanner is intentionally syntax-level and cannot prove arbitrary semantic absence of ownership math; this finding concerns its newly promised syntactic model boundary, not an invented semantic guarantee.

No other P0/P1/P2 defect reproduced. The whitespace filter checks exact path/hash/context line and exact `+ ` diagnostic pair, and only filters Git's whitespace exit 2. Unknown diagnostics survive. Identity validation is independent of Git's whitespace result. No new architecture/runtime owner, dependency, fallback, source mapping or application behavior appears in the four-file delta.

## Security Review

No separate security finding. Normal staged source/test/docs scanning is retained, unsupported/unknown diagnostics fail, malformed/missing source cannot qualify, and the immutable hashes derive from original evidence authority rather than a regenerated manifest. The secret scanner passed within its supported-pattern scope, with eight fresh scanner tests including redacted output behavior. No `.env`, private sponsor material, raw provider/document body, credential or confidential exception detail was inspected or copied. No secret/confidential artifact is newly tracked by this reviewer.

## Required Fixes

P2-1 only. Preserve this frozen FAIL report, remediate only the architecture function-scope guard and meaningful regression, freeze the changed tooling identity, rerun affected verification, and obtain fresh independent review. Do not change historical patch bytes or their accepted hashes. No current defect is reclassified as technical debt.

## Readiness

The historical-patch exception itself is verified; the combined four-file publication-tooling candidate is **not ready** because P2-1 remains. No commit/push/PR should proceed under this verdict. After exact fresh independent PASS and unchanged accepted content, the coordinator may continue the already owner-authorized sequence without asking again: finish staging/hygiene, local publication commit, clean committed official pre-PR, authorized push/one PR, inspect remote CI and stop. Human merge only. No Phase 25 or Live/provider readiness is inferred.

## Git Status and Reviewer Boundary

Before report writing: 144 staged prior publication paths, exactly four assigned unstaged tooling files, one untracked tooling manifest; 149 status entries. `git diff --cached --name-status` and `--stat` reviewed (144 files, 15902 insertions, 1668 deletions). No drift outside the assigned four-file tooling delta. Prior staged Git objects and raw bytes remain unchanged. This report becomes the sole additional reviewer-authored untracked file. No source/test/configuration/ordinary-documentation fix, Git mutation, commit, push, PR, merge, provider/database operation, lifecycle invocation or next phase occurred. Report-only writes and disposable test fixtures are the complete write boundary.

Relative to accepted Phase 24C plus accepted lifecycle tooling: application API/type **no**; durable schema **no**; connector **no**; application configuration **no**; business rule **no**; target mapping **no**; auth/security semantics **no**; architecture owner/dependency direction **no**; provider status **no**; application/runtime lifecycle behavior **no**. Publication checker and syntax-level architecture guard behavior **yes**, with adverse tests. Post-report preservation verification must retain the frozen identities for this verdict to apply.
