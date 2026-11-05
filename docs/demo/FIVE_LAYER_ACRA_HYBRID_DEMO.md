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
| Synthetic-basis comparison | Same inclusive >= 25% comparator on the declared basis, demonstration only (API field `synthetic_basis_threshold_result`). The UI shows it apart from the formal classification as "Assumed-basis matches" and "Meets the threshold on an assumed basis — review required" |
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
   *Ownership structure* shows **5 layers**, 11 parties and the neutral banner
   **Multi-layer ownership simulation calculated** (D-086, backend
   `simulation_calculated`), followed by a separate explanation that the formal UBO
   classification and readiness remain review-required. The indented hierarchy shows
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

## 7a. Scenario B: OPQ -> GARDEN BUSINESS -> SIM LIM (D-086, explicitly selected)

A separate three-entity demonstration on the same OPQ root. Select it explicitly with
`ACRA_MARKETPLACE_OPQ_SCENARIO=garden_sim_lim_chain` (default `five_layer_simulation`)
together with `ACRA_CONNECTOR_MODE=api_marketplace_mock` and
`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`. Only one OPQ scenario is active
per runtime.

| Level | Entity | Identity evidence | Link to parent |
|---|---|---|---|
| L1 | OPQ PTE. LTD. `201511222D` | Official Marketplace Mock root profile (legal form read as `OTHER`: decoder gap, disclosed) | — |
| L2 | GARDEN BUSINESS `11111999A` | Official profile, `BUSINESS_PARTNERSHIP` (shown as "Business partnership") | **100%, owner-declared** `LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL · owner-declared percentage` |
| L3 | SIM LIM PTE. LTD. `111111111M` | Operation-scoped name from its official shareholder rows (no entity profile) | 62.5%, Garden's owner-supplied register (unchanged) |
| Persons | ABCD123 900 Ordinary, TAN WEI LING 100 Preference, EFGH2345 100 Others (active; withdrawn 10000 excluded) | Official `coShareholdersDetails` rows | `LOCAL_POC_ASSUMED_EQUAL_UNITS` 81.818182 / 9.090909 / 9.090909 |

Effective interests (unchanged engine): ABCD123 51.13636375%, LIM CHOON HUAT 37.5% (via
Garden), TAN WEI LING and EFGH2345 5.681818125% each. The 100% is a demonstration
assumption: no share units exist for it, and it is never an ACRA quantity. The hierarchy
labels the link "owner-declared percentage". Intermediate entities show their engine-path
effective interests (Garden 100%, SIM LIM 62.5%); in the five-layer scenario L2 80%, L3 50%,
L4A 30%, L4B 20% and L5 40% (30% + 10% across the diamond). These are presentation values,
not UBO classifications.

**Readiness (owner decision D-087).** Garden's four official OFFICERS Owner roles (three
current, one ceased) are kept on its discovery record. Scenario B's trusted declaration
names Garden and the `OWNER` role kind as descriptive intermediate context, so with
`ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE=accept_eligible_poc` a fresh case shows
**Ownership calculated — POC basis accepted**, ownership readiness is READY with no
blocker, and the case waits for explicit target confirmation. The formal classifications
stay REVIEW_REQUIRED and nothing is sent automatically. Any other ownership-like role
kind on Garden, or such a role on another issuer, still blocks.

## 7b. OPQ multi-holder: GARDEN BUSINESS 50% and ABC COMPANY 50% (D-088, D-089)

Select it with `ACRA_MARKETPLACE_OPQ_SCENARIO=garden_abc_multi_holder`. This is a separate
variant; the default and the 100% variant are unchanged.

| Level | Entity | Basis |
|---|---|---|
| L1 | OPQ PTE. LTD. `201511222D` | Official Marketplace Mock root (legal form read as `OTHER`) |
| L2 | GARDEN BUSINESS `11111999A` | **50%, owner-declared** `LOCAL_SYNTHETIC_RELATIONSHIP`; Garden's register below is unchanged |
| L2 | ABC COMPANY PTE. LTD. `201688888A` | **50%, owner-declared** `LOCAL_SYNTHETIC_RELATIONSHIP` |
| Person | ABC's individual holder | 1000 of 1000 issued ORDINARY (SGD) from ABC's official businessProfile: `LOCAL_POC_ISSUED_CAPITAL_BASIS · LOCAL · from ACRA Mock business profile` (100%) |

- **Effective interests.** ABC's holder 50%, ABCD123 25.568181875%, LIM CHOON HUAT
  18.75%, TAN WEI LING and EFGH2345 2.8409090625% each.
- **Assumed-basis threshold matches.** ABC's holder and ABCD123.
- **Entity values.** Garden 50%, SIM LIM 31.25%, ABC 50%.
- **Readiness.** With the opt-in POC policy, the case shows **Ownership calculated — POC
  basis accepted**, ownership is READY with no blocker, and it waits for explicit target
  confirmation. Mock GoldTier only.

The businessProfile row returned no status; treating it as current is the recorded D-088
assumption. It applies only because the row exactly equals ABC's single issued class.
The offline transport uses a synthetic holder name in the observed shape.

## 8. Garden under the same concept

With `hybrid_direct_overlay`, Garden `11111999A` keeps its official Marketplace Mock
entity/people facts. The owner-supplied Garden body becomes a direct-only overlay: SIM
LIM 5000 / LIM CHOON HUAT 3000 of 8000 = 62.5% / 37.5%. SIM LIM `111111111M` receives
its own official cache-first lookup. Its entity profile is empty in the Marketplace Mock.
Under D-079, returned official `coShareholdersDetails` rows are retained as
`official_shareholders`.

Under D-081 (owner scope correction), this opt-in lane also distributes SIM LIM's own
current rows as POC equal units:
- each active holder's units are divided by SIM LIM's total active units;
- the existing six-decimal rule applies;
- each link is labelled `LOCAL_POC_ASSUMED_EQUAL_UNITS` / `LOCAL`.

The record keeps outcome `PROVIDER_PARTIAL`, with reason
`OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS`. The `OWNERSHIP_DENOMINATOR_REQUIRED` issue states
that the percentages assume equal POC units, not an ACRA denominator. Every candidate stays
REVIEW_REQUIRED.

Other outcomes:
- rows that cannot support the convention keep reason
  `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE` with no links;
- an empty shareholder result stays `NOT_FOUND` (`OFFICIAL_SHAREHOLDERS_EMPTY`).

The local 900/100/100 fixture is never used here. The default `garden_legacy_supplement`
keeps the accepted flattened Garden result (ABCD123 51.13636375%).

### Reading SIM LIM's retained rows

With official rows present, the ownership graph shows SIM LIM's current holders under it.
Their links read `LOCAL_POC_ASSUMED_EQUAL_UNITS · LOCAL`; Garden's two links read
`LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL`. Withdrawn holders never become links. The record
also appears in these places:

- *Corporate owners from separate registry records* shows SIM LIM as **Incomplete
  registry evidence** with reason `OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS`, or
  `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE` when no links could be derived;
- the issue list contains `OWNERSHIP_DENOMINATOR_REQUIRED` ("… retained without an entity
  profile; current rows mix share classes; percentages shown assume equal POC units, not
  an ACRA denominator.");
- `GET /api/onboarding/cases/{case_id}/ownership` returns, for the `discovery.records[]`
  entry with `registration_number` `111111111M`, the `official_shareholders` rows and
  `official_shareholder_lookup`. Each row has the source id and name, party type,
  category, status, exact `share_allotted`, the source `share_type` and `currency`
  (D-080), `current_interest` (true only for an Active row) and Marketplace Mock
  provenance. The lookup is `SHAREHOLDERS_FETCHED`, or `SHAREHOLDERS_CACHE_REUSED` on
  reuse.

In the bounded Mock read of 2026-10-24, SIM LIM's current rows were 900 Ordinary, 100
Preference and 100 Others, beside a withdrawn corporate row. `coCapitalDetails` for SIM LIM
was empty, so no *verified* denominator exists.

Under the D-081 POC assumption (1100 equal units), the direct links are ABCD123 81.818182%,
TAN WEI LING 9.090909% and EFGH2345 9.090909%. The resulting Garden interests are:
- ABCD123 51.13636375%;
- LIM CHOON HUAT 37.5%;
- TAN WEI LING 5.681818125%;
- EFGH2345 5.681818125%.

All of them are REVIEW_REQUIRED. Pooling the classes is illustrative only; the retained rows
keep their true classes.

In the Ownership & UBO explorer, **Provisional UBOs** stays 0 and **Assumed-basis matches**
shows 2. The section **Meets the threshold on an assumed basis — review required** lists:
- ABCD123 51.14% (POC equal-unit assumption);
- LIM CHOON HUAT 37.5% (Local synthetic overlay basis).

The selected holder shows the assumed-basis comparison (MET) apart from the formal
INDETERMINATE result. Review & Send shows the same section. The five-layer case lists
BEATRICE LIM and DIANA KOH the same way.

The hierarchy labels the client "Root entity — N/A" and SIM LIM "62.5% — direct holding in
client". Deeper or multi-path corporate holders show "Not calculated…"; no company interest
is calculated in the browser. For this POC case the banner reads **Ownership calculated —
verification required**. Any unresolved, conflicting or structural issue keeps the general
"Partial or disputed ownership evidence" warning.

The POC percentages cannot clear the ownership blocker (owner F1 decision). On this case,
**Keep current ownership evidence** is refused with `409
OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED`. So is submitting the pre-filled POC values
unchanged as a declaration, including under new party IDs or after other declarations
(D-120). Nothing is replaced, and readiness stays blocked. Clearing the blocker needs
selected current document observations, which may state the same values, or a corrected
declaration, under the existing rules. Selected rows stay client-stated evidence; they are
not verified ownership.

**Optional POC acceptance policy (D-085).** To show Garden reaching final review without
manual ownership verification, also set
`ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE=accept_eligible_poc` (default `disabled`). No
other setting is needed; the D-082 officer-role key/allowlist settings were removed and are
ignored if still present. Then onboard a **new** Garden case. Existing cases (including
D-082-accepted ones) are never accepted retroactively. The five-layer scenario declares no
POC acceptance and stays under ordinary review.
- The Ownership & UBO status reads **Ownership calculated — POC basis accepted**, and the
  explorer shows "Calculated — POC basis accepted".
- The analysis stays REVIEW_REQUIRED, with 0 provisional UBOs and 2 assumed-basis matches.
- Readiness shows no blockers. Final review & send still requires the explicit **Confirm
  and send to Mock GoldTier**, and the Mock snapshot carries no provisional UBO ids.
- Garden's four official OFFICERS Owner role records (three current, one ceased) are kept
  unchanged as descriptive context under the scenario's declared
  `DESCRIPTIVE_OFFICER_ROLES` assumption. They do not corroborate the synthetic
  shareholder links.
- The manual form stays available, and the Option B refusals above still apply.

Restarting without the setting, or outside the hybrid lane, revokes readiness:
- the ownership blocker returns;
- confirmation is refused;
- resume restores the ordinary ownership hold.

After re-enabling, the next resume of the case (the existing
`POST /api/clm/zero-touch/cases/<case_id>/resume` operation) returns it to target
confirmation. Until then it shows the ordinary ownership hold.

The unchanged UI does not render the retained rows themselves. To read them, open the signed-in app tab's
browser developer tools and inspect the ownership response in the Network panel, or run
this in its console:

```js
fetch("/api/onboarding/cases/<case_id>/ownership").then((r) => r.json()).then((o) => o.discovery.records)
```

### Seeing D-079 on an existing case

A case keeps the ownership analysis it was given. A backend restart or reopening the
page never re-analyses it, and `ownership/load` is refused with `OWNERSHIP_ALREADY_LOADED`
unless the case's documents or identity changed. So a Garden case analysed before D-079
still shows SIM LIM as `NOT_FOUND`. That does not show that D-079 failed. Likewise, a
case analysed under D-079 keeps its rows with no share class. To see the current
behaviour, create a **new** Garden case; the old case and its history stay unchanged.
A D-079 shareholder cache entry is never reused under D-080, so the first new case makes
one fresh shareholder read.

The new case reuses fresh cache entries. SIM LIM's empty entity profile is a negative
cache entry (600 s by default), COMPLETE shareholder evidence follows the registry
freshness window (90 days by default), and an empty shareholder result is negative-cached
like the profile. In memory persistence, cases and caches are lost on restart; the
explicit Mongo mode keeps both.
