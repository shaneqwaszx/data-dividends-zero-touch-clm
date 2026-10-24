# Five-layer hybrid ACRA Marketplace Mock onboarding demo (D-077)

This guide reproduces the five-corporate-layer onboarding scenario. It is a
**non-production demonstration**. Entity identity comes from the official ACRA API
Marketplace **Mock** where the provider supplies it. Every ownership link and share
allotment is a fictional local declaration (`LOCAL_SYNTHETIC_RELATIONSHIP` / `LOCAL`).
None of it is ACRA-returned ownership, Live/production registry evidence, a legal UBO
determination or a GoldTier submission.

## 1. Truth labels at a glance

| Concept | Value in this demo |
|---|---|
| Topology | Five corporate levels L1 -> L5 plus persons, with one equal-length diamond |
| Official identity | Root only (when the official profile is returned); unverified issuers are `LOCAL_SYNTHETIC_IDENTITY` |
| Quantitative evidence | Always local synthetic (`quantitative_evidence_complete = false`) |
| Classification | Every candidate `REVIEW_REQUIRED` / threshold `INDETERMINATE` |
| Synthetic-basis comparison | Same inclusive >= 25% comparator on the declared basis, demonstration only (API field `synthetic_basis_threshold_result`; not rendered by the unchanged UI) |
| Readiness | Ownership review blocks progression; nothing is sent to GoldTier automatically |

## 2. Source catalogue and candidate selection

Input: the user-supplied seven-page *ACRA API Marketplace — Entity Information Query —
Sample data* catalogue (last updated 18 November 2025, SHA-256
`121b908f21867108a256e8af9d4914d856a8e64b80702f3286bf5f679eebf2f9`). It is a
per-operation sample index, not a hierarchy, coherent issuer record or denominator. The
PDF is not stored in Git; only this sanitized UEN/page matrix is.

| UEN | Catalogue page / operation | Latest official observation (Phase 24, 2026-10-01/02) | This session |
|---|---|---|---|
| `11111999A` GARDEN BUSINESS | p.6 Entity Basic Information | Same-UEN profile, BUSINESS_PARTNERSHIP, four role rows | NOT_RUN_CREDENTIALS |
| `201511222D` OPQ PTE. LTD. | p.6 Entity Basic Information | Same-UEN profile; classifier `OTHER` | NOT_RUN_CREDENTIALS |
| `111111111M` | p.2-5 operation-specific samples | Basic entities empty; shareholder op returns unbound units | NOT_RUN_CREDENTIALS |
| `200811111M` | p.1-2 Directory Search / Verification / Key Dates | Never probed for basic information | NOT_RUN_CREDENTIALS |
| `201688888A` | p.7 Business Profile | Never probed for basic information | NOT_RUN_CREDENTIALS |
| `200811111K` | p.3 Foreign and Redomiciliation | Never probed for basic information | NOT_RUN_CREDENTIALS |
| `199801111H` | p.5 Company FYE / LLP Annual Declaration | Never probed for basic information | NOT_RUN_CREDENTIALS |
| `111111111K` | p.4 Company Capital | Basic entities empty | NOT_RUN_CREDENTIALS |

`NOT_RUN_CREDENTIALS`: the implementing session was not permitted to read the
Marketplace credentials, so it made **zero** Marketplace calls. Run the bounded probe in
section 7 to record live Mock outcomes.

## 3. L1-L5 company table

| Level | Company (display) | UEN | Identity source | Incoming synthetic edge | Local denominator |
|---|---|---|---|---|---|
| L1 (root, depth 0) | OPQ PTE. LTD. | `201511222D` | Official Marketplace Mock profile (legal form `OTHER`) | — | 10,000 units |
| L2 (depth 1) | FIVE LAYER L2 HOLDINGS (SYNTHETIC) | `200811111M` | Official lookup, then `LOCAL_SYNTHETIC_IDENTITY` if NOT_FOUND | 8,000 of 10,000 = 80% | 1,000 units |
| L3 (depth 2) | FIVE LAYER L3 INVESTMENTS (SYNTHETIC) | `201688888A` | As L2 | 625 of 1,000 = 62.5% | 1,000 units |
| L4A (depth 3) | FIVE LAYER L4A CAPITAL (SYNTHETIC) | `200811111K` | As L2 | 600 of 1,000 = 60% | 100 units |
| L4B (depth 3) | FIVE LAYER L4B VENTURES (SYNTHETIC) | `199801111H` | As L2 | 400 of 1,000 = 40% | 100 units |
| L5 (depth 4) | FIVE LAYER L5 HOLDCO (SYNTHETIC) | `111111111K` | As L2 (diamond: acquired once) | 100 of 100 = 100% via L4A; 50 of 100 = 50% via L4B | 1,000 units |

Each denominator is a locally declared complete same-class active register. Names below
the root are synthetic labels, not the catalogue's operation-specific sample names. If
the official provider returns a profile for an issuer, that profile's legal name and legal
form replace the synthetic display name. The links stay local. If the profile has
official shareholder rows, the overlay is refused and the branch stays unresolved.

## 4. Ownership tree and exact Decimal paths

```text
L1 OPQ PTE. LTD. (201511222D)
├── ALEX TAN (SYNTHETIC PERSON) ............ 20%      path 20
└── L2 200811111M ......................... 80%
    ├── BEATRICE LIM (SYNTHETIC PERSON) .... 37.5%    path 80 x 37.5 = 30
    └── L3 201688888A ..................... 62.5%
        ├── L4A 200811111K ................ 60%
        │   └── L5 111111111K ............. 100%
        │       ├── DIANA KOH ............. 62.5%  path 80 x 62.5 x 60 x 100 x 62.5 = 18.75
        │       └── EDWARD NG ............. 37.5%  path 80 x 62.5 x 60 x 100 x 37.5 = 11.25
        └── L4B 199801111H ................ 40%
            ├── CHARLES ONG (SYNTHETIC) ... 50%    path 80 x 62.5 x 40 x 50 = 10
            └── L5 111111111K (same issuer)  50%
                ├── DIANA KOH ............. 62.5%  path 80 x 62.5 x 40 x 50 x 62.5 = 6.25
                └── EDWARD NG ............. 37.5%  path 80 x 62.5 x 40 x 50 x 37.5 = 3.75
```

| Person | Aggregate | Classification (authoritative) | Synthetic-basis comparison (>= 25%) |
|---|---|---|---|
| BEATRICE LIM | 30 | REVIEW_REQUIRED / INDETERMINATE | MET (above) |
| DIANA KOH | 18.75 + 6.25 = 25 | REVIEW_REQUIRED / INDETERMINATE | MET (exactly equal; inclusive) |
| ALEX TAN | 20 | REVIEW_REQUIRED / INDETERMINATE | NOT_MET |
| EDWARD NG | 11.25 + 3.75 = 15 | REVIEW_REQUIRED / INDETERMINATE | NOT_MET |
| CHARLES ONG | 10 | REVIEW_REQUIRED / INDETERMINATE | NOT_MET |

Complete **by topology** (no unresolved corporate leaf), not complete **by evidence**:
official identity is incomplete, and quantitative evidence is local synthetic. Issues are
`SYNTHETIC_OWNERSHIP_EVIDENCE` and `OWNERSHIP_METHOD_UNSUPPORTED` (root legal form `OTHER`).

## 5. Uploadable document

- Asset: `apps/backend/tests/fixtures/uat/five-layer-marketplace-hybrid-client.pdf`,
  SHA-256 `a2d9b1985d53e31414b00af40ba3902689f4dffcd67a5fd7a620abe7e5555551`, 1,387 bytes.
- Generator (byte-reproducible): `python -m scripts.generate_five_layer_marketplace_hybrid_client`
  (from the repository root, with `apps/backend` on `PYTHONPATH`).
- Extracted fields: `Legal Name: OPQ PTE. LTD.`, `UEN: 201511222D`, `Country: SG`.
  The registered address is deliberately absent because no official address was
  confirmed. It reconciles as `REGISTRY_ONLY` under the certificate-of-incorporation
  profile. The PDF declares no percentages, share counts or person identifiers, so
  document ownership extraction yields no observations.
- Indexed in `apps/backend/tests/fixtures/uat/README.md` and the exact allowlist in
  `tests/test_phase_07_delivery_assets.py`.

## 6. UI sequence

1. Sign in as a Relationship Manager (for example `maya-lim`). Open **New onboarding**.
2. Jurisdiction `SG`, Company Legal Name `OPQ PTE. LTD.`, Registration ID / UEN
   `201511222D`. Attach the PDF above and select **Create onboarding**. Provide the
   submission classification (KYC type *Company - Private*, segment *Corporate*) through
   the normal classification control when asked; the browser test sets the same values
   through the authenticated classification API.
3. The case stops at `WAITING_FOR_REVIEW` / `OWNERSHIP`. The document is auto-confirmed,
   and reconciliation is MATCHED (address REGISTRY_ONLY).
4. Open **Ownership & UBO**. The existing, unchanged components render the case.
   *Ownership structure* shows **5 layers**, 11 parties and the banner *Partial or
   disputed ownership evidence — review required*. The indented hierarchy shows
   OPQ PTE. LTD. (source `ACRA_REGISTRY_ACQUISITION · MOCK`), then L2 *Holds 80% of
   OPQ PTE. LTD.*, L3 *Holds 62.5%*, L4A *Holds 60%* / L4B *Holds 40%*, and L5
   *Holds 100%* / *50%*. Every link's source column reads
   `LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL`.
5. Select DIANA KOH. The detail shows aggregate 25%, `GREATER_THAN_OR_EQUAL_TO 25% →
   INDETERMINATE`, `REVIEW_REQUIRED`, the calculation
   `80% x 62.5% x 60% x 100% x 62.5% = 18.75%`, and *2 retained paths reach this person*.
6. Open *Corporate owners from separate registry records (5)*. It lists each issuer's
   UEN, depth and outcome. Overlay-attached issuers show the raw outcome
   `LOCAL_SYNTHETIC_OVERLAY`.
7. Onboard the same root again. Issuers answered NOT_FOUND reuse the official-namespace
   negative cache, with zero GETs within its 600 s TTL. An issuer with an official
   COMPANY profile reuses its cached entity profile but re-reads its required, empty
   shareholder operation, so it still counts as provider-backed.

The Ownership & UBO frontend, the PR #103 10-step rail and the GoldTier sections are
unchanged (owner scope correction, 2026-10-23). No GoldTier send button is offered while
ownership review is outstanding.

Some values are available only through the API (`GET /api/onboarding/cases/{id}/ownership`),
because the existing UI does not render these optional backend fields:

- per-issuer `identity_basis` (`LOCAL_SYNTHETIC_IDENTITY` or
  `OFFICIAL_MOCK_ENTITY_PROFILE`) and `official_entity_lookup` (for example
  `NOT_FOUND`, `NOT_FOUND_CACHE_REUSED`, `ENTITY_PROFILE_FETCHED`);
- the audit's `topology_complete`, `official_identity_complete` and
  `quantitative_evidence_complete`;
- each candidate's `synthetic_basis_threshold_result`.

Displaying them would need an owner-authorized frontend change.

## 7. Running it

**A. Offline browser demonstration (no credentials, no network).** It uses the real
official connector against the allowlisted protocol transport
(`scripts/five_layer_hybrid_fixture.py`). The banner labels it *API Marketplace protocol
test*.

```powershell
python scripts/run_e2e.py --selectors-file <file containing e2e/five-layer-hybrid.e2e.ts:78> --results-json <new file>
```

Offline counters, recorded by the passing selector: first onboarding uses 1 token request
and 7 GETs (root entity profile twice for company plus embedded officers, and each of the
five issuers once). The second onboarding of the same root adds 0 tokens and 0 GETs, and
discovery reports 5 cache hits and 0 provider-backed lookups. In the offline fixture,
unprobed UENs answer NOT_FOUND by assumption, and OPQ carries a visibly synthetic
offline address. Neither is an observation.

**B. Official Marketplace Mock lane (owner credentials).** Use your existing approved
credential injection. Set `ACRA_CONNECTOR_MODE=api_marketplace_mock` and
`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`, start the backend and
frontend with your usual local commands, then follow section 6. Possible honest live
outcomes:

- Without an official registered address for OPQ, the registry stage stops at
  `CANONICAL_DATA_INCOMPLETE` before ownership.
- If the official legal name differs from `OPQ PTE. LTD.`, reconciliation raises a name
  conflict for review.
- Issuers the provider verifies are recorded through the API with `identity_basis =
  OFFICIAL_MOCK_ENTITY_PROFILE` and `official_entity_lookup = ENTITY_PROFILE_FETCHED`, and
  their official legal name replaces the synthetic display name. The links stay local.
- Issuers with official shareholder rows stay unresolved
  (`OFFICIAL_QUANTITY_PRECLUDES_OVERLAY`).
- Provider failures leave branches unresolved.

The memory cache is process-local. Mongo reuse requires the explicit Mongo mode.

**C. Bounded live probe (owner-run).**

```powershell
python scripts/phase24_acra_mock_discovery.py --config-env-path <approved env file> --lane five-layer-hybrid
```

It reads at most 16 GETs for the eight UENs above and prints only sanitized
counts/flags. Its `evidence_class` is derived from the recorded receipts:

- `MOCK_INTEROPERABILITY_OBSERVED`: at least one official data read returned HTTP 200.
  That means live HTTPS access to the Marketplace **Mock** environment, never ACRA
  production verification.
- `AUTHENTICATION_FAILED`: the token request or a read returned 401/403.
- `TRANSPORT_FAILURE`: no HTTP response was received.
- `NO_SUCCESSFUL_READ`: anything else without a successful read.

## 8. Garden under the same concept

With `hybrid_direct_overlay`, Garden `11111999A` keeps its official Marketplace Mock
entity/people facts. The owner-supplied Garden body becomes a direct-only overlay: SIM
LIM 5000 / LIM CHOON HUAT 3000 of 8000 = 62.5% / 37.5%. SIM LIM `111111111M` receives
its own official cache-first lookup. Its entity profile is empty in the Marketplace Mock.
Under D-079, returned official `coShareholdersDetails` rows are kept beside the graph as
`official_shareholders`. The record shows outcome `PROVIDER_PARTIAL`, reason
`OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, and an `OWNERSHIP_DENOMINATOR_REQUIRED`
issue is added. An empty shareholder result stays `NOT_FOUND`
(`OFFICIAL_SHAREHOLDERS_EMPTY`). Either way no percentage is inferred and the branch stays
unresolved. LIM CHOON HUAT's synthetic-basis comparison is MET
(37.5%), and no 900/100/100 subtree is attached under any label. The default
`garden_legacy_supplement` keeps the accepted flattened Garden result (ABCD123
51.13636375%).
