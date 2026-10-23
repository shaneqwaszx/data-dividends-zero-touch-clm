# SIM LIM official shareholder evidence — investigation and bounded model proposal

Stage 1 investigation, 2026-10-24. No product code has been changed. This document asks
the owner to approve the model and persistence change below before implementation. It
is not an independent QG verdict.

**Owner decision (2026-10-24):** P1 approved as proposed, with `shareType`/`currency`
retention deferred. It is implemented; see `SIM_LIM_SHAREHOLDER_EVIDENCE_REPORT.md`.

## Identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-shareholder-evidence-20261024`.
- Branch `feat/sim-lim-official-shareholder-evidence-20261024`.
- BASE = `origin/main` = `2d8b84af46f2ac0f1d94965ca638e1cd7a1c7e54` (merged PR #106).
- Change classes, if approved: `BACKEND_DOMAIN`, `EXTERNAL_PROVIDER`, `PERSISTENCE`.

## Reproduction

Offline protocol transport, 0 external calls. The transport carries the SIM LIM shape
the owner's diagnostic observed: an empty entity profile plus four shareholder rows. I
used synthetic names and values, 1 corporate row and 1 withdrawn row.

| Path | Observed |
|---|---|
| Normal onboarding (Garden hybrid) | SIM LIM `NOT_FOUND`. Calls: Garden `ENTITY_PROFILE` ×2, SIM LIM `ENTITY_PROFILE` ×1, **no `SHAREHOLDERS` call**. No SIM LIM evidence or holders reach the analysis |
| Direct connector call (what the diagnostic does) | `fetch_company` → `None`. `fetch_ownership_parties` → 4 rows bound to `111111111M` from the `coShareholdersDetails` endpoint |

## 1. Why the diagnostic succeeds while onboarding loses the shareholders

- `AcraRegistryProviderAdapter.retrieve_acquisition` returns `None` as soon as
  `fetch_company` returns `None` (explicit empty `entities`). The acquisition contract
  requires a canonical entity profile first.
- The coordinator then caches a definitive `NOT_FOUND`, and discovery `_classify` reports
  `NOT_FOUND`.
- `coShareholdersDetails` is never dispatched. The accepted contract also dispatches the
  company-shareholder operation only for a recognized COMPANY legal form, which needs a
  profile (`ACRA_MOCK_API_PROFILE.md`, "Safe errors and call stopping").
- `AcraDiagnosticService` calls `connector.fetch_ownership_parties(uen)` directly,
  independent of the profile.

## 2. Issuer binding guaranteed by the existing decoder

`BizfileMockOwnershipPartiesDecoder` with `include_withdrawn=True` enforces:
- exactly one entity row, whose `uen` equals the requested uppercase UEN;
- a `shareholders` collection that is present (a missing collection is rejected, not
  read as empty);
- non-empty `grouping` is rejected;
- categories are only Corporate or Individual;
- `shareAllotted` is an exact Decimal ≥ 0 (floats rejected);
- an explicit empty `entities` collection means EMPTY;
- the response must be HTTP 200, `application/json` and at most 256 KiB, with 401/403,
  timeout and 5xx mapped to safe errors.

## 3. What can be retained

| Field | Retained by the current DTO? |
|---|---|
| Issuer UEN, operation provenance (endpoint without query, retrieval time) | Yes |
| `shareholderId`, `shareholderName`, category → party type | Yes |
| `status` (Active / Withdrawn) | Yes (withdrawn rows kept) |
| `shareAllotted` | Yes (exact Decimal) |
| `shareType`, `currency` | **No**: dropped by the DTO (`extra="ignore"`) |
| Corporate holder registration identifier | **No**: always `None`; not in the decoded contract |
| Denominator / issued capital | Not returned by this operation |

## 4. What is missing for confirmed percentages

A same-entity, same-class authoritative denominator (issued shares). `coShareholdersDetails`
does not provide one. A capital operation is outside the current contract (Q-012). The
sum of visible active allotments is authorized as a denominator only inside the
project-defined local Garden fixture. So without new authority the evidence stays as
quantities without percentages, and review stays required.

## 5. Does it survive onboarding today?

No. See §1.

## 6. Can FGH SERVICES, INC. be queried further?

Not legitimately. The decoder supplies no registration identifier, and discovery recurses
only through a verified Singapore UEN (`_verified_uen`). Nothing in the response
establishes a jurisdiction or UEN; the name alone is not evidence. It would be retained as
an unverified corporate holder.

## Why the current model cannot represent this safely

1. `RegistryAcquisitionBundle.entity_profile` is required. Relaxing it would weaken the
   canonical acquisition contract, which is forbidden.
2. `RegistrySnapshotEntry` holds only a bundle or `NOT_FOUND`, so there is nowhere to
   cache operation-specific shareholder evidence for an issuer with an empty profile.
3. The analysis cannot hold the holders:
   - the ownership graph rejects parties without edges;
   - `OwnershipEvidence` has no name or party type;
   - discovery records have no shareholder field;
   - `supplemental_*` fields are rendered by the unchanged UI as "Retained local
     supplement graph", which would mislabel official evidence;
   - adding issuer units to `evidence` would also change Garden's single root-level
     issue (role message → activity message), a diagnostic regression.

## Proposed minimal change (P1) — needs owner approval

**A. Registry layer** (`EXTERNAL_PROVIDER`, registry cache `PERSISTENCE`)
- `RegistryShareholderEvidence` holds:
  - the requested identifier;
  - status `COMPLETE`/`EMPTY` and record count;
  - provenance (ACRA, MOCK, `OWNERSHIP_PARTIES`, retrieval time, evidence reference);
  - the shareholder rows, withdrawn included with status.
- `AcraRegistryProviderAdapter.retrieve_shareholder_evidence(uen)` uses the existing
  connector's `fetch_ownership_parties`, in the official Marketplace composition only. It
  never uses `MockAcraConnector`.
- `RegistryAcquisitionCoordinator.acquire_shareholder_evidence(...)` reuses the same cache
  repository, key locks and CAS. Its key is distinguished by
  `acquisition_contract_version="MARKETPLACE_SHAREHOLDERS_V1"`.
- `RegistrySnapshotEntry` gains `cache_schema_version: 3` with an exclusive
  `shareholder_evidence` field. v1/v2 entries are unchanged.
- Freshness uses the existing policy for COMPLETE and the existing negative TTL for
  EMPTY. Failures are never cached.

**B. Discovery** (`BACKEND_DOMAIN`)
- **Trigger, only when all hold:**
  - official Marketplace lane;
  - a corporate holder that is not a scenario-overlay issuer;
  - a verified UEN already discovered from the parent;
  - a definitive (fresh or cached) entity-profile `NOT_FOUND`.

  One extra bounded read, inside the existing budget and limits. OPQ overlay issuers keep
  D-077 behaviour.
- **COMPLETE with rows:**
  - outcome `PROVIDER_PARTIAL`, reason `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`;
  - the branch stays unresolved (Garden bound stays 62.5%);
  - no graph party or edge is added, and no identity, legal form or verification is
    manufactured.
- **EMPTY:** the outcome stays `NOT_FOUND`.
- **New record field:** `official_shareholders` (bounded). Each observation holds the
  source id, name, party type, category, status, units, `current_interest` (Active only)
  and provenance, plus a lookup disposition (fetched or cache-reused).
- **Withdrawn rows** are kept as history and never count as current interest.
- **Corporate holders** are not recursed without a verified UEN, so FGH stays unverified.
- **One additional issue** using the existing code `OWNERSHIP_DENOMINATOR_REQUIRED`
  (affected `111111111M`): official units are retained, no percentage is inferred, and a
  same-entity denominator is required. Garden's existing issues are unchanged and the
  case stays REVIEW_REQUIRED, with readiness and GoldTier blocked.
- **Complete, compatible quantitative evidence** keeps the existing engine path: a
  COMPLETE acquisition with relationships still resolves through `FETCHED`.

**C. Persistence**
- Case envelope schema 13: an exact V12 reader rejects the new fields, and legacy readers
  reject them.
- Registry cache schema 3.
- Physical Mongo round-trip and restart tests for both.

**D. API/UI**
- API: the discovery record gains an additive `official_shareholders` field.
- UI: the unchanged frontend types do not include it, so the rows will not render. Only
  the new issue message is visible.
- Displaying the rows is a separate owner decision.

**E. Optional:** retain `shareType`/`currency` in the source DTO. That is a connector DTO
change, and useful only for a future same-class denominator. Recommendation: defer.

**F. Documentation:** D-079 records the owner-authorized exception to "shareholder
dispatch only for a recognized COMPANY legal form", limited to identified corporate
holders with an empty profile. The documents to amend are:
- `ACRA_MOCK_API_PROFILE.md`;
- `REGISTRY_CACHE_FRESHNESS_PROFILE.md`;
- `OWNERSHIP_UBO_PROFILE.md`;
- an ADR-013 amendment.

**Tests:** every acceptance scenario in the assignment, using offline contract transports:
- empty, malformed, issuer-mismatch, timeout and 401/403 shareholder responses;
- cache hit and miss;
- unverified corporate holder;
- withdrawn rows;
- regression for Garden legacy, Garden hybrid, OPQ and the synthetic Mock lane.

**Verification:**
1. Focused checks.
2. Integrated acceptance: full backend, physical Mongo, contract lane, and targeted
   Garden/OPQ browser selectors.
3. Independent QG.

The size is comparable to D-077.
