# Sim Lim ACRA ownership follow-through (D-080) — Stage 1/2 report

Implementer report, 2026-10-24. It is implementer evidence only, not an independent QG
verdict. Nothing is committed, pushed or published.

## Outcome

- **D-079 works in normal onboarding, including against the real Marketplace Mock.** A
  fresh Garden case made SIM LIM's independent `coShareholdersDetails` read and retained
  all four official rows. A second fresh case reused them with zero GETs.
- **The owner's three-party graph is expected.** Retained rows are never graph parties.
  The graph shows GARDEN BUSINESS, SIM LIM and LIM CHOON HUAT with or without D-079 (see
  §2).
- **No defensible percentage exists for SIM LIM's holders.** There are two reasons:
  - the Mock has no same-entity capital record (`coCapitalDetails` is empty);
  - SIM LIM's three current holdings are in three different share classes.
- **One genuine retention gap was found and fixed (D-080, owner-approved).** The retained
  rows dropped `shareType`/`currency`, so the API showed 900/100/100 as if the units were
  comparable. Rows now keep their own source class and currency, and the denominator issue
  says when current rows mix classes. No arithmetic, edge, identity or readiness rule
  changed.
- Status: `OWNER REVIEW / PUBLICATION AUTHORIZATION PENDING` after the independent QG.

## Identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024`.
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024` (upstream unset).
- BASE = `origin/main` = `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (merged PR #107,
  D-079), unchanged at acceptance time (see §8).
- Uncommitted. The frozen product content is identified in §8; this report is outside it.
- Change classes: `BACKEND_DOMAIN`, `EXTERNAL_PROVIDER`, `PERSISTENCE`, `BACKEND_API`
  (additive response fields).

## 1. Stage 0 — preflight (this session)

- **Tools:** Bash/PowerShell, file tools, subagents, the built-in browser (not used) and
  Docker 29.9.2. The GitHub MCP server failed to connect (not needed).
- **Python:** 3.12.10 from the primary checkout's `.venv`, with `PYTHONPATH` pinned to the
  worktree backend (`app.__file__` verified).
- **Credentials:** absent from the process environment. A primary-checkout `.env` exists.
  I never displayed or inspected its contents. With the owner's two in-session
  authorizations, my scratch script opened it in memory for the bounded live reads (§4),
  kept only the two named Marketplace keys, and never printed them.
- **Owner runtime (read-only observation):** a backend on `127.0.0.1:8000` (`--reload`,
  primary checkout) started at 05:21:38 +08. The primary `main` fast-forwarded to
  `ceefe1e` at 05:19:01, so that backend runs PR #107 code. Its configuration needs an
  authenticated session and was not inspected; no sign-in was attempted.

## 2. Stage 1A — fresh Garden journey and the first evidence boundary

The same HTTP journey (fresh Garden case through the zero-touch API, memory persistence,
Mock GoldTier, hybrid direct-only overlay, offline protocol transport) was run on the
D-079 tree and on the pre-D-079 base `2d8b84a`. 0 external calls.

| | Pre-D-079 (`2d8b84a`) | D-079 (`ceefe1e`) |
|---|---|---|
| Graph parties | GARDEN BUSINESS, SIM LIM, LIM CHOON HUAT | the same three |
| Edges | `LOCAL_SYNTHETIC_RELATIONSHIP` 62.5 / 37.5 | the same |
| SIM LIM discovery record | `NOT_FOUND`, no rows | `PROVIDER_PARTIAL` / `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, 4 rows |
| `OWNERSHIP_DENOMINATOR_REQUIRED` | absent | present |
| GETs, first case | Garden entity ×2, SIM LIM entity ×1 | + SIM LIM shareholders ×1 |
| GETs, second fresh case | 0 | 0 (`SHAREHOLDERS_CACHE_REUSED`) |
| State / readiness | REVIEW_REQUIRED / `OWNERSHIP_REVIEW_REQUIRED` | the same |

So the graph cannot tell the two versions apart. The first boundary where useful evidence
stops is by design: discovery keeps the rows on `discovery.records[].official_shareholders`
and never turns them into parties or edges. The API exposes them; the unchanged UI renders
only the outcome label ("Incomplete registry evidence"), the reason code and the issue
message.

**Old cases.** A case keeps the analysis it was given. Restarting or reopening never
re-analyses it, and `ownership/load` is refused (`OWNERSHIP_ALREADY_LOADED`) unless its
documents or identity changed. The supported refresh is a new Garden case. This is now
pinned by a test (§5). Demo guide §8 gives the inspection and refresh procedure.

**Which explanation fits the owner's screenshot?** The owner's runtime started after
PR #107, and the three-party graph proves the hybrid overlay is active (the legacy
supplement shows the flattened subtree). The screenshot alone cannot show whether the
case predates the restart. Either way three parties is the correct D-079 rendering; the
discriminator is SIM LIM's discovery-row label and the denominator issue.

## 3. Stage 1B — what the official data supports

`coShareholdersDetails` row fields observed live (field names only): `shareholderCategory`,
`shareholderId`, `shareholderName`, `shareholderAliasName`,
`shareholderHanyuPinyinName`, `shareholderHanyuPinyinAliasName`,
`shareholderMarriedName`, `shareholderFbrn`, `shareAllotted`, `shareType`, `currency`,
`appointmentDate`, `cessationDate`, `status`. `grouping` was empty.

SIM LIM `111111111M` (one entity, returned UEN equal to requested):

| Holder | Category | Status | `shareAllotted` | `shareType` | `currency` | Current interest |
|---|---|---|---|---|---|---|
| FGH SERVICES, INC. | Corporate | Withdrawn (cessation date present) | 10000 | Ordinary | SINGAPORE DOLLAR | No |
| ABCD123 | Individual | Active | 900 | Ordinary | SINGAPORE DOLLAR | Yes |
| TAN WEI LING | Individual | Active | 100 | Preference | SINGAPORE DOLLAR | Yes |
| EFGH2345 | Individual | Active | 100 | Others | SINGAPORE DOLLAR | Yes |

The names are those the owner already listed; identifiers are not reproduced.

- **Issuer binding:** returned UEN equals the requested UEN (strict decoder).
- **Coverage:** the response is a validated collection, but it states no issued total, so
  completeness of coverage cannot be established. A diagnostic `COMPLETE` means the
  collection validated, nothing more.
- **Denominator:** none in this response. `coCapitalDetails` (listed in the confirmed
  contract, not a runtime operation) returned HTTP 200 with an explicit empty collection
  for `111111111M`. No same-entity capital record exists in the Mock. Q-012 still leaves
  capital/share-class semantics open.
- **FGH SERVICES, INC.:** its `shareholderId` has a UEN-eligible shape and a
  foreign-registration field is present. The contract does not define either as a verified
  registration number, and the row is **Withdrawn**, so it holds no current interest and
  needs no recursion. It stays an unverified observation, not a resolved branch.
- **Local fixture contrast:** the owner-supplied local SIM LIM fixture (D-076) uses the same
  three individual names and units but declares every row `Ordinary`, with a withdrawn
  corporate row named FORMER OWNER. Its `garden_legacy_supplement` result (ABCD123
  51.13636375%) is therefore a synthetic basis that the official Mock's class structure
  does not support. It is unchanged and remains labelled synthetic (§7).

## 4. Live Marketplace Mock verification (owner-authorized, bounded)

Scratch scripts outside the repository, modelled on the reviewed `phase24` probe and
dry-run offline first:
- verified TLS, `trust_env=False`, no redirects;
- allowlisted host, operations and UENs (`11111999A`, `111111111M`);
- hard caps checked before dispatch;
- sanitized output only. A scan of the output found no credential-like content.

| Run | Token POST | GETs | Result |
|---|---|---|---|
| 1. Two fresh Garden onboardings in-process + 1 capital read | 1 | 5: Garden entity ×2, SIM LIM entity ×1 (empty), SIM LIM shareholders ×1, SIM LIM capital ×1 | Token and the 4 journey GETs HTTP 200; the capital read's status was not printed (reporting gap). Case 1: SIM LIM `PROVIDER_PARTIAL`, 4 rows retained, `SHAREHOLDERS_FETCHED`. Case 2: 0 GETs, `SHAREHOLDERS_CACHE_REUSED` |
| 2. Rows + capital (second owner approval) | 1 | 2: SIM LIM shareholders ×1, SIM LIM capital ×1 | All 3 receipts HTTP 200. Per-row class recorded (§3). Capital: 15 bytes, 0 entities |
| **Total genuine** | **2** | **7** | 8 of 9 receipts recorded HTTP 200 (one status not captured). Within the 16-read cap. No Sandbox/Live host, no GoldTier call |

Run 1 used the D-080 candidate tree **before** share-class retention was coded, so it
proves D-079 end to end. D-080 itself has offline evidence only (the protocol transport
carries the observed class shape). Classification: `MOCK_INTEROPERABILITY_OBSERVED`, never
Live.

## 5. Stage 1C — changes

**D-080 (owner-approved during this assignment).** Implementation notes:
- `connectors/acra_bizfile_sandbox.py`, `connectors/acra.py`: the strict decoder reads
  optional `shareType`/`currency` (untrusted text, at most 64 characters).
- `connectors/registry.py`: only `retrieve_shareholder_evidence` keeps them
  (`_normalize_shareholder_evidence_party`). Ordinary acquisitions drop them.
- `domain/models.py`:
  - `RegistryOwnershipParty.share_type/currency`;
  - bundles reject a class;
  - contract `MARKETPLACE_SHAREHOLDERS_V2` with registry cache schema 4;
  - V1 schema-3 entries stay valid without a class.
- `services/registry_acquisition.py`: writes schema 4.
- `domain/ownership.py`, `services/ownership_discovery.py`: `OfficialShareholderObservation`
  carries the class.
- `services/ownership_analysis.py`: the issue message adds "current rows mix share classes"
  when an issuer's current rows report more than one class. It stays within the 200-character
  bound, and the single-class message is unchanged.
- `persistence/models.py`, `mongo_case_store.py`: case envelope schema 14 with an exact
  `DurableCaseSnapshotV13` reader. v13 rejects a non-null class, and explicit null keeps the
  D-079 meaning.

**Tests:**
- `test_official_shareholder_evidence.py`: 13 → 19 test functions, 23 → 34 collected
  cases. New:
  - malformed quantities (negative, non-numeric, boolean, more than 6 decimals, more than
    18 digits);
  - a pre-D-079 stored case is never re-analysed or rewritten, while a fresh case reads once
    and retains the rows;
  - rows named like the local fixture keep the Mock's own ids, units and provenance;
  - mixed classes are retained per row, never combined, with the message variant;
  - only current rows decide whether classes are mixed (QG N1);
  - a COMPANY-form Marketplace ordinary acquisition never carries a class (QG N2);
  - a fresh D-079 V1 cache entry is neither reused nor rewritten;
  - exact cache contract/schema pairing;
  - envelope 14 round trip, v13 rejection and acceptance, v12 rejection, and the supported
    version list including 13 (QG N3).
- `test_recursive_ownership_real_mongo.py` (physical): classes survive restart, cache
  schema 4, and exact v13/v12 envelopes fail closed. A class-free v13 envelope reads into
  the current form, without rewrite (QG N3).
- 38 mechanical schema pins in 18 files: 13 → 14, and the unknown-version sentinels 14 → 15.

**Docs:** D-080 (`DECISION_LOG.md`); `ACRA_MOCK_API_PROFILE.md`, `OWNERSHIP_UBO_PROFILE.md`,
`REGISTRY_CACHE_FRESHNESS_PROFILE.md`; ADR-013 amendment; `ARCHITECTURE.md`;
`PROJECT_STATE.md` (envelope 14, candidate note, stale "v12" corrected);
`ACRA_API_MARKETPLACE_MOCK_READINESS.md` (2026-10-24 observation); demo guide §8.

**Change statement:**

| Area | Change |
|---|---|
| API/types | Additive `share_type`/`currency` on `official_shareholders` rows; one issue-message variant (existing code) |
| Schema | Case envelope 14; registry cache 4 (new key `MARKETPLACE_SHAREHOLDERS_V2`) |
| Connector | The decoder reads two optional fields; there is no new operation or endpoint |
| Configuration | None |
| Business rule | None. No class rule, weighting, denominator or percentage |
| Mapping | No source-to-target mapping. Source text is kept as-is |
| Auth/security | Unchanged |
| Architecture | Same owners (ADR-013 amendment) |
| Provider classification | Unchanged (`MOCK`) |
| Runtime | After upgrade, the first new case per issuer makes one fresh shareholder read (V1 entries are not reused). Existing cases are not re-analysed |
| Frontend | Byte-identical |

**Residual risks:**
- A `shareType`/`currency` longer than 64 characters, or non-string, now fails the shareholder
  decode closed (safe `PROVIDER_FAILED`) where it was previously ignored. This also covers
  COMPANY-form Marketplace acquisitions and the dormant/diagnostic decoder users.
- Rolling back to `ceefe1e` in Mongo mode fails closed at startup, the same as earlier
  envelope bumps. Any v14 case in the case collection refuses startup. In the registry
  cache collection, schema-4 entries and D-080-written schema-1/2 entries with ownership
  parties (null `share_type`/`currency`) also refuse startup, until the cache collection
  is cleared.

## 6. Acceptance scenarios

| # | Scenario | Evidence |
|---|---|---|
| 1 | Fresh Garden onboarding, Marketplace mode, direct-only overlay | Offline API journey (§2); live run 1 (§4); `test_api_projects_retained_rows_and_keeps_readiness_blocked` |
| 2 | Empty SIM LIM profile, shareholders present | Live run 1; `test_empty_profile_corporate_holder_keeps_official_shareholders_beside_the_graph` |
| 3 | All four rows under the correct issuer/operation | Live run 1 (4 rows, UEN bound, `OWNERSHIP_PARTIES` provenance); journey tests |
| 4 | Active/withdrawn | `current_interest` only for Active (journey and mixed-class tests; physical test) |
| 5 | Fresh cache hit, no redundant calls | Live run 1 case 2 (0 GETs); `test_repeat_onboarding_reuses_cached_shareholder_evidence_with_zero_calls` |
| 6 | Cache miss calls the operation | Coordinator and journey tests; `test_a_fresh_d079_cache_entry_is_neither_reused_nor_rewritten` |
| 7 | Stale, empty, mismatched UEN, malformed quantities, grouping, 401/403, timeout, 5xx | Coordinator stale/expiry tests; failure parametrization (now 13 cases); empty test |
| 8 | No denominator → no percentage/UBO | Journey and mixed-class tests (LIM CHOON HUAT only candidate, INDETERMINATE; bound 62.5) |
| 9 | Controlled complete same-issuer/same-class denominator fixture | Existing authority only: local synthetic lane (`test_recursive_ownership_discovery.py`, 81.818182/9.090909 and 51.13636375 path multiplication) |
| 10 | Multiple branches aggregate without double counting | OPQ DIANA KOH 18.75 + 6.25 = 25 (`test_hybrid_five_layer_overlay.py`) |
| 11 | Unsupported corporate identifiers unresolved | No registration identifier is ever supplied; no record or recursion (journey test) |
| 12 | Garden legacy and OPQ scenarios | Existing suites (full backend run) |
| 13 | Manual reconciliation, versioning, persistence, readiness, GoldTier no-replay | Existing suites (full backend and physical Mongo runs) |
| 14 | Existing cases not rewritten | `test_a_case_analysed_before_d079_is_kept_and_only_a_fresh_case_retains_rows`; v13 to v14 read without rewrite (unit and physical tests) |
| 15 | No local synthetic holders passed off as ACRA's | `test_rows_named_like_the_local_fixture_keep_the_mock_values_and_provenance`; `test_ordinary_acquisitions_never_carry_a_share_class` |

## 7. Owner decisions and proposals (none implemented)

**P-A. Demonstration-only denominator (assignment §6). Recommendation: do not adopt.**

Numerators are the current rows: 900 Ordinary, 100 Preference, 100 Others. Every
assumed denominator is a project rule, never ACRA-verified, because:
- the Mock has no issued-share total and no capital record for SIM LIM;
- Q-012 leaves completeness and share-class semantics open;
- converting class units into an economic interest needs class rights (Q-004) that no
  source provides.

| Option | Assumed denominator | What it assumes | Demonstration result | Assessment |
|---|---|---|---|---|
| A1 cross-class sum | 1100 (all current units) | Every unit of every class is economically equal; the three holders own all issued shares | ABCD123 81.818182%, others 9.090909% each. Via Garden 62.5%: 51.13636375% and 5.681818125% (before engine quantization) | Contradicted by the observed classes. Not recommended |
| A2 per-class share | 900 / 100 / 100 (each class's current units) | Each class is fully represented | Each holder has 100% of its own class | Mathematically defined, but not an ownership or UBO percentage. Display only |
| A3 owner-declared class rights | for example Ordinary only | A project economic rule | ABCD123 100% of the counted class (62.5% through Garden) | A material policy rule (Q-004). Sponsor input required |

Any adoption would need a new decision, labels such as `ASSUMED_DENOMINATOR_DEMONSTRATION`,
no readiness or GoldTier effect, and a frontend owner decision to show it.

**P-B. Capital operation.** Runtime `coCapitalDetails` would not help SIM LIM, whose Mock
capital record is empty. It might help issuers whose samples have one, but that needs
Q-012 semantics plus a strict DTO, issuer/class/currency/date reconciliation and a new
contract key. Recommendation: defer.

**P-C. Corporate `shareholderId` as a registration number.** Not needed for SIM LIM: the
FGH row is withdrawn. The general rule needs Q-012/Q-019 authority. Recommendation: keep
the current "no supplied verified identifier, no recursion" rule.

**P-D. Optional read-only "Official shareholder evidence" UI section.** A compact table
under SIM LIM's discovery row:
- columns: holder, category, status, units, share class, currency, current interest;
- source label "ACRA API Marketplace Mock · coShareholdersDetails";
- caption: "Share counts by class only — no percentage without an issued-share
  denominator".

It needs frontend types, a component and an E2E selector, and is not implemented
(owner rule: no Ownership & UBO UI changes without explicit authorization).

**P-E. Legacy local fixture divergence.** The default `garden_legacy_supplement` lane
declares SIM LIM's rows all `Ordinary` and computes ABCD123 51.13636375%. The official
Mock reports Ordinary/Preference/Others. Options: keep it (labelled synthetic, accepted
D-046 scope) or relabel/retire it. It is unchanged here.

## 8. Stage 2 — integrated acceptance

**Integration.** `git fetch` shows `origin/main` = BASE `ceefe1e`, so no integration
merge was needed (re-checked before freezing).

**Frozen product content.** Tree **`4944456a612e02b87a106e8bfe5d1408715840ee`**:
- built with a temporary index outside the repository (`git read-tree HEAD`, then
  `git add -- $(git diff --name-only)`, then `git write-tree`);
- 38 paths;
- this report is excluded.

Every result below ran on that content. One exception: the `PROJECT_STATE.md`
compatibility-paragraph wording was shortened after the first backend run and before the
chunked run. It is documentation only, and the chunked run is on the frozen tree.

| Check | Result |
|---|---|
| Ruff `apps/backend` (app + tests) | PASS |
| Ruff format (changed/new tests) | PASS |
| mypy `app` | PASS, 129 files |
| D-079/D-080 module | 33 passed |
| Focused suites | All passed. Ownership/persistence/pin modules (14 files) and connector/registry/ownership modules (22 files) |
| Full backend pytest, 4 sequential fresh-process file chunks (JUnit) | 3162 collected = 732 + 991 + 653 + 786; **2987 passed, 175 skipped (169 physical-Mongo + 6 Tesseract OCR, as on baseline), 0 failed, 0 errors**; 993 s |
| Physical Mongo | **PASSED**: 25 suites, 169/169, 0 skipped. Run with `run_physical_mongo_tests.py` against a task-owned disposable `mongo:7` container on loopback, with generated allowlisted DBs (never `clm_poc`); no URI printed |
| CI unittest lanes | All OK: contract 44, delivery assets 4, secrets, pre-PR, policy authority, provider readiness, skill pointers, GoldTier examples |
| dev-context / project-state / architecture tests | 55 OK (see note) |
| Checkers: `check_project_state`, `check_architecture`, `check_secrets`, `check_policy_authority`, `check_external_provider_readiness`, `check_tooling_config` | PASS |
| `git diff --check`; EOL churn (`--stat` vs `--ignore-cr-at-eol --stat`) | Clean; identical (38 files) |
| Full browser suite (`run_e2e.py --timeout-seconds 60`, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT`) | **115/115 PASS** in isolated lifecycles, first run, 1463 s. Slowest: `performance-browser.e2e.ts:137` at 55.7 s of 60 |
| Frontend typecheck / Vitest / build | Not rerun: `apps/frontend` is byte-identical to BASE (`npm ci` from the unchanged lockfile; no tracked change) |

**Two environment stalls (not product failures).** The first two full single-process
backend runs stalled at 66% and 63%. Both stalls were the known Windows asyncio
`socket.socketpair()` fallback hang (`_fallback_socketpair` → `accept`, faulthandler
dump), inside `test_phase24b_*` TestClient setup. Only the verified pytest PIDs were
force-stopped.
- The affected modules passed 100/100 in isolation.
- The chunked run passed every file, including those modules.
- Classification: ENVIRONMENT-BLOCKED, not a reproducible defect. The tests-only
  pre-D-080 run had passed in one process (2984 passed, 175 skipped).

**Context benchmark.** My first `PROJECT_STATE.md` wording grew the routine selection, and
`test_routine_benchmark_reduces_mean_utf8_footprint_by_thirty_percent` failed (29.96%
against a 30% floor; main is 30.07%). The paragraph was rewritten more compactly, and the
benchmark is now 30.047%. Headroom is very small for any future addition to that section.

## 8a. QG round 1 remediation

The independent QG (`SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_QUALITY_GATE.md`) gave **PASS WITH
MINOR FIXES** on tree `4944456…`. It found no product defect. Every fix below is to docs
or tests; no application code changed.

| Finding | Fix |
|---|---|
| F1 (Medium) cache rollback statement | `REGISTRY_CACHE_FRESHNESS_PROFILE.md` schema-4 rollback text now says that startup decodes every cache document. An earlier version therefore refuses to start, fail-closed, on schema-4 entries and on D-080-written schema-1/2 entries with ownership parties, and also on any v14 case. This report's rollback note is corrected to match |
| F2 (Low) "all HTTP 200" | `DECISION_LOG.md` and the readiness doc now say 8 of 9 receipts recorded HTTP 200 (the first capital read's status was not captured). The capital conclusion now rests on the fully recorded read (HTTP 200, 0 entities) |
| F3 (Low) live-run code identity | `PROJECT_STATE.md` and the readiness doc now say the live onboarding ran pre-D-080 (D-079) code, and that D-080 has offline evidence only |
| N1 | New test: only current rows decide whether classes are mixed (a mutant dropping the filter is now killed) |
| N2 | The ordinary-acquisition test now drives a COMPANY-form Marketplace acquisition. A mutant keeping the class in bundles is now killed |
| N3 | The supported version list (1..14) is pinned. The physical test now also reads a class-free v13 envelope into the current form and checks the stored document is unchanged |
| N4 | `ACRA_MOCK_API_PROFILE.md` documents that the stricter shared decoder fails COMPANY-form acquisitions and the diagnostic read closed on hostile `shareType`/`currency` |
| N5 | Informational (exact-string class comparison; affects only the message). No change |
| N6 | Report corrected: test counts, skip composition (169 physical + 6 Tesseract), `.env` wording, and the HTTP 200 statements |

**Rerun after remediation**, on tree **`5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`**
(38 paths, `origin/main` still `ceefe1e`):

| Check | Result |
|---|---|
| D-079/D-080 module | 34 passed (19 test functions) |
| N1/N2 mutants (temporary in-place, byte-exact restore verified) | Both killed |
| Physical `test_recursive_ownership_real_mongo.py` | 4 passed, 0 skipped |
| Physical runner (all 25 suites) | PASSED, 169/169, 0 skipped. The count is unchanged because the new assertions are in an existing test |
| Ruff, format (changed tests) | PASS |
| `git diff --check`; EOL stats | Clean; identical (+755/−85) |
| Checkers | PASS: project-state, architecture, secrets, policy authority, provider readiness, tooling config |
| dev-context / project-state / architecture tests | 55 OK; benchmark 30.047% |
| Contract lane | 44 OK |

Reused unchanged evidence (no application, configuration or frontend change since
`4944456…`; only the two test modules and docs changed):
- the chunked full backend run;
- the browser suite 115/115;
- mypy;
- the CI unittest lanes.

**Fresh independent re-QG: PASS** on tree `5dfa8442cb9eb015b6c7cee26d577ad5c1fff342`, with
no required fixes (`SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_RE_QUALITY_GATE.md`). It records
three informational wording notes (I1–I3), left as they are so the reviewed content does
not change.

## 9. Reproducible new-Garden procedure (owner runtime)

1. From an up-to-date checkout of the candidate (or `main` after merge), set
   `ACRA_CONNECTOR_MODE=api_marketplace_mock`,
   `ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay` and
   `REGISTRY_CACHE_MODE=auto`. Use your approved credential injection and a disposable or
   memory persistence mode.
2. Restart the backend so the new code is loaded. `--reload` only reloads the checkout it
   watches.
3. Sign in as a Relationship Manager and create a **new** Garden case (`11111999A`,
   `GARDEN BUSINESS`, SG) with the usual Garden document.
4. In *Ownership & UBO*, expect three graph parties, SIM LIM as *Incomplete registry
   evidence* (`OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`), and the issue "4 official
   Marketplace Mock shareholder row(s) are retained without an entity profile; current rows
   mix share classes and no authoritative denominator exists, so no percentage is
   inferred."
5. Read the rows with the console snippet in demo guide §8.

## Next authorized action

`OWNER REVIEW / PUBLICATION AUTHORIZATION PENDING`. Stage 4 needs explicit owner
authorization to commit, push and open a PR for exactly tree `5dfa844…`. It would start
with a fresh `origin/main` drift check and a clean-tree `python scripts/pre_pr_check.py`.
Any adoption of P-A to P-E needs a separate owner decision.
