# Phase 24 closeout tooling independent quality gate - 2026-10-02

## Executive Result

**FAIL.** One reproducible P2 defect leaves the malformed-port acceptance criterion unmet: both lifecycle port overrides accept an otherwise numeric value ending in LF. No remediation was performed. All other inspected criteria and focused independent executions passed; this verdict does not weaken the existing Phase 24C accepted gate.

Reviewer: fresh `final_closeout_gate`, requested GPT-6.1 Sol / High route. Applied `fyp-quality-gate` and its report template. Read root AGENTS.md, current CI_TOOLING Tier 1 selections, repository skill routing, latest owner authorization attachment db3f784d, owning source/tests/runbook, frozen manifests, original accepted Phase 24C gate, and coordinator lifecycle receipt/log. No scoped AGENTS file applies to the three tooling paths.

### Reviewed identity and boundary

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/phase24-registry-identity-ownership-ubo/data-dividends-zero-touch-clm`.
- Branch: `feat/phase24-registry-identity-ownership-ubo`.
- BASE_SHA, HEAD, merge base and inspected origin/main: `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. The coordinator owns fetch/publication; this reviewer made no remote freshness claim or Git mutation.
- Reviewed complete tooling path set: `scripts/demo_lifecycle.ps1`, `tests/test_demo_lifecycle_windows.py`, `docs/demo/DEMO_RUNBOOK.md`.
- Tooling content SHA256: `0891be7859d87ef58977c4672f88588b524ef4da59a4318b318921de18c86649` (sorted UTF-8 path/NUL/file SHA256/LF).
- Tooling manifest SHA256: `38c6a2075d3fb4c2aa2935d95118f53d9804b2400001fb2357ac0d7dc441d907`.
- Original accepted candidate: 135 entries, content `6da4e190816e25357d71c2fb61bf8b9493d896097b49e1906ddf8f2d1e88b3a7`; manifest SHA256 `b2dcfd06191c66976cc77501af3d1ceddf5fd5ddf4a7d4d0769425aec09e9ad4`.
- Original independent Phase 24C PASS report SHA256: `e9fa711fcc26c8e825a9854713746d2807f1d0c4ab5a749fee59a255da15afe7`.

Every original 135 entry and each tooling entry matched its frozen byte hash before execution and at final pre-report recheck. Full dirty-path inventory equals the original accepted set plus the explicitly assigned tooling/manifests/reports; no unexpected source path. The index is empty. This initial gate reviewed the unchanged uncommitted content, not merely the HEAD commit.

| Tooling file | SHA256 |
|---|---|
| docs/demo/DEMO_RUNBOOK.md | 63f88749a8c44a72efecae5d64a3730ce8917a6964ef0c787bd00bd44cd9a2e2 |
| scripts/demo_lifecycle.ps1 | 5cc8803fce3ec613694be9c4884f8d9dfc0ab09e44267a19e9f3b2620e59aea3 |
| tests/test_demo_lifecycle_windows.py | b372ec2edeb587631b6dd798c9cfb4021d0828dc2af20ee7208f8f568c1a4b2e |

## Closeout Tooling Acceptance Checklist

| # | Criterion | Result and direct evidence |
|---:|---|---|
| 1 | Backend default remains 8000 | PASS: sole resolver default and fresh default/parser execution. |
| 2 | Frontend default remains 5173 | PASS: sole resolver default and fresh default/parser execution; empty Windows environment values retain defaults. |
| 3 | Overrides work independently | PASS: independent parser executes actual PowerShell resolver for each single override, retaining the other default. |
| 4 | Overrides work simultaneously | PASS: independent resolver and real start/status/proxy-login/stop on backend 60950 and frontend 60951; process metadata expected ports asserted. |
| 5 | Invalid values fail safely before action | **FAIL, P2-1:** ordinary invalid/range/space/whitespace-only cases reject; numeric value ending in LF is accepted for either variable. |
| 6 | Same-port configuration fails safely | PASS: both-explicit and collisions with either retained default reject; resolver executes before action dispatch/state access. |
| 7 | Occupied unrelated ports are untouched | PASS: independent real occupied-port test checks both requested ports, clear abort text, no metadata and living holder; original 8000/5173 owners remain unchanged. Vite --strictPort prevents silent allocation. |
| 8 | All original 20 runtime lifecycle tests execute and pass | VERIFIED COORDINATOR EVIDENCE: exact frozen log records 31 tests / OK, including all original 20, 1 added runtime safety test, 7 port tests and 3 creation-time tests. Independent inventory/diff confirms all 20 names and assertions retained; independent focused execution is separately recorded below. |
| 9 | Cleanup complete | PASS: independent start/stop and changed-port refusal/restore/stop verify owned-process shutdown; ports 60950/60951 bindable afterward, metadata and temporary metadata absent. Coordinator 55572/55573 also free. |
| 10 | No application/product semantics changed | PASS: delta limited to the three tooling owners; existing backend configured-origin seam and Vite proxy seam used without application edits. API/schema/provider/business/cache/ownership/RBAC code unchanged from accepted manifest. |
| 11 | Accepted Phase 24C candidate otherwise unchanged | PASS: all 135 file hashes and original manifest/report identities retained before and after execution. |

## Contract and Integration Findings

No contract or provider finding. This is local demo/testing orchestration only. The launcher retains Mock ACRA/GoldTier/ownership and Local POC IDP, loopback listeners and memory persistence. No real ACRA, GoldTier, PingFed or Live readiness is inferred. Sponsor dependencies remain unchanged. No external provider, physical Mongo, retained database, Atlas, clm_poc or GoldTier 143880 operation was performed.

## Tester and Adversarial Findings

### Fresh independent execution

Task `.venv/Scripts/python.exe -B` was available; no dependency install or Desktop edit. `dev_context.py --change-class CI_TOOLING` completed. Before execution, two freshly selected independent ports 60950/60951 were simultaneously bound to verify availability, then explicitly assigned to CLM_DEMO_BACKEND_PORT / CLM_DEMO_FRONTEND_PORT. Shared lifecycle execution was serialized with the coordinator.

A programmatic unittest suite loaded both configuration/creation-time classes and these real runtime methods:

- `test_start_stop_health_pids_and_unrelated_processes`
- `test_occupied_ports_fail_without_terminating_occupants`
- `test_changed_port_refuses_stop_and_preserves_owned_session`

**13 executed / 13 PASS / zero skips, 75.038s:** 7 port tests + 3 creation-time tests + 3 runtime tests. Actual startup printed resolved 60950/60951, real HTTP health and frontend proxy login passed, status owned exactly two roles, exact owned PIDs stopped, unrelated test processes survived, occupied requested ports failed safely, and changed-port Stop refused without changing the running session. Restoring the original configuration allowed clean owned shutdown.

Independent adversarial resolver probes: trailing LF **accepted** for both variables; trailing CRLF, digits followed by LF plus payload, tab-only and full-width digits rejected. This is supplemental execution of actual PowerShell resolver, not a duplicate Python validator.

Fresh checks: configured Ruff `check --no-cache apps/backend scripts tests` PASS; `check_project_state.py`, `check_architecture.py`, `check_tooling_config.py`, `check_secrets.py` all PASS. `git diff --check` on the three tooling files PASS, and explicit trailing-whitespace checks found zero. An initial Ruff invocation incorrectly included the PowerShell path and produced Python syntax errors; the corrected configured Python-only traversal passed. This invocation error is not reported as a successful run or a source defect.

Resource final check: original 8000 listener PID 45896 (python, same start time 2026-10-01 20:23:30 local) and 5173 listener PID 8456 (node, same start time 2026-10-01 20:24:47 local) remain listening. No task listener on 60950/60951 or 55572/55573; all four ports bindable. `.runtime/demo-processes.json` and `.tmp` absent. Ignored launcher diagnostic logs are existing task runtime outputs, not publication content; their bodies were not inspected or copied into this report.

### Coordinator evidence, separately attributed

Inspected `tmp/phase24-closeout/lifecycle.log` SHA256 `5b1939fb17fde0f20b20ce5adc422214bbd389287582b8cd50989bd922181c51`; its unchanged frozen-content run reports **31 tests / OK / 371.065s**. Receipt records exit 0, ports 55572/55573 closed and metadata absent. This is the coordinator's complete lane, not a claim that this reviewer reran all 31. Original runtime test inventory is 20; candidate inventory is 21. Review found no removed original assertions: existing runtime-class assertion-call count rises from 155 to 164, with port substitutions and stronger safety checks. The three-file diff was inspected directly in addition to inventory/count comparisons.

No broad product/publication suites or pre-PR workflow were run by this narrow reviewer. Publication verification remains a distinct later authorized role, contingent on exact PASS.

## Code and Architecture Review

**P2-1 - LF-terminated port values bypass strict malformed-input rejection.** At `scripts/demo_lifecycle.ps1:32`, pattern `^[0-9]{1,5}$` uses .NET's `$` anchor, which can match immediately before a final LF. `[int]::TryParse` at line 33 then accepts the trailing whitespace. Reproduction: set either override to the six-character value `43210` followed by LF; calling the actual resolver succeeds with port 43210. Defaults for the other role remain 5173 or 8000. The implementation can consequently proceed into a lifecycle action for malformed input, contrary to the assigned validation requirement. The authored invalid-value set at `tests/test_demo_lifecycle_windows.py:186` omits this case.

Required bounded correction: enforce full-string ASCII digits with a strict end-of-string check, retaining range/default/equal-port behavior; add both-variable trailing-LF regression and prove rejection occurs before any action/state access. Refreeze and obtain a fresh independent gate after affected focused/full lifecycle execution. No correction was made during this review.

Other owner flow is coherent: resolved ports feed launch command markers, strict Vite port, health probes, reported URLs, expected metadata, runtime client URLs, frontend-origin headers and shutdown checks. Metadata-port mismatch fails closed before selecting a process. Occupied-port preflight precedes runtime state creation and process startup. No new owner, fallback provider, direct route-to-persistence or ledger bypass.

Fixed 5173 references in the three changed owners are the resolver default, compatibility/collision test expectations and documented default examples/troubleshooting. Runtime execution uses resolved variables; runbook documents retaining overrides for all lifecycle actions. Separate normal seed/runbook default examples are not an overridden lifecycle client path. No lifecycle-owned Playwright path exists in this lane; its real HTTP clients are covered above.

## Security Review

No separate security finding. The launcher supplies the actual local frontend to the existing PHASE13_BROWSER_ORIGIN configuration, preserving central backend Origin/session/CSRF validation; VITE_BACKEND_PROXY_TARGET uses the existing Vite seam for the actual backend. Application configuration and RBAC semantics were not edited. No credential material, protected .env, private sponsor payload, document body or confidential response was accessed or added to publication paths. Secret scanner passed. Logs/handoff here contain only safe identifiers, modes, ports, hashes and outcomes.

## Required Fixes

P2-1 only. This is a current acceptance defect, not accepted debt or a sponsor dependency. Owner confirmed the defect is inside assigned malformed-value scope and reserved bounded remediation round 1; this initial gate consumes no remediation round. All original accepted Phase 24C evidence remains immutable.

## Readiness

Closeout tooling is **not publication-ready** until P2-1 is corrected, content is refrozen and a fresh independent gate issues exact PASS. Do not begin broad closeout/publication or Phase 25 on this FAIL. Original Phase 24C PASS remains accepted for its own unchanged content. No new next-phase or real ACRA/GoldTier readiness claim is made. Next authorized action belongs to the coordinator: bounded tooling remediation, affected verification and fresh independent review.

## Git Status and Change Classification

Combined accepted candidate and tooling are intentionally uncommitted/unstaged; index empty. Complete status/dirty scope inspected. Reviewer authored only this assigned report; transient ignored lifecycle output was generated by required execution. No implementation/test/configuration/doc fix, Git mutation, commit, push, PR, merge or next phase.

Changes relative to accepted Phase 24C: API/type **no**; durable schema **no**; connector **no**; application configuration **no**; demo-launcher session configuration **yes**; business rule **no**; target mapping **no**; application auth/RBAC/security semantics **no**; architecture **no**; provider status **no**; local lifecycle runtime behavior **yes** (validated explicit ports, linkage and cleanup). This verdict applies only to the recorded frozen content and must not transfer to remediation content.
