# PR89 P1 implicit warm-up disclosure remediation — independent Quality Gate

Date: 17 October 2026. Verdict: **PASS** for the bounded, uncommitted P1 correction on the exact frozen content below. No required fix remains in this assignment. This gate does not authorize publication, deployment, a CI waiver or another remediation/phase.

## Independence, authority and reviewed identity

This reviewer did not implement the correction. Review applied `fyp-quality-gate`, the integration-security checklist and affected POC regression guidance. The explicit owner assignment and `output/pr89-p1-security-20261017/TASK.md` define the bounded scope. Current source/tests, AGENTS.md, the AUTH_RBAC_SECURITY/EXTERNAL_PROVIDER `dev_context.py` read-set, architecture/state, decisions/open questions and the preceding PR89 document-intake gate were inspected. Historical acceptance is not substituted for this review.

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr89-p1-security-20261017/data-dividends-zero-touch-clm`.
- Branch: `codex/pr89-p1-security-20261017`.
- HEAD / original published behavioral baseline: `8407d9eded03df5c504ed5c97b3c9b2a938a1b40`.
- BASE_SHA / locally verified origin/main: `12ba994b8128a4777e12fcc764bafc8f39b9292a`. The coordinator separately confirmed direct remote main and the published PR89 branch remain at these respective revisions.
- Reviewed implementation identity: **`2265909103b1e0bb7d63ebf4d771480f96c3c3d5041524c6f2732a2de3ed27c5`**.
- Algorithm: SHA256 of compact ASCII JSON containing sorted `{path, sha256}` entries, each inner hash over raw current file bytes. All 2,121 entries were independently recomputed initially, during review and immediately before this verdict: zero mismatches. The complete path set is `output/pr89-p1-security-20261017/FROZEN_CONTENT.json`; it includes every tracked path and the new warm-up security test. Evidence/scratch and this report are excluded.
- HEAD alone does not identify the corrected behavior: the correction is intentionally unstaged/uncommitted. The raw manifest identifies the actual tested/reviewed content.

The complete bounded delta is:

| Path | Reviewed change |
|---|---|
| `apps/assistant/ai_assistant/llm.py` | Shared literal-loopback eligibility predicate; actual warm transport destination guard; warm-up ignores environment proxies and cannot follow redirects |
| `apps/assistant/ai_assistant/main.py` | Skip untrusted background prompt construction/model call before the existing throttle |
| `apps/assistant/ai_assistant/config.py` | Clarifying comments; fields/defaults unchanged |
| `apps/assistant/.env.example` | Clarify the existing warm flag cannot authorize remote disclosure |
| `apps/assistant/README.md` | Explain eligibility, local-inference prerequisite and separate explicit-question/deployment authority |
| `apps/assistant/tests/test_warm_up_security.py` | 70 new synthetic regression cases |

The full tracked diff and the complete new test were inspected. All 17 tracked original Assistant test/instruction/guardrail/prompt paths remain equal to published HEAD after Git checkout normalization; their frozen raw bytes also remained unchanged. No original R1–R4 assertion was weakened.

## Acceptance evidence

| Required boundary | Independent assessment |
|---|---|
| Reproduce the original P1 | PASS. Git-exported untouched published Assistant modules and their tracked instruction resources, isolated under gate scratch, reproduced a default-enabled `/brief` POST to a synthetic remote model endpoint containing synthetic company and document facts. No explicit question was sent. The backend requests remained GET-only. This independently establishes the causal defect rather than relying on implementer RED logs. |
| Block implicit remote warm-up even with the flag true/defaulted | PASS. The same synthetic remote `/brief` on the correction makes zero model requests. New normal-composition/environment tests verify remote configuration plus `LLM_WARM_UP=true` remains blocked. Startup/health do not dispatch model requests. |
| Enforce the actual transport destination | PASS. `llm.py:210` checks `self._url` before payload/client construction. Direct `.warm()` and local-settings/remote-adapter disagreement both make zero requests. The scheduling check is not the sole enforcement point. |
| Fail closed on ambiguous hosts/URLs | PASS. The authored matrix and 22 additional independent denied cases cover DNS/localhost, misleading hostname suffixes, shorthand/octal/integer IPv4, mapped/scoped IPv6, userinfo, encoded authority, noncanonical ports, controls/Unicode, backslashes, query/fragment routing, wildcard/private/nonloopback addresses and malformed schemes/authorities. |
| Preserve usable local warm-up | PASS. Literal numeric IPv4 loopback and IPv6 `::1`, including expanded IPv6, retain the one-token nonstreaming POST. Four supplemental positive cases preserve origin identity. A double-slash path remains a path on the same numeric loopback origin. Existing throttle/prompt-prefix tests pass. |
| Prevent proxy/redirect escape | PASS. Real synthetic loopback HTTP, using the actual installed HTTPX transport and no MockTransport, sent two warm payloads directly to the local inference trap while HTTP_PROXY/HTTPS_PROXY/ALL_PROXY pointed to a separate trap and NO_PROXY was empty: zero proxy requests. A 307 redirect to another trap produced zero target requests. Authored tests separately cover 301/302/303/307/308 with remote locations. |
| No alternative automatic disclosure path | PASS. Source tracing finds the sole background dispatch at `/brief -> warm_up -> model.warm`; it has both eligibility guards. Model complete/stream calls occur only in explicit chat routes. The unchanged frontend effect requests a brief; asking a question occurs through user event handlers. No new automatic path or fallback dispatch was introduced. |
| Backend authority and actor/case/session isolation | PASS. Independent two-case/two-actor probes verify the correct company/viewer per warm/chat prompt, inaccessible-case404 and expired-session401 stopping before further model calls, and backend GET-only requests. Two fresh actual backend API bridge tests cover Mock/Sandbox compositions, current evidence invalidation and no case/ledger/target mutation. |
| Explicit questions, streaming, fallback and R1–R4 | PASS. All 198 Assistant tests pass, including the original128 and new70. Remote explicit complete/stream still work as a separate boundary; unavailable model paths use the safe case-data fallback. Existing SSE terminal/malformed/cancellation handling, exact authorized guidance and Search destinations remain intact. |
| Protected data, logging and authority | PASS. No new logging/body retention is added. DEBUG log tests exclude synthetic case/document values, session and model credential material; model requests contain no session cookie. Supported secret scanning plus scanner tests pass, and manual inspection of all six paths found only synthetic placeholders. No cloud/sponsor approval switch or new data-handling permission was invented. |

A literal loopback URL establishes network destination, not inference provenance. A local forwarding gateway could forward data; the documented operational prerequisite is a controlled local inference server. This gate does not certify a deployment, local process provenance or remote/cloud handling of explicit questions. These remain separate owner/deployment authority boundaries and are not silently approved by the warm flag or this PASS.

## Fresh independent execution

Runtime: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe`, Python3.12.10; HTTPX0.28.1. Candidate root/Assistant/backend import paths were explicitly used as appropriate. Dotenv was disabled before Assistant module composition; backend tests use the repository ordinary memory/Mock containment. Python bytecode/pytest caches were disabled; configured type caches and generated probes stayed under `tmp/pr89-p1-independent-gate`.

| Independent command / observation | Actual result |
|---|---|
| `python -B tmp/pr89-p1-independent-gate/independent_probes.py` from task root | PASS: untouched-baseline reproduction; corrected remote/default block; 22 denied +4 positive supplemental URL cases; direct/mismatched destination guards; real local HTTP proxy/redirect traps; actor/session prefix separation |
| `python -B tmp/pr89-p1-independent-gate/case_isolation.py` | PASS: two cases/two actors, correct warm/chat facts, cross-case404, expired401, backend GET-only |
| `python -B -m pytest -p no:cacheprovider -o addopts= -q tests`, cwd `apps/assistant` | **198 passed**, exit0,4.44s; one existing Starlette/httpx deprecation warning |
| `python -B -m pytest -p no:cacheprovider -o addopts= -q tests/test_ai_assistant_main_integration.py`, cwd `apps/backend`, after broad-resource release | **2 passed**, exit0,2.71s; one existing deprecation warning |
| `python -B -m unittest discover -s tests/contract -p test_*.py` | **44 passed**, exit0 |
| `python -B scripts/check_secrets.py`; `python -B -m unittest discover -s tests -p test_check_secrets.py` | Scanner PASS; **8 tests passed** |
| `python -B scripts/check_project_state.py`; `python -B scripts/check_architecture.py` | Both PASS |
| Assistant `ruff check ai_assistant tests --no-cache`; `ruff format --check ai_assistant tests --no-cache`; strict mypy with gate scratch cache | PASS;24 files formatted;12 source files type-clean |
| `git diff --check`; `git diff --cached --check`; explicit six-path whitespace inspection | PASS; no staged delta. New/untracked content was checked explicitly. |

Final independent logs are under `tmp/pr89-p1-independent-gate`: `independent-probes.log`, `case-isolation.log`, `assistant-full-counted.log`, `backend-bridge.log` and `contracts.log`. Initial gate-only scratch setup/assertion assumptions were corrected before these final results: missing exported Markdown resources, textual IPv6 normalization, minimized prompt shape and Git CRLF checkout normalization. No implementation or test assertion in the reviewed source was changed.

Official HTTPX documentation describes [environment-variable disabling with trust_env](https://www.python-httpx.org/environment_variables/) and [redirect behavior](https://www.python-httpx.org/compatibility/#redirects). Installed0.28.1 source was independently inspected: its environment proxy gate depends on `trust_env`, and redirect following defaults false. The actual TCP probes above, rather than documentation alone, establish current runtime behavior.

## Broad affected evidence and preserved failures

These lanes were executed by the coordinator on the same frozen content; they are not relabelled as independent executions. This reviewer inspected their evidence index, relevant source/tests and final logs, including the complete-runtime backend terminal result.

| Coordinator frozen-content lane | Actual result |
|---|---|
| Complete backend, cwd `apps/backend`, explicit candidate root PYTHONPATH, complete virtualenv `python -m pytest` | **2707 passed,158 skipped,4 warnings**, exit0,1062.62s. Final log: `output/pr89-p1-security-20261017/backend-verified-runtime.log`. Relevant accepted Mock/domain/call-stopping/regression and actual Assistant integration suites are included. |
| Frontend | **872 passed /54 files**; typecheck/build PASS. Frontend source is unchanged. Existing React act warnings and chunk-size advice remain recorded. |
| Backend static/dependencies | Ruff PASS; strict mypy127 source files PASS; pip check PASS |
| Assistant static | Ruff/format PASS; strict mypy12 source files PASS, also independently rerun above |
| Contracts |44 PASS, also independently rerun above |
| Security/governance |115 tests PASS; project-state, architecture, tooling, policy-authority, external-provider-readiness and supported secret checks PASS. Scanner/state/architecture also independently rerun above. |
| Frontend dependencies | npm offline install/integrity and npm-ls PASS |

The first global-interpreter backend attempt remains a failed environment execution:614 failed/2141 passed/158 skipped, with missing PDFium/structural document failures; its original `backend.log` is retained. It is not passing evidence. The complete installed runtime independently collected a different parametrized inventory,2865, then executed it successfully. No assertion, parser, test inventory or product source was repaired to make that rerun pass.

The exact ordered collection/execution inventory in `output/pr89-p1-security-20261017/backend-skip-inventory.json` maps the158 skips to152 real-Mongo cases and6 real local-OCR cases. These skips do not certify either physical/runtime lane. They do not block this bounded model transport correction: no persistence/schema/driver/repository/auth-store or OCR behavior changed. The four full-backend warnings are the existing Starlette/httpx deprecation and three hostile-DTO Pydantic serialization warnings in provider conformance. There is no new catalog scenario or catalogue edit.

Whole-application browser/lifecycle campaigns were not rerun because no frontend/browser/process owner changed. This gate claims service transport behavior using synthetic HTTP plus unchanged frontend tests and fresh backend bridge evidence. Historical browser/OCR/physical evidence keeps its original identity. No real model, sponsor provider or database was used by this review.

## Code, architecture and security conclusion

No active finding remains within the assigned P1 scope. `is_local_model_url` is one small shared predicate in the existing model adapter. It rejects before network construction; the consumer also avoids constructing sensitive warm-up prompts for untrusted configuration. The existing throttle, request-local backend reads, exact output catalogue and failure owners remain. The change enforces the existing protected-data boundary without introducing a provider, authorization/persistence owner, framework, dependency or speculative approval mechanism. The bounded enforcement does not require a new ADR.

Scope impact is explicit:

- API/shared types: unchanged; only an internal URL predicate was added.
- Durable schema/persistence: unchanged.
- Connector: model warm transport restricted; ACRA/GoldTier/IDP connectors unchanged.
- Configuration: fields/defaults unchanged; existing warm-up flag behavior is constrained and documented.
- Business rules/mappings: unchanged.
- Auth/security: backend identity/RBAC/session owners unchanged; implicit model egress is restricted at the existing transport owner.
- Architecture/dependencies/provider status: unchanged; no Live promotion or interoperability claim.
- Runtime: remote/ambiguous implicit warm-up is skipped, safe numeric-loopback warm-up remains, explicit questions/stream/fallback remain under the existing separate boundary.

Required fixes: **none**. Existing conversation-history overflow, document-read-unavailability projection and deployment/model handling limitations retain their separate dispositions; this correction does not expand or resolve them. Open sponsor questions remain open, including privacy/retention and production deployment/identity authority. No production, real-model quality/latency, Live ACRA/GoldTier or sponsor-approved cloud disclosure is certified.

## Readiness and Git receipt

**PASS** accepts only the frozen bounded local P1 correction. The next authorized action is the coordinator's uncommitted handoff to the owner. Publication remains pending and requires separate explicit owner authority, unchanged reviewed content, latest-main assessment and the required clean committed-state pre-PR checks. `pre_pr_check.py` was intentionally not run on this user-required uncommitted tree.

Hosted CI remains separately blocked. The coordinator's direct GitHub observations identify published-head PR run39020032075 and push run39020029106, attempt1, as failed with zero steps in all nine jobs; the backend annotation says the run did not start because of account payment/spending-limit requirements. This reviewer does not convert that result to green or waive it. There is no corrected-content hosted CI result because no new commit/push is authorized.

Final branch/HEAD/origin-main remain as recorded above; the index has no delta. The five tracked implementation/document changes, new security test and task-owned `output/` evidence remain uncommitted. This reviewer added only this assigned report as ordinary repository content and generated authorized ignored gate scratch/caches. It made no source/test/configuration fix, Git mutation, commit, push, PR mutation, merge, CI waiver or next-phase change. No dotenv, protected sponsor/customer data or database was accessed.

Evidence strength: fresh direct causal baseline reproduction, corrected actual-transport/adverse/isolation probes,252 independently passing tests across the named suites, unchanged raw reviewed identity and successful broad affected evidence. Confidence is A for this bounded local P1 acceptance; deployment provenance, explicit-question data handling and publication infrastructure remain outside the claim.
