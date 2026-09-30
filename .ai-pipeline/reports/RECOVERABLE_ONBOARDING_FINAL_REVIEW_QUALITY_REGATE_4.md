# Recoverable onboarding final review — independent Quality Regate 4

## Executive result

**PASS** — the five assigned post-remediation criteria are verified on the exact
uncommitted candidate below. The fresh independent reviewer inspected current source,
tests, complete dirty scope, retained artifacts and freshly generated browser/print
evidence. Fresh execution was supplied by the coordinator in this same gate run;
the reviewer independently assessed its scope and limitations. No required fix remains.

This report supersedes stale current-status prose in the work checkpoint/evidence
records: the printable review has **seven pages**, the original Garden ZIP is available
and has been checked, the offline serializer passes, and the fresh gate is now complete.
Those historical records and earlier failed/PASS reports remain unchanged. In particular,
QUALITY_REGATE_3 certifies its earlier 101-path tree, not this candidate.

## Frozen candidate and evidence revision

- Branch: `feat/recoverable-onboarding-final-review`.
- HEAD / base / local main / locally recorded origin/main:
  `3d6e7b560b8062daeb93c31cf91b0df957797e9c`.
- No fresh remote fetch; this is no claim about current remote main or CI.
- Reviewed path set: **123 files**, including all task-owned untracked files and
  28 retained operator-route artifacts. The exact paths and individual byte hashes
  appear in the appendix. Only this report is excluded from the candidate identity.
- Identity: `8805f0a71e15028541a610b2f27e4b3417f4fc658ae43460274e8972e6fcd72a`.
  Algorithm: sort the union of `git diff --name-only` and
  `git ls-files --others --exclude-standard`; exclude this report; SHA-256 each file's
  raw bytes; join `hash<TAB>relative-path` rows with LF, without terminal LF; SHA-256
  the UTF-8 result. Identity was unchanged before and after fresh execution.

The current source and tests outrank historical prose. Guidance reviewed includes
AGENTS.md, DEVELOPMENT_WORKFLOW, CODEX_WORKFLOW, skill routing, the quality-gate skill,
the active bounded planner, prior gates, remediation records, architecture/state,
ADR-007 and relevant current contracts/decisions. Applied review lanes: frontend UI,
backend domain/API, authorization, persistence, provider boundary, frontend cache.

## Acceptance checklist

| Assigned criterion | Result | Direct evidence |
| --- | --- | --- |
| RM-readable review copy and technical appendix | PASS | ReviewAndSend translates retained codes into plain impact/action notes; raw codes, provenance, authority and versions remain in collapsed screen details and expanded print. Exact operation fields, legal form, owning team, local-only limitations and server digest semantics remain visible. Fresh ordinary RM journey and all seven rendered A4 pages inspected. |
| KYC/legal-form advisory | PASS | Existing domain intelligence owner projects a strict non-blocking `PROJECT_ADVISORY_ONLY` advisory. Unknown combinations stay unknown/reviewable; no invented regulatory rule or policy owner. Company/association mismatch gives correction guidance and focuses the existing classification surface. Component/domain execution and fresh browser case demonstrate it. |
| Truthful Mock/Sandbox projection | PASS | Destination and confirmation labels derive from the backend plan; Mock says no external GoldTier submission. Sandbox remains partial; no Live implication. Mock Search/Shell/Policy/Amend preview matches the strict mapper, with provisional system fields and bound target ID marked. Backend confirmation remains authoritative. |
| Offline smoke serializer | PASS | Script reads current initial-target-search/status owners; profile verification requires COMPLETE plus canonical entity; unsupported/not-attempted operations stay explicit. Five-case regression covers status-only and absent projections without provider calls; focused backend execution passes. |
| Supplied Garden ZIP/PDF verification | PASS | Original ZIP read directly; both supplied PDFs processed by current local parser, four uniquely labelled fields each match its supplied validation manifest. Exact hashes recorded below. Synthetic provenance retained; no substituted generated regression and no asserted address parity with the distinct local mock response. |

## Contract, architecture and security findings

No current blocker or actionable defect was found. Review confirmation still binds
every preview field, including stable acceptedAt, to server versions and digest. Sensitive
mutations reauthorize within the owning lock; material identity/canonical drift requires
fresh review. Normal/incremental target flow cannot bypass valid confirmation. Target
ledger ordering and no-replay behavior remain owned by existing orchestration.

Case recovery, blocker decisions and manual evidence stay in existing service/repository
boundaries. Manual ownership replacement remains version/document bound and enters the
single Decimal ownership engine. ACRA diagnostic composition reuses the existing
connector, bounded safe outputs and HR-only capability; it creates no case or ledger.
Frontend cache effects remain centralized and user/session/team scoped. Corrective
actions focus real owners; ownership edits require the typed server action, otherwise
the review explicitly says review-only. UI presentation does not supply authorization.

Schema-v7 additions and strict legacy decoding in the complete candidate preserve
existing Mongo identity/CAS semantics and explicit storage modes. The five later
remediations do not change persistence or confirmation semantics; the advisory is an
API projection, not another durable owner. Under the user's conditional instruction,
physical Mongo was not rerun. Earlier physical restart/confirmation results remain
historical support only, not fresh certification of Mongo/server behavior.

No new secret, raw confidential artifact or provider payload was introduced. ZIP
verification retained only safe hashes/results here. No `.env` was read by the reviewer.
Mock provenance, provisional policy and unresolved sponsor authority remain explicit.
External hierarchy/relationship creation, final approval and official interoperability
remain later dependencies, not capabilities certified by this gate.

## Fresh testing and adversarial evidence

Coordinator execution against the unchanged candidate, assessed by this reviewer:

| Check | Fresh result |
| --- | --- |
| Backend `../../.venv/Scripts/python.exe -m pytest -q`, cwd apps/backend | Exit 0; fresh collect-only inventory 1,518; 37 expected skips observed. Quiet execution did not print a passed-count summary; no historical 1,557 count is transferred. |
| Focused backend four suites (advisory, review/orchestration, Garden, serializer) | Exit 0, 119 executed dots. |
| Frontend `npm test -- --reporter=dot` | 31 files, 369/369 pass. |
| Frontend typecheck; production build to temporary outDir | Pass; build 124 modules. |
| Contracts with `Settings.model_config['env_file']=None`, unittest discovery tests/contract | 44/44 pass. |
| Ruff `--no-cache` backend app/tests and smoke script | Pass. |
| Strict mypy backend app, cache-dir nul | Pass, 112 source files. |
| Architecture, project-state, policy-authority, external-provider-readiness, tooling and secrets checks | Pass; project-state required a read-only escalated execution to resolve sandbox ancestry visibility. |
| Guarded authorized manual ownership Playwright | 1/1 pass; real Mock HTTP on owned ports 8876/4284. |
| Guarded ordinary RM repairs Playwright | 1/1 pass, 13.8 seconds; exact test unchanged, real Mock HTTP, same owned ports. |
| Tracked diff whitespace / explicit 32 untracked text files | Pass / zero trailing whitespace. |

The initial root contract invocation imported default composition and failed at DNS
before a database connection. It was not a passing result; the explicit dotenv-disabled
contract rerun above passed. No successful external/database operation resulted from
that failed attempt. No new provider requests or writes were made.

Source/tests inspected include stale digest/version rejection, duplicate confirmation,
target-call stopping, changed canonical identity, ownership edit authority, role/team
reauthorization, current-document binding, malformed/manual graph cycles and Decimal
totals, safe diagnostics outcomes, serializer absent/status-only states, and Mock versus
Sandbox warnings. Passing authored tests were assessed alongside the implementation.

The ordinary RM harness previously wrote frozen artifact paths. To obtain fresh runtime
evidence without changing reviewed bytes, the coordinator used task-owned wrappers
outside the repository: `qg-browser/run.py` adds a Playwright-only Node preload;
`redirect.cjs` redirects only `fs.promises.writeFile` below the operator-route artifact
prefix. The reviewer read both wrappers: test/app source, assertions, fixtures and
network/process guard policy were unchanged. No reviewed artifact was overwritten.

Fresh runtime covers 320px reflow; 360/768/1280/1440/1920 layouts; long labels; distinct
default/hover/keyboard focus; 200% reflow; section focus targets; beforeprint appendix
opening; and no confirmation POST/target mutation. The reviewer visually inspected
fresh long-label default/hover/focus, mobile review, keyboard review and zoom captures,
alongside previously inspected retained viewport captures. All seven **fresh** rendered
print pages were individually inspected: readable wrapping, operations, advisory,
plain notes, expanded provenance and decision appendix, unclipped page numbers and
hidden corrective controls. Sparse operation pages are an accepted layout tradeoff,
not missing content. Confirmation was enabled but not clicked.

Fresh browser evidence resides at:
`C:/Users/shane/.codex-clean2/visualizations/2026/09/30/01a0f1e5-cdee-7430-ba93-ca328dbe873c/qg-browser/`.
It is supplemental execution evidence, not part of the frozen repository path set.
The retained seven-page PDF hash is
`a0dd16435038e4aed09f7cd3a4fd3bf6ad90e1d4f048f6867794eeabc500d834`.
The freshly generated PDF has current case timestamps/IDs, so byte equality with the
retained historical PDF is neither expected nor claimed.

## Supplied Garden evidence

Original: `C:/Users/shane/Downloads/garden-business-demo-pack.zip`.
The reviewer independently confirmed ZIP and PDF hashes; the coordinator processed
PDF bytes in memory with the current local parser and compared to the supplied manifest.

- ZIP SHA-256: `29b4d3bb6ba466f2f2b5afd3504b694f51b3acb497a29914ebfddeae3a291298`.
- Supplied profile PDF: `19c98a17b0227610ce035460ea9d34edadfe86baa8df340680f01440c181434e`.
- Supplied ownership PDF: `b3956b9e59d7a4f1efac827035ef3e5a7447dbbd9e323df4c98a0c3c36677475`.
- Each is one page; four extracted fields are `UNIQUE_LABELLED_TEXT`; supplied-manifest
  parity passes and extracted text retains synthetic markers.
- Supplied pack address differs from the current local Mock address. The pack instructs
  comparison to the current response. Supplied-profile validation is proven; current
  provider-profile/address verification is not claimed. The generated synthetic-PDF
  regression is separate evidence and did not replace this verification.

## Required fixes and readiness

Required fixes: **none**.

- **LOCAL WORKFLOW PASS** for this frozen bounded candidate.
- **OFFICIAL MOCK COVERAGE PARTIAL** remains separate: historical ACRA 12/12,
  GoldTier Searches 4/6, writes 0; these were not re-executed here.
- **EXTERNAL GOLDTIER SUBMISSION NOT EXECUTED**. No official interoperability, Live
  integration, sponsor policy approval or final customer approval is certified.

Ready for the compact uncommitted handoff. This verdict does not authorize publication,
another phase or new external calls. Changed reviewed bytes require a fresh gate.

## Git status and compact handoff

The candidate before this report had 63 modified tracked files, 93 porcelain entries,
zero staged changes. Current HEAD/base/local-main identity is recorded above; no fetch
was performed. This reviewer wrote only this assigned report. No implementation fix,
commit, push, PR, merge or next phase occurred; dirty work was preserved.

Relative to base, the complete candidate changes API/types, schema, configuration,
project-defined runtime/business behavior, Mock preview mapping, auth route coverage,
architecture documentation/composition and runtime recovery/confirmation/UI behavior.
Provider classification is unchanged. Connector transport implementations are unchanged;
diagnostic composition reuses an existing connector and does not certify new provider
capability. The five post-regate3 remediations add review copy/advisory projections,
truthful labels, offline serialization and verification evidence; they do not replace
backend authority or introduce a new persistence/advisory owner.

Next authorized action: deliver the uncommitted candidate and this exact independent
PASS to the owner. Remote integration/publication remains unauthorized.

## Complete reviewed path manifest

Each following line is `SHA-256<TAB>relative path`; the report itself is excluded.

```text
6f361c3f46ffbb7682654381a8d0980bde59f39769c4be5bb02c64881ae16fce	.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_GATE.md
bc5d800b7e9fcd6f7281e1f7ebe34d6ba184c75886f2b6567649e12df42b3ae1	.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE.md
2556ac6bf7e01219bdad0a63cbe2030dac9afdd77e842e4d43e5711a8a18106e	.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE_2.md
18fb897fc7ae0aca1323a5b204a979465b5594cdae4fa2497d63f65f63803d2d	.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE_3.md
e43d58193a6c03c52d554f6d8af08f0d0fe33560879df06c508d4886e43eab7e	apps/backend/app/api_acra_diagnostics.py
1de5bf84632ed32f61713d3fbc5f648c8302bf415cf14b65e19fb74e7a99afc0	apps/backend/app/api_models.py
96de46c0d43ba918765c734d15fd530862cbe746c7289afb09535f8788ff1ba6	apps/backend/app/composition.py
9b6774205bc114755e6ef7553acd36c21a9eedc36663fc745f49e0994c24bf7a	apps/backend/app/config.py
ceffc673605ed0c7637beaa2c70c8e1a5519e0e51f1b3c2a980dfa87798c7900	apps/backend/app/domain/models.py
3a82cdce681435581f985234394b40445b8bf3717dc370c7d5422435c2500894	apps/backend/app/domain/onboarding_intelligence.py
2a927ae15501f8dc25f766a063174213cfc2ae1520519cc27505e14ab542d9e5	apps/backend/app/domain/ownership.py
3040baad4a6871fbee6ee3579d3a5a25f7822a852df2dd99553a986868e1cf8b	apps/backend/app/domain/policy.py
854b124f16805ee0538affa718a6c7a0ab829f2c3547bbde901ebef11e4399ad	apps/backend/app/domain/zero_touch.py
a6777bfa66e3e4ed9aecf127f8b415fed1b1b2a17676918f8e6457ff121092c5	apps/backend/app/main.py
1dfd23cafba3bf374a21a0c041b14cfa448ff9f4f28889d8496f820c196f0777	apps/backend/app/mappers/goldtier.py
c857aa0978466b56ba690f25b33e9dce05376fcd65076af4357afb7331b3cf76	apps/backend/app/persistence/models.py
f61e9c483321bfe484f4611aaf97f5679959534ed8801a05672c478d7b582c91	apps/backend/app/persistence/mongo_case_store.py
f4cfbe41e89a31f4168b49a4d4ec14c04719e13a642471d49f655499c205166b	apps/backend/app/persistence/repositories.py
38387be007ec8161b1ff9e3ab932379056e4baddbef57e81e9d6fa8c6e387260	apps/backend/app/services/acra_diagnostics.py
3b7f0ac62f82b890cf8251856fc8d158250d30bd3fb949233d9cf0a6e2689c42	apps/backend/app/services/authorization.py
b10efe1979c298d4c20934b9956cd9a16f45fb1dac5a386797b38a35a5b45a2e	apps/backend/app/services/blocker_decision_policy.py
60ed99313158c33e601d6924e0beb7be295a5b47f9a1e7c50100c36dc20b59bd	apps/backend/app/services/clm_orchestration.py
91caffc1bd054e2a85a4659c6567db5ad49d6bafedea8635c7f51c4a673346ab	apps/backend/app/services/manual_ownership_evidence.py
974171b45ffd1f85fe9076b89fe8ad370a35941a3ed270b99d169deda36f9745	apps/backend/app/services/onboarding.py
fac809f135f2951677e3673af63f3fcfb395818f42082dfbe22bfd0d5b1b4952	apps/backend/app/services/ownership_analysis.py
fcdd66a17ab649c2e289f957638ae92b14488b7cd57a439053562000a2790262	apps/backend/app/services/ownership_repository.py
9ddafb36f75512ab17158a8952c6fbfdbbcfabf19e480cc6e66c2e5d61455b52	apps/backend/app/services/zero_touch_orchestration.py
2d86c4788691e46cbce809376ca00d76f3495d9ad52acbd8ebfd16d741a5d80a	apps/backend/tests/test_acra_diagnostics.py
b05cebc02484988aeddf63e02e1d07e06d088afd874841a77081a8462e222ab0	apps/backend/tests/test_acra_diagnostics_api.py
327753788ab1cfd3e72c9b41c728ea6d872a04c19d1bd5743063344454bd0456	apps/backend/tests/test_acra_modes.py
71d0c612527301c2be6bb9fd41d579e59a1c5b79cdc5f12311920d416aef2338	apps/backend/tests/test_blocker_decision_policy.py
c796adbc5a0a3938a387c1db9839e2cf6ed764713a3ea6398d5f688249dce620	apps/backend/tests/test_clm_orchestration.py
24266714f50c525783ab1b091e192b057afb9c413ee4da0c3df2c3298f6372e4	apps/backend/tests/test_evidence_workbench_registry_projection.py
0e95205ec7ed2e43d4b3da1bf37f1868a1f974ac56e06b204a806dcc5d242da6	apps/backend/tests/test_garden_business_fixture.py
d0371573f8f2e52ca58600dd59ca31faa923b7a5d014d9441fcbb3fb67d5d9fa	apps/backend/tests/test_goldtier_xpi_sandbox.py
de553e4bdcfdd2bf9fbb2fc667793c69837de1588550387fb64ab8962219843d	apps/backend/tests/test_manual_ownership_evidence.py
f95fdd2e2623273852a939d1fb79695cb6d34197db9eaf4c6b9b0373edd1b5e0	apps/backend/tests/test_onboarding.py
8aa990424ccd592d8fe1d3ca36dadf481dade97dea60dd5d75b5c9391fb8c64e	apps/backend/tests/test_onboarding_api.py
7f16b0a85853e19be8a5bb0766e9ca1738280b22a1c4a1e94b99fa6d1bc02fe0	apps/backend/tests/test_onboarding_intelligence.py
1e57cea944171f567c1402e55c927670fe2326cd6d9fcb3a61e3c7b52a2c08aa	apps/backend/tests/test_onboarding_resilience.py
7d21f04191c94bc5eefb12f5cf33a5a350e434c9c3631fcaa90e0d2ede4d5946	apps/backend/tests/test_phase06_provider_conformance.py
7a2daf056c841313e2c3f6d217e56fb9535d31bfc914005461a790b5314d9325	apps/backend/tests/test_phase11_reconciliation.py
da3ee443dfc2a68a6f78f66e8d4c26760cc3ebf0d0ae031b3ab8aeb89d78e347	apps/backend/tests/test_phase12_persistence.py
1bd09772dd322775ed97092b8aad95aed2891152c1b2aee878f3c2807b574f3c	apps/backend/tests/test_phase12_real_mongo.py
045ea417ec3d0400f6f60c7cac8af5281abc12b3b3c499d17cb31edcaa1a160d	apps/backend/tests/test_phase13_auth_rbac.py
435d3feba400b00e23a946a6785b193c3bb7b355b39b7f05d6abb0060b73fbb6	apps/backend/tests/test_phase13_demo_scripts.py
e3bb5c5e961ad6210a6d7989cd7d3f2125cb5c8b4b7e131dc4cf9f7333c3e2ad	apps/backend/tests/test_phase13_priority.py
a9d71914ef9eada3fb66198e4b16e81817399f41a00225d6eaf66b855d783e60	apps/backend/tests/test_phase_07_uat.py
87c8e8d1ee5a992e2c6f5f93398ea79f741eb38190441c2a9505df14ce6d0b97	apps/backend/tests/test_phase_08_input_driven.py
35dd3c71ef0c8edf4013a5d6fd5071f6e99da5d19efd4347f8adb1c7539fab23	apps/backend/tests/test_pre_phase12_workspace_multidoc.py
b076987b8d752d3dc2f4b4d23d310d228a47d6d9ffd513c9948f1493c0130bfa	apps/backend/tests/test_recoverable_onboarding_smoke_report.py
cda59604a08d1c6d24c1fa17892f9f891b43b61f4882a365ed849d8591927f95	apps/backend/tests/test_zero_touch_orchestration.py
20b3998296c3a2c65beee10072467c84444459c5117099867492c3004b1132e1	apps/frontend/e2e/authenticated-zero-touch.e2e.ts
2fff15fe926ec4bf9e49aa94a6da6cac5705c94f814535fe9756d401b01f8557	apps/frontend/e2e/responsive-layout.e2e.ts
0a29a74ca6aa6cafbc9cb5d58cdad86f8d0915194aeafaeedb7ec9216d5e367c	apps/frontend/src/App.tsx
88294fe9461d93aeeec955ceeaf9334b8d906c72c22d1867ebaf0be1c417ac90	apps/frontend/src/AttentionQueue.test.tsx
216b2e86e7c6dd872053cd80cedd940a97368c10eb9c585732f41b5b58e163bd	apps/frontend/src/Phase15CNavigation.test.tsx
5c5acb10a9839fec77bf216175746602a566e4bd90d67f3f7255ac27bf8de086	apps/frontend/src/api.ts
9e333fb69ad710603c4a087df9e625fcd514e6a75a1a4956d04c827ec2af5c2d	apps/frontend/src/caseQueries.ts
380e3674fa40b07060a9727ba781bdf26bb19e0051685a1f79a85c796bae337d	apps/frontend/src/navigation.tsx
ea0bacede8640c62cdd8e2c06d9a14194224b7b483a96deb9361159b937eeaf7	apps/frontend/src/pages/AcraDiagnostics.test.tsx
a5a02e742b80042b45260506821ae24621520d3bad8916b651dc1c0e5998421d	apps/frontend/src/pages/AcraDiagnostics.tsx
5fff4802fd001df11dff1a794b07b9dd94a5aafccd1bc0e1b220bc4561dbf136	apps/frontend/src/pages/BlockerDecisionDetails.test.tsx
4b35e7b10b37b0159143005aeb491c6e62a5be9c749e89dd8d01983e77b18e76	apps/frontend/src/pages/BlockerDecisionDetails.tsx
cca0ec8063dacd285b8ccc8b0ef0aa7f60b8b6225970121ea879e97b4457b133	apps/frontend/src/pages/CaseDetail.tsx
20f4a4942da46e5105f2f958c0d938a66537deab3221e2d53233eff7a013fa2a	apps/frontend/src/pages/CaseStateExplanationPanel.test.tsx
c60dd065c2e32becce613bf4cc431b38bbdf19098ce5177eadc014bea5d4a638	apps/frontend/src/pages/CaseStateExplanationPanel.tsx
1c941d1a69fc9ff63b64b3c354f55db7eb72f20c2f55dadb87a531c041e05c22	apps/frontend/src/pages/CaseStatePanels.test.tsx
b6fcc1944f7d29595a801857801548775e5164c03a8716b77982b23d3d9cf6b4	apps/frontend/src/pages/CaseStatePanels.tsx
e3503a9d4e9da4703a2f5c7f2749b14ec3b7d4dd5028828cdf081f15a539fd6e	apps/frontend/src/pages/HumanInterventionPanel.tsx
b1411e41fbb1bdcbbc38b0302fc7bd4e19a27e9cc4855a6eb35737c5bc5464bd	apps/frontend/src/pages/IdentityCorrectionForm.test.tsx
cbf140f63b21343988ce0ec7f1681b23a29b1628fac9980fec728b8de6a38e66	apps/frontend/src/pages/IdentityCorrectionForm.tsx
287d74a82714e4ae2dc92719da997d4346a73729af24271cac1ca505c0b14302	apps/frontend/src/pages/ManualOwnershipEvidenceForm.test.tsx
6fe923a04d1b481d193b69b4cbc0cd3a1456fd3a4565c94f8858eea135a2af15	apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx
e5b9a8df81b9f5bd399e2e9733106df2f7fc6a5a0b0f5f77984e5474d81ad5f8	apps/frontend/src/pages/PolicyRebindPanel.test.tsx
927a8e7696ec4ccb9f968fec4125a64b8e92d65aa6b03eda374bd3668f7c195d	apps/frontend/src/pages/PolicyRebindPanel.tsx
70f8d5eeb0d1c882721065c19ac9595324eb40ec9c788795d0995f8c9841d715	apps/frontend/src/pages/ReviewAndSend.test.tsx
15ce8e7b9c6326dd74e6084426857422d7a835a739c542b0548c52d63ad1b385	apps/frontend/src/pages/ReviewAndSend.tsx
f430006b76186e1f30a0b30eebf1492fd3de981f8f8fac01bafa67a748da65cb	apps/frontend/src/pages/TargetClassificationPanel.test.tsx
b2a41e7088324b85a299d50a4c1a3b6f4a4c97e6151802158b31643b6aaa9b0b	apps/frontend/src/pages/TargetClassificationPanel.tsx
18df80d0733a60f2ec9bbc07e9867d0152e5818e7c5815e90aa032890389987f	apps/frontend/src/styles.css
2048502817720e6cd07945dc9bd51c2efb253ebf2e7d3133345ce1b54b9f9602	apps/frontend/src/types.ts
96ccaeedc735ddf8aa2f56ce9e9727d4cb4653a84fc5fc291eeda39ed0e6d8b2	apps/frontend/test-artifacts/operator-route/1280-review-default.png
96ccaeedc735ddf8aa2f56ce9e9727d4cb4653a84fc5fc291eeda39ed0e6d8b2	apps/frontend/test-artifacts/operator-route/1280-review-focus.png
96ccaeedc735ddf8aa2f56ce9e9727d4cb4653a84fc5fc291eeda39ed0e6d8b2	apps/frontend/test-artifacts/operator-route/1280-review-hover.png
7a10cee3df382de61ea0ee0a1bfcdb1ef0663eabc5230f78d6235d8fb567b199	apps/frontend/test-artifacts/operator-route/1440-final-review.png
34eb61555d9e8c9cdb712d49c15324709c1c02a3e19d80f20d6aeaeb87346601	apps/frontend/test-artifacts/operator-route/1440-review-and-send.png
34eb61555d9e8c9cdb712d49c15324709c1c02a3e19d80f20d6aeaeb87346601	apps/frontend/test-artifacts/operator-route/1440-review-default.png
34eb61555d9e8c9cdb712d49c15324709c1c02a3e19d80f20d6aeaeb87346601	apps/frontend/test-artifacts/operator-route/1440-review-focus.png
34eb61555d9e8c9cdb712d49c15324709c1c02a3e19d80f20d6aeaeb87346601	apps/frontend/test-artifacts/operator-route/1440-review-hover.png
16520f07d4beb136dca01b7ab3ec65ee225ddc04f204224110125a1ca68620bf	apps/frontend/test-artifacts/operator-route/1920-review-default.png
16520f07d4beb136dca01b7ab3ec65ee225ddc04f204224110125a1ca68620bf	apps/frontend/test-artifacts/operator-route/1920-review-focus.png
16520f07d4beb136dca01b7ab3ec65ee225ddc04f204224110125a1ca68620bf	apps/frontend/test-artifacts/operator-route/1920-review-hover.png
c24470e6db362e3e113c3f3d3a08d7625f693caa1d7c3c5245283f7d25f7d5eb	apps/frontend/test-artifacts/operator-route/200-percent-review-reflow.png
e9dc69f9b9366d9925a944624fc19cf35084e14d5519ad7d7ece4e0f4cbf568a	apps/frontend/test-artifacts/operator-route/320-long-label-default.png
9ef233ac54ed09925c9136689b7114bea44a6bf393e8600640e17fc3b86cc6ce	apps/frontend/test-artifacts/operator-route/320-long-label-focus-context.png
159c6a8088383465c3647243dc587a622e1eca83fbe602eb60e324c2aa720a3d	apps/frontend/test-artifacts/operator-route/320-long-label-focus.png
90204f6f0e9da12e7b3eed6cb7664402b1dd9d0693492f26e18f7647bca3cf77	apps/frontend/test-artifacts/operator-route/320-long-label-hover.png
a9e9a6a31653477c5f225f57391ebeeaf7b761774f62f1b4d5850d7db15bb0fa	apps/frontend/test-artifacts/operator-route/320-review-reflow.png
12065c0b0a70b7a23b2a3dfa36b61dbf4494281be9ea34d81635f1142d6e7614	apps/frontend/test-artifacts/operator-route/360-long-label-default.png
6254a2c0d141dc968e91fbf6241e440aa60efed24105a1a564566dd1f2c92a69	apps/frontend/test-artifacts/operator-route/360-long-label-focus-context.png
732aa989d5a00ab9c3e5b8948bad200f08df39aeba5b14c2330e8ec24b687d8d	apps/frontend/test-artifacts/operator-route/360-long-label-focus.png
933d365fba43f8f58d338883703f927620c950398c7eff3c0301749c157cb619	apps/frontend/test-artifacts/operator-route/360-long-label-hover.png
9576a8c171a51349658f64ba515eb80a8d379c079128765947345dc789dd75d3	apps/frontend/test-artifacts/operator-route/360-review-default.png
9576a8c171a51349658f64ba515eb80a8d379c079128765947345dc789dd75d3	apps/frontend/test-artifacts/operator-route/360-review-focus.png
9576a8c171a51349658f64ba515eb80a8d379c079128765947345dc789dd75d3	apps/frontend/test-artifacts/operator-route/360-review-hover.png
2b67303e4c1fb5227de9f67e002816d39f17ff26b5a6c79ab3c8dbe797a55a0d	apps/frontend/test-artifacts/operator-route/768-review-default.png
2b67303e4c1fb5227de9f67e002816d39f17ff26b5a6c79ab3c8dbe797a55a0d	apps/frontend/test-artifacts/operator-route/768-review-focus.png
2b67303e4c1fb5227de9f67e002816d39f17ff26b5a6c79ab3c8dbe797a55a0d	apps/frontend/test-artifacts/operator-route/768-review-hover.png
a0dd16435038e4aed09f7cd3a4fd3bf6ad90e1d4f048f6867794eeabc500d834	apps/frontend/test-artifacts/operator-route/review-and-send-a4.pdf
e36c4bd5ccff1e53ab9d79a01dfaa1e98650deebccd99813cb2cb0376e9b5201	docs/ARCHITECTURE.md
5e73961e82cebb936542da6f0a7a0a87f9fa98f34ccf783c239745b34e1a5eb7	docs/PROJECT_STATE.md
27f24b2682feb3ebdbb5208736875bd68bf69e64c403a506e6bff071c89cfd79	docs/aegis/INDEX.md
a4fcc93d37b7c3a045e86e0e4fb35e4770d4a4a55566023b56bee6676d5c7578	docs/aegis/plans/2026-09-29-recoverable-onboarding-final-review.md
ee596fbe10a98a788e19c523735e5368ee394d4c8dc51e7fc3be2caf204b91e5	docs/aegis/work/2026-09-29-recoverable-onboarding-final-review/10-intent.md
969c2a457cf35922e8297793595e17fca3b22c566ddb5edd6e68947e11fe160b	docs/aegis/work/2026-09-29-recoverable-onboarding-final-review/20-checkpoint.md
8ce8bc07319bcf12775ab9d27657d6c36ee84c47e2c3f2e7b0926d359a68cf33	docs/aegis/work/2026-09-29-recoverable-onboarding-final-review/90-evidence.md
df372ceeb52798dae6f037a9d117502e360eb3b03fc42f157b21a10d0ff8d0e7	docs/aegis/work/2026-09-29-recoverable-onboarding-final-review/99-reflection.md
35dda2d7a2ff8d6fee7b8c74b881b4db1ab478694300806f955ca466c1144a7d	docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
40ff4849f27cec25a72ee27a905be000e070dec8731698ff3a372b7bd4c05e3d	docs/decisions/ADR-007_RECOVERABLE_ONBOARDING_AND_FINAL_CONFIRMATION.md
52d297b9a236f28ab6d9e37477094c8ac1424f935062139cbf569746fb226bcb	docs/decisions/DECISION_LOG.md
9d9dadf866499c2b30497dad2ce720ff6e572ff9accbb5e0759fb87cd4bf0464	scripts/recoverable_onboarding_smoke_report.py
9f24da617a37300833eaf876e8395b935320de9284621018c6f8ebe06d7e52b7	tests/contract/test_phase_05_clm_contract.py
```
