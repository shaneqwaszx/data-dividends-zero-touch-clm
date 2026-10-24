# SIM LIM official shareholder evidence (D-079) — Stage 1/2 report

Implementer report, 2026-10-24. It is implementer evidence only, not an independent QG
verdict. The owner approved proposal P1 (`SIM_LIM_SHAREHOLDER_EVIDENCE_PROPOSAL.md`):
registry cache schema 3, case envelope schema 13, discovery field `official_shareholders`
and D-079. Retaining `shareType`/`currency` is deferred.

## Identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-shareholder-evidence-20261024`.
- Branch `feat/sim-lim-official-shareholder-evidence-20261024`.
- BASE = `origin/main` = `2d8b84af46f2ac0f1d94965ca638e1cd7a1c7e54` (merged PR #106,
  unchanged at acceptance time).
- Uncommitted. Nothing is staged.
- Frozen product content (temporary index; all modified and untracked paths except
  `.ai-pipeline/reports/`, 35 paths): tree **`e88d7a34d0a670f4a7dda90bd0618f8dae32f105`**.
- Change classes: `BACKEND_DOMAIN`, `EXTERNAL_PROVIDER`, `PERSISTENCE`.

## Answers

1. **Why the diagnostic retrieved the shareholders but onboarding lost them (before).**
   `AcraRegistryProviderAdapter.retrieve_acquisition` returned `None` when `fetch_company`
   saw an empty `entities` collection. The coordinator then cached a definitive
   `NOT_FOUND`, discovery recorded `NOT_FOUND`, and `coShareholdersDetails` was never
   dispatched. `AcraDiagnosticService` calls `connector.fetch_ownership_parties` directly.
2. **API evidence and issuer binding.** The read is the existing official
   `entityQuery/coShareholdersDetails` operation, through the unchanged
   `AcraApiMarketplaceMockConnector` and the strict `BizfileMockOwnershipPartiesDecoder`
   (`include_withdrawn=True`). The decoder enforces:
   - exactly one entity row, whose UEN equals the requested uppercase UEN;
   - a shareholders collection that is present;
   - grouping is rejected;
   - categories are only Corporate or Individual;
   - `shareAllotted` is an exact Decimal;
   - HTTP 200, JSON, at most 256 KiB.

   The adapter's shared collection path then re-binds the UEN, requires the MOCK
   environment and records operation provenance. Errors map to safe codes
   (`REGISTRY_OPERATION_TIMEOUT`, `…_MALFORMED_RESPONSE`, `…_UNAVAILABLE`).
3. **Retained per row:**
   - source shareholder id, name, party type (Corporate → `LEGAL_ENTITY`, Individual →
     `NATURAL_PERSON`), source category and status;
   - exact `shareAllotted`;
   - `current_interest`: true only for an explicitly Active status, so Withdrawn and
     unknown are false;
   - official provenance: `ACRA_REGISTRY_ACQUISITION` / `MOCK` /
     `ACRA_API_MARKETPLACE_MOCK_V1` / `OWNERSHIP_PARTIES`, retrieval time and evidence
     reference.

   Not retained: `shareType` and `currency` (deferred). A registration identifier is never
   supplied by this contract.
4. **Missing for confirmed percentages.** A same-entity, same-class authoritative
   denominator, such as issued shares. This operation does not return one, and a capital
   operation is outside the contract (Q-012). Visible allotments are never summed into a
   denominator. A COMPLETE acquisition with relationships still resolves through the
   existing engine (`FETCHED`); the local synthetic lane's tests cover this unchanged.
5. **Does it now survive normal onboarding? Yes**, offline-verified:
   - **SIM LIM record:** outcome `PROVIDER_PARTIAL`, reason
     `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE`, lookup `SHAREHOLDERS_FETCHED`, then
     `SHAREHOLDERS_CACHE_REUSED` on a repeat. All rows are kept.
   - **Graph:** Garden's two direct links and the 62.5% unresolved bound are unchanged.
   - **Issues:** one `OWNERSHIP_DENOMINATOR_REQUIRED` issue names SIM LIM. Garden's four
     existing issues remain.
   - **Review:** the case stays REVIEW_REQUIRED, LIM CHOON HUAT stays INDETERMINATE /
     REVIEW_REQUIRED (synthetic basis MET), and readiness and GoldTier stay blocked.
   - **Calls:** one extra GET per cache miss; zero on a repeat.
6. **FGH SERVICES, INC.** No: no registration identifier is supplied, and discovery recurses
   only through a verified Singapore UEN. It stays a `LEGAL_ENTITY` observation with no
   discovery record or lookup.

## Files

**Application:**
- `domain/models.py`: `RegistryShareholderEvidence`; `RegistrySnapshotEntry` schema 3
  with an exclusive `shareholder_evidence`; `SHAREHOLDER_EVIDENCE_CONTRACT_VERSION`.
- `connectors/registry.py`:
  - `supports_shareholder_evidence` and `retrieve_shareholder_evidence`, both Marketplace
    connector only;
  - a shared `_normalize_ownership_party`;
  - the `ShareholderEvidenceProvider` protocol.
- `services/registry_acquisition.py`: `acquire_shareholder_evidence` (same repository,
  key lock and CAS; distinct key; COMPLETE by policy, EMPTY by negative TTL, FAILED never
  written) and its result types.
- `services/onboarding.py`: `acquire_subsidiary_shareholder_evidence`, which returns
  `None` with no call outside the Marketplace lane.
- `domain/ownership.py`: `OfficialShareholderObservation`; the record fields
  `official_shareholders` and `official_shareholder_lookup`, with validators.
- `services/ownership_discovery.py`: `_official_shareholders`, on the definitive-NOT_FOUND
  path for non-overlay issuers only. The issuer counts as provider-backed if either read
  reached the provider.
- `services/ownership_analysis.py`: the additional `OWNERSHIP_DENOMINATOR_REQUIRED` issue.
- `persistence/models.py` and `mongo_case_store.py`: schema 13, an exact
  `DurableCaseSnapshotV12`, and rejection of the new fields in v1..v12.

**Tests:**
- new `tests/test_official_shareholder_evidence.py` (19);
- a new physical test in `test_recursive_ownership_real_mongo.py`;
- schema pins moved 12 → 13 and the unknown-version sentinels 13 → 14 (37 lines).

**Docs:**
- D-079 (`DECISION_LOG.md`);
- `ACRA_MOCK_API_PROFILE.md`, `REGISTRY_CACHE_FRESHNESS_PROFILE.md`,
  `OWNERSHIP_UBO_PROFILE.md`;
- an ADR-013 amendment;
- `ARCHITECTURE.md`;
- `PROJECT_STATE.md` (candidate note; `case_envelope_schema_version` 13).

**Change statement:**

| Area | Change |
|---|---|
| API/types | Additive discovery-record fields and one more issue instance (existing code) |
| Schema | Case envelope 13 and registry cache 3 |
| Connector | Unchanged; the adapter gains a read path |
| Configuration | None |
| Business rule | D-079 exception to "shareholders only for a recognized COMPANY legal form" |
| Mapping | No new field mapping |
| Auth/security | Unchanged |
| Architecture | Same owners (ADR-013 amendment) |
| Provider classification | Unchanged |
| Runtime | One extra bounded read in the Marketplace lane for empty-profile, non-overlay corporate holders |
| Frontend | Byte-identical |

## Evidence (on product tree `e88d7a3…`)

| Check | Result |
|---|---|
| Ruff (`apps/backend`, `scripts`, `tests`) / format (new and changed tests) | PASS |
| mypy `app` | PASS, 129 files |
| New D-079 module | 19 passed |
| Focused existing modules (hybrid, recursive discovery, persistence, cache, connector, diagnostics, Slice B, policy) | 728 passed, 0 failed |
| Full backend pytest (JUnit) | 3148 collected, 0 failed, 0 errors, 175 skipped (physical-only), 1246 s |
| Physical Mongo (`run_physical_mongo_tests.py`, task-owned disposable `mongo:7` on loopback, generated allowlisted DBs; never `clm_poc`) | PASS, 25 suites, 169/169, 0 skipped (includes the new D-079 restart/schema-12 test) |
| CI unittest lanes: contract 44, delivery assets 4, secrets 8, pre-PR 64, policy authority 14, provider readiness 19, skill pointers 7, `test_run_e2e` 71, GoldTier examples 5 | All OK |
| dev-context / project-state / policy-authority tests | 55 passed |
| `check_secrets`, `check_project_state`, `check_architecture`, `check_policy_authority` | PASS |
| `git diff --check`; EOL churn (`--stat` vs `--ignore-cr-at-eol`) | Clean; identical |
| Full browser suite (`run_e2e.py --timeout-seconds 60`, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT`) | **115/115 PASS** on run 3 (1600 s; slowest `performance-browser.e2e.ts:138` at 56.4 s of 60 s). Runs 1 and 2 stopped at selector 14/115 (`authenticated-zero-touch.e2e.ts:1248`) with Playwright `response.json: Protocol error (Network.getResponseBody): No resource with given identifier found`. Run 3 used `--keep-going`; no selector failed, so selection and isolation match a normal full run. See the classification below |
| Frontend typecheck / Vitest / build | Not rerun: `apps/frontend` is byte-identical to BASE (reused PR #105 evidence) |

**Selector-14 classification (intermittent test race; not attributed to this change):**
- The test reads the body of the first `/documents` response after navigation. The browser
  can discard that body when the page refetches.
- Selector 14 passed 3/3 when run alone (`--grep`).
- The same first-14 selector sequence passed 14/14 on the candidate and 14/14 on
  base-identical code (the D-077 worktree; application and E2E sources identical to BASE).
- The full run then passed 115/115.
- The test and the frontend are unchanged, and the local Mock lane it uses never makes the
  new read.

`test_run_e2e` first failed for missing infrastructure: the new worktree had no frontend
`node_modules`. After `npm ci` from the unchanged lockfile it passed 71/71, with no tracked
change.

## External calls

- No live Marketplace call was made in this assignment, because no credential use was
  authorized.
- All evidence is offline (`AUTOMATED_OFFLINE_SIMULATION`, 0 external calls).
- The owner-reported diagnostic (4 records, `ACRA_DIAGNOSTIC_SHAREHOLDERS_COMPLETE`) is
  cited as reported, not re-observed.
- Live-lane onboarding: NOT_RUN.

## Remaining limitations

- **Provider:**
  - no SIM LIM entity profile;
  - no denominator, capital operation or relationships operation (Q-012);
  - no corporate-holder registration identifiers.
- **Authority:** Q-004, Q-012 and Q-019 remain open. D-079 is `USER_AUTHORIZED_POC`.
- **Frontend:** the API exposes `discovery.records[].official_shareholders`, but the
  unchanged UI types and discovery table do not render them. The discovery table shows
  SIM LIM's outcome label ("Incomplete registry evidence") with the reason code, and the
  issue list shows the new message. Displaying the rows needs a separate owner decision.
- **OPQ:** scenario-overlay issuers keep D-077 behaviour, so no shareholder read is made
  for a NOT_FOUND overlay issuer. Whether official rows should be checked there is an open
  owner question.

## QG round 1 remediation

The independent QG gave PASS WITH MINOR FIXES on tree
`3c550c38e5d3ce94e45bf37cd46c39183d92ace8`.
- **MF-1 (fixed):** the demo guide §8 SIM LIM sentence, and the UI-visibility wording in
  D-079, the contract and this report.
- **Advisories applied:**
  - A-2: cache rollback wording;
  - A-3: the `PROJECT_STATE` compatibility paragraph now names v13;
  - A-1: new tests for the issuer counter after a negative-cached profile, for
    shareholder-read cache failure and busy outcomes, and for evidence that expires
    during its own fetch.
- **No application code changed.**

## Next authorized action

Independent Quality Gate of the exact candidate (product tree plus these reports). Commit,
push and PR need separate owner authorization.
