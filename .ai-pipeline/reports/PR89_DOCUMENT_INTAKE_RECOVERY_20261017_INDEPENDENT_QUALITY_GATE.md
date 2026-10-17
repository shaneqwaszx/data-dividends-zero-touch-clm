# PR89 document-intake recovery — independent Quality Gate

Date: 17 October 2026 (Singapore). Verdict: **PASS** for the bounded local document-intake recovery and latest-main integrated candidate. No required source correction remains within this assignment. Publication is pending and is not authorized by this gate.

## Independence and frozen content

This reviewer did not implement the recovery, R1–R4 corrections, integration, runtime provisioning or campaign instrumentation. Its only filesystem write is this assigned report. Source inspection proceeded during the coordinator's checks; reviewer test execution began only after the explicit campaign/resource release.

- Reviewed worktree: `C:/Users/shane/.codex-clean2/worktrees/pr89-503-main-integration-20261017/data-dividends-zero-touch-clm`.
- Detached HEAD, BASE_SHA, fetched origin/main and independently observed remote main: `12ba994b8128a4777e12fcc764bafc8f39b9292a`; main tree `c2654a63760b8da4b8ee475a9d66162194216d5b`.
- Complete normalized in-memory reviewed tree: `281c5299a14c945bcfec3416e373fd50821e49e5`. This identifies uncommitted content, not a new commit or stored Git tree.
- Complete present-source inventory: all 2,119 raw hashes in `FROZEN_IDENTITY.json`. Reviewer independently compared every current file and the matching `POST_CAMPAIGN_IDENTITY.json`.
- Unchanged integration index SHA256: `4f06d4c6de4038b096e5ba73a93e7ab90ddfcbadf413ad0cd5a9d359475697dc`.
- Complete 61-path candidate delta: 29 tracked modifications/deletions plus 32 task-owned new files. Exact path/content evidence is `integration-provenance.json`, `final-hygiene.json` and `final-integrated-candidate.patch`; patch SHA256 independently verified as `f1788d1b53e9b080da481cb904e83cab63de0694f51f9af5b3a5efe197e0ae06`.
- Original preserved runtime tree: `0a0498597066e880f940c7139b755ede50f264d9`, original HEAD/main `151802e0cfe02d5164ff6819c3e3dd7c85b05f1d`, original integration index tree `89a41ab17766383a759d87b57455be25798f0743`. Original diagnostic entry tracked/candidate hashes still match. Historical incomplete `849621a` is not substituted for complete runtime content.

Independent final read-only GitHub/remote observations confirm PR89 remains OPEN at `badf0c378f2991fc1f8e52e6902706588995a171` and PR94 is MERGED at `12ba994`. GitHub's separately captured PR89 base metadata reports `66cd66f` with base name main; that metadata is not used as the actual fetched/direct remote main identity.

## Acceptance evidence

Evidence filenames in this section are under this report directory unless explicitly called original. Original means the retained `pr89-required-p2-remediation-20261017` worktree's same recovery directory.

| Requirement | Independent assessment |
|---|---|
| Actual HTTP503 classification before broad campaign | PASS. Original `original-backend.jsonl` records HTTP503, code `OCR_RUNTIME_UNAVAILABLE`, public message “Bounded local document processing could not be completed.”, DOCUMENT_INTAKE stage, safe correlation/document identifiers, two successful media-worker exits, and retained terminal document FAILED with the same code and zero fields |
| Proven runtime cause | PASS / PROVEN. Installed Program Files Tesseract v5.4.0.20240606 exists with eng data and works by absolute path; inherited PATH resolution and LOCAL_OCR_EXECUTABLE were absent. Original preflight genuinely decoded the unchanged scanned PNG and ran English OCR: 23 words, mean confidence approximately95.18. PDFium/Pillow and isolated worker imports/startup are verified |
| Minimal justified correction | PASS. Only the task-owned backend process receives the installed Tesseract directory prepended to PATH. No permanent configuration, download, installation, document-processing product source, OCR score, fixture, assertion, deadline or retry change |
| Exact original Garden selector | PASS. Original `corrected-garden.log` has one passing unchanged selector at historical line469; `corrected-backend.jsonl` binds HTTP201 and actual Tesseract exit0. Original failure remains preserved |
| Latest-main/PR94 integration | PASS. Independently verified all25 PR94 paths match current main. The exact61-path original PR89/R1–R4 delta is retained; the only additional source difference is swapping the first two CASE_PAGE_SECTIONS entries to Search before Registry. Existing source-bound regression has retained RED then GREEN evidence |
| Genuine integrated Garden OCR | PASS. Campaign selector `e2e/s3-sandbox-submission.e2e.ts:486`, shard1 position38, passed. Its `campaign-eec5c3e00e627936-backend.jsonl` contains real Tesseract exit0 and intake201. The business assertions still require LOCAL_TESSERACT_OCR, confidence>=0.85, AUTO_CONFIRMED/REVIEWED, exact ownership result, retained Sandbox identity, exact target call counts and zero external calls |
| R1–R4 Assistant behavior | PASS. Current Search destinations/seven-stage inventory, required supported SSE terminal, malformed response containment and exact current-backend guidance catalog were inspected and freshly tested. No R1–R4 correction was weakened |
| Complete official browser campaign | PASS. Both original sequential shards exit0; current discovery107 selectors/136 Chromium records, ordered54/53 disjoint exhaustive partitions, zero retries, one worker and original60-second lifecycle bounds |
| Full record/process/fixture reconciliation | PASS. Reviewer recomputed the inspected audit logic read-only from raw discovery/native logs/reporter JSONL/process records, without rewriting audit files:107 selectors,136 begins/ends, all records PASS,321 created/stopped process pairs and13 required fixture-cleanup receipts. Second discovery agrees;107 backend runtime imports match frozen hashes |
| Historical evidence and resource protection | PASS. Earlier FAIL/NOT_RUN records remain historical; no old incident is relabelled. Exact owned Mongo container was removed only after ownership checks and only system databases remained. No fixture databases remain; final owned-listener receipt is explicit[] |

The original Garden scan body and business assertions are unchanged between old and new main; PR94 adds accepted surrounding UI checks and moves its line number. Every reviewed document owner, current runner and scanned PNG matches latest main. The observer forwards the original ASGI messages and subprocess operations; it persists only allowlisted status/code/public message, safe IDs, executable/module provenance and child status. It neither records upload/session bodies nor alters response semantics.

## Fresh tests and retained lanes

Reviewer commands used the integration worktree's virtualenv, explicit candidate import paths, Python bytecode disabled and pytest cache disabled. Tests disable owner dotenv/model configuration. No actual model or sponsor endpoint was used.

| Execution | Result |
|---|---|
| Independent Assistant: `python -B -m pytest -p no:cacheprovider -x tests`, cwd apps/assistant |128 passed, exit0,4.23s |
| Independent backend: `pytest -p no:cacheprovider -o addopts= -x -q` on test_ai_assistant_main_integration plus selected test_s2_local_ocr functions |14 passed, exit0,13.85s. Covers GET-only Mock/Sandbox Assistant integration, absent-runtime terminal record/native usability, failed-OCR temp cleanup/sanitization, real subprocess deadline/output/error bounds, TSV rejection, and all6 real OCR acceptance parameters. Tesseract PATH and CLM_REAL_OCR_REQUIRED=1 are task-process-only |
| Coordinator frozen Assistant/static |128 passed; Ruff, format and strict mypy PASS |
| Coordinator frozen frontend |872 tests/54 files, typecheck and build PASS |
| Coordinator frozen backend/document focus |308 passed/6 skipped, exit0. The6 real-OCR parameters skipped in this unprovisioned lane were explicitly rerun with required real OCR:6 PASS/0 skip, and independently included in the14 above |
| Coordinator frozen contracts/security/governance |44 contract tests and8 secret-check tests PASS; project-state, architecture, tooling, policy, provider-readiness and secret checkers PASS |
| Official browser campaign |107 selectors/136 records PASS; shard native durations727.047s/697.343s. No assertion failure, lifecycle timeout or ECONNRESET |

Known Starlette/httpx deprecation warnings remain. Frontend build's existing chunk advisory is not hidden. One reviewer focused invocation yielded progress before the tool wrapper retained its terminal metadata; it is not counted as PASS. Reviewer confirmed that process had ended, then obtained the explicit14-pass/exit0 receipt above with a bounded wait. This was evidence-capture recovery, without a source repair or product failure.

The prior full backend2707-pass/158-skip, backend Ruff/mypy and unchanged-lane reports retain their original execution identities. They are not described as freshly executed here. The only old-main-to-new-main commit is PR94's25 frontend/report/documentation paths; backend production, dependencies, contracts and harness remain unchanged. Fresh Assistant, affected backend/document checks, contracts/security and complete integrated browser evidence cover the changed composition. Skipped physical persistence lanes are not certified; no schema/repository production change requires a new physical suite for this recovery.

## Contract, architecture, security and adverse review

No new finding remains in the assigned scope.

The document adapter still fails closed when OCR cannot resolve. Media decoding/rendering remains isolated; OCR uses a fixed English operation with bounded subprocess time/output and sanitized errors. The document owner persists a terminal failure before API503 projection and clears partial fields/pages. The corrected runtime executes the same adapter, quality/provenance and review logic. No fallback to Mock IDP or injected fixture text exists.

R1 uses current UI titles and routes all four Search readiness categories to Existing-customer search. Backend processing-node order remains distinct. R2/R3 require DONE or stop/length and validate event/choices/choice/delta/content before access; EOF, malformed JSON/shapes, timeout and cancellation retain safe partial/fallback semantics. R4 only displays complete exact code-owned catalog lines based on current authorized backend actions; model/history/document values cannot extend that catalog. Unsupported source precedence, invented controls, legal UBO, Live/approval and resend assertions are rejected before display. Local Review & Send approval remains correctly distinguished from GoldTier-internal or regulatory/KYC approval.

The Assistant bridge remains GET-only with the caller's session; backend authorization/team scope/safe404 remain authoritative. The model receives no mutation tools. React renders text without HTML interpretation; session replacement and case cancellation remain with existing owners. Ledger ordering, no-replay, Decimal ownership, source mapping, persistence and provider classifications remain unchanged. No second owner, schema, framework, dependency direction or compatibility layer is introduced by this recovery.

Scope statement: relative to the preserved PR89/R1–R4 candidate plus new main, no API/type, durable schema, connector implementation, business rule, mapping, authentication/security owner, architecture, dependency or provider-status change occurred. Product guide ordering was reconciled to the accepted UI. Runtime provisioning changes only backend process executable resolution, enabling existing real LOCAL OCR; this must be supplied again for future backend launches. The retained broader PR89 package/proxy/configuration rename and streaming/advice changes keep their earlier explicit rollout requirements.

Tracked and cached whitespace checks pass; task-owned untracked Markdown was separately checked. The complete new-file inventory and secret-check results show no newly tracked secret/confidential artifact. This reviewer did not inspect .env, protected data, unrelated worktrees or clm_poc.

## Remaining boundaries and readiness

This **PASS** accepts the bounded local recovery and integrated frozen content. It closes the missing complete-browser criterion for this candidate, not the causes of unrelated historical500/ECONNRESET incidents or a universal reliability claim.

Hosted CI remains a separate infrastructure blocker: main push run39003489540 at12ba994 is marked failed; the backend job has no executed steps and its annotation says it was not started because account payment/spending-limit requirements were unmet. Local results do not turn that run green. This unpublished candidate has no exact-head hosted CI; no billing change, CI exception or repair is authorized.

Inherited I1 conversation-history overflow, document-read-unavailability-as-absence projection, dependency advisories, deployment/model endpoint/data handling, package rollout and unresolved sponsor questions retain their separate owner dispositions. Real-model quality/latency, production deployment and Live ACRA/GoldTier interoperability remain unverified. No provider is promoted to Live.

No next phase or deployment is authorized. The next owner boundary is explicit publication authorization, with unchanged reviewed content, scoped committed state and the required clean-tree pre-PR gate plus applicable executed hosted CI or an explicit separate human disposition. pre_pr_check.py was intentionally not run on this uncommitted handoff.

## Git receipt

Task worktree remains detached at12ba994 with its intended unstaged61-path delta and unchanged main index. The original remediation/evidence worktree and its index remain preserved. This reviewer made no implementation, test, configuration or ordinary documentation fix, Git mutation, commit, push, PR update, merge or next-phase change. Its sole write is this ignored independent report.

Evidence strength: direct target reproduction/correction, fresh independent142 tests, complete official integrated browser/process/fixture evidence, current remote observations and final unchanged-content checks. Confidence is A for this bounded local acceptance; hosted publication/deployment evidence remains outside that claim.
