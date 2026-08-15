# Phase 07 Sponsor Dependency Matrix

This is a prioritized view of existing questions, not a replacement question log.
Authoritative wording/status remains in `OPEN_QUESTIONS.md`; none was closed in Phase 07.

| Priority | Q / decision | Needed | Why it matters | Current Mock workaround | Becomes possible | Blocks Mock POC? | Blocks live/final flow? |
|---:|---|---|---|---|---|---|---|
| 1 | Q-001 | Exact Ready-for-Approval/four-eye action, state, role | Defines final CLM outcome | Stop at `MOCK_GOLDTIER_SUBMITTED` | Authorized final transition/UAT | No | Yes |
| 2 | Q-008 / D-018 | Rotated/revoked old material; sanitized reference; approved sandbox/PingFed URLs, scopes, auth, fresh credentials, TLS details | Enables safe target authentication | Credential-free Mock connector | Real GoldTier conformance/smoke | No | Yes |
| 3 | Q-007 | Approved Singapore fields/value lists/proof codes | Prevents guessed target mapping | Minimal provisional Mock mapping | Real SG payloads | No | Yes |
| 4 | Q-002 | Hierarchy retrieval endpoint/schema/IDs/pagination/provenance | Enables seeded complex ownership | Synthetic provider-neutral graphs | Live hierarchy display/analysis | No | Yes |
| 5 | Q-004 | Threshold/comparator/jurisdiction/legal controller rule | Determines final UBO policy | Configurable inclusive 25% project default | Sponsor-approved UBO result | No | Yes |
| 6 | Q-003 / Q-014 | Document types/fields, confidence, missing/conflict actions, reviewer roles, SoD, audit | Defines real IDP/HITL | Four-field/0.85 provisional Mock policy | Final document workflow | No | Yes |
| 7 | Q-005 | Source authority and validation ownership | Governs registry/document conflicts | Conservative registry retention only after explicit allowed action | Final discrepancy/master-data policy | No | Yes |
| 8 | Q-012 | ACRA subscriber endpoint/schema/auth/errors/rates/TLS and authorized access | Enables exact live registry binding | Mock plus sandbox-shaped seam | Verified ACRA adapter | No | Yes |
| 9 | Q-006 | Direct related-party mandatory fields and atomic link persistence | Governs supported first-level write | Preparation summary; no write | Real related-party call | No | Yes |
| 10 | Q-013 / Q-014 | Privacy, lawful test data, storage/retention/encryption, upload security, reviewer access | Required for higher-trust deployment | Transient synthetic PDF, no raw output retention | Production-capable document/review boundary | No | Yes |
| 11 | Q-009 | Authoritative enum values/casing | Prevents invalid target values | Standalone enum; contradictory examples quarantined | Corrected fixtures/mapping | No | Yes |
| 12 | Q-010 | Confirmation of mandatory-field authority | Resolves structural/business-minimum conflicts | D-016 provisional overlay | Final validated contract | No | Yes |
| 13 | Q-011 | Corrected request/response examples | Removes quarantined/stale examples | Validator classification and standalone schemas | Canonical sponsor examples | No | Yes |

## Sponsor-facing requested order

1. Ready-for-Approval semantics.
2. GoldTier sandbox/PingFed access.
3. Singapore mappings/value lists.
4. Hierarchy retrieval contract.
5. UBO policy.
6. IDP document/confidence/reviewer policy.
7. Source-of-truth conflict policy.
8. ACRA live subscriber details.
9. Related-party operation semantics.
10. Privacy/retention/deployment requirements.

## Current gates

- Mock sponsor UAT: not blocked by these external dependencies.
- Live ACRA: **BLOCKED** by Q-012.
- Live hierarchy: **BLOCKED** by Q-002.
- Real GoldTier: **NOT READY** under Q-008/D-018 and Q-007.
- Final document/readiness policy: **NOT CONFIRMED**.
- Sponsor UBO policy: **NOT CONFIRMED**.
- Ready-for-Approval: **NOT CONFIRMED** under Q-001.

No new sponsor artefact was supplied for Phase 07. The existing evidence hierarchy,
contract baseline, discrepancy catalogue, D-015/D-016, quarantines, and Q-001–Q-014
therefore remain unchanged.
