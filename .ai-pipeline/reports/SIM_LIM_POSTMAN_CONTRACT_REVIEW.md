# Postman ACRA API contract review — Sim Lim and five-layer identity

Read-only review, 2026-10-24. There was no product change. The only external requests were the
owner-approved Tier 1 probe (§Tier 1 results). It is not a QG verdict.

**Status:** `OWNER TECHNICAL DECISION PENDING`. Stage 4 is not authorized.

## Identity (unchanged)

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`.
- HEAD = `origin/main` = `ceefe1e`; nothing staged.
- Reviewed product tree, recomputed: **`5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`**. This
  matches the independent re-QG PASS. All reports, including this one, are outside it.

## Inputs and handling

Teammate files, read in place under `Downloads\Telegram Desktop`, with nothing copied into
the repository:
- **`JSON_COLLECTION_ENTITY_INFORMATION_QUERY (2).zip`:** byte-identical (same SHA-256, 26742
  bytes) to the collection already reviewed from `private/sponsor-artifacts-v2/`.
- **The standalone `Company Shareholders Details` and `Entity Basic Information`
  collections:** request-for-request identical to their copies inside the ZIP.
- **None of the collections contains saved example responses.**
- **`APIMarketplace-Mock.postman_environment.json`:** holds an exported
  `acra.api.oauth2.token` (type `secret`, exported 2024-05-13). Attaching the file loaded it
  into the assistant's context. The value was never repeated, logged, copied or used.
  Recommendation: revoke/rotate it if it could still be valid, and do not store the file in
  the repository. Its only non-secret metadata is the base paths, which equal the
  connector's fixed constants.
- **Future authorized requests** will use only the project's approved mechanism: the two
  named Marketplace keys, read in memory, with a fresh OAuth token.

## Investigation A — Sim Lim `111111111M`

| # | Question | Finding (source) |
|---|---|---|
| 1 | Same effective query? | **Yes.** Postman "Company Profile with Shareholders" enables only `uen=111111111M`, with header `token`. `name`, `appointmentStatus` and `shareType` are disabled. The connector sends only `urlencode({'uen': uen})` with headers `{token, Accept}` (`acra_api_marketplace_mock.py:69-72, 109-111`) |
| 2 | Do the filters change the obtainable evidence? | **They only narrow it.** `appointmentStatus=ACTIVE` (valid example; `AC` gives E1012) would drop withdrawn rows. `shareType=ORDINARY` (valid; `ORD` gives E1012) would return one class only. `name` is an alternative lookup key: E1012 requests use `name` without `uen`, and `uen` + `name` together is labelled E1001, whose semantics are undocumented. No filter adds a denominator or any new field. Using one would make the retained collection deliberately partial, so D-080 rightly requests unfiltered. The request vocabulary is upper-case (`ACTIVE`, `ORDINARY`), while the response labels are "Active" / "Ordinary" |
| 3 | Can another *supported* operation bind Sim Lim's legal identity? | **Only as operation evidence** (Tier 1 G1: the shareholder response itself returns name "SIM LIM PTE. LTD." and companyType "PRIVATE COMPANY LIMITED BY SHARES"). **No profile.** The runtime implements only `entityBasicInformation` (empty for `111111111M`) and `coShareholdersDetails`. The shareholder response's entity `uen` is strictly bound, and its `name` is required non-blank but not retained, so it is an operation-specific echo, not an entity profile. Among *unimplemented* operations, `businessProfile` is observed empty for `111111111M`, and `111111111M` is not a sample for `entityVerification`/`entitySearch` |
| 4 | Same-UEN, same-class issued-share denominator? | **No.** `coShareholdersDetails` carries no issued totals. `coCapitalDetails` and `businessProfile` for `111111111M` are both empty (observed) |
| 5 | Do the differing sample names contradict the issuer identity? | **Yes, if operations were combined.** The Postman shareholder sample names `111111111M` "SIM LIM PTE. LTD.". The catalogue lists the same UEN under five other company names for address/SSIC/constitution, name history, officers, charges and liquidator operations. The UEN is a reused placeholder, not one coherent issuer, so any cross-operation identity fusion for it must fail closed. D-079/D-080 are unaffected: they bind rows by UEN within the shareholder operation only and create no identity. The "SIM LIM PTE. LTD." display name comes from the local Garden overlay declaration. It is consistent with the Postman sample name, but not read from the official response |
| 6 | Are the four observations retained correctly? | **Yes.** The four rows are retained with exact units, status, `current_interest` (Active only), source share class and currency, under the issuer UEN with operation provenance. There is no edge or percentage. Evidence: live D-079 run, offline D-080 tests, and the independent re-QG PASS on `5dfa844`. The one unretained datum is the response's entity `name` (see C-2) |

## Investigation B — five-layer candidate operations

Common to every row: none of these operations is implemented, none is observed except
where stated, and there are no saved example responses. Identity tier is defined as:
- **PROFILE:** an entity-level record (name, type, status and address);
- **VERIFICATION:** a validity, name and type assertion;
- **ECHO:** UEN and name returned only as context for operation-specific data.

| Level / UEN | Operation (Postman parameters) | Postman/catalogue context | Expected identity tier | Quantitative content | Conflict with the D-077 declaration |
|---|---|---|---|---|---|
| L2 `200811111M` | `entityVerification` (`uen`; `name` optional) | Company Profile sample; a "validity false" variant exists (`T12UL2222D`) | **VERIFICATION** (likely), unobserved | None | None expected |
| L2 `200811111M` | `entitySearch` (`uen`; `name` optional; `fbrn` variant) | Same sample UEN as verification | ECHO / directory, unobserved | None | None expected |
| L3 `201688888A` | `businessProfile` (`uen`) | Company sample; **observed** (P-A): same UEN, 59 fields | **PROFILE.** Identity fields (`entityName`, `companyType`, `statusOfCompany`) were present but not recorded by P-A | **Official**: issued = paid-up = 1000 ORDINARY; one individual holds 1000 ORDINARY | **Yes.** D-077 declares L3's holders as L4A 600 + L4B 400 of 1000. The official record says one individual holds all 1000. The safety rule (`OFFICIAL_QUANTITY_PRECLUDES_OVERLAY`) would refuse the overlay, and must keep refusing it. So L3 cannot have official identity **and** synthetic links |
| L4A `200811111K` | `entityForeignRedom` (`uen`; **`comType=REDOM` enabled**) | Redomiciled-company sample | ECHO (redomiciliation particulars), unobserved | None | None expected |
| L4B `199801111H` | `coFyeLlpAnnualDeclaration` (`uen`; `name`/`type=COM` optional) | Company FYE sample | ECHO (FYE/AGM/annual-return dates), unobserved | None | None expected |
| L5 `111111111K` | `coCapitalDetails` (`uen`; `name` optional) | Capital sample. **Not empty:** same-UEN capital body observed 2026-09-26 (schema only, no values recorded). Only its `entityBasicInformation` is empty | ECHO | **Official capital**: issued/paid-up by share type, values unrecorded | **Possible.** D-077 declares a local 1000-unit denominator for L5. An official issued total that differs would contradict it, and the current safety rule covers official shareholder rows only, not capital |

FGH SERVICES, INC. (SIM LIM's withdrawn corporate holder) appears in the
`entitySearch`/`entityVerification` samples as unregistered foreign entity `T16UF3333A`, FBRN
`US-C1234567`. The live row had a 10-character UEN-shaped identifier and an FBRN field. That
is consistent with this, but the value was not recorded. The row is withdrawn and foreign, so
nothing changes.

## Tier 1 results (owner-approved, executed once, 2026-10-24)

A scratch script dry-ran offline first. That dry run caught a sanitizer leak (`shareholderId` and
`shareholderName` keys matched the "share" filter). It was fixed with an explicit block on name,
ID and FBRN keys before any live call.

Bounds:
- a fixed, ordered allowlist of 5 (operation, UEN) pairs;
- only the `uen` query key;
- caps of 1 token and 5 GETs, checked before dispatch;
- verified TLS, no proxy inheritance, no redirects;
- only the two named keys read in memory; the Postman token was not used.

**Genuine requests: 1 token POST + 5 GETs, all HTTP 200.** A credential-pattern scan of the
output was clean, and no person names or identifiers were printed.

| # | Request | Result | Identity evidence | Quantitative evidence |
|---|---|---|---|---|
| G1 | `coShareholdersDetails?uen=111111111M` | 1278 bytes, 1 entity, UEN bound; entity keys `uen, name, companyType, shareholders` | **name "SIM LIM PTE. LTD."; companyType "PRIVATE COMPANY LIMITED BY SHARES"** (the current decoder ignores `companyType`) | 4 rows unchanged, matching D-080 exactly. `grouping` empty |
| G3 | `entityVerification?uen=200811111M` | 86 bytes. **Flat object, no `entities` wrapper**, with keys `uen, name, entityType, isValid` | VERIFICATION-tier *shape* confirmed. **Values not recorded**: the script extracted identity values only from `entities[0]` (a reporting gap) | None |
| G7 | `coCapitalDetails?uen=111111111K` | 589 bytes, 1 entity, UEN bound; keys `uen, name, shareDetails` | name "ABC PTE. LTD."; no type/status (ECHO tier) | `shareDetails` has 4 per-class rows: Treasury 0/0, Others 0/0, Preference 0/0, **Ordinary issued 50,002,606.14 / allotted 50,002,606.14**. Currency string "SINGAPORE, DOLLARS" |
| G8 | `businessProfile?uen=201688888A` | 1404 bytes, 1 entity, UEN bound, 58 field paths | **entityName "ABC COMPANY PTE. LTD."; companyType "EXEMPT PRIVATE COMPANY LIMITED BY SHARES"; statusOfCompany "LIVE COMPANY"**; registered office present (type Local); officer list present (PROFILE tier) | Issued = paid-up = 1000 ORDINARY; 1 individual holds 1000 ORDINARY |
| G9 | `entityVerification?uen=111111111M` | 17 bytes, only key `isValid` | **No name and no type.** 17 bytes equals `{"isValid":false}`, an inference from length, since the value was not printed | None |

What the results establish:
- **SIM LIM.** Its own shareholder operation asserts the company's name and company type, so
  the declared name is now officially echoed. Verification for its UEN returns no identity
  (most likely invalid). Business Profile, basic information and capital are all empty. So
  the name and type stand only as **shareholder-operation evidence**, with no profile and no
  denominator. Other operations' samples name the same UEN differently, so the placeholder
  contradiction stands.
- **L2 `200811111M`.** Verification returns exactly the VERIFICATION-tier fields; the values
  remain to be recorded.
- **L3 `201688888A`.** Confirmed as a PROFILE-tier company with official holdings (one
  individual holds 1000 of 1000 ORDINARY), which contradicts the D-077 synthetic links
  (600 / 400).
- **L5 `111111111K`.** Official per-class capital exists: Ordinary 50,002,606.14 issued and
  allotted, others zero. That contradicts the declared local 1000-unit denominator. The
  non-integer "shareAllotted" suggests the figure may be an amount rather than a share
  count. Either way it is not a share count usable with the declared units. ECHO-tier
  identity only.
- **Vocabulary differs across operations.** Class labels appear as "Ordinary" and
  "ORDINARY". Currency appears as "SINGAPORE DOLLAR" and "SINGAPORE, DOLLARS". Response
  envelopes differ too: `entities` list vs a flat object. Any normalization needs explicit
  per-operation mapping.

Cumulative genuine requests this session: 4 token POSTs + 14 GETs.

## Investigation C — recommendations

1. **Operations worth integrating, in order.**
   - **`businessProfile`.** It is the only operation that returns a profile-grade company
     identity *and* a same-issuer, same-class capital/shareholder tuple in one response. Its
     contract gaps need handling: the spec gives no endpoint (Postman supplies the path);
     counts arrive as floats; the class vocabulary is upper-case; capital has no "as at"
     date; and it is entity-type-specific.
   - **`entityVerification`.** A lightweight identity assertion (validity, name, type).
   - The others (`entitySearch`, `entityForeignRedom`, `coFyeLlpAnnualDeclaration`) carry
     only narrow, operation-specific data and are not identity sources.
   - `coCapitalDetails` matters only as a denominator. No catalogue issuer has both a
     `coShareholdersDetails` sample and a `coCapitalDetails` sample, so it cannot complete any
     shareholder numerator in the Mock.
2. **Identity normalization without invention.** Keep a separate *operation-specific identity
   assertion* holding:
   - UEN, returned name, returned type code and validity flag, but only if present;
   - operation, time and provenance.

   The rules for using assertions:
   - Never synthesize the canonical entity profile from an assertion.
   - Never derive legal form from a name or a sample category. Use only an explicit type field
     through an owner-approved vocabulary map, otherwise `UNKNOWN`.
   - Require same-UEN binding.
   - Treat different names for the same UEN across operations as `IDENTITY_CONFLICT`
     (fail closed, review). The `111111111M` placeholder shows this case is real.
   - Record a tier (PROFILE, VERIFICATION or ECHO), and allow an overlay only at VERIFICATION
     tier or above.
   - Extend the precluding rule: an official capital denominator that disagrees with a
     declared synthetic denominator also refuses the overlay.
3. **Can the five-layer demo meet the target design (verified company records at every level,
   synthetic links only)?** **Not with the current L1–L5.**
   - L3's official holdings conflict with the synthetic links.
   - L4A, L4B and L5 are at best ECHO tier.
   - L2 is at best VERIFICATION, and unobserved.

   Under the current supported operations it remains `NOT_FEASIBLE_WITH_VERIFIED_SAMPLE_DATA`.
4. **A better UEN selection is available**, pending probe confirmation and owner acceptance of
   *bodies corporate* rather than Singapore companies only:
   - L1 `201511222D` (company, PROFILE via `entityBasicInformation`);
   - an LLP `T15LL1111W` (PROFILE);
   - a foreign-company branch `T13FC1122A` (PROFILE);
   - `200811111M` (company, VERIFICATION);
   - `201688888A` (company, PROFILE via `businessProfile`) as the **bottom** level.

   At the bottom, its official individual holder becomes a genuine official leaf: 1000 of 1000
   ORDINARY, same issuer, same class. That leaf needs an owner/sponsor denominator decision
   (Q-012). The four upper links stay synthetic. This gives officially identified entities at
   every level with no conflict, but it needs two new operations and a denominator policy.
   With Singapore companies only, three levels (`201511222D` ← `200811111M` ← `201688888A`) is
   the most the verified data supports.
5. **Preserve D-080 unchanged.** That covers:
   - share-class and currency retention;
   - the `MARKETPLACE_SHAREHOLDERS_V2` key and cache schema 4;
   - case envelope 14;
   - the D-079 trigger and retention;
   - all tests and docs.

   Its request matches the Postman contract. The only optional later addition is retaining the
   shareholder response's entity name as an ECHO assertion, which belongs to item 2's design
   rather than to D-080.

## Bounded probe plan (not executed — owner approval required)

All reads: official Mock host only, read-only GET, verified TLS, no proxy, no redirects,
10 s timeout. Hard caps are checked before dispatch, and the approved credential mechanism is
used, never the Postman token.

The sanitized output records:
- status, content type, bytes, entity count and UEN binding;
- field paths (keys only);
- **company-level** identity values: entity name, type/company type, status and validity;
- capital per class: shares, amount, currency and type;
- shareholder rows as counts by category, class and units only.

It records no person names, identifiers, addresses or raw bodies.

| # | Operation and query | Purpose | Expected characteristics |
|---|---|---|---|
| G1 | `coShareholdersDetails?uen=111111111M` | Is the response entity name "SIM LIM PTE. LTD."? Are rows unchanged (4; classes as D-080)? | 200, 1 entity, same UEN, 4 rows |
| G2 | `coShareholdersDetails?uen=111111111M&shareType=ORDINARY` | Does the upper-case request enum select the "Ordinary" rows (class equivalence)? | 200, 2 rows expected (withdrawn and the 900 holding) |
| G3 | `entityVerification?uen=200811111M` | L2 identity tier: validity, name, type | 200, 1 entity, same UEN |
| G4 | `entitySearch?uen=200811111M` | L2 directory shape vs verification | 200, 1 entity |
| G5 | `entityForeignRedom?uen=200811111K&comType=REDOM` | L4A: identity echo or narrower | 200, 1 entity |
| G6 | `coFyeLlpAnnualDeclaration?uen=199801111H` | L4B: identity echo or narrower | 200, 1 entity |
| G7 | `coCapitalDetails?uen=111111111K` | L5 capital values per class; conflict with the declared 1000-unit denominator? | 200, 1 entity, capital array |
| G8 | `businessProfile?uen=201688888A` | L3 identity fields (entity name, company type, status) left unrecorded by P-A | 200, 1 entity |
| G9 | `entityVerification?uen=111111111M` | Does any verification exist for SIM LIM's UEN, and under which name? | 200, empty expected (not a sample) |

Request budget:
- **Tier 1 (recommended):** G1, G3, G7, G8, G9, at most **1 token + 5 GETs**.
- **Full:** G1–G9, at most **1 token + 9 GETs**.

## Smallest recommended next action

Tier 1 is done. Now decide:
- the identity-normalization design (C-2). It is now evidenced by three envelope/vocabulary
  variants and SIM LIM's shareholder-operation identity;
- the five-layer direction (C-3/C-4). L3 and L5 official evidence now **conflicts** with the
  current synthetic links and denominator, so the current L1–L5 cannot become "official
  identity + synthetic links" without overriding official evidence. That stays prohibited;
- optionally, one GET (`entityVerification?uen=200811111M`) to record the L2 values missed by
  the reporting gap.

The next development would be a separately authorized phase. D-080 stays preserved and
unpublished.
