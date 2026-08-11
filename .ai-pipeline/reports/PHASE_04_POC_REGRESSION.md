# Phase 04 POC Regression Check - Post-Remediation

## Result

**PASS.** The remediation preserves all accepted Phase 01/02 onboarding, Phase 03
document, and seven Phase 04 ownership outcomes. The six independent gate findings now
have direct regression coverage. No false completion, connector-order, isolation,
terminal-finality, or user-claim regression was found.

The canonical catalogue was updated only with remediation invariants; no accepted
scenario outcome or sponsor policy was rewritten.

## Canonical onboarding scenarios

| UEN | Accepted and verified terminal result | Required stopping/order | Result |
|---|---|---|---|
| `202400001A` | `COMPLETED` | ACRA; GoldTier search `NO_MATCH` -> shell -> policy -> amend | PASS |
| `202400002B` | `REVIEW_REQUIRED / CANONICAL_DATA_INCOMPLETE` | ACRA only; no GoldTier | PASS |
| `202400003C` | `FAILED / GT_POLICY_VALIDATION_FAILED` | ACRA; search -> shell -> policy; no amend | PASS |
| `202400004D` | `REVIEW_REQUIRED / GT_OPTIONAL_SECTION_REVIEW` | ACRA; search -> shell -> policy -> partial amend; no completion | PASS |
| `999999999Z` | `FAILED / ACRA_ENTITY_NOT_FOUND` | ACRA only; no GoldTier | PASS |

Focused results: Phase 01 28/28; Phase 02 80/80. Only explicit GoldTier `NO_MATCH`
permits shell creation, and required-stage exceptions remain sanitized terminal records.

## Phase 03 document scenarios

| Scenario | Verified document result | Required behavior | Result |
|---|---|---|---|
| `ALL_FIELDS_MATCH` | `REVIEW_REQUIRED`, then `REVIEWED` after four decisions | Mock IDP once; explicit field review | PASS |
| `FIELD_MISMATCH` | `REVIEW_REQUIRED` | Mismatch remains visible | PASS |
| `LOW_CONFIDENCE` | `REVIEW_REQUIRED` | 0.54 address confidence remains reviewable | PASS |
| `MISSING_FIELD` | `REVIEW_REQUIRED` | Missing suggestion cannot be accepted | PASS |
| `PROCESSOR_FAILURE` | `FAILED / IDP_PROCESSING_FAILED` | No field/review/later event | PASS |

Focused Phase 03 result: 59/59. Document operations remain case-scoped, do not mutate
the parent canonical entity, and cannot strand `PROCESSING` after an accepted failure.

## Phase 04 ownership scenarios

The API probe inspected stored results, event sequences, candidate evidence, issues, and
browser provenance directly.

| Scenario | Actual result | Candidate/issue evidence | Actual events | Result |
|---|---|---|---|---|
| `DIRECT_OWNER` | `ANALYZED` | A 60%, B 40%; both provisional candidates | load start -> loaded -> analysis start -> completed | PASS |
| `INDIRECT_OWNER` | `ANALYZED` | C 30% candidate; D 10% below; exact `40 x 75` and `40 x 25` paths | load start -> loaded -> analysis start -> completed | PASS |
| `MULTIPLE_PATHS` | `ANALYZED` | A direct 20% + indirect 20% = 40%; unique paths once | load start -> loaded -> analysis start -> completed | PASS |
| `BELOW_THRESHOLD` | `ANALYZED` | A 20%, B 15%; both below | load start -> loaded -> analysis start -> completed | PASS |
| `INCOMPLETE_CHAIN` | `REVIEW_REQUIRED` | no candidate; `INCOMPLETE_LEGAL_ENTITY` | load start -> loaded -> analysis start -> review required | PASS |
| `CYCLE` | `REVIEW_REQUIRED` | no candidate; `CYCLE_DETECTED` | load start -> loaded -> analysis start -> review required | PASS |
| `PROVIDER_FAILURE` | retrievable `FAILED / OWNERSHIP_PROVIDER_FAILED` | no candidate/issue partials | load start -> analysis failed | PASS |

Every probed browser result omitted `source_reference`. Focused Phase 04 result: 77/77.

## Quality-gate remediation regressions

| Risk | Verified actual behavior | Result |
|---|---|---|
| Natural-person owned parent | Root, nested, mixed-validity, and multi-level shapes become safe `FAILED`; zero definitive candidates | PASS |
| Mutated provider instance/subclass | Provider name, party text, relationship ID/percentage, and nested provenance are freshly rejected; no provider graph retained | PASS |
| Private/token-like reference | Scheme, userinfo, query, fragment, token/secret-like, raw body, blank/control, and overlong forms fail before browser projection | PASS |
| Failed then stale success | Expected-version stale success rejected; final `FAILED` event/state retained | PASS |
| Analyzed then stale failure | Expected-version stale failure rejected; final `ANALYZED` event/state retained | PASS |
| Simultaneous analyze | Exactly one `ANALYZING` transition; one `ANALYZED`, one stable conflict | PASS |
| Simultaneous load | Exactly one record/load history; one `LOADED`, one already-loaded conflict | PASS |
| Maximum path-ID composition | 64-character edge IDs at depth 8 and configured depth 64 analyze successfully with a 72-character digest ID | PASS |
| Threshold precision | Six decimal places accepted; seven, zero, and over-100 rejected before workflow use | PASS |
| Exact frontend Decimal | `24.9999995%` remains below 25%; equal/above/long indirect/multiple-path values remain exact | PASS |

## Cross-phase invariants

| Invariant | Result |
|---|---|
| Required-stage failure stops later connector calls | PASS |
| Accepted unexpected failure becomes retrievable terminal `FAILED` with sanitized error | PASS |
| `COMPLETED` requires every accepted onboarding stage and never means Ready-for-Approval | PASS |
| Incomplete/uncertain document or ownership data routes to review as specified | PASS |
| Mock, sandbox-shaped synthetic, and live labels remain distinct | PASS |
| Cases/documents/ownership records retain independent IDs, histories, and UTC order | PASS |
| Terminal event remains final under sequential and concurrent access | PASS |
| Ownership failure cannot mutate onboarding or Phase 03 document state | PASS |
| Document failure cannot mutate ownership state | PASS |
| Cycle/incomplete/limit/malformed-parent input cannot produce a false candidate | PASS |
| API/UI claims remain ownership-only, synthetic, provisional, and non-approval | PASS |

## Catalogue update

`.agents/skills/poc-regression-check/references/regression-catalogue.md` now records:

- legal-entity owned-parent semantics;
- fresh provider-model reconstruction and server-only opaque provenance;
- atomic expected-version terminal finality;
- digest path-ID composition;
- shared six-decimal threshold precision; and
- exact browser Decimal truth.

No Phase 01/02/03 outcome or original Phase 04 scenario was superseded.

## Complete evidence used

- Full backend: 244 passed.
- Phase 01: 28 passed; Phase 02: 80 passed; Phase 03: 59 passed; Phase 04: 77 passed.
- Repository unittest: 39 passed; contract: 29 passed.
- Frontend typecheck: PASS; frontend tests: 16 passed; production build: PASS.
- Ruff, strict mypy, secret scanner/tests, GoldTier validator tests/classification,
  dependency integrity, and final diff/whitespace checks: PASS.

## Truthful claim assessment

`ANALYZED` means deterministic ownership calculation completed. A
`PROVISIONAL_UBO_CANDIDATE` means only that exact aggregated ownership met the
project-defined provisional inclusive threshold. Neither means a legal controller
finding, KYC/compliance approval, GoldTier approval, live hierarchy interoperability,
or Ready-for-Approval.
