# Sim Lim ACRA ownership follow-through (D-080) - Stage 3 Quality Gate

Independent Stage 3 review, 2026-10-24. The reviewer did not author or remediate the
reviewed content. Review only: nothing was fixed, staged, committed or pushed.

## 1. Executive Result

**PASS WITH MINOR FIXES.**

The product behaviour meets the assignment. Fresh Garden onboarding in the official
Marketplace Mock lane keeps SIM LIM's official rows (D-079). Each row now also keeps its own
source share class and currency (D-080), and no percentage, edge, party, identity,
denominator or cross-class sum is created. The 25% threshold, the Decimal engine, recursion
bounds, CAS, manual evidence authority and GoldTier protections are untouched, and
`apps/frontend` is byte-identical. I verified the Stage 2 evidence and it is bound to the
frozen tree. My own focused, physical, adversarial and mutation checks found no product
defect.

Three bounded documentation corrections are still required, all inside the reviewed tree
(§7):
- F1, Medium: the persistence contract's rollback statement for the registry cache is
  incomplete and misleading;
- F2, Low: two docs overstate the live evidence ("all HTTP 200");
- F3, Low: the `PROJECT_STATE.md` evidence bullet blurs which code (D-079 or D-080) the live
  run exercised.

Consequence: the candidate is not ready for publication until F1-F3 are remediated and
rechecked. The recheck is docs-only, but it must rerun the governance lanes, because the
routine context benchmark has 0.047 points of headroom (§4).

## Reviewed identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024`.
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`.
- HEAD = BASE = local `origin/main` = `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. The QG
  did not re-fetch.
- The frozen product content is the 38 paths in `git diff --name-only`, all unstaged. The
  recomputed tree is **`4944456a612e02b87a106e8bfe5d1408715840ee`**, built with a temporary
  index under the scratch `qg` folder (`git read-tree HEAD`, `git add` of the 38 paths,
  `git write-tree`). It matches the Stage 2 identity, and I recomputed it again after all
  checks with the same result.
- Excluded from the tree: the implementer report
  `.ai-pipeline/reports/SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_REPORT.md` and this report.
- All 38 product files were last modified at 07:26:42 +08. That is earlier than every Stage 2
  run: the chunks started at 08:16:40, the physical run ended at 08:39 and the E2E run at
  09:03.

## 2. Acceptance Checklist (assignment report §6)

| # | Scenario | Result | Direct evidence (QG) |
|---|---|---|---|
| 1 | Fresh Garden, Marketplace, direct-only overlay | PASS | Focused module 33/33. Sanitized live run 1 inspected (D-079 code) |
| 2 | Empty SIM LIM profile, shareholders present | PASS | `test_empty_profile_corporate_holder_...`. Live receipts: SIM LIM entity 15 bytes / 0 entities; shareholders 1 entity |
| 3 | Four rows, correct issuer and operation | PASS | Strict decoder UEN binding (`acra_bizfile_sandbox.py:427`); `RegistrySnapshotEntry` identity checks; live `returned_uen_equal=True` |
| 4 | Active / withdrawn | PASS | `OfficialShareholderObservation.only_active_rows_are_current`. Probe: withdrawn rows retained with `current_interest=False` |
| 5 | Fresh cache hit, no redundant calls | PASS | Repeat-onboarding test. Live case 2 has 0 receipts |
| 6 | Cache miss calls the operation | PASS | `test_a_fresh_d079_cache_entry_is_neither_reused_nor_rewritten`, where the V2 key misses and makes one read |
| 7 | Stale, empty, mismatch, malformed, grouping, 401/403, timeout, 5xx | PASS | 13-case failure parametrization and coordinator tests. QG hostile-class probe: safe `PROVIDER_FAILED`, nothing retained |
| 8 | No denominator, so no percentage or UBO | PASS | Mixed-class test and QG probe: 3 parties, LIM CHOON HUAT the only candidate, REVIEW_REQUIRED, bound 62.5 |
| 9 | Controlled complete same-class denominator | PASS (existing evidence) | Local synthetic engine arithmetic (`test_recursive_ownership_discovery.py:391`, `:465`). No Marketplace-lane denominator exists by design: building one would invent a capital source (Q-012) |
| 10 | Multiple branches without double counting | PASS | DIANA KOH 18.75 + 6.25 = 25 (`test_hybrid_five_layer_overlay.py:369`); Stage 2 full run |
| 11 | Unsupported corporate identifiers unresolved | PASS | No supplied verified identifier, so no recursion. The withdrawn FGH row is not used |
| 12 | Garden legacy and OPQ | PASS | Stage 2 full run (verified); QG focused regression 652/652 |
| 13 | Manual, versioning, persistence, readiness, no-replay | PASS | Stage 2 full and physical runs (verified); QG physical rerun 27/27 |
| 14 | Existing cases not rewritten | PASS | `test_a_case_analysed_before_d079_...`. QG probe: a v13 decode leaves the raw document unmodified, and only a later write emits v14 |
| 15 | No local holders passed off as ACRA's | PASS | `test_rows_named_like_the_local_fixture_...`. The dataset namespace stays `ACRA_API_MARKETPLACE_MOCK_V1` |

## 3. Contract and Integration Findings

**F1 - Medium (documentation/contract truthfulness, reproducible).**
`docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md:229` says "Old readers: a V1-only reader
never looks up the V2 key", and the schema-4 section gives no rollback statement. The code
behaves differently:
- `MongoRegistryCacheStore.initialize()` decodes every cache document at startup
  (`mongo_registry_cache_store.py:51`).
- QG probe: I extracted `ceefe1e` into scratch and gave its reader the cache documents
  written by the candidate.
  - The schema-4 `MARKETPLACE_SHAREHOLDERS_V2` entry was rejected.
  - Every D-080-written schema-2 ordinary acquisition entry with ownership parties was also
    rejected. These entries serialize `share_type: null` and `currency: null`, which the
    old strict model forbids.
  - Both raise `RegistrySnapshotRepositoryInvalidError`.
- So in Mongo mode with the registry cache enabled, rolling back after D-080 has written
  cache entries makes startup fail closed until the disposable cache collection is cleared.
  The behaviour is safe, but the contract implies a compatibility it does not have. The
  D-079 section (`:220`) states its own equivalent rollback consequence correctly.
- The implementer report (§5, line 203) likewise covers only case envelopes. Its phrase
  "fails closed on those cases" understates the effect: `MongoCaseStore.initialize()`
  (`mongo_case_store.py:178`) refuses startup on any v14 case, as earlier envelope bumps did.

**F2 - Low (evidence overstatement).**
`DECISION_LOG.md:483` ("2 token requests and 7 GETs, all HTTP 200") and
`ACRA_API_MARKETPLACE_MOCK_READINESS.md:127-128` ("9 genuine requests ... all HTTP 200")
claim more than was recorded. So does `:141` ("`coCapitalDetails` ... (×2) returned an
explicit empty collection").
- In the sanitized run-1 output, the status and entity count of the run-1 `coCapitalDetails`
  receipt were never printed. The output shows only that the read was dispatched, with no
  transport failure and no field paths.
- 8 of the 9 receipts recorded HTTP 200. The run-2 capital read recorded HTTP 200, 15 bytes
  and 0 entities.
- The implementer report admits this gap (§4, line 130) but still writes "All HTTP 200" in
  the same cell.
- The conclusion (SIM LIM has an empty capital collection) still stands on run 2.

**F3 - Low (evidence identity).** The D-080 candidate section of `docs/PROJECT_STATE.md`
(`:1013-1017`) lists the live verification as evidence and says "It retained SIM LIM's four
rows during a fresh Garden onboarding". It does not say that this onboarding ran the
pre-D-080 (D-079) code, or that D-080 share-class retention itself has offline evidence
only. `DECISION_LOG.md`, the readiness doc ("retained as D-079 official shareholder
evidence") and the implementer report (§4) all state this correctly.

Verified as correct:
- **Mock vs Live.** Every durable statement says Mock and never Live. The classification is
  `MOCK_INTEROPERABILITY_OBSERVED`, the provider matrix is unchanged, and no Sandbox, Live or
  GoldTier call was made.
- **Live-run bounds.** Run 1 used 1 token and 5 GETs. Run 2 used 1 token and 2 GETs. This
  matches the two owner approvals exactly.
- **D-080 scope.** The class is kept on D-079 official rows only. Registry cache schema 4 and
  envelope schema 14 are as approved. There is no mapping, class rule, weighting or
  calculation change.
- **No new identifiers or PII.** The docs diff and the implementer report contain only the
  UENs `11111999A` and `111111111M`. The holder names in the implementer report already
  appear in tracked HEAD files. `DECISION_LOG.md` lists rows by number only.

**Unresolved sponsor authority (not defects):**
- Q-004: share-class economic and control rights;
- Q-012: Marketplace capital and denominator semantics, `coCapitalDetails` DTO, and whether
  corporate `shareholderId` is a registration number;
- Q-019: person identity.

These correctly block any SIM LIM percentage. Proposals P-A to P-E remain unadopted
proposals.

## 4. Tester and Adversarial Findings

**Stage 2 evidence, verified against the frozen identity:**
- **Chunk JUnit totals:** 732 + 991 + 653 + 786 = 3162 collected, 2987 passed, 175 skipped,
  0 failed, 0 errors.
- **Skip reasons:** 169 are physical Mongo tests without a URI. The other 6 are
  `test_s2_local_ocr::test_real_local_ocr_acceptance`, skipped because Tesseract is
  unavailable, so they are not "physical-only" as the implementer report (line 292) says.
  These OCR tests are unrelated to this change.
- **Two stalled single-process runs:** both logs show `Timeout (0:05:00)` inside
  `socket._fallback_socketpair`. The ENVIRONMENT-BLOCKED classification is confirmed.
- **Physical:** `physical.log` shows PASSED, 25 suites, 169/169.
- **E2E:** `e2e.log` shows 115/115 PASS, exit 0.

**QG commands (worktree `app` verified first on the path):**

| Check | Result |
|---|---|
| Focused `test_official_shareholder_evidence.py` | 33 passed |
| Focused regression, 12 modules (hybrid overlay, recursive discovery, phase12/13 persistence, slice A, discovery policy, S2 security, classification, manual evidence, target continuation, zero-touch, five-layer journey) | 652 passed, 0 skipped, 340 s |
| Physical `test_recursive_ownership_real_mongo.py` and `test_phase12_real_mongo.py` on disposable loopback mongo:7 (`sim-lim-d080-mongo`), with generated allowlisted DBs and the URI never printed | 27 passed, 0 skipped |
| Ruff check `app tests` (no cache) | PASS |
| Ruff format, changed test files | formatted. Two app model files are unformatted at base too (pre-existing; CI runs only `ruff check`) |
| mypy `app` (scratch cache) | no issues, 129 files |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | 55 OK. Routine benchmark 30.047% (35.632 / 20.961 / 33.547) against the 30% floor |
| Contract 44, delivery assets 4, secrets 8, pre-PR 64, policy authority 14, provider readiness 19, skill pointers 7 | all OK |
| `check_project_state`, `check_architecture`, `check_secrets`, `check_policy_authority`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | clean; identical (38 files, +664/-84) |
| Untracked implementer report hygiene | 0 trailing-whitespace lines, 0 tabs, final newline present |

**Adversarial probes (scratch scripts, synthetic data only):**

- **Decoder, candidate vs `ceefe1e` (19 cases).**
  - Rejected with `AcraMalformedResponseError`: int, bool, list or dict values; more than 64
    characters; NUL, newline or zero-width (Cf) characters. This also applies to a withdrawn
    row, because the collection is validated before filtering.
  - Accepted: blank, empty or null values become `None`; padded values are trimmed; exactly
    64 characters is kept.
  - The base decoder ignored every one of these values.
  - Effect on a COMPANY-form ordinary acquisition with a 65-character class: L2 changes from
    `PROVIDER_PARTIAL/OFFICIAL_QUANTITY_PRECLUDES_OVERLAY` to
    `PROVIDER_FAILED/REGISTRY_OPERATION_MALFORMED_RESPONSE` and stays REVIEW_REQUIRED.
  - This is an acceptable fail-closed posture (N4).
- **Mixed-class message (journey probes):**
  - A withdrawn row with a different class is not flagged.
  - One current row with no class plus one Ordinary row is flagged ("unreported counts as
    one", as documented).
  - When no current row reports a class, the D-079 text is unchanged.
  - Case variants (Ordinary vs ORDINARY) are flagged as mixed, and a currency difference is
    not flagged (N5).
  - The message is at most 188 characters in the probes. The worst case, 6400 rows, gives
    191 characters, within the 200 limit.
  - A hostile class makes the read `PROVIDER_FAILED` with 0 rows retained.
- **Persistence (18 cases).**
  - v14 round-trips.
  - v13 with explicit null, or with the keys absent, reads into v14.
  - v13 with a currency only, or a share type only, is rejected with
    `PersistenceDataInvalidError`, and so is the exact `DurableCaseSnapshotV13` model.
  - The helper rejects a class inside `prior_analyses`.
  - v12 with rows is rejected. v15 raises `PersistenceSchemaUnsupportedError`.
  - A v13 read does not mutate the raw document, and re-encoding it writes 14.
  - Cache rules hold: V1+schema 3 is valid; V2+schema 3 is invalid; V2+schema 4 is valid;
    V1+schema 4 is invalid.
  - Also invalid: a V1 row with a currency only, a V1 row with an empty class, and a schema
    given as the string "4". The V1 and V2 key digests differ.
- **Forward compatibility.** A D-079-shaped schema-2 entry (no class keys) still decodes. A
  schema-2 entry that carries a class is rejected.
- **Rollback.** The base reader rejects candidate documents, as described in F1.
- **Mutation testing (scratch copy, never the worktree; 7 mutants).** 5 were killed and 2
  survived.

  | Mutant | Result |
  |---|---|
  | M1: ordinary bundles keep the class | killed, but only by `test_hybrid_five_layer_overlay::test_official_shareholder_rows_are_never_overridden_by_the_overlay`, not by the dedicated D-080 test (N2) |
  | M2: mixed check ignores `current_interest` | **survived** (N1) |
  | M3: v13 class rejection disabled | killed |
  | M4: schema-3 class check removed | killed |
  | M5: bundle class rejection removed | killed |
  | M6: discovery drops `share_type` | killed |
  | M7: portfolio version list omits 13 | **survived** in unit modules (N3) |

**Test quality:**
- The new tests are mostly falsifying: v13/v12 rejection, V1 non-reuse, exact pairing, the
  message variant, and per-row classes.
- I checked all 38 mechanical schema pins in 18 files. They are 13 → 14, plus the two
  unknown-version sentinels 14 → 15 (`test_phase12_persistence.py`,
  `test_slice_a_legacy_compatibility.py`). No legacy-read assertion was weakened.

**Not run by the QG:**
- The GoldTier-examples lane: it needs an extra requirements install, which this gate
  forbids. It is unaffected, and the implementer's evidence is reused.
- Frontend checks: the frontend is byte-identical.
- The full single-process backend run: the chunked Stage 2 evidence was verified instead.
- Hosted CI: the content is uncommitted.
- The live Mock run: it cannot be re-observed. Its sanitized outputs `live.json` and
  `live2.json` were inspected and contain no credential-like content.

## 5. Code and Architecture Review

- **Owners unchanged.**
  - Decoder: `acra_bizfile_sandbox.py:369-370`.
  - Payload: `acra.py:178-179`.
  - Ordinary normalization drops the class; only `_normalize_shareholder_evidence_party`
    keeps it (`registry.py:85`, `:91-95`, `:198`).
  - Bundle validator rejects a class (`models.py:303-307`).
  - Exact contract/schema pairing (`models.py:619-640`).
  - The coordinator writes schema 4 (`registry_acquisition.py:377`).
  - The observation field (`ownership.py:379-380`) uses `SafeOptionalIdentifier`, and a
    `ValidationError` there maps to `PROVIDER_INVALID` (`ownership_discovery.py:545`).
  - Message variant only (`ownership_analysis.py:1178-1193`).
  - Envelope 14 with an exact V13 reader (`persistence/models.py:688-723`, `:846-859`);
    reader wiring in `mongo_case_store.py:86`, `:602`, `:611-612`, `:673-676`.
- **API.** Additive `share_type`/`currency` on `discovery.records[].official_shareholders`
  through the domain `OwnershipDiscoveryAudit` (`api_models.py:547`).
  `BrowserRegistryOwnershipParty` is built from attributes (`from_attributes`), so ordinary
  bundles still project no class. The frontend does not reference these fields.
- **Untouched.** The engine, 25% threshold, path arithmetic, recursion bounds, CAS, manual
  evidence, readiness and GoldTier code are not in the diff. There is no scope creep and no
  new endpoint or operation.
- **Test design (Low).**
  - N1: the current-interest filter of the mixed check is never falsified.
  - N2: the comment in `test_ordinary_acquisitions_never_carry_a_share_class`
    (`test_official_shareholder_evidence.py:424`) is inaccurate. The local lane builds its
    payloads without a class (`garden_business.py` `derive_issuer_direct_ownership`), so the
    first half of the test cannot fail if the `registry.py:85` drop regresses.
  - N3: the portfolio projection of v13 is not unit-tested, and physical tests prove only
    the v13 rejection path (`test_recursive_ownership_real_mongo.py:341`), not a positive
    v13 read.

## 6. Security Review

No security finding.
- Source text is bounded to 64 characters and free of control characters. It is never
  mapped, compared for policy, logged or rendered by the UI. HTML-like text is kept
  verbatim as data, like other source names, and the JSON API returns it as data.
- Issuer binding is unchanged. A tampered cache entry fails closed: an empty or mismatched
  class, or a schema/key mismatch, raises `ValidationError` or
  `RegistrySnapshotRepositoryInvalidError`.
- Live-run hygiene, as far as observable: verified TLS, no proxy inheritance, no redirects,
  an allowlisted host, operations and UENs, and hard caps. The sanitized outputs contain no
  credential-like strings.
- `.env` was used only under the owner's two in-chat authorizations. The implementer
  report's "never opened by me" (line 41) is imprecise, because its scratch script read two
  keys from the file in memory (N6).
- No secret, URI, raw payload or new identifier is tracked.
- Deferred hardening: N4. Record in the contract that hostile `shareType`/`currency` values
  now fail ordinary COMPANY-form acquisitions and the diagnostic path closed. Today this is
  stated only in the implementer report.

## 7. Required Fixes (documentation only; no code or test change)

1. **F1.** In `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md` (schema-4 section,
   `:229`), replace or extend "Old readers" with an accurate rollback statement:
   - a pre-D-080 version's startup scan fails closed on schema-4 entries;
   - it also fails closed on D-080-written schema-1/2 entries that hold ownership parties,
     because these serialize null `share_type`/`currency`;
   - rollback therefore requires clearing the disposable registry cache collection.
   Optionally mirror this in the D-080 persistence bullet of `DECISION_LOG.md`.
2. **F2.** In `docs/decisions/DECISION_LOG.md:483` and
   `docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md:127-128, :141`, qualify "all
   HTTP 200" and "(×2) ... explicit empty collection":
   - 8 of 9 receipts recorded HTTP 200;
   - the run-1 capital receipt was not recorded;
   - the run-2 capital read recorded HTTP 200, 15 bytes and 0 entities.
3. **F3.** In `docs/PROJECT_STATE.md:1013-1017`, state that the live onboarding exercised
   the pre-D-080 (D-079) code, and that D-080 share-class retention has offline evidence
   only. Keep the wording compact: the routine benchmark headroom is 0.047 points.

**Recheck scope after remediation:**
- `git diff --check` and the EOL comparison;
- the dev-context, project-state and architecture unittest lanes, including the benchmark
  (it must stay at or above 30%);
- `check_project_state`, `check_architecture`, the secrets lane and the contract lane;
- a fresh independent review of the changed delta.

Backend, physical and E2E behavioural evidence is unaffected by doc-only edits and can be
reused.

**Recommended, non-blocking (accepted residual or outside the reviewed tree):**
- N1: add a mixed-class case where only a withdrawn row differs.
- N2: correct the test comment, or point the test at a Marketplace COMPANY-form bundle.
- N3: optional coverage for the v13 portfolio projection and a positive physical v13 read.
- N4: document the fail-closed decoder change in `ACRA_MOCK_API_PROFILE.md` or D-080.
- N5: case-sensitive class comparison, and currency not compared. Message only, informational.
- N6: corrections to the implementer report before it is tracked:
  - line 162: "19 → 24 test functions" should be 13 → 18 (23 → 33 collected is correct);
  - line 292: the skips are 169 physical Mongo plus 6 Tesseract OCR;
  - line 223: the positive v13 read is unit-only;
  - line 203: the rollback statement understates the effect (startup refusal, plus the
    cache);
  - line 41: the `.env` wording;
  - line 130: "All HTTP 200" sits beside the admitted reporting gap.

## 8. Readiness

- **Publication readiness:** NOT READY. F1-F3 need bounded remediation, then a fresh
  independent recheck of that delta (Stage 1 to Stage 3). Commit, push and PR then need
  explicit owner authorization.
- **Next-phase readiness:** not applicable. No next phase is authorized or begun.
- **Live ACRA readiness:** not claimed. The evidence is `MOCK_INTEROPERABILITY_OBSERVED`
  only. The Marketplace denominator, capital and class semantics (Q-012) and class rights
  (Q-004) remain open sponsor authority.
- **Real GoldTier integration readiness:** unaffected and not claimed. SIM LIM keeps the case
  REVIEW_REQUIRED, so readiness and GoldTier stay blocked.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE =
  `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (local `origin/main`).
- 38 tracked files modified and unstaged. Staged: none. The real index was untouched; the
  tree was computed only through temporary index files under the scratch `qg` folder.
- Untracked: the implementer report and this QG report. This report is the QG's only
  repository write.
- Six checker stdout files were briefly written to `C:\Users\shane\AppData\Local\Temp\`
  and immediately moved into the scratch `qg\checkers` folder. Nothing else was written
  outside the scratch `qg` folder.
- No implementation fix, test or config edit, stash, commit, push, PR, merge or next phase
  occurred. No `.env` was opened, no ACRA or GoldTier host was contacted, no process the
  QG did not start was touched, and `clm_poc` was never connected to.
