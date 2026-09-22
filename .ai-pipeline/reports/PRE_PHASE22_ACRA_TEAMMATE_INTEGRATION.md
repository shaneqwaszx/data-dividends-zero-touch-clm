# Pre-Phase 22 ACRA Teammate Integration

## Status

Implementation candidate frozen for independent review on
`integration/acra-teammate-reconciliation`. This report records implementer evidence;
it is not an independent verdict and does not authorize publication or Phase 22.

## Baseline and boundaries

- Accepted `origin/main` / `BASE_SHA`: `ef338c9b7926a298e8987acb975fd93c96ed2bfb`.
- Starting source revision: `83a2c2651f4f719778baf70389a8ff460a43dfa9`.
- Teammate branch/head: `origin/acra-integration` at `6bcea75efd660e6dbaaa5dc2079b62749fc0abf1`.
- Existing stabilization ancestors retained unchanged: `fd613a89`, `83a2c265`.
- Change classes: `BACKEND_DOMAIN`, `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY`,
  `DOCS_ONLY`.
- Provider truth: Mock remains active/default; generic sandbox remains Partial; BizFile
  remains Dormant/uncomposed/runtime-disabled; Q-004/Q-012 remain open.

## Complete original-change reconciliation

| Original commit | Original feature | Original file | Current-main state | Action taken | Final current owner | Tests | Residual blocker |
|---|---|---|---|---|---|---|---|
| `4ae4ed19` | Initial BizFile connection, DTOs, decoders, transport/error handling, no-header seam | `connectors/acra_bizfile_sandbox.py` | Present with later OAuth retirement/security hardening | Retained; strengthened single-entity binding and safe provenance | Dormant BizFile adapter | Focused BizFile/security tests | Q-012 blocks authoritative binding/activation |
| `4ae4ed19` | Speculative OAuth/token lifecycle | same | Removed by `74a5fd2f` | Not restored | None | OAuth-absence + secret scan | Q-012/auth authority |
| `897a4c4` | Runtime `bizfile_mock` composition | `app/composition.py` | Absent by deliberate retirement | Not restored | Existing Mock/generic sandbox composition | Mode/provider-readiness tests | Q-012 and Phase 21 |
| `897a4c4` | `bizfile_mock` setting | `app/config.py` | Absent by deliberate retirement | Not restored | Existing strict settings | Mode/provider-readiness tests | Q-012 and Phase 21 |
| `897a4c4` | Business-profile URL helper, query-free provenance, 200/empty semantics, empty relationships | `connectors/acra_bizfile_sandbox.py` | Missing after security retirement | Ported as dormant URL construction and strict operation-specific response behavior | Dormant BizFile adapter | Focused BizFile tests | No runtime operation/contract claim |
| `897a4c4` | Wider bounded SG UEN syntax | `domain/jurisdiction.py` | Narrow nine-digit predicate | Ported to the shared eligibility owner | Jurisdiction domain predicate | Phase 09 routing/zero-call tests | Not a complete official/Live validator |
| `897a4c4` | Direct connector smoke | `check_acra_connector.py` | Absent | Not restored | Sanitized readiness tooling | Provider-readiness checker | Q-012/account/access authority |
| `897a4c4` | Raw URL/body debug | `debug_acra_raw.py` | Absent | Not restored | None | Security/secret review | Superseded by redaction boundary |
| `79e808f` | Garden share counts and derived relationships inside dormant BizFile | `connectors/acra_bizfile_sandbox.py` | Deleted by retirement | Adapted to active synthetic Mock fixture boundary; no generic inference | `connectors/garden_business.py` + `mock_acra.py` | Garden fixture/acquisition/ownership/E2E tests | Q-004/Q-012; synthetic only |
| `79e808f` | Garden direct shareholder fixture/constants | `connectors/garden_business_shareholders.py` | Deleted | Rebuilt as strict direct + recursive local fixture | `connectors/garden_business.py` | Fixture validation/order/percentage tests | Synthetic only |
| `79e808f` | Garden connector assertions | `tests/test_acra_bizfile_sandbox_connector.py` | Removed | Reconciled into current BizFile and Garden suites | Focused tests | Focused tests | None for Mock behavior |
| `79e808f` | Garden ownership profile entry | `docs/contracts/OWNERSHIP_UBO_PROFILE.md` | Removed | Restored under current provisional authority and exact calculations | Ownership profile | Contract/governance checks | Q-004/Q-012 |
| `79e808f` | Historical D-034 | `docs/decisions/DECISION_LOG.md` | Number now belongs to Phase 13 | Historical number not restored; appended D-046 | Current decision log | Policy-authority check | Still provisional |

The feature-level exhaustive matrix, including classifications and evidence, is in
`docs/integration/ACRA_TEAMMATE_RECONCILIATION.md`.

## Garden result

- Root: `GARDEN BUSINESS` / `11111999A`.
- Direct: SIM LIM `62.500000%`; LIM CHOON HUAT `37.500000%`.
- SIM LIM active direct holders: `81.818182%`, `9.090909%`, `9.090909%`; withdrawn
  holder excluded.
- Effective leading path: `62.500000% x 81.818182% = 51.13636375%` (approximately
  `51.136364%` at six decimals).
- The existing provisional inclusive 25% engine classifies S123AC1234E and LIM CHOON
  HUAT as candidates; no final legal UBO claim is made.
- A matching local synthetic document reaches ordinary `COMPLETED /
  MOCK_GOLDTIER_SUBMITTED` with no external ACRA network activation.

## Why historical security/runtime slices remain retired

- OAuth/token code depends on unknown Q-012 authority and would recreate a credential
  and replay/cache boundary without a contract.
- Raw debug output would expose provider URLs/bodies outside the current sanitized
  evidence boundary.
- Runtime `bizfile_mock` composition would falsely activate a Dormant provider and
  contradict Phase 21 readiness truth.

## Verification

All results below were obtained on the final implementation source content before the
independent gate. The later edits that finalized this report and Aegis records are
documentation-only; the reviewer must independently identify and freeze the complete
tracked and task-owned untracked path set.

| Check | Result |
|---|---|
| BizFile + Garden + Phase 09 + Phase 10 focused suite | `117 passed` in 3.24s |
| Ownership analysis/API + zero-touch suites | `133 passed` in 23.70s |
| ACRA mode/mapping/sandbox/smoke/provider-conformance suites | `177 passed`, 3 expected malformed-payload warnings |
| Phase 16 cache focused suite after compatibility repair | `22 passed` |
| Full backend suite after the final source repair | `1176 passed, 28 skipped`, 3 expected malformed-payload warnings in 97.83s |
| Contract suite | `44 tests OK` in 20.466s |
| Ruff | PASS; inaccessible pre-existing pytest-cache directory warnings only |
| mypy | PASS, 95 source files |
| Project-state, architecture, tooling-config, policy-authority, external-provider-readiness | PASS |
| Supported secret-pattern scan | PASS |
| `git diff --check` | PASS; line-ending conversion notices only |

The first full-backend attempt exposed a candidate-caused Phase 16 adjacent-cache-key
failure (`1175 passed, 28 skipped, 1 failed`). The unnecessary Mock dataset namespace
bump was removed because Garden had no previously eligible/cacheable identifier. The
focused cache suite and full backend suite then passed on the repaired source.

The first independent gate returned `PASS WITH MINOR FIXES` because the dormant BizFile
module note incorrectly described `fetch_relationships` as failing closed while its
intentional implementation returns an explicit typed empty result without a network
call or endpoint claim. The note was corrected without changing executable behavior;
focused BizFile tests and hygiene were rerun before requesting a fresh gate.

Frontend, physical Mongo, and browser lifecycle checks were not run because this change
does not touch frontend, persistence, browser, or process-lifecycle behavior. The local
API-level Garden orchestration test exercises acquisition through terminal target-ledger
ordering without any external provider or database activation.

## Security and architecture self-review

- No OAuth, token lifecycle, client secret, bearer-header, or raw-response debug path was
  restored. `check_acra_connector.py` and `debug_acra_raw.py` remain absent.
- BizFile remains uncomposed and runtime-disabled. No composition, configuration, or
  readiness-registry path changed, and the adapter still inherits the existing verified
  TLS and redirect policy from `HttpxAcraTransport`.
- Query parameters are excluded from provenance. Decoder identity binding is strict,
  ambiguous multi-entity envelopes fail closed, and operation-specific 200/empty
  semantics are typed without exposing provider bodies.
- Garden share counts are bounded local synthetic inputs. The fixture excludes withdrawn
  holders, rejects malformed or duplicate active owners, uses Decimal arithmetic, and
  delegates aggregation and threshold classification to the existing canonical engine.
- No API/type, persistence schema, connector activation/configuration, authorization,
  architecture-owner, or external provider-status change is introduced. D-046 records
  the bounded provisional Mock decision; Q-004 and Q-012 remain open.

## Publication condition

Publication may proceed only if the fresh independent report at
`.ai-pipeline/reports/PRE_PHASE22_ACRA_TEAMMATE_INTEGRATION_QUALITY_GATE.md` returns exact
`PASS` for the frozen candidate. Any implementation or acceptance-content change after
review invalidates that verdict and requires a fresh gate.
