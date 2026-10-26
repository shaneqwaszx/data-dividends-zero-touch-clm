# AI Assistant Phase A2 — Implementation and Offline Verification Handoff (WP3 + WP4)

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Role | Stage 1 implementation plus owner-assigned integrated offline verification. Not an independent Quality Gate |
| Authority | Owner authorisation "AI Assistant Phase A2 implementation" (OD-1 to OD-9 approved for offline A2, with safeguards S1–S3); planner `.ai-pipeline/001_planner/AI_ASSISTANT_PHASE_A2_GOVERNANCE_AND_IMPLEMENTATION_PLAN.md` Rev 1 |
| Candidate (integrated) | Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a2-int-20261026`, branch `feat/assistant-phase-a2-20261026-int`, base `7d6a31aa196cff23c0b5b1fd4e5e31cf9bce0efc` (latest `origin/main`, PR #113 merged), **uncommitted** |
| Pre-integration copy | Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a2-20261026`, branch `feat/assistant-phase-a2-20261026`, base `769c149`, uncommitted, unchanged since integration (historical; not the candidate) |
| Change classes | `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY`, `PERSISTENCE` (assistant-local SQLite only), `ARCHITECTURE_REFACTOR`, `CI_TOOLING`, `DOCS_ONLY` |
| Spend / remote activity | US$0.00. No OpenRouter inference, key, generation, endpoint or account request; no real ledger; `OPENROUTER_API_KEY` never read |

## 1. Outcome

A2-WP3 and A2-WP4 are implemented offline and dormant. The default profile is unchanged
(byte-identical requests and responses); the OpenRouter profile cannot compose against a real
network. Results: section 6. Not committed; publication needs a separate owner instruction and
an independent Quality Gate on a frozen commit.

## 2. Integration with latest main (mid-run)

`origin/main` moved from `769c149` to `7d6a31a` (PR #113, answer records, D-084) during the
run. Overlap with A2: `apps/assistant/ai_assistant/config.py` and `main.py` (plus the docs A2
had not yet edited). Because commits, stash and reset are not authorised, A2 was carried into a
new integration worktree from `7d6a31a`: non-overlapping files copied byte-for-byte; the two
overlapping files merged with `git merge-file` (base `769c149`, EOL-normalised): `config.py`
clean, `main.py` one additive conflict in `_Outcome` (both field sets kept). One semantic
integration change: #113's `record_reason()` now maps A2's `budget_refused` fallback to its
existing `model_unavailable` reason (no answer-record schema change). Docs were written on top
of #113's versions. PR #114 is still a draft; D-091 / Amendment 3 numbering re-checked (0
hits).

## 3. Delta

| Area | Files |
|---|---|
| WP3 new | `ai_assistant/model_profiles.py` (registry, `ApprovedEndpoint`, no endpoint approved), `ai_assistant/openrouter.py` (dormant adapter), `ai_assistant/model_factory.py` (one composition point, locks L1–L4, lazy credential) |
| WP4 new | `ai_assistant/budget.py` (estimator, ledger, `BudgetedChatModel`), `scripts/budget_ledger.py` (offline CLI) |
| Shared (Track 2) | `llm.py` (additive types and vocabularies), `config.py` (inert settings), `main.py` (composition through the factory, metrics fields, `record_reason` mapping), `telemetry.py` (v2), `tests/conftest.py` (suite-wide network guard, key removal), `tests/test_telemetry.py` (version assertion 1 → 2) |
| Scanner (SC-1–SC-8) | `scripts/check_secrets.py`, `tests/test_check_secrets.py` |
| Tests new | `tests/remote_fixtures.py`, `test_default_request_golden.py`, `test_model_factory.py`, `test_openrouter_adapter.py`, `test_budget_ledger.py`, `test_budget_guard.py`, `test_budget_cli.py` |
| Docs | `apps/assistant/README.md`, `apps/assistant/.env.example`, `docs/ARCHITECTURE.md`, `DECISION_LOG.md` (D-091 PROPOSED), `ADR-012` (Amendment 3 PROPOSED), A1 planner renumbering note, this report, the A2 plan (copied unchanged) |

## 4. Owner safeguards

| Safeguard | Implementation | Evidence |
|---|---|---|
| S1 exact endpoint | Registry records the full endpoint slug (`provider[/variant][/region][/tier]`, verified shape from the provider-selection docs), quantisation, prices, output ceiling, documented-guarantee flag and `slug_unique_for_model`; settings name one slug; request sends it in `provider.order` and `provider.only` with fallbacks off; a base slug or a record without uniqueness evidence is refused. Uniqueness cannot be demonstrated offline: **Phase B prerequisite** | `test_a_base_provider_slug_does_not_select_an_endpoint`, `test_an_endpoint_not_shown_to_be_unique_is_refused`, payload test |
| S2 transport containment | The adapter itself accepts only `type(t) is httpx.MockTransport`; real, async, subclassed and wrapping transports are refused in the factory and in the adapter constructor; the service refuses to start with the remote profile; a session-wide conftest guard fails any non-loopback connect, asyncio connection or name lookup | `test_a_live_capable_transport_cannot_open_a_network_path` (5 cases), `test_the_suite_guard_blocks_remote_connections`, `test_the_service_refuses_to_start_with_the_remote_profile` |
| S3 ledger identifier privacy | `key_alias` must be one of `key-01`..`key-04` (code allow-list, CHECK constraint); STRICT tables; every TEXT column is a CHECK-constrained code or pattern-validated opaque id; timestamps and amounts are INTEGER; no key or key hash | `test_only_an_approved_opaque_key_alias_is_accepted`, `test_every_text_column_is_a_closed_code_or_an_opaque_identifier`, `test_the_ledger_never_stores_a_key_or_key_hash` |

## 5. Deviations from the plan (all narrow)

1. Setting `AI_ASSISTANT_OPENROUTER_ENDPOINT` (one full slug) instead of `..._PROVIDER` (S1).
2. Prices come from the endpoint record, not settings (Rev 1 §5.3); `max_price` is sent from it.
3. `build_chat_model(local_adapter=...)`: `main.py` passes its own adapter reference so the
   existing warm-up security test that patches `ai_assistant.main.OpenAICompatibleChatModel`
   keeps working unchanged.
4. Telemetry records the *requested* endpoint and `provider_verified=false`; the adapter keeps
   any undocumented response `provider` value only as an advisory comparison with the record's
   listed provider name.
5. Anomalies are stored as an integer bitmask (closed codes), not text.
6. Ledger `durable=False` exists only for the randomised invariant test (skips disk sync).
7. Post-finish frame problems keep the validated answer (`read_through_incomplete`).
8. Test files consolidated (factory/profile tests in one file; invariants in the ledger file).
9. Integration worktree (section 2).

## 6. Verification

All on the integrated candidate (base `7d6a31a`), offline, mock transports only.

| Check | Result |
|---|---|
| Full assistant suite, base `7d6a31a` (git-archive export) vs candidate, JUnit compared | Base 1,574 tests, 14 not passed; candidate 1,810 (+236 new, none removed), 14 not passed. 12 failures common to both: `OSError: [Errno 24] Too many open files` in `test_streaming_resources.py` real-HTTP tests (Windows host limit; A1 recorded the same class). Base-only: 2 (a test needing a file outside the partial export; a ChromaDB internal error). Candidate-only: 2, both classified below |
| Candidate-only 1: `test_knowledge_answers.py::test_streaming_shows_the_knowledge_line_and_carries_sources` | Pre-existing flake: 1/8 isolated runs fail on **base** and 1/8 on candidate, same assertion (case-data text instead of the knowledge line). Not an A2 regression |
| Candidate-only 2: `test_model_factory.py::test_the_suite_guard_blocks_remote_connections` | Errno 24 in the full run only (same host limit); passes alone and with all A2 tests in suite order (144 passed, 87 s) |
| New A2 tests | golden 6, factory/locks/S1/S2 50, adapter 92, ledger/invariants/S3 60, guard 16, CLI 12 (236); scanner 9 new of 17 |
| Golden default requests (T3-01) | complete, stream and warm: URL, all headers and body bytes equal the bytes captured at `769c149` (SHA-256 pinned) |
| Differential parity probe (336 requests over 7 model modes x 12 questions x 2 histories x 2 routes, plus brief/health and 41 outgoing model requests) | Base and candidate SHA-256 identical `def72e8b...92bc`; sensitivity control (temperature 0.2 -> 0.21) changes it (`4195faa0...e332`) |
| A1 snapshots | `evaluate_answers.py check`: current, 84 turns, sha256 `9341411d512d3beb` (unchanged) |
| Randomised accounting invariants | 1,000 seeded sequences (INV-2/3/5/6/7) pass; worked-example steps 0-9 and T4-17 to T4-25 pass |
| Ruff / format / mypy strict (assistant `ai_assistant`, `assistant_eval`, both scripts) | pass |
| Backend `test_ai_assistant_main_integration.py` | 2 passed |
| Full backend pytest | 3,173 passed, 177 skipped, 0 failed (18 min 46 s) |
| Backend Ruff, mypy strict | pass. `ruff format --check`: 156 files would be reformatted, identical on the untouched A1 tree; A2 changes no backend file (pre-existing, not A2) |
| Frontend (no frontend file changed; existing `node_modules` linked temporarily, package files identical, nothing installed) | typecheck pass; Vitest 64 files / 1,109 tests pass; build pass |
| `check_secrets.py` (hardened), `check_architecture.py`, `check_project_state.py`, `check_tooling_config.py`, `check_policy_authority.py`, `check_external_provider_readiness.py` | all PASS |
| `git diff --check`; EOL churn (`--numstat` vs `--ignore-cr-at-eol`) | clean; identical (+640/-19 tracked) after rebuilding the mixed-EOL `ARCHITECTURE.md` from its blob |
| POC lifecycle / E2E (`run_e2e.py`, `assistant-streaming`) | **NOT EXECUTED**: Tesseract not on PATH, Docker not running, no disposable Mongo port configured |
| Hosted CI | **NOT EXECUTED** (nothing pushed); never reported as PASS |
| `pre_pr_check.py` | not run: intentionally uncommitted handoff (AGENTS.md) |
| Zero remote activity | session-wide socket guard active for the whole assistant suite (0 recorded attempts at teardown apart from the self-test's own blocked attempts); no request path other than `/chat/completions` in code; no real ledger (`data/budget` absent); key never read |

## 7. Findings, blockers and limitations

No blocking finding in this self-review; an independent Quality Gate is still required.

1. **Environment:** Windows `Errno 24` real-HTTP failures (12 on base and candidate) and one
   asyncio stall of the parity control (stopped by PID, re-run passed): host limits, not A2.
2. **Pre-existing flake** in `test_knowledge_answers.py` (1/8 on base and candidate).
3. **Not executed:** E2E/POC lifecycle (prerequisites missing), hosted CI, physical Mongo (N/A:
   no Mongo surface).
4. **Integration change to #113 code:** `record_reason()` maps `budget_refused` to
   `model_unavailable`; answer records still store only the model name (adding the profile
   would change #113's record schema: follow-up, not done).
5. **Labelled bound (R2 PARTIAL):** reservations are not a proven maximum; BP-2/BP-4/BP-6 and
   endpoint uniqueness (S1) remain Phase B Batch 0 prerequisites.
6. **Randomised invariant test** takes about 66 s.
7. **Stop conditions:** none triggered.

## 8. Governance and authority

D-091 and ADR-012 Amendment 3 are recorded as **PROPOSED** only; D-090 / Amendment 2 untouched
(PR #114). No remote inference, data transmission, spending, model selection or shared
deployment is enabled or approved. API/response schemas, notices, prompts, retrieval, catalog,
exact-line guard, answer records schema, CLM integration, frontend: unchanged. Configuration:
new inert settings only. Persistence: new assistant-local ledger owner (dormant). Provider
status: remote profile DORMANT, not a `PROJECT_STATE.md` provider.

## 9. Next authorised action

Owner decision on publication: commit the integrated candidate on
`feat/assistant-phase-a2-20261026-int`, then an independent Quality Gate on that frozen commit,
then `pre_pr_check.py`. Phase B stays blocked (plan section 15).
