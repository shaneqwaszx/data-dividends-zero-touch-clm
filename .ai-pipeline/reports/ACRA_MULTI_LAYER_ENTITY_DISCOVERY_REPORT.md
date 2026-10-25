# ACRA multi-layer entity discovery — final report

Research agent report, 2026-10-25.

**Verdict: `INSUFFICIENT_MARKETPLACE_MOCK_DATA`.** Under the owner rules, fewer than 3
corporate layers are supportable, and 5 layers are not feasible.

**Scope and safeguards:**
- Offline review of tracked evidence, then **one** owner-approved bounded live probe of the
  ACRA API Marketplace **Mock**. The coordinator relayed the approval: credentials
  rotated, manifest SHA-256
  `e0a54613540f2f3211135e6849ac7e226fcb0201f44b89982dd1a6ab589d8a57`.
- No repository file was created, edited or deleted, and no git mutation ran. GoldTier was
  not called.
- The `.env` was read only by the probe, in memory, filtered to the two named Mock keys.
  Nothing was printed or persisted.
- Evidence class: `MOCK_INTEROPERABILITY_OBSERVED`, never Live or production.

**Provenance labels:**
- **MOCK-OBS (date):** an actual Mock observation.
  - `LIVE-25`: this probe, 2026-10-25 02:35:44–02:35:53 UTC.
  - Earlier dates come from tracked reports.
- **CATALOGUE:** the private Postman collection or sample index. It names candidates only.
- **LOCAL FIXTURE:** offline test data. It is never a Mock observation.

**Working files** (session scratch only, never tracked): the bounded probe script, its
dry-run and offline-simulation outputs, and the sanitized live output (30,463 bytes).

## 1. Operations researched

| Operation | Documented | Runtime implementation | Observed |
|---|---|---|---|
| `entityBasicInformation` | Postman; catalogue p.6 | **Yes** (`fetch_company`/`fetch_officers`) | 09-26, 10-01/02, 10-23, 10-24, **LIVE-25** |
| `coShareholdersDetails` | Postman (`uen`; optional `name`, `appointmentStatus`, `shareType`); catalogue p.5 | **Yes**, strict decoder. A non-empty `grouping` or missing `shareholders` is rejected | 09-26 → 10-24, **LIVE-25** (8 UENs) |
| `businessProfile` | BP spec v1.0 (fields only); Postman path | **No** (dormant URL builder only) | 10-24, **LIVE-25** (6 UENs) |
| `coCapitalDetails` | Postman; catalogue p.4 | **No** (smoke script and scratch probes only) | 09-26, 10-24, **LIVE-25** (2 UENs) |
| `entityVerification` | Postman; catalogue p.1 | **No** | 10-24, **LIVE-25** (3 UENs) |
| 16 other EIQ operations (`entitySearch`, `entityForeignRedom`, `coFyeLlpAnnualDeclaration`, …) | Postman | **No** | Never called. None carries share quantities. `entityPeopleDetails` needs person inputs, so it is excluded |

## 2. Candidates inspected

Companies:
- `11111999A`
- `111111111M`
- `201688888A`
- `201511222D`
- `200811111M`
- `200811111K`
- `199801111H`
- `111111111K`
- `333333333C`
- `222222222C`

Catalogue-only company UENs noted but not probed:
- `111111111C`
- `333333333V`
- `111111112M`
- `T16FC0001L`

Non-company profiles (LLP, LP, PAF, business, unregistered) were excluded: they are not
share-issuing bodies corporate.

Corporate-holder identifiers that the Mock **returned inside rows**:
- `T20VC0011A`
- `199301234H`
- `200212345D`
- `T16UF3333A`

Only `T16UF3333A` is a catalogue UEN. None of them was queried, because the manifest was
fixed.

## 3. Sanitized request counts

**This probe (LIVE-25):**
- **1 OAuth token POST**, HTTP 200.
- **18 GETs**, all HTTP 200 `application/json`.
- No redirect, no host drift, no retry, no stop.
- Two GETs of the budget left unused.
- Leak check **clean**:
  - the in-script guard passed (person-id pattern, credential and token values,
    authorization strings), so the output was printed;
  - a separate re-scan of `live_output.json` found no person-id pattern and no
    authorization or token-like content.

| # | Request | HTTP | Bytes | Envelope / entities | UEN bound |
|---|---|---|---|---|---|
| 1 | coShareholdersDetails `222222222C` | 200 | 2551 | list / 1 | yes |
| 2 | coShareholdersDetails `333333333C` | 200 | 1099 | list / 1 | yes |
| 3 | entityVerification `222222222C` | 200 | 17 | flat; only `isValid=false` | no (no uen) |
| 4 | businessProfile `222222222C` | 200 | 15 | list / 0 | — |
| 5 | coCapitalDetails `222222222C` | 200 | 15 | list / 0 | — |
| 6 | entityVerification `333333333C` | 200 | 17 | flat; only `isValid=false` | no |
| 7 | businessProfile `333333333C` | 200 | 15 | list / 0 | — |
| 8 | coCapitalDetails `333333333C` | 200 | 15 | list / 0 | — |
| 9 | entityBasicInformation `201511222D` | 200 | 2008 | list / 1 | yes |
| 10 | coShareholdersDetails `201511222D` | 200 | 15 | list / 0 | — |
| 11 | businessProfile `201511222D` | 200 | 15 | list / 0 | — |
| 12 | entityVerification `200811111M` | 200 | 86 | flat | yes |
| 13 | coShareholdersDetails `200811111M` | 200 | 15 | list / 0 | — |
| 14 | businessProfile `200811111M` | 200 | 15 | list / 0 | — |
| 15 | coShareholdersDetails `201688888A` | 200 | 15 | list / 0 | — |
| 16 | coShareholdersDetails `111111111K` | 200 | 15 | list / 0 | — |
| 17 | businessProfile `111111111K` | 200 | 15 | list / 0 | — |
| 18 | coShareholdersDetails `111111111M` | 200 | 1278 | list / 1 | yes |

**Prior recorded genuine requests:**

| Date | Run | Token requests | GETs |
|---|---|---|---|
| 09-26 | Smoke | ≥1 | 4 |
| 10-01/02 | Phase 24 | 6 | 18 attempted |
| 10-23 | D-077 | 1 | 10 |
| 10-24 | Sim Lim run 1 | 2 | 7 |
| 10-24 | P-A | 1 | 2 |
| 10-24 | Tier 1 | 1 | 5 |
| 10-24 | Ownership investigation | 1 | 3 |
| 10-24/25 | D-082 smoke | 1 | 4 |

## 4. Evidence availability (matrix)

Column key:
- **Id**: PROF = official profile; VER = verification; ECHO = operation-scoped name/type;
  UNAV = unavailable.
- **Denom**: AUTH = authoritative within class (Q-012 caveats); POC = POC-assumed only;
  UNAV = unavailable.
- **Int?**: suitable as an intermediate layer.

Privacy: no person names or identifiers appear. Corporate holder names and ids appear only
for Corporate-category rows.

| UEN | Operation | HTTP / result | Id | Type / form | Shareholders | Quantities | Classes (currency) | Current / historical | Issued capital | Denom | Corporate holders | Int? | Contradictions | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `222222222C` | coShareholdersDetails | 200, 1 entity, bound | ECHO "ABC Limited PTE. LTD." | PRIVATE COMPANY LIMITED BY SHARES (echo) | 5 individual-list rows (2 Corporate, 3 Individual) + 2 joint `grouping` blocks (`shareGroup`, `shareholders[]`, `shareSubGroups[]`) | integers, below | Ordinary, Preference (SGD **and** AUD) | below | none | UNAV | **2 Active Corporate rows** (below) | **No identified parent/child possible without override** (§8) | Verification `isValid=false`. "Limited PTE. LTD." naming is odd | MOCK-OBS LIVE-25 (summary 10-01/02) |
| ″ | entityVerification | 200, `{isValid:false}` only | UNAV | — | — | — | — | — | — | — | — | — | Invalid while its shareholder op returns data | LIVE-25 |
| ″ | businessProfile / coCapitalDetails | 200, empty / empty | — | — | — | — | — | — | **none** | UNAV | — | — | — | LIVE-25 |
| ″ | entityBasicInformation | 200, empty (10-01/02) | UNAV | — | — | — | — | — | — | — | — | — | — | MOCK-OBS |
| `333333333C` | coShareholdersDetails | 200, 1 entity, bound; `members[]` (no `shareholders`) | ECHO "XYZ123 PTE. LTD." | **PUBLIC COMPANY LIMITED BY GUARANTEE** (echo) | 4 members: 3 Corporate, 1 Individual | **none as shares**; `guaranteedAmount` 500 SGD each (a monetary guarantee) | none | 2 Active (both Corporate), 2 Withdrawn | n/a (guarantee company) | UNAV | Active: "EFGH" `199301234H`; "TYUI" `200212345D`. Withdrawn: "FGH SERVICES, INC" `T16UF3333A` | **No**: membership, not share ownership | Name ends "PTE. LTD." but type is public guarantee | LIVE-25 |
| ″ | entityVerification / BP / capital | 200, `isValid:false` / empty / empty | UNAV | — | — | — | — | — | none | UNAV | — | — | — | LIVE-25 |
| `111111111M` | coShareholdersDetails | 200, 1278 B, bound; **unchanged** | ECHO "SIM LIM PTE. LTD." | PRIVATE COMPANY LIMITED BY SHARES (echo) | 4 rows | 10000 (Withdrawn), 900 / 100 / 100 (Active) | Ordinary (W), Ordinary, Preference, Others (SGD) | 3 Active, 1 Withdrawn | none | UNAV | Withdrawn only: "FGH SERVICES, INC." `T16UF3333A` | **No**: bottom only | Same UEN carries 5 other names in the catalogue for other ops. Local fixture is all-Ordinary | LIVE-25 + earlier MOCK-OBS |
| ″ | entityBasicInformation / coCapitalDetails / businessProfile / entityVerification | 200, empty / empty / empty / `isValid` only | UNAV | — | — | — | — | — | none | UNAV | — | — | — | MOCK-OBS 10-23/24 |
| `201688888A` | businessProfile | 200, 1404 B, bound | **PROF** "ABC COMPANY PTE. LTD.", LIVE COMPANY | EXEMPT PRIVATE COMPANY LIMITED BY SHARES | 1 Individual | 1000 (JSON float) | ORDINARY (SGD) | no status field | issued = paid-up = 1000 shares (1000 SGD) ORDINARY | **AUTH** within class (float counts, no as-at date) | none | **No** (bottom only) | Conflicts with D-077 L3 600/400 | MOCK-OBS 10-24 |
| ″ | coShareholdersDetails | 200, **empty** | — | — | 0 | — | — | — | — | — | — | — | BP shows a holder; shareholder op is empty (operation-specific dataset) | LIVE-25 |
| ″ | entityBasicInformation | 200, empty | UNAV | — | — | — | — | — | — | — | — | — | — | MOCK-OBS 10-23 |
| `201511222D` | entityBasicInformation | 200, 2008 B, bound | **PROF** "OPQ PTE. LTD." | `entityConstnDetailsAndType.{companyType, companyConstitution}` present (values not recorded) | none (officers only: 3 Active, 1 Withdrawn) | — | — | — | not in this op | UNAV | — | **No**: no rows | Registered address block present, so the earlier "no address" concern is likely moot | LIVE-25 |
| ″ | coShareholdersDetails / businessProfile | 200, empty / empty | — | — | 0 | — | — | — | none | UNAV | — | — | — | LIVE-25 |
| `200811111M` | entityVerification | 200, 86 B, bound | **VER** "JKL TECHNOLOGY PTE LTD", entityType `COM`, `isValid=true` | COM (code; mapping unconfirmed) | — | — | — | — | — | UNAV | — | **No**: no rows | — | LIVE-25 |
| ″ | coShareholdersDetails / businessProfile / entityBasicInformation | 200, empty ×3 | — | — | 0 | — | — | — | none | UNAV | — | — | — | LIVE-25 / 10-23 |
| `111111111K` | coCapitalDetails | 200, 589 B, bound | ECHO "ABC PTE. LTD." | — | none | — | Ordinary issued/allotted **50,002,606.14**; others 0 ("SINGAPORE, DOLLARS") | — | present, but non-integer: a **monetary amount, not a share count** | UNAV | — | No | Conflicts with D-077 L5 1000 units | MOCK-OBS 10-24 |
| ″ | coShareholdersDetails / businessProfile / entityBasicInformation | 200, empty ×3 | — | — | 0 | — | — | — | — | — | — | No | — | LIVE-25 / 10-23 |
| `11111999A` | entityBasicInformation / coShareholdersDetails | 200 profile / 200 empty | PROF "GARDEN BUSINESS" | BUSINESS_PARTNERSHIP (not a body corporate) | none; 4 OWNER roles (3 current, 1 ceased) | none | — | roles only | none | UNAV | — | No | Local Garden body vs. official empty shareholder read | MOCK-OBS |
| `200811111K` / `199801111H` | entityBasicInformation | 200, empty (10-23); own ops never called | UNAV | — | — | — | — | — | — | — | — | No | — | MOCK-OBS |

**`222222222C` rows in detail** (LIVE-25; each row is the issuer's own and same-UEN):

| Row | Collection | Category | Status | Units | Class | Currency | Holder (Corporate only) |
|---|---|---|---|---|---|---|---|
| R1 | individual | Individual | Withdrawn | 100 | Ordinary | SINGAPORE DOLLAR | — |
| R2 | individual | Individual | Withdrawn | 200 | Preference | AUSTRALIA DOLLAR | — |
| **R3** | individual | **Corporate** | **Active** | **123** | **Ordinary** | **AUSTRALIA DOLLAR** | "XYZ"; id **not UEN-shaped** (not emitted) |
| R4 | individual | Individual | Active | 321 | Preference | AUSTRALIA DOLLAR | — |
| **R5** | individual | **Corporate** | **Active** | **100** | **Ordinary** | **SINGAPORE DOLLAR** | "EFGH23XX", id `T20VC0011A` (UEN-shaped, not a catalogue UEN, never queried) |
| G1 | grouping (3 joint holders: 2 Individual + Corporate "FGH SERVICES, INC." `T16UF3333A`, FBRN present) | sub-group | Withdrawn | 0 | Ordinary | SINGAPORE DOLLAR | joint |
| G2 | grouping (2 joint Individual holders) | sub-group | Active | 300 | Preference | SINGAPORE DOLLAR | joint |

## 5. Data consistency concerns

1. **Identity is operation-specific.**
   - Every shareholder-bearing sample has ECHO identity only. Their `entityVerification`
     says `isValid=false` (`111111111M`, `222222222C`, `333333333C`), and their basic,
     BP and capital records are all empty.
   - The profile-grade companies (`201511222D`, `200811111M`, `201688888A`, `11111999A`)
     have no `coShareholdersDetails` rows.
   - No UEN has both a profile and a shareholder-operation row set.
2. **Cross-operation inconsistency.** `201688888A` has 1 holder in BP but an empty
   shareholder operation. Neither result can corroborate the other.
3. **One class, mixed currencies.** `222222222C` Ordinary units are in AUD (R3, 123) and
   SGD (R5, 100). The units are not comparable without a rule.
4. **Joint holdings.** The `grouping` units belong to a joint group (`shareSubGroups`). They
   cannot be split among joint holders without a rule. The current strict decoder rejects
   them.
5. **Guarantee company.** `333333333C` has `guaranteedAmount` (money) and no shares. It
   cannot supply a share-quantity basis.
6. **Vocabulary and shape drift.**
   - Envelopes: `entities` list versus flat object.
   - Classes: `Ordinary` versus `ORDINARY`.
   - Currency strings: `SINGAPORE DOLLAR` versus `SINGAPORE, DOLLARS`.
   - Members use `memberCategory` versus `shareholderCategory`.
   - BP counts are floats; capital is non-integer.
7. **Repository decoder gap (finding, not fixed).** OPQ's response carries
   `entityConstnDetailsAndType.companyType`/`companyConstitution`. The decoder reads only
   `constitution`, which explains the persistent legal form `OTHER`. The values were not
   recorded.
8. **Placeholder reuse.** `111111111M` has six names across operations. "FGH SERVICES"
   (`T16UF3333A`, an unregistered foreign entity) recurs as a **Withdrawn** holder or
   member in three issuers.
9. **Existing synthetic scenarios conflict with official data.** D-077 L3 and L5, the
   D-076 all-Ordinary fixture, and D-081 class pooling all disagree with Mock rows or
   capital.

## 6. Recommended companies (real, independently identified; roles limited)

| UEN | Identity | Recommended role | Why / limit |
|---|---|---|---|
| `201688888A` | PROF | **Bottom issuer** (official individual leaf) | The only same-issuer, same-class denominator: 1000 of 1000 ORDINARY |
| `222222222C` | ECHO (verification invalid) | Issuer with **official corporate holders** (R3, R5) | Richest share data, but no denominator; mixed currencies; joint groups |
| `111111111M` | ECHO | Bottom issuer (units only) | 3 classes and no denominator |
| `201511222D` | PROF | Root identity only | No rows of its own; nothing quantitative links into it |
| `200811111M` | VER (`COM`, valid) | Identity only | No rows or capital |
| `333333333C` | ECHO | Not for share ownership | Guarantee company (membership amounts only) |

Not recommended:
- `111111111K`: capital amount only.
- `11111999A`: a partnership.
- `200811111K`, `199801111H`: no identity.

## 7. Five-layer feasibility

**Not feasible.** Five layers need four links, each backed by an Active row of the child
issuer naming that parent. The Mock contains **zero** such rows between independently
identified companies.

## 8. Three-layer feasibility

**`INSUFFICIENT_MARKETPLACE_MOCK_DATA`.**

Under the owner rules, a supportable corporate link needs an Active same-UEN share row
whose holder *is* the parent, without rewriting holder, category, status or identity.

| Candidate link | Quantitative basis (issuer row) | Override required? | Supportable? |
|---|---|---|---|
| Real company P (for example OPQ or `200811111M`) → `222222222C` | R5: `222222222C`, Corporate, Active, 100, Ordinary, SGD | **Yes**: holder identity "EFGH23XX"/`T20VC0011A` would be rewritten | **No: owner-decision conflict** |
| P → `222222222C` | R3: `222222222C`, Corporate, Active, 123, Ordinary, AUD | **Yes**: holder "XYZ" would be rewritten | **No: conflict** |
| P → `111111111M` | Active 900 Ordinary SGD row (Individual) | **Yes**: category and identity | **No: conflict** |
| P → `111111111M` | 10000 Ordinary SGD row (Corporate) | **Yes**: the row is Withdrawn, and identity is FGH | **No** (withdrawn) |
| P → `201688888A` | BP holder: Individual, 1000 ORDINARY | **Yes**: category and identity | **No: conflict** |
| P → `333333333C` | Corporate members, Active, `guaranteedAmount` 500 SGD | Amount is money, not shares; identity override also needed | **No** |
| `T20VC0011A` → `222222222C` (official, not simulated) | R5 | No override | The link is genuine, but the **parent identity is unverified**: no same-UEN record, not a catalogue UEN, no rows below it. It cannot be counted as an identified layer |
| "XYZ" → `222222222C` (official) | R3 | No override | The holder id is not UEN-shaped, so the parent is unidentifiable |

**Supportable today: 1 identified corporate layer with official holders.** Examples:
- `201688888A` with its individual holder;
- `222222222C` with its official holders, where the corporate branches stay unresolved.

That is fewer than 3.

## 9. Gaps needing synthetic relationships

- Every inter-company link between identified companies would be synthetic, and **none has
  an admissible quantity basis**. Each candidate either needs a holder override (an owner
  decision) or invented units (prohibited).
- A route to a genuine second layer would need a new owner approval for a follow-up probe:
  same-UEN `entityBasicInformation`, `entityVerification` and `coShareholdersDetails` for
  the Mock-returned holder id `T20VC0011A`, 3 GETs. It would be a genuine layer only if
  that id returns its own identity **and** rows. It is not a catalogue sample, so a
  non-empty result is unlikely.
- `199301234H` and `200212345D` would yield membership only, not share ownership.
- Any demonstration denominator for `222222222C` or `111111111M` would be POC-assumed (a
  D-081-style decision), never authoritative.

## 10. Exact quantitative basis per calculation

| Calc | Issuer (same UEN only) | Numerator | Denominator | Result | Status |
|---|---|---|---|---|---|
| Q-A | `201688888A` (BP) | Individual holder 1000 ORDINARY | issued 1000 ORDINARY (same response) | 100% share-count proportion within ORDINARY | **Supportable** (Mock; float counts, no as-at date). Not an official percentage |
| Q-B | `111111111M` | Active 900 Ordinary / 100 Preference / 100 Others (SGD) | none | units per class only | No percentage |
| Q-C | `222222222C` | Active: R5 100 Ord SGD (Corp `T20VC0011A`); R3 123 Ord AUD (Corp "XYZ"); R4 321 Pref AUD (Ind); G2 300 Pref SGD (joint, 2 Ind) | none (BP and capital empty) | units per class and currency only | No percentage. A POC denominator would need an owner decision covering currency and joint-holding rules |
| Q-D | `333333333C` | `guaranteedAmount` 500 SGD × 2 Active Corporate members | n/a | none | Excluded (money, not shares) |
| Q-E | `111111111K` | — | capital 50,002,606.14 (amount) | none | Excluded (no amount used as a share count) |

Excluded from every calculation:
- withdrawn rows (R1, R2, G1, SIM LIM's 10000);
- cross-UEN combinations;
- class pooling.

## Confidential-artefact handling

- The private Postman ZIP and the catalogue PDF were read in memory only. The ZIP's
  environment token file was parsed but not printed.
- This report contains only:
  - operation names, paths and parameter names;
  - sample UENs;
  - company-level names and types returned by the Mock;
  - Corporate-holder names and ids.
- It contains no person names or ids, no addresses, no raw bodies, and no credentials or
  tokens.
