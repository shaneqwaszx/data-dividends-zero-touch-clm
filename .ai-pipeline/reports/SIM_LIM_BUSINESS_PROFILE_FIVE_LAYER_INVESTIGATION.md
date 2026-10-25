# Business Profile and five-layer evidence authenticity — investigation

Read-only investigation, 2026-10-24. No product content changed. The only credentialed
requests were the owner-approved probe P-A (1 token + 2 GETs, §Probe P-A). It is not a QG
verdict.

**Status:** `OWNER TECHNICAL DECISION PENDING`. D-080 publication stays on hold.

## Identity (unchanged)

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024`.
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`.
- HEAD = `origin/main` = `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`; nothing staged; 38 modified
  paths.
- Reviewed product tree, recomputed: **`5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`**. This
  matches the independent re-QG PASS. This report sits outside it.

## Inputs read

The two owner-supplied ACRA documents (private, git-ignored; inspected in memory, nothing
copied into tracked files):
1. **Business Profile API Specifications Document v1.0** (34 pages, version 1.0, 18 Nov
   2025). It contains **response parameters only**, for six entity types: Business, LLP, LP,
   PAF, Company, Foreign Company. It gives no endpoint path, request parameters,
   authentication, error schema, cardinality rules or sample UENs.
2. **SAMPLE_DATA_ENTITY_INFORMATION_QUERY** (7 pages, last updated 18 Nov 2025). This is
   the per-operation sample index already used by D-077.

The supplied Postman collection (`JSON_COLLECTION_ENTITY_INFORMATION_QUERY.zip`) was read
only for request names, paths and sample `uen` values. It has no saved example responses.

## Documented vs implemented vs observed

| Operation | Documented in | Runtime implementation | Sample UENs (Postman/catalogue) | Observed live |
|---|---|---|---|---|
| `entityBasicInformation` | Postman; catalogue p.6 | **Yes** (identity + officers) | `11111999A`, `201511222D`, `T13FC1122A`, `T15LL1111W`, `T17LP1111A`, `T19PF1111A` | Same-UEN profiles for all six (Phase 24, 2026-10-01/02). Empty for `111111111M`, `333333333C`, `222222222C`, `111111111K` and five-layer L2–L5 |
| `coShareholdersDetails` | Postman; catalogue p.5 | **Yes** (D-079/D-080) | `111111111M`, `333333333C`, `222222222C`. Postman also shows `appointmentStatus` and `shareType` filters | SIM LIM: 4 rows (2026-10-24) |
| `coCapitalDetails` | Postman; catalogue p.4 | **No.** Called only by `scripts/acra_marketplace_mock_smoke.py` (`111111111K`) and this session's bounded probe | `111111111K` only | `111111111K`: same-UEN, schema only (2026-09-26). `111111111M`: HTTP 200, empty (2026-10-24) |
| `businessProfile` | **BP spec** (fields only); Postman `GET {base}/entityQuery/businessProfile` | **No.** Only a dormant URL builder (`AcraBizfileConnection.business_profile_endpoint`, "no connector operation calls it") | Company `201688888A`; Business `16888888A`; FC `T16FC0001L`; LLP `T08LL8888Z`; LP `T09LP8888Z`; PAF `S88PF8888A` | Probe P-A (2026-10-24): `111111111M` empty; `201688888A` same-UEN company record with capital |
| `entityVerification`, `entityForeignRedom`, `coFyeLlpAnnualDeclaration` | Postman; catalogue p.1–5 | **No** | Company samples `200811111M`, `200811111K`, `199801111H` (five-layer L2, L4A, L4B) | Never called |

The BP spec's Company section documents (p.25, 27–28):
- `issuedShareCapital.{amount, numberOfShares, currency, shareType}`;
- `paidUpCapital.{amount, numberOfShares, currency, shareType}`;
- `ordinarySharesHeldAsTreasuryShares.{numberOfShares, currency}`;
- `shareholder.{numberOfShares, numberOfShares.type, currency, category, id}`;
- `groupShare.*`.

It does **not** document:
- whether capital is a per-class list;
- an "as at" date for capital, beyond AGM/annual return dates;
- a shareholder active/withdrawn status;
- any class voting, dividend or capital rights.

## Probe P-A (owner-approved, executed once, 2026-10-24)

A scratch script dry-run offline first. Bounds:
- the fixed official Mock host and `/entityQuery/businessProfile` only;
- UENs `111111111M` then `201688888A` only;
- caps of 1 token and 2 GETs, checked before dispatch;
- verified TLS, no proxy inheritance, no redirects;
- only the two named keys read in memory.

The output is sanitized: no names, identifiers, addresses or raw bodies. A credential-pattern
scan of the output was clean. **Genuine requests: 1 token POST + 2 GETs, all HTTP 200.**

| UEN | Result | Capital | Shareholders |
|---|---|---|---|
| `111111111M` (SIM LIM) | HTTP 200, `application/json`, 15 bytes, `entities` empty | None | None |
| `201688888A` (BP Company sample; five-layer L3) | HTTP 200, 1404 bytes, 1 entity, returned UEN equals requested, 59 field paths | `issuedShareCapital` is a list of 1: 1000 shares, amount 1000, SINGAPORE DOLLAR, ORDINARY. `paidUpCapital` is identical. No treasury-share block | 1 row: Individual, 1000, ORDINARY, SINGAPORE DOLLAR |

Contract facts observed, beyond the specification:
- capital is an **array** (per-class entries are possible);
- shareholder rows carry `shareType`, where the spec says `numberOfShares.type`;
- share counts and amounts are **JSON numbers that decode as floats** (1000.0). The project's
  strict decoders reject float share counts, so exact-Decimal ingestion would need its own
  contract handling;
- the class vocabulary is **upper-case** ("ORDINARY"), while `coShareholdersDetails` uses
  "Ordinary", "Preference" and "Others". Cross-operation class matching would need an
  authorized vocabulary mapping.

`201688888A` is internally coherent. Issued ORDINARY shares (1000) equal paid-up shares and the
sole holder's 1000 ORDINARY. That is a same-issuer, same-class, same-operation tuple, so
within that class a share-count proportion of 100% is arithmetically defined. It is a
**different issuer**, though, and must never be combined with SIM LIM. It also arrives only
through an unimplemented operation. No date is supplied for the capital figures.

Cumulative genuine requests this session: 3 token POSTs + 9 GETs (7 earlier + 2 here).

## Matrix A — SIM LIM `111111111M`

| Operation | Real response | Numerator | Share class | Available denominator | Calculation admissibility | Remaining blockers |
|---|---|---|---|---|---|---|
| `entityBasicInformation` | HTTP 200, explicit empty `entities` (Phase 24 and 2026-10-24) | — | — | — | Not applicable: no official identity | Not a basic-information sample UEN |
| `coShareholdersDetails` | HTTP 200, 1 entity, UEN bound, 4 rows (2026-10-24, twice) | FGH SERVICES, INC. 10000 (Withdrawn, no current interest); 900 / 100 / 100 Active | Ordinary (withdrawn row); Ordinary / Preference / Others (active rows) | None in this response | Units retained (D-079/D-080); **no percentage** | No issued total; three classes |
| `coCapitalDetails` | HTTP 200, explicit empty `entities` (one fully recorded read; one status unrecorded) | — | — | **None for this UEN** | — | Dataset limitation: the only capital sample is `111111111K`. It must not be combined |
| `businessProfile` | HTTP 200, explicit empty `entities` (probe P-A, 2026-10-24) | — | — | **None for this UEN** | — | Dataset limitation (not a BP sample). The operation is also unimplemented, and the spec lacks dates/rights; Q-012 |
| Any combination | — | 900 Ordinary is the only Ordinary active holding | Mixed | Would need a same-UEN, same-class, same-date issued `numberOfShares`, net of treasury shares for Ordinary | **Inadmissible today** | No denominator. Class rights undocumented (Q-004) |

Answers A1–A7:
1. **No.** The implemented operations do not expose the BP Company capital fields. The
   decoders read none, and BP is a separate operation.
2. **Yes, different.** `businessProfile` is a distinct endpoint with an entity-type-specific
   response, unlike `entityBasicInformation`, `coShareholdersDetails` and `coCapitalDetails`.
3. **No (observed).** Probe P-A got HTTP 200 with an explicit empty collection for
   `111111111M`.
4. **Not for SIM LIM.** It has no capital record on any operation. Structurally, BP returns
   `issuedShareCapital` as a **list**: the `201688888A` sample had one ORDINARY entry. So
   per-class entries are possible, but multi-class behaviour has not been observed.
5. **Not established.** No source documents class rights. At most, a within-class
   share-count proportion could be described. Here each class has exactly one active holder
   and no class total, so even that is unavailable.
6. **Dataset limitation, not an operation mismatch.** It is the same `coCapitalDetails` path
   that returned a same-UEN capital body for its sample `111111111K`. Business Profile is
   empty for `111111111M` too.
7. **No.** No matched issuer + class + currency + date + completeness tuple exists. The only
   capital record (`111111111K`) belongs to another issuer.

## Matrix B — five-layer `FIVE_LAYER_MARKETPLACE_HYBRID_V1`

Common to all levels:
- **Operation called:** `entityBasicInformation` only. No other runtime identity operation
  exists.
- **Genuine HTTPS so far:** two bounded *probes*, not application onboardings:
  - Phase 24 (2026-10-01/02);
  - D-077 closeout (2026-10-23, 1 token + 10 GETs).
  The five-layer onboarding has only ever run on the offline protocol transport.
- **Offline transport:** returns a synthetic same-UEN root profile, including a visibly
  synthetic address, and an empty answer for L2–L5.
- **Relationships:** every edge and denominator is local synthetic
  (`LOCAL_SYNTHETIC_RELATIONSHIP`), from `hybrid_ownership_overlay.py`. All six persons are
  synthetic.
- **Calculation source:** the single Decimal engine over the declared units. The result is
  always REVIEW_REQUIRED/INDETERMINATE, with a labelled `synthetic_basis_threshold_result`.

| Level | UEN | Catalogue operation for this UEN | Official same-UEN profile (live probe) | Official name / legal form | Local identity substituted | Disposition (offline counters) | Officially identified? |
|---|---|---|---|---|---|---|---|
| L1 root | `201511222D` | `entityBasicInformation` | **Yes** (Phase 24 + 2026-10-23) | Name not recorded by the probe (catalogue: OPQ PTE. LTD.); legal form `OTHER` (no constitution value) | No (`OFFICIAL_MOCK_ENTITY_PROFILE`) | Root acquisition, 2 GETs; then cached | **Identity yes**; legal form unclassified. Live onboarding not run; it may stop at `CANONICAL_DATA_INCOMPLETE` (no official address observed) |
| L2 | `200811111M` | `entityVerification` / directory / key dates | **No**: explicit empty (2026-10-23) | — | **Yes**: `LOCAL_SYNTHETIC_IDENTITY`, name "FIVE LAYER L2 HOLDINGS (SYNTHETIC)" | 1 GET, then negative cache (600 s) | **No** |
| L3 | `201688888A` | `businessProfile` | **No**: empty | — | **Yes** ("… L3 INVESTMENTS (SYNTHETIC)") | 1 GET, then negative cache | **No** |
| L4A | `200811111K` | `entityForeignRedom` | **No**: empty | — | **Yes** ("… L4A CAPITAL (SYNTHETIC)") | 1 GET, then negative cache | **No** |
| L4B | `199801111H` | `coFyeLlpAnnualDeclaration` | **No**: empty | — | **Yes** ("… L4B VENTURES (SYNTHETIC)") | 1 GET, then negative cache | **No** |
| L5 | `111111111K` | `coCapitalDetails` | **No**: empty (Phase 24 + 2026-10-23) | — | **Yes** ("… L5 HOLDCO (SYNTHETIC)") | 1 GET (diamond: acquired once), then negative cache | **No** |

**The claim "only the relationships are synthetic" is false.** These are synthetic:
- the relationships and percentages;
- the identities and names of L2–L5;
- all six persons.

The L2–L5 UENs are genuine catalogue identifiers, but for other operations. Their
`entityBasicInformation` answer is empty, and D-077 then substitutes
`LOCAL_SYNTHETIC_IDENTITY` (`ownership_discovery.py`, `_attach_overlay`). This is labelled
in three ways:
- the API fields `identity_basis` / `official_entity_lookup`;
- the "(SYNTHETIC)" display names;
- the `SYNTHETIC_OWNERSHIP_EVIDENCE` issue.

D-077 approved it, and the demo guide §1/§3 states "Official identity: Root only". It is
not a code defect. It does, however, contradict the stated intended architecture
("entity records must not silently become synthetic"). D-077 closeout limitation 1
records that the unchanged UI caption reads as if each owner came from its own registry
record.

## Investigation C — feasibility

**Result: `NOT_FEASIBLE_WITH_VERIFIED_SAMPLE_DATA`** for five corporate layers with genuine
official identity at every level under the existing supported operation.

| Option | Official identity source | Verified data | Assessment |
|---|---|---|---|
| C1. Five local companies via `entityBasicInformation` | Supported op | Only **one** local company returns a profile (`201511222D`) | Not feasible |
| C2. Five official entities of mixed types via `entityBasicInformation`: `201511222D` company, `T13FC1122A` foreign-company branch, `T15LL1111W` LLP, `T17LP1111A` LP, `T19PF1111A` PAF | Supported op; same-UEN profiles observed 2026-10-01/02 | 5 identities. Re-verification advisable: about 3 weeks old, and every classifier result was `OTHER` or `BUSINESS_PARTNERSHIP` | Technically possible as a whitelist/data change. **Not recommended:** LPs, PAFs and partnerships are not bodies corporate, and a branch is not a separate legal person. Showing them as share-holding parents would be fiction about entity type, not just about links |
| C3. Keep the L2–L5 UENs and identify each through its own operation (`entityVerification`, `businessProfile`, `entityForeignRedom`, `coFyeLlpAnnualDeclaration`, `coCapitalDetails`) | **Four or five new provider operations** | L3 `201688888A` now has an observed same-UEN BP company record (P-A). The others are unobserved, except capital schema for `111111111K` | Needs new operations, decoders, contract reconciliation (Q-012) and a data-source policy. It also conflicts with the recorded rule "sample catalogue is operation-specific; do not combine identifiers across operations". Owner decision |

## Conclusions

1. **Why lookup succeeds but percentages stay unavailable:** `coShareholdersDetails` has a
   sample for `111111111M` and returns validated per-holder counts. No operation returns a
   same-entity issued-share total for that UEN, and the three current holdings are in three
   classes with undocumented rights.
2. **Business Profile:** for SIM LIM, observed empty. It is a real capital-and-shareholder
   source for its own sample company (`201688888A`), but on an unimplemented operation, with
   float-typed counts and an upper-case class vocabulary. So it is not a usable denominator
   for SIM LIM, and is only a candidate future source for other issuers.
3. **Five-layer design vs intent:** it does not satisfy the real-entity-plus-synthetic-
   relationship architecture. Only L1's identity is official.
4. **Smallest justified improvement:**
   - **Code:** none. No defect was found against approved scope, and the reviewed tree is
     unchanged.
   - **Evidence:** one bounded read-only probe (below) would replace inference A3/A4 with
     observation.
   - **Documentation (optional):** refresh demo guide §2's stale "Never probed /
     NOT_RUN_CREDENTIALS" columns with the 2026-10-23 probe results. That changes reviewed
     content and needs a re-QG; it was previously left unchanged by owner choice.
5. **Owner decisions required:** see the next section.
6. **Content identity:** unchanged, `5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`.

## Owner decisions requested

- **D1. Bounded read-only probes.**
  - *P-A: EXECUTED (owner-approved); results above.* 1 token + 2 GETs, `businessProfile?uen=111111111M` and
    `businessProfile?uen=201688888A`.
    - Purpose: does SIM LIM have any BP capital record, and what is the BP Company capital
      shape (per-class list or single, `shareType` values, treasury fields)?
    - Sanitized output: status, entity count, UEN binding, capital field paths, class
      labels, share counts.
  - *P-B (only if C3 is of interest):* +4 GETs, one each to
    `entityVerification?uen=200811111M`, `entityForeignRedom?uen=200811111K`,
    `coFyeLlpAnnualDeclaration?uen=199801111H` and `coCapitalDetails?uen=111111111K`.
    - Purpose: record whether each returns a same-UEN name/type usable as identity.
  - *P-C (only if C2 is of interest):* +4 GETs, `entityBasicInformation` for `T13FC1122A`,
    `T15LL1111W`, `T17LP1111A`, `T19PF1111A`.
    - Purpose: re-verify identities and raw constitution values.
- **D2. Five-layer direction:**
  - keep D-077 as is (root official, rest labelled synthetic);
  - C2 mixed-type official entities (not recommended);
  - C3 new identity operations (new provider contract work);
  - or retire the five-layer scenario.
- **D3. Any denominator policy** (BP-sourced, assumed or per-class) needs a separate decision
  plus sponsor input on class rights (Q-004) and Marketplace semantics (Q-012).
- **D4. D-080 publication:** still on hold. The re-QG PASS stays valid while the tree is
  `5dfa844…`.
