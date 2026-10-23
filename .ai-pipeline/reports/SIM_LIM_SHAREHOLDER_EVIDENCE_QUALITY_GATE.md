# SIM LIM official shareholder evidence (D-079) — independent Stage 3 Quality Gate

Reviewer: independent QG run (did not author or remediate the candidate), 2026-10-24.
Skill: `fyp-quality-gate`. Read-only review. This report is the only file written to the
worktree.

## 1. Executive result

**PASS WITH MINOR FIXES.**

Every substantive acceptance criterion was verified independently: trigger scope, issuer
binding, provenance, no manufactured identity/edge/percentage, unchanged
review/readiness/GoldTier safeguards, failure safety, cache schema 3, envelope schema 13,
counters, and the Garden/OPQ/legacy/local-lane regressions. The verification used code
inspection, targeted tests, a physical Mongo rerun, an isolated browser selector rerun,
17 mutants, adversarial probes and a BASE-vs-candidate behavioural diff.

One bounded, documentation-only correction is required (MF-1). An affected durable demo
document still describes the pre-D-079 SIM LIM outcome, and D-079 slightly misstates
what the unchanged UI shows. Nothing security-, contract-, arithmetic- or
false-success-related remains. After MF-1, the doc-only delta needs a fresh independent
review. The product-code evidence below stays valid if no product path changes.

## 2. Frozen identity (verified at start and end)

| Item | Observed |
|---|---|
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\sim-lim-shareholder-evidence-20261024`, `feat/sim-lim-official-shareholder-evidence-20261024`, no upstream |
| HEAD = BASE = `origin/main` | `2d8b84af46f2ac0f1d94965ca638e1cd7a1c7e54` |
| Candidate paths | 37 (`git status --porcelain=v1 -uall`): 34 modified, 3 untracked (new test module and two implementer reports). Real index: 0 staged |
| Full-candidate tree (temp index in reviewer scratch: `read-tree HEAD`, `add -- <37 paths>`, `write-tree`) | `3c550c38e5d3ce94e45bf37cd46c39183d92ace8` — matches, at start and end |
| Product tree (35 paths, without `.ai-pipeline/reports/`) | `e88d7a34d0a670f4a7dda90bd0618f8dae32f105` — matches, at start and end |
| `apps/frontend` | Tree `3c5ba18036c14d007779f8deaa874baef240a858` at BASE and in the product tree. 0 differing paths; no working-copy change |
| EOL churn | `git diff --stat` is identical to `git diff --ignore-cr-at-eol --stat` (34 files, +895/−58) |
| Whitespace | `git diff --check` is clean. Untracked files have 0 trailing-whitespace lines and 0 tabs. The test and proposal are LF and the implementer report is CRLF; all normalize to LF on add, so no blob churn |

The end check reused the saved 37-path list. This report is a separate, new untracked
path and is not part of either frozen tree.

## 3. Acceptance checklist

| # | Requirement | Result | Direct evidence |
|---|---|---|---|
| 1 | Frozen trees; frontend byte-identical | PASS | §2 |
| 2a | Uses the actual `AcraApiMarketplaceMockConnector`, never `MockAcraConnector` | PASS | `supports_shareholder_evidence` = `company_shareholders_only` (set only for `api_marketplace_mock`, `composition.py:160`) **and** `isinstance(connector, AcraApiMarketplaceMockConnector)`. `retrieve_shareholder_evidence` raises `AcraOperationUnsupportedError` otherwise. In the local lane, `acquire_subsidiary_shareholder_evidence` returns `None` with no call (test plus mutant M1 killed) |
| 2b | Only non-overlay corporate holders with a verified SG UEN, after a definitive entity NOT_FOUND (fresh or negative-cache hit) | PASS | Only `_acquire` runs it, which needs `_ineligible` to pass (`_verified_uen`, SG, not duplicate, depth). It runs only in the `else` branch after `issuer_overlay is None`, and only when `_classify` returns `NOT_FOUND`. That happens only for `bundle is None`, meaning explicit empty `entities` or a negative-cache hit; errors raise instead. Probes: profile present → `PROVIDER_UNSUPPORTED`, no extra read (P3). Entity 500 → `PROVIDER_FAILED`, no read (P4). Repeat run on the negative-cache hit reuses the cached rows (test) |
| 2c | OPQ overlay issuers, `garden_legacy_supplement` and the local synthetic lane make no shareholder-only read | PASS | Lane test, plus BASE-vs-candidate diff: OPQ and legacy outputs and call counters are identical to BASE. Legacy: discovery needs `source.relationships` and a discovery source classification, and the Marketplace lane yields no registration identifiers, so the trigger is structurally unreachable there. Mutant M7 (trigger on any rejection) is killed by the existing D-077 test `test_an_officially_found_non_scenario_issuer_stays_unresolved` |
| 3a | Issuer binding | PASS | The decoder requires exactly one entity with UEN == request, a present collection, no grouping, a Corporate/Individual category, and exact units. `_retrieve_collection` re-binds `payload.uen` and the MOCK environment. The coordinator and discovery re-check `requested_identifier`. Mutants: either binding layer alone survives (defence in depth), both removed are killed (M6a/M6b/M6c) |
| 3b | Row retention and provenance | PASS | Probe P1 (owner-reported shape: 1 Corporate and 3 others, no percentages): 4 rows. Corporate → `LEGAL_ENTITY`, Individual → `NATURAL_PERSON`; exact units; withdrawn `current_interest=False`; `registration_identifier=None`. Provenance is `ACRA_REGISTRY_ACQUISITION`/`MOCK`/`ACRA_API_MARKETPLACE_MOCK_V1`/`OWNERSHIP_PARTIES` (Literal-pinned in the model). `current_interest` matches only `strip().casefold()=="active"`; `Ceased` and missing status → False (P7c). A validator enforces it, and envelope tampering is rejected |
| 3c | No identity/legal form/graph party/edge/percentage; branch unresolved; issue added; safeguards unchanged | PASS | BASE-vs-candidate diff for Garden hybrid with rows: the only differences are SIM LIM `NOT_FOUND→PROVIDER_PARTIAL`/`OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, one extra `SHAREHOLDERS:111111111M` call, and one added `OWNERSHIP_DENOMINATOR_REQUIRED` issue (affected `111111111M`). These are identical to BASE: issues `INCOMPLETE_LEGAL_ENTITY`, `CORPORATE_OWNERSHIP_UNRESOLVED`, `SYNTHETIC_OWNERSHIP_EVIDENCE`, `UBO_REVIEW_REQUIRED`; candidate LIM CHOON HUAT `INDETERMINATE`/`REVIEW_REQUIRED` (synthetic basis `MET`); 2 edges; 3 parties; bound 62.5; flags; counters; state `REVIEW_REQUIRED`. The API test asserts the `OWNERSHIP_REVIEW_REQUIRED` blocker, `goldtier_result` None and submission None |
| 3d | No recursion into FGH SERVICES, INC. | PASS | The corporate row has no registration identifier. Discovery records are only `{111111111M}` (test and P1) |
| 4 | Failure safety | PASS | Parametrized test (8 cases): grouping, missing collection, UEN mismatch, float units, timeout, 401, 403, 500 → `PROVIDER_FAILED` with a safe code, nothing retained, not cached (2nd run re-reads). Empty → `NOT_FOUND`/`OFFICIAL_SHAREHOLDERS_EMPTY`, cached (one call in two runs). Probes: cache read failure → `CACHE_FAILURE`/`REGISTRY_CACHE_READ_FAILED` with no provider call (P5). Cache write failure → `CACHE_FAILURE`/`REGISTRY_CACHE_WRITE_FAILED` (P5b). Busy → `HARD_LIMIT`/`REGISTRY_ACQUISITION_BUSY` (P6). Duplicate ids → `PROVIDER_FAILED`, not cached (P7). 65 rows → `REGISTRY_OPERATION_MALFORMED_RESPONSE` (P7b). All stay `REVIEW_REQUIRED` with bound 62.5 |
| 5 | Cache | PASS (A-2 advisory) | Same repository, `_key_lock` and CAS `_write`. The key differs only by `acquisition_contract_version=MARKETPLACE_SHAREHOLDERS_V1`; the ordinary key stays absent (test). The schema-3 validator rejects acquisition, negative result, effective time, non-MOCK, FAILED, identifier, provider or env mismatch, and anchor ≠ retrieval or write-before-retrieval. COMPLETE uses the policy window and EMPTY the negative TTL: boundary test at 90 d and 600 s, and mutant M9 is killed. FAILED is never written (M3a/M3b killed). The Mongo codec round-trips (test). The physical test asserts one schema-3 document and zero-call reuse after restart. Schema-1/2 keys and validation are unchanged; candidate code reads BASE-written schema-2 entries (probe). See A-2 for rollback |
| 6 | Envelope schema 13 and legacy rejection | PASS | Codec probe on a candidate envelope: v12/v11/v10/v9/v5/v1 with rows → rejected. v12 with only `OFFICIAL_SHAREHOLDERS_EMPTY` → rejected; with that reason removed → reads as 13. Explicit `[]`/`null` keeps the legacy meaning (reads as 13). Lookup alone → rejected. v12 `prior_analyses` carrying D-079 content → rejected. Mutant M10b (V12 validator plus store pre-check removed) is killed; M10a survives only because the store pre-check duplicates it. All 37 test-pin edits are mechanical (35 `12→13`, 2 unknown sentinels `13→14`), with no assertion removed or weakened |
| 7 | Counters and budget | PASS (A-1 coverage gap) | Probe P2: entity negative-cache hit plus shareholder read reaching the provider → `(lookups, backed, hits) = (1, 1, 0)`. Full cache reuse → `(1, 0, 1)`. Failures, busy and cache errors count as provider-backed (conservative, matching the existing first-read rule). `OwnershipDiscoveryAudit` enforces `backed + hits == lookups`. The read honours the discovery deadline (`cancelled`). The budget stays per-issuer, as before |
| 8 | Regression-test quality | PASS (A-1) | 19/19 new tests and 4/4 physical tests pass. Of 17 mutants, 11 are killed. Survivors: M6a, M6b and M10a, each redundant with a second layer, plus M8 and M12, which are genuine coverage gaps (A-1) |
| 9 | Docs accurate; no overclaim | PASS WITH MF-1 | D-079, the ACRA profile, cache profile, ownership profile, ADR-013 amendment, ARCHITECTURE and PROJECT_STATE JSON (13) match the code. Authority is `USER_AUTHORIZED_POC`/`PROJECT_DEFINED_PROVISIONAL`, with no Live/legal/sponsor claim, and Q-004/Q-012/Q-019 stay open. Gaps: MF-1, A-2 and A-3 |
| 10 | Browser evidence and selector-14 classification | PASS (defensible; see §5.4) | Isolated rerun on the frozen candidate: 1/1 PASS (14.1 s), "guarded authenticated local Mock browser suite" |

## 4. Contract and integration findings

- **Authority.** D-079 is recorded as an owner-authorized POC exception to the "company
  shareholder operation only for a recognized COMPANY legal form" rule. It is not
  sponsor-confirmed. The Marketplace denominator and relationships (Q-012), UBO policy
  (Q-004) and person identity (Q-019) remain open. Provider classifications are
  unchanged (MOCK); the PROJECT_STATE JSON was only bumped to envelope 13.
- **No contradictory example promoted.** The old synthetic SIM LIM 900/100/100 subtree
  is not attached in the hybrid lane: parties are exactly Garden, SIM LIM and LIM CHOON
  HUAT. The coordinator's shareholder path never consults the local synthetic seed
  identity.
- **Mapping.** No new field mapping. The connector and decoder are unchanged.
  `_normalize_ownership_party` is a behaviour-preserving extraction of the existing
  lambda, reused by the new path.
- **API/UI.** `discovery.records[].official_shareholders` and
  `official_shareholder_lookup` are additive. The unchanged frontend has no runtime
  schema validation, and `OWNERSHIP_DENOMINATOR_REQUIRED` is already in its union type.

## 5. Tester and adversarial findings

### 5.1 Commands and results (this session, frozen content)

All Python runs used the repo venv with PYTHONPATH pinned to the worktree; `import app`
resolved into the worktree.

| Check | Result |
|---|---|
| Focused pytest, 19 modules: `test_official_shareholder_evidence`, `test_hybrid_five_layer_overlay`, `test_five_layer_hybrid_journey`, `test_recursive_ownership_discovery`, `test_phase12_persistence`, `test_slice_a_legacy_compatibility`, `test_phase16_registry_cache`, `test_phase24c_registry`, `test_phase10_registry_acquisition`, `test_acra_api_marketplace_mock_connector`, `test_acra_diagnostics`, `test_ownership_discovery_policy`, `test_manual_ownership_evidence`, `test_slice_b_registry_demo`, `test_s2_persistence_security`, `test_phase13_priority`, `test_classification_conflict_review`, `test_target_classification_continuation`, `test_zero_touch_orchestration` | JUnit: **810 passed, 0 failed, 0 errors, 0 skipped**, 373.9 s |
| New D-079 module alone | 19 passed |
| Contract lane (`unittest discover -s ../../tests/contract`) | 44 tests OK |
| Physical Mongo: `tests/test_recursive_ownership_real_mongo.py` against the task-owned disposable `sim-lim-d079-mongo` (`mongo:7`, loopback 27221, generated ephemeral databases) | **4/4 passed** (3.9 s), including the new D-079 restart/schema-12 test. Afterwards only `admin,config,local` remained. Disclosure: I ran the whole 4-test module, not only `-k official_shareholder`; the other 3 are pre-existing tests in the same module, on the same disposable container |
| `ruff check .` (apps/backend, CI form); `ruff check scripts tests` (root) | All checks passed (both) |
| `ruff format --check` on the new and changed physical test | 2 files already formatted |
| `mypy app` (cache in reviewer scratch) | Success: no issues in 129 source files |
| `check_project_state`, `check_architecture`, `check_secrets`, `check_policy_authority` | PASS ×4 |
| Browser: `run_e2e.py --timeout-seconds 60 --grep "review-ready actions render after authoritative current document evidence loads"` (Tesseract on PATH, synthetic Mongo port 27221) | **1 passed** (14.1 s) |

Not rerun, by instruction: full backend suite, full physical suite and full browser
suite. The implementer's figures (3148/0/175 skipped; 169/169 physical; 115/115 browser
on run 3) are reused as implementer evidence. They are consistent with every independent
spot-check above but were not re-executed by this gate.

### 5.2 Mutation testing

Each mutant is a scratch copy of `apps/backend/app` placed first on PYTHONPATH (the
worktree was never touched), run against the new module. Survivors were re-run against
9 related modules (229 tests). The baseline copy passed 19/19.

| Mutant | Result |
|---|---|
| M1 `supports_shareholder_evidence` always True | KILLED |
| M2 withdrawn rows current (validator off and discovery marks any status current) | KILLED |
| M2b observation "only Active is current" validator removed | KILLED |
| M3a coordinator caches FAILED | KILLED |
| M3b coordinator caches FAILED and the schema-3 validator allows FAILED | KILLED |
| M4 rows treated as resolving the branch (no `CORPORATE_OWNERSHIP_UNRESOLVED`) | KILLED |
| M5 `OWNERSHIP_DENOMINATOR_REQUIRED` issue skipped | KILLED |
| M6a adapter UEN re-binding removed | survived (decoder still binds) |
| M6b decoder UEN binding removed | survived (adapter still binds) |
| M6c both bindings removed | KILLED |
| M7 trigger on any `_classify` rejection, not only NOT_FOUND | KILLED (existing D-077 test, broader run) |
| M8 issuer counter ignores the shareholder read | **SURVIVED (229 tests)** — A-1 |
| M9 EMPTY uses the policy window, not the negative TTL | KILLED |
| M10a V12 reader validator removed | survived (store pre-check duplicates it) |
| M10b V12 validator and store pre-check removed | KILLED |
| M11 lookup always `SHAREHOLDERS_FETCHED` | KILLED |
| M12 COMPLETE evidence written even when expired at bind time | **SURVIVED (229 tests)** — A-1 |

### 5.3 Adversarial and behavioural probes (offline, synthetic rows, 0 external calls)

- **BASE vs candidate.** The same script ran on a BASE `git archive` extract and on the
  candidate. The only differences are the D-079 deltas listed in §3, rows 3c and 4
  (empty rows: the reason `null → OFFICIAL_SHAREHOLDERS_EMPTY` plus one call). OPQ
  five-layer and the Garden legacy supplement lane are byte-identical in outcome.
- **Probes.** P1–P7 are summarised in §3. P8: schema-2 negative entries now serialize
  `shareholder_evidence: null` (A-2).

### 5.4 Selector-14 browser classification — reviewer view

The implementer classified the two full-run stops at `authenticated-zero-touch.e2e.ts:1248`
as an intermittent test race not attributable to this change. I find this **defensible**:
- The failure is a Playwright `Network.getResponseBody` protocol error while reading the
  body of the first `/documents` response after `page.goto`. This is a browser-side race
  (the body was evicted after a refetch), not a backend assertion.
- `run_e2e.py` gives every selector its own isolated lifecycle, so earlier selectors do
  not share backend state with it.
- `--keep-going` changes behaviour only after a failure, so run 3's
  `E2E SUITE PASS: 115` is a normal acceptance pass (verified in `run_e2e.py`).
- The test uses the local Mock lane (UEN `202400001A`), where the D-079 read is
  unreachable (`supports_shareholder_evidence` is False). The frontend and the E2E source
  are byte-identical to BASE.
- My independent isolated rerun on the frozen candidate passed.

Residual caveat: two consecutive full-run failures at the same position show a
non-trivial flake rate under full-suite load. The failure was never reproduced on base
under full-run conditions; only the first-14 sequence ran on base. Nothing further is
required for this candidate. Track it separately as a known flake (A-6).

## 6. Code and architecture review

- Owners are preserved:
  - one registry coordinator: same repository, locks and CAS, plus a separate
    single-flight key;
  - one provider adapter: same connector, decoder and `_retrieve_collection`;
  - one discovery scheduler: same issuer lookup and counters;
  - one Decimal engine, unchanged; rows never enter `OwnershipSourceResult`.
- No route-to-Mongo access, frontend authorization, direct ACRA→GoldTier mapping or
  ledger bypass was added.
- Validation is fail-closed at every layer:
  - `RegistryShareholderEvidence` checks count, uniqueness, operation provenance and the
    absence of a percentage;
  - the schema-3 entry is exclusive;
  - `OfficialShareholderObservation` pins provenance Literals and the Active-only rule;
  - the discovery-record validator ties rows, lookup, outcome and reason together.
- Scope: the 35 product paths are all on-task. There are no dependency, lockfile,
  config or generated-file changes. One small refactor (`_normalize_ownership_party`)
  is justified by reuse.
- Low-severity observations (advisory, not defects):
  - A-4: an evidence-construction `ValidationError` (for example duplicate ids) surfaces
    as `SHAREHOLDER_PROVIDER_FAILED`, not the standard
    `REGISTRY_OPERATION_MALFORMED_RESPONSE`. It is safe and not cached.
  - A-5: a row valid at registry level but invalid for the observation model would leave
    COMPLETE evidence cached while each analysis reports `PROVIDER_INVALID`. This is safe,
    and practically unreachable because the constraints are equivalent.
  - A-8: EMPTY is negative-cached (600 s), so rows that newly appear during the TTL are
    not seen. This follows the approved P1 design.

## 7. Security review

- No secrets. The physical test uses the established synthetic `SecretStr`
  placeholders, also used in four existing test modules. `check_secrets` passes; manual
  scans of the diff and untracked files found no tokens, URIs or keys.
- No live calls: offline transports only, no credential use.
- No raw payloads are persisted. `evidence_reference` is the existing opaque reference;
  query-free endpoint provenance stays connector-internal.
- Logging and errors use safe codes only.
- The reports cite only the corporate holder name given in the owner assignment. They
  contain no natural-person KYC data, document bodies or credentials.
- A-7 (low): source shareholder identifiers are persisted and projected on the API. This
  is the same class as the existing ownership-party ids. It is acceptable for Mock data,
  but a Live use would need PII review.

## 8. Findings

### Required fix (minor, documentation only)

**MF-1 — affected durable documentation not current (Low).**
- `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md` §8 still says SIM LIM's "historically empty
  profile becomes `NOT_FOUND`". With D-079 the hybrid lane yields:
  - `PROVIDER_PARTIAL` / `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, with rows
    retained beside the graph and an added `OWNERSHIP_DENOMINATOR_REQUIRED` issue, when
    the shareholder operation returns rows (as this doc's own §2 table says it does);
  - `NOT_FOUND` / `OFFICIAL_SHAREHOLDERS_EMPTY` when it is empty.

  The branch still stays unresolved, so this is not a false-success claim. AGENTS.md
  completion still requires affected durable documentation to be current.
- In the same correction, the D-079 entry (`DECISION_LOG.md`) says "only the issue
  message is visible". The unchanged discovery table (`OwnershipPathExplorer.tsx:56`)
  also shows the outcome label and reason code ("Incomplete registry evidence ·
  OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE"). Reword it as: the rows are not
  rendered; the outcome/reason and the issue are visible.

### Advisory (not required for this candidate)

- **A-1 test coverage:**
  - Pin the counter rule when only the shareholder read reaches the provider (M8): entity
    negative-cache hit plus shareholder miss → `provider_backed_lookups == 1`.
  - Add tests for shareholder-read `CACHE_FAILURE` and `HARD_LIMIT` outcomes (verified by
    probes P5, P5b and P6, but untested).
  - Cover expiry crossing during the shareholder acquisition (M12).
  - Optionally add per-layer issuer-binding unit tests and per-field v12 rejection tests.
- **A-2 rollback note:** schema-1/2 registry cache documents written by the candidate
  carry `shareholder_evidence: null`. BASE code cannot decode them; it fails closed with
  `RegistrySnapshotRepositoryInvalidError`, which becomes `CACHE_FAILURE`. The candidate
  reads BASE-written entries fine. #67 (schema 2 / `negative_result`) set the same
  precedent. Consider qualifying "schema1/schema2 entries and keys are untouched" as
  "read, validation and keys unchanged; newly written documents add a null field".
- **A-3 PROJECT_STATE prose:** the envelope-compatibility paragraph (about lines 142–150)
  still describes v12/D-077 reading v1..v11 as current. The JSON (13) and the new bottom
  section are correct, and `check_project_state` passes.
- **A-4, A-5, A-7, A-8:** see §6 and §7.
- **A-6:** track the selector-14 `getResponseBody` flake separately. Possible hardening:
  read the body through `page.request`, or capture it before follow-up navigation.

### Implementer report factual check

The claims checked are true:
- 19 tests and 37 pin lines;
- the product tree identity;
- one extra GET on a miss and zero on a repeat;
- Garden's four issues retained;
- `--keep-going` semantics;
- contract 44, mypy 129 files, ruff PASS.

Its phrase "Only the issue message is visible" carries the same imprecision as MF-1.

## 9. Readiness

- This candidate becomes ready for publication-stage steps once MF-1 is remediated and
  the doc-only delta passes a fresh independent review. That review can reuse the
  product-code evidence above if no product path changes.
- Commit, push and PR still need explicit owner authorization.
- Live ACRA Marketplace verification and real GoldTier integration readiness are
  **not established**. All evidence is offline (`AUTOMATED_OFFLINE_SIMULATION`); live
  onboarding is NOT_RUN; sponsor questions Q-004, Q-012 and Q-019 remain open.

## 10. Git status and reviewer conduct

- Branch `feat/sim-lim-official-shareholder-evidence-20261024`, HEAD = BASE
  `2d8b84af46f2ac0f1d94965ca638e1cd7a1c7e54`.
- 37 candidate paths are unchanged. Both frozen trees were re-verified with a temporary
  index in reviewer scratch. The real index has 0 staged entries.
- The only worktree write is this report, a new untracked file.
- No git mutation: no add to the real index, commit, stash, reset, checkout, clean or
  push. No implementation fix. No next phase started.
- Incidental ignored artefacts:
  - my first two pytest invocations ran without `PYTHONDONTWRITEBYTECODE`, so ignored
    `__pycache__` entries may have been refreshed;
  - the authorized single-selector browser rerun wrote ignored E2E runtime artefacts
    under `tmp/`.

  Neither touches any candidate path.
- No `.env` was read. No network or live credentials were used. No Mongo database other
  than the task-owned disposable container was touched; `clm_poc` was never used, and
  no URI is recorded.

## Recheck (round 2) — remediation delta, 2026-10-24

**Result: PASS** for frozen full-candidate tree
`72de7a38fe5021055ed08dafa6cc53b2475720f6`.

### Identity

- The tree was recomputed with a temporary index in reviewer scratch over 38 paths: every
  `git status --porcelain=v1 -uall` path except this QG report. It matched before and after
  the recheck. HEAD = BASE = `origin/main` `2d8b84af…`; the real index has 0 staged entries.
- `git diff --name-status 3c550c38… 72de7a38…` lists exactly 7 modified paths, as the
  coordinator stated:
  - the implementer report;
  - `apps/backend/tests/test_official_shareholder_evidence.py`;
  - `docs/PROJECT_STATE.md`;
  - `docs/contracts/OWNERSHIP_UBO_PROFILE.md`;
  - `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md`;
  - `docs/decisions/DECISION_LOG.md`;
  - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`.
- `apps/backend/app` (`4ab7525f…`), `scripts` (`13468e95…`) and `apps/frontend` (`3c5ba180…`)
  are byte-identical between the round-1 and round-2 trees. No other test file changed. All
  round-1 application-code evidence therefore remains valid.
- Delta hygiene: `git diff --check` is clean, and `--stat` equals `--ignore-cr-at-eol --stat`
  (7 files, +122/−13). The changed untracked files have no trailing whitespace.

### Delta review

- **MF-1: resolved.**
  - Demo guide §8 now matches the code:
    - empty Marketplace entity profile;
    - returned `coShareholdersDetails` rows kept beside the graph as
      `official_shareholders`;
    - `PROVIDER_PARTIAL` / `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, with the added
      `OWNERSHIP_DENOMINATOR_REQUIRED` issue;
    - an empty result stays `NOT_FOUND` / `OFFICIAL_SHAREHOLDERS_EMPTY`;
    - no percentage either way, and the branch stays unresolved.
  - The UI-visibility wording in D-079, `OWNERSHIP_UBO_PROFILE` and the implementer report
    is now accurate against the unchanged frontend. `OwnershipPathExplorer.tsx` renders
    `DISCOVERY_OUTCOME_LABELS.PROVIDER_PARTIAL` ("Incomplete registry evidence") followed by
    ` · {reason_code}`. `App.tsx` lists each issue as code plus message. The rows are not
    rendered.
- **A-2: accurate.** The text says "schema1/schema2 keys and meanings are unchanged", and the
  rollback note says newly written schema-1/2 documents serialize `shareholder_evidence: null`
  so an earlier version fails closed. This matches my round-1 probe: BASE decoding a
  candidate-written schema-2 entry raises `RegistrySnapshotRepositoryInvalidError`, while
  the candidate reads BASE-written entries.
- **A-3: accurate.** The compatibility paragraph now says D-077 introduced v12 and that the
  D-079 candidate uses v13 and reads v1..v12 without read-time rewrite. This matches
  `CASE_SNAPSHOT_SCHEMA_VERSION = 13` and the decoder set.
- **A-1 tests: meaningful.**
  - `test_a_cached_empty_profile_with_a_fresh_shareholder_read_counts_as_provider_backed`:
    an uncached shareholder failure, then a negative-cached entity profile plus a fresh
    shareholder read. It asserts one entity call, `SHAREHOLDERS_FETCHED` and counters
    `(1, 1, 0)`.
  - `test_shareholder_cache_and_busy_failures_stop_safely[…]`: the coordinator method raises
    `RegistryCacheReadError` or busy. It asserts `CACHE_FAILURE`/`REGISTRY_CACHE_READ_FAILED`
    or `HARD_LIMIT`/`REGISTRY_ACQUISITION_BUSY`, no rows, no denominator issue,
    `REVIEW_REQUIRED` and the 62.5 bound.
  - `test_coordinator_refuses_evidence_that_expires_during_its_own_fetch`: the clock crosses
    the 90-day window during the provider call. It asserts `RegistryCacheInvalidError`, one
    call and nothing written.
- **Implementer report "QG round 1 remediation" section: accurate** about what changed. See
  advisory R2-A1.

### Evidence (this session, round-2 tree)

| Check | Result |
|---|---|
| `tests/test_official_shareholder_evidence.py` | **23 passed** (19 + 4 new), 0 failed, 0 skipped (JUnit) |
| Mutants re-run against the new module (scratch app copies; unmutated copy 23/23) | **M8** (counter ignores the shareholder read): **KILLED** by the counter test (`(1, 0, 1) != (1, 1, 0)`). **M12** (expiry crossing during the fetch): **KILLED** by the expiry test (`DID NOT RAISE`). New M13 (shareholder cache error mapped to `PROVIDER_FAILED`) and M14 (busy mapped to `PROVIDER_FAILED`): both KILLED by the new parametrized test. The other 11 round-1 kills are still killed. Survivors are only M6a/M6b/M10a, each redundant with a second layer, and M7. The new module alone does not kill M7, but the unchanged D-077 test kills it, as shown in round 1 |
| `check_project_state`, `check_architecture`, `check_secrets`, `check_policy_authority` | PASS ×4 |
| `tests/test_dev_context.py`, `test_check_project_state.py`, `test_check_policy_authority.py`, `test_check_architecture.py`, `test_check_secrets.py` | 77 passed |
| `ruff check .` (apps/backend); `ruff format --check` on the test module | All checks passed; already formatted |

Not rerun: mypy, the focused backend modules, physical Mongo and the browser selector. The
application code is unchanged, so round-1 evidence stands.

### Advisories (non-blocking)

- **R2-A1:** the implementer report's Identity and Evidence sections still describe round-1
  content: product tree `e88d7a3…`, "(19)" tests, "19 passed". They are honestly labelled as
  evidence on that tree, but the remediation section records neither the new tree
  (`72de7a3…`) nor the post-remediation evidence (23/23). This recheck records both.
- **R2-A2 (cosmetic):** the edited D-079 line in `DECISION_LOG.md` (line 468) is not
  re-wrapped (164 characters). Markdown renders correctly and no check enforces wrapping.

### Readiness and conduct

- No required fixes remain. The candidate at `72de7a38…` has an independent QG **PASS** and is
  ready for the publication stage. Commit, push and PR still need explicit owner
  authorization.
- Live ACRA and real GoldTier readiness remain unestablished. Q-004, Q-012 and Q-019 remain
  open.
- This round's only worktree write is appending this section to the QG report.
- No git mutation, real-index change, network use, `.env` read or database use occurred.
