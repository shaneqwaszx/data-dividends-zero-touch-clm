# Phase 25 + 26 final combined validation

Date: 2026-10-05. Branch: `feat/phase25-26-final-poc-hardening`.
Worktree: `C:/Users/shane/.codex-clean2/worktrees/phase25-26-final-poc-hardening/data-dividends-zero-touch-clm`.
BASE_SHA, source HEAD and freshly fetched origin/main:
`73967401379378927c810d6227b0c7aa95fba061`.
Behavioral tree: `8ce0ee18ea16eff1667a99cff41796f597a74f3e`.
Change class: DOCS_ONLY. The final reviewed identity is the exact manifest below,
including uncommitted documentation, rather than source HEAD alone.

## Sequential acceptance and scope

Phase25 fresh independent PASS is recorded in ignored
`.runtime/phase25/INDEPENDENT_GATE_BLOCKER_RESOLUTION.md`, raw SHA256:
`898447578dfa19fa7eaff14ebb09cb4e3db9f8db4a5d5bee2985b4d50bc3a030`.
The earlier acceptance-blocker FAIL remains historical evidence. No product
remediation was required (0/2), and no empty Phase25 commit is warranted.

Phase26 fresh independent [PASS](PHASE_26_QUALITY_GATE.md), raw SHA256:
`4fdbc4968775381c1126d6f972bd34dcbbd21a3f3c39075d3353ea44c5556b8f`.
Its 13-file candidate aggregate is
`1049e17f142ed631badc8810a2d46483d8b877a158f97bd135b27414a336f381`.
Those 13 raw files and the Phase26 gate are unchanged in this final candidate.
Phase26 product remediation:0/2; final remediation:0/1 before the final review.

The change refreshes stale documentation, records validation, and creates the
[Phase27 handoff](../../docs/PHASE_27_HANDOFF.md). No executable, configuration,
dependency or lockfile changes are included. API/type, schema, connector, business
rule, mapping, authentication/security, architecture owners/dependencies, provider
classification and product runtime behavior are UNCHANGED. No Phase27 implementation.
Historical combined FAIL and later narrow P2 remediation PASS remain distinct;
this bounded acceptance does not replace historical whole-program verdicts.

## Protected retained data and normal startup

Original clm_poc was touched only read-only under explicit owner authority. Three
case records (schemas2/2/8) decoded successfully with the current reader. Original
raw document/index fingerprints and counts matched before and after validation
and clone removal; original mutation commands0. No original application startup,
recovery, migration, repair, normalization or synthetic record creation occurred.

Exact raw BSON clone: case3/profile6/team2/policy1; registry cache remained absent.
Normal application startup changed only its allowlisted database name. Backend,
frontend and health returned200. All3 retained cases passed authenticated HTTP
and actual frontend document/reconciliation/ownership/UBO/blocker/history/target
inspection. Controlled legacy optional-intelligence404 was retained; current200.
Director3 visible; RM2 accessible/third safe404; HR policy/diagnostics accessible,
portfolio403/all3 case reads404. All logout checks auth/me401 with no stale state.
Provider calls and blocked attempts0. Clone document mutations/recovery0; normal
startup createIndexes9 was allowed only on the disposable clone.

Clone removal was verified after Phase25 independent PASS. Cleanup receipt SHA256:
`747214d61493922a1026d4c061f793a9406f35e3f295384a3eb3fb8479ed398b`.
Original preservation=true, clone removal_verified=true. OS process/listener checks
established normal runtime cleanup; native socket probes were inconclusive.
These physical facts are coordinator observations independently reviewed in the
Phase25 gate, not new final-stage database operations. No raw database copy is on disk.

## Final newly executed checks

Execution used the unchanged behavioral source plus the accepted documentation.
Python3.12.10 in the normal repository venv; Node22.23.3/npm10.9.9.
Full safe command/log receipts are in the ignored normal-checkout directory
`.runtime/phase25-blockers/final`. The final manifest freezes their raw SHA256.

| Check | Executed result |
| --- | --- |
| Backend regression |416 passed,0 skips,1 existing warning;336.22s;exit0 |
| Ruff |`python -m ruff check .` in apps/backend;PASS |
| Strict mypy |`python -m mypy app`;124 source files, no issues;PASS |
| Python integrity |`python -m pip check`;no broken requirements;PASS |
| Frontend typecheck |`npm run typecheck`;PASS |
| Frontend production build |`npm run build`;128 modules;PASS |
| Frontend dependency integrity |`npm ls --all`;PASS |
| Contracts |44 unittest tests;PASS |
| Governance/security |124 unittest tests across9 modules;PASS |
| Six scanners |Project state, architecture, policy authority, external readiness, tooling configuration, secrets;all PASS |
| Final actual HTTP/browser |7 selectors, each in a fresh offline memory lifecycle;all PASS |
| Optional private GoldTier archives |NOT VALIDATED: absent archives;--if-present exit0 is not an example-validation PASS |

Backend command: `python -m pytest -q -o "addopts=-p no:cacheprovider"`
with tests/test_phase13_auth_rbac.py, test_phase14_5_case_access.py,
test_zero_touch_orchestration.py, test_clm_orchestration.py,
test_s2_persistence_security.py and test_p2_remediation.py from apps/backend.
These broaden the earlier focused owner/adverse checks with role isolation,
orchestration, persistence/security and accepted final-P2 regressions. A full
backend suite is not triggered by the documentation-only delta. Phase26 separately
ran181 owner/adverse backend tests and80 frontend tests across5 files; independent
Phase26 review reran those counts. A full frontend suite is not triggered because
no frontend implementation changed. Counts are separate executions, not additive
claims of distinct test inventory.

Contracts command: `python -m unittest discover -s tests/contract -p test_*.py`.
Governance modules: test_dev_context, test_check_project_state,
test_check_architecture, test_check_policy_authority,
test_check_external_provider_readiness, test_check_secrets,
test_validate_external_provider_evidence, test_validate_goldtier_examples,
test_phase_07_delivery_assets. Scanner commands are their corresponding scripts,
plus check_tooling_config. Existing Starlette/httpx deprecation and React SSR
warnings are not new assertion failures.

Browser base: `python -u scripts/run_e2e.py --backend-port 8875 --frontend-port 4273`.
Each separate command used one --grep selector:

- `Slice B Garden partnership`, --registry-demo garden-partnership;
- `Slice B second synthetic`, --registry-demo synthetic-cache;
- `Slice B Merlion fresh cache`, --registry-demo synthetic-cache;
- `S1 wrong UEN retains`;
- `S2 creator edits calculable`, --garden-protocol;
- `Slice E HR and Director same impact`;
- `S3 uncertain Policy checks`, --sandbox-demo uncertain-policy.

Garden official-shaped offline identity/officers remain distinct from reviewed
LOCAL ownership. The second company is synthetic; cache evidence proves zero
additional ACRA operations in its own lifecycle. Recovery preserves the same
case/document. Ownership uses the single deterministic Decimal owner. HR proposal,
distinct Director activation and frozen old/new policy snapshots are proved by
the existing harness. Uncertain Policy status permits a read-only identity check,
without completion or replay. Guards use generated credentials, dotenv disabled,
in-memory repositories and offline transports; external browser violations0.
Actual processes/HTTP/browser are used, without sponsor/provider calls.

Phase26's earlier18 successful selectors and independent8 fresh selectors retain
separate provenance; the final7 are additional executions, not a total unique
coverage claim. Phase25's earlier8 offline journeys are recorded in its gate.

## Failed infrastructure attempts and unexecuted lanes

The first final frontend summary wrapper failed with Windows cp1252
UnicodeEncodeError after typecheck/build exited0; npm integrity had not run.
After the ignored wrapper's output encoding was corrected to UTF-8, the entire
unchanged lane reran successfully. The first wrapper is not passing evidence.
One sandbox read of the normal checkout reported dubious Git ownership; the
correct authorized elevated read succeeded with main clean. No global Git safety
configuration was changed. No product remediation or test weakening occurred.

Physical Mongo pack is not newly triggered: no schema, persistence or runtime
compatibility change. Phase25 exact-clone evidence is the applicable physical
proof. Actual OCR is NOT_RUN on this host: Tesseract is absent, no OCR code/runtime
configuration changed, and historical isolated OCR receipts are not a current
host pass. Manual sponsor UAT is NOT_RUN. Optional private archives remain absent.
External ACRA calls0; external GoldTier calls0 throughout these assigned phases.
Historical external receipts remain unchanged, attributed to their original run.

## Final review and owner boundary

Frozen final manifest: `.runtime/phase26/FINAL_CANDIDATE.json`, covering all15
candidate Markdown files, including this report and the prior Phase26 gate.
Algorithm: SHA256 of UTF-8 json.dumps(files, sort_keys=True, separators=(',', ':'));
individual raw-file hashes and final receipt hashes are retained in that manifest.
Only the manifest and the assigned [final independent gate](PHASE_25_26_FINAL_QUALITY_GATE.md)
are excluded bookkeeping. The gate must establish exact PASS with P0/P1/P2=0
before the coordinator creates the explicitly authorized local logical commit.

Origin/main was fetched after Phase26 PASS and still matches the merged baseline;
no drift/rebase/merge occurred. Index is empty before review. Local commit only,
no push/PR/merge, no publication pre-PR gate and no empty Phase25 commit.
Phase27 handoff is ready for later owner assignment; implementation has not begun.
True limitations remain PARTIAL Sandbox, process-local/single-instance bounds,
absent host OCR, manual UAT unrun and unresolved sponsor/production/legal contracts.
