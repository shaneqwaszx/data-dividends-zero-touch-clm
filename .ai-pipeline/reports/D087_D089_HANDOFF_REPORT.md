# D-087 / D-088 / D-089 handoff: OPQ POC readiness, Mock businessProfile and the OPQ multi-holder variant

These are owner assignments from 2026-10-25 and 2026-10-26. This report follows the D-085/D-086 handoff
(`GENERALIZED_POC_ACCEPTANCE_D085_D086_REPORT.md`, unchanged) on the same PR #111.

## 1. Identity

| Item | Value |
|---|---|
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` (PR #111) |
| Previously published head | `8451e2a70030f74c50d68194b060bf106aebe7b4` |
| D-087 reviewed tree (preserved) | `db56b8e104e5fbcbda955c089063ed221f75b51c` |
| Product commit | `7047d46ffd5e14ea6a07c4fc3feb7f4e88d3cca0`, tree `a9b5c07a571cefc7ec397c071529872d002e3668` (exactly the reviewed candidate) |
| Main integration | merge `5b2e4cd8c70d3ad20ec2bab4a725498e8698e27d` with `origin/main` `a6e86fc` (README-only, #112); tree `88a014e25229448f123ae00dd6dd03fa00a35a80` |
| Product delta identity | `git patch-id` of the PR delta is `3a3c5727…`, both before integration (`5de7f24..7047d46`) and after (`a6e86fc..5b2e4cd`) |

## 2. Behaviour

- **D-087.**
  - A trusted scenario declaration may name intermediate issuers and the ownership-like role kinds that are descriptive context (`DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES`). OPQ -> Garden -> SIM LIM names Garden `OWNER` only.
  - A fresh case is POC-accepted, ownership-READY with 0 blockers, and waits for explicit target confirmation.
  - Undeclared issuers, the root, undeclared kinds and malformed or improperly bound observations still block.
  - The accepted banner discloses the retained roles and the owner-declared link.
- **D-088.**
  - A Mock-only Marketplace `businessProfile` capability:
    - fixed host and path;
    - strict decoder: whole JSON counts only, never strings; officer, address and nationality fields dropped;
    - holder id replaced by a pseudonymous unkeyed `BP-` digest (Mock only; a keyed digest is required before any non-Mock use);
    - cache schema 5, key `MARKETPLACE_BUSINESS_PROFILE_V1`.
  - It is read only for scenario-named holders whose entity profile and shareholder operation are both empty.
  - Status-free rows that exactly equal one compatible issued class, with paid-up agreeing, attach as `LOCAL_POC_ISSUED_CAPITAL_BASIS` links under `ISSUED_CAPITAL_DENOMINATOR`. Everything else fails closed.
  - `provider_status` is recorded separately from `assumed_current`.
- **D-089.** The separate selector `garden_abc_multi_holder` (`OPQ_GARDEN_ABC_V1`) declares owner-declared OPQ -> Garden 50% and OPQ -> ABC COMPANY 50%. Results:

  | Party | Effective % | Assumed-basis match |
  |---|---|---|
  | ABC's individual holder | 50 | MET |
  | ABCD123 | 25.568181875 | MET |
  | LIM CHOON HUAT | 18.75 | NOT_MET |
  | TAN WEI LING | 2.8409090625 | NOT_MET |
  | EFGH2345 | 2.8409090625 | NOT_MET |

  Entity values: Garden 50, SIM LIM 31.25, ABC 50.
- **Unchanged.** The five-layer default, the OPQ -> Garden 100% variant, direct Garden onboarding, the D-085/D-086 safeguards, explicit Mock GoldTier confirmation and the `:1248` race fix.

## 3. Provider evidence

There was one owner-authorized live Marketplace Mock read: 1 token and 1 GET, `businessProfile` for `201688888A`, HTTP 200. It showed one Individual holding 1000 ORDINARY (SGD) with no status, and issued and paid-up capital of 1000 ORDINARY (SGD). The output was sanitized and leak-checked; no personal data is in the repository. The offline fixture uses a synthetic holder name in the observed shape.

## 4. Evidence

| Lane | Content | Result |
|---|---|---|
| Full backend + physical Mongo (disposable `mongo:7`) | `a9b5c07` | 3350 tests, 0 failures, 6 skipped (OCR) |
| Frontend vitest / tsc / build | `b23d03a` (no frontend change after) | 1084 / clean / OK |
| Browser E2E (115 selectors) | `b23d03a` | 115/115; the reviewer confirmed it is not invalidated by the remediation |
| Multi-holder visual smoke (offline, Mock GoldTier, sandbox writes off) | `a9b5c07` | 16/16, including explicit Mock send |
| D-087 smoke (OPQ 100%, Garden, five-layer) | `db56b8e` | 21/21 |
| Checkers (project state, architecture, secrets, policy authority, provider readiness, tooling) | merge `88a014e` | PASS |

## 5. Independent gates

| Tree | Verdict | Report |
|---|---|---|
| `db56b8e` (D-087) | PASS (four P3 notes, fixed in this candidate) | `D087_QUALITY_GATE.md` |
| `b23d03a` (D-087 to D-089) | PASS WITH MINOR FIXES | `D088_D089_QUALITY_GATE.md` |
| `a9b5c07` (remediated) | **PASS** | `D088_D089_RE_QUALITY_GATE.md` |
| `88a014e` (post-integration) | **PASS** | `D085_D089_POST_INTEGRATION_QUALITY_GATE.md` |

## 6. Change statement

- **API/type:**
  - new optional discovery field `official_business_profile`;
  - acceptance fields `descriptive_intermediate_*_role_count` and `issued_capital_relationship_ids`;
  - assumptions `DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES` and `ISSUED_CAPITAL_DENOMINATOR`.
- **Schema:** case envelope 15 additions (still unreleased in this PR), with legacy rejection; registry cache schema 5.
- **Connector:** new Mock-only `businessProfile` operation (external provider).
- **Configuration:** the selector gains `garden_abc_multi_holder`.
- **Business rules:** D-087, D-088, D-089 (project-defined POC).
- **Mapping:** none.
- **Auth:** none.
- **Architecture:** the registry owner gains a Mock-only capability; the single engine is reused.
- **Provider status:** unchanged (Mock).

## 7. Limitations

- These are POC decisions, not sponsor policy; Q-004 and Q-012 remain open.
- Formal classifications stay REVIEW_REQUIRED, and there are no provisional UBOs.
- The holder digest is pseudonymous; non-Mock use is prohibited pending a security decision.
- OPQ's legal form still reads `OTHER` (the `companyType` decoder limitation).
- Hosted CI has been billing-blocked; any manual-CI exception is the owner's decision.
