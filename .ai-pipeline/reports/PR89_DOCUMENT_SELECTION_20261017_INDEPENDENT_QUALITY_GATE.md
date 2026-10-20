# PR89 document-selection remediation - independent Quality Gate

**Verdict: PASS.** The bounded document-selection correction satisfies every current local acceptance criterion. No required source correction remains. This verdict applies only to the frozen candidate below; conditional publication still requires unchanged content, latest-main assessment, clean committed pre-PR validation, hosted review/CI assessment and the owner's existing authorization.

Reviewer: `independent_document_selection_gate`, a fresh reviewer independent of implementation. Reviewed 2026-10-17 (Singapore). Applied `.agents/skills/fyp-quality-gate/SKILL.md`. No source, tests, configuration, ordinary documentation or Git state was changed by this reviewer. Only this assigned report was written. No new phase, publication, GitHub action, database access or AM18 diagnostic was performed by the reviewer.

## Authority, identity and write boundary

Authority: owner request in attachment `1128b493-283f-4a7f-a76d-bf030eb57e1b`, AGENTS.md, current source/tests, DEVELOPMENT_WORKFLOW and the bounded checkpoint. Read the applicable BACKEND_DOMAIN context selector, repository workflow/architecture/provider/sponsor context, reviewer/security roles, previous publication handoff and accepted streaming gate. No sponsor-controlled rule is inferred.

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr89-streaming-resource-p2-20261017/data-dividends-zero-touch-clm`.
- Branch: `codex/pr89-streaming-resource-p2-20261017`.
- Current HEAD / published starting revision: `34eef0b7ebba406ad4018931cbfe942e67e9e9c9`; baseline committed tree: `2b864f26a8039460f2859e42c55bff4e979a80f4`.
- BASE_SHA / merge base / locally inspected origin/main: `12ba994b8128a4777e12fcc764bafc8f39b9292a`. This reviewer made no new remote-main claim.
- Frozen reviewed working content: **`3995b30288335ec69a92f98641935d367b1949767072ca5b3ba46f04e6ce20c4`**, **2,128 paths**. This raw manifest identity is not a Git commit/tree SHA.
- Identity method: SHA256 of compact ASCII JSON of sorted `{path,sha256}` entries; inner hashes cover raw file bytes. `tmp/pr89-document-selection-20261017/FROZEN_CONTENT.json` supplies the complete path set.
- Initial and final independent audits recomputed every file hash, exact tracked plus nonignored untracked inventory, combined identity and Git status. Zero mismatches, missing or extra paths. Index empty; only the following two paths differ from HEAD. The prior streaming/resource correction remains unchanged.

| Reviewed delta | Classification | Raw SHA256 |
|---|---|---|
| `apps/assistant/ai_assistant/context.py` | INTENDED | `55e6ba54e61c5ee474b1bdff5deb29212c466ea19c062a5d6872f94f8dc59d28` |
| `apps/assistant/tests/test_document_selection.py` | SUPPORTING, new | `f67d073d932d22b7f569dba68467b3b9400ce1e74c51382ec6349e7b90fab2a6` |

The full tracked delta is four added/three removed source lines; the entire new test file was inspected. `git diff --check` and explicit changed/new-file trailing-whitespace checks pass. No new secret, confidential sponsor artifact or private document/provider content appears in the synthetic delta; supported repository secret scanning passes. No `.env` was accessed. This report is outside the frozen implementation inventory and may be copied byte-identically to the authorized canonical report path.

## Acceptance and combined review

| Criterion | Independent assessment |
|---|---|
| Current replacement after six superseded records | PASS. `_documents` filters eligibility before slicing; replacement is projected and the false no-uploaded answer is avoided. |
| Correct supersession predicate | PASS. `superseded_by_document_id is None` matches `DocumentProcessingRecord.is_current_evidence` and adjacent `_document_field_review`. No alternative lifecycle or source precedence is invented. Missing serialized optional field remains eligible; non-None falsy malformed identifiers remain excluded. |
| Order and document/field caps | PASS. Filtering preserves received order; first six eligible records remain selected; `MAX_DOCUMENTS=6` and `MAX_FIELDS_PER_DOCUMENT=8` are unchanged. Interleaved, over-six, exactly-six, empty and all-superseded inputs are covered. |
| Fields, confidence and provenance | PASS. Existing display name/profile/state and field label/value fallback/confidence/comparison/review status are retained. The eighth field remains the last projected field. No extraction, confidence decision, backend record or replacement lineage changes. |
| Facts, questions and fallback | PASS. Seven-record scenario reaches facts and the suggested document question; deterministic fallback names the current replacement and its synthetic field. Genuinely empty input preserves existing empty guidance. |
| Authorization, GET-only and nonmutation | PASS. Session forwarding, safe403/404-to404, missing-session401 and backend GET-only calls are exercised. Deep-copy comparisons confirm unchanged source records/snapshot. Adjacent review-choice tests retain capability and fingerprint gating. No review permission was added. |
| Malformed boundary and maintainability | PASS. Backend client already filters received document items to dictionaries before this helper; scanning beyond the former first six therefore does not introduce a nondictionary API-path failure. Existing projection owner performs one simple ordered filter; no query, framework, cache or lifecycle owner is added. |
| Architecture, contracts and security | PASS. Existing backend authority, trusted/untrusted projection boundaries and owner map are preserved. No new endpoint, mutation, credential, logging, persistence or external data disclosure path. All reviewed test records are synthetic. |

The reviewer independently executed the actual focused suites using `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe -B -m pytest tests/test_document_selection.py tests/test_document_review_choices.py -o "addopts=-p no:cacheprovider" -q` from `apps/assistant`: **13 PASS**, one existing Starlette/httpx deprecation warning (9 new regression cases plus 4 adjacent review/permission tests).

An independent read-only in-memory challenge exhaustively exercised **2,047** superseded/current patterns of lengths 0 through 10, checking exact eligible order, six-document cap and source nonmutation: PASS. Six additional missing/None-predicate adverse cases passed. Loading the published HEAD helper from `git show` into a separate namespace independently reproduced zero projected records for six superseded plus one current; corrected helper projected one. No reviewed file was overwritten to run this probe.

Actual implementer failing-first receipt `failing-first.log` contains **5 failed / 4 passed** against the published baseline, with causal missing replacement/facts/question assertions. `corrected-focused.log` contains **9 PASS**. Initial helper-import/incorrect-path attempts were not passing evidence. The reviewer's own first command named nonexistent `test_document_understanding.py` and ran no tests; the corrected actual command above is the sole counted focused pytest run. A terminal rendering attempt hit a cp1252 UnicodeEncodeError while displaying frontend output; corrected ASCII-escaped receipt inspection succeeded without changing tests or results.

## Fresh applicable verification

The coordinator's serialized `run_checks.py` / `checks.json` records **20 completed commands, all exit 0** on this candidate. The reviewer inspected each command, cwd, exit and native terminal result; no duplicate heavy suite or browser campaign was started. Commands use the established repository virtualenv, with caches disabled or ignored task-local mypy caches. Exact commands and complete native logs remain under `tmp/pr89-document-selection-20261017/`.

| Fresh command lane | Observed result |
|---|---|
| Assistant `pytest tests -o addopts=-p no:cacheprovider -q` | **238 PASS**, 1 existing deprecation warning |
| Backend same full pytest invocation | **2,707 PASS / 158 SKIPPED**, 4 existing warnings; native duration 1,164.87s |
| Assistant Ruff / format check / strict mypy | PASS; 26 files already formatted; 12 mypy source files |
| Backend Ruff / strict mypy | PASS; 127 mypy source files |
| `unittest discover -s tests/contract -p test_*.py` | **44 PASS** |
| Eight named security/governance unittest modules | **120 PASS** |
| Six governance scripts | Project state, architecture, tooling config, policy authority, external provider readiness and supported secret scan PASS |
| `pip check` / `npm ls --all` | PASS dependency integrity |
| Four focused Assistant frontend Vitest files | **60 PASS / 4 files** |
| Frontend `npm run typecheck` / `npm run build` | PASS; existing >500kB chunk advice remains |

The earlier global-Python backend failure is not PASS evidence: missing PDFium caused synthetic upload failure; that run was canceled and preserved. The authoritative established-venv targeted runtime check passed 8 tests and the full established-venv backend execution above passed. No source or dependency change was used to hide the environment mismatch.

The 158 opt-in physical Mongo/local-OCR skips remain unexecuted. Existing Starlette/httpx deprecation and malformed-fixture Pydantic serializer warnings remain visible. No persistence, driver/server, OCR, startup/process ownership or lifecycle implementation changed, so physical Mongo and a new complete lifecycle campaign are not required for this predicate correction. Full backend regression supplies fresh unaffected domain/state/authority coverage. No physical database was started by this gate.

## Browser applicability and preservation of prior evidence

The corrected deterministic question/answer is browser-visible, so fresh configured Playwright plus real HTTP/process evidence is required and was obtained. Reviewed `browser-probe.e2e.ts`, `browser_service.py`, `browser.log` and cleanup receipt show **1 actual Chromium PASS** through configured `scripts/run_e2e.py`, actual Assistant service, synthetic cookie-authorized backend HTTP and the actual Assistant panel. The document suggested question was received; the browser displayed `Synthetic document 6 (REVIEW_REQUIRED)` and `Synthetic value 0`; the false empty answer was absent. Six authorized backend GETs were observed, network-policy violations were empty and the owned service was stopped. Recorded runner ports 28765/24173 are bind-free. This is synthetic Local/Mock evidence, not real-provider interoperability.

The disposable probe was moved into ignored evidence before freeze; it is not a committed regression test. Its earlier selector/UI-expectation/deprecation-stderr harness failures are preserved and are not counted as passing runs. The final native configured record is PASS. No process-startup owner, browser transport, cache or streaming source changed here; a full prior campaign rerun is not necessary solely for this projection correction.

Preserved prior accepted counts remain historical and exact-scope evidence: **229 Assistant PASS; 920 frontend PASS; 2,707 backend PASS / 158 SKIP; 44 contracts PASS; 120 security/governance PASS; 108 selectors / 137 Chromium records PASS**. Equal numeric totals in fresh lanes do not relabel historical execution as fresh. Full frontend 920 and full browser 108/137 were not newly executed for this correction. Prior streaming/resource acceptance remains valid for its unchanged scope.

**Historical AM18 HTTP500 cause: UNKNOWN/OPEN. Main-versus-PR89 attribution: UNPROVEN.** This correction does not resolve or diagnose that historical failure. No AM18 diagnostic was launched. Existing document-unavailability projection and other explicitly retained prior limitations remain outside this bounded correction; they do not negate the verified current-replacement fix.

## Verdict, scope effects and next authorized action

No actionable finding or current acceptance blocker remains. **PASS** applies to the exact frozen two-path correction with the inspected evidence. No correction/re-gate cycle was needed. The gate is complete for bounded local acceptance, not a new product-phase or Live-provider readiness decision.

API/type, durable schema, connectors, configuration, business rules, mappings, auth/security ownership, architecture/dependency boundaries and provider status: **unchanged**. Runtime behavior: **changed only in ordered current-document projection before the existing six-document cap**, restoring accurate current-replacement facts/questions/fallback. The Assistant remains read-only/backend-authoritative. No sponsor policy, approval, Ready-for-Approval or Live claim is introduced.

At gate completion the candidate remains intentionally uncommitted; `pre_pr_check.py` is NOT_RUN by this reviewer. Hosted new-head review/CI have not yet occurred for this correction. This PASS supplies the required independent prerequisite for the owner's conditional publication authorization, not a waiver of downstream checks. Coordinator may copy this report byte-identically, prove accepted content unchanged, assess latest remote/main, stage only the accepted correction/test/report, commit normally and run the clean committed pre-PR gate before authorized fast-forward publication. Any executable/instruction integration change requires fresh independent review. Preserve all prior limits and assess exactly one fresh exact-head review and both applicable CI events. Repository-owner humans decide and perform merge.
