# QG D-087 + D-088 + D-089 — independent Quality Gate report (combined candidate)

Reviewer: fresh, independent, read-only. No worktree edits, staging, commits, stashes,
resets or cleans were made. All scratch files are under `scratchpad\qg-d088\`.

## 1. Identity

| Item | Value | Evidence |
|---|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025` | `git rev-parse` |
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` | `git branch --show-current` |
| HEAD | `8451e2a70030f74c50d68194b060bf106aebe7b4` (PR #111 head) | verified |
| Base / merge-base with origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` | `git merge-base HEAD origin/main` |
| origin/main | `a6e86fc041d7745271d6349c4200a1b3a779852f` | verified |
| Main drift | `git diff --name-only 5de7f24 origin/main` = `README.md` only; README.md is not among the 27 candidate paths → **no overlap** | verified |
| Candidate inventory | 27 paths (25 modified + 2 untracked tests); `git status --short` shows exactly these 27 entries, nothing else | verified |
| Frozen tree | Scratch index copy + `git add --pathspec-from-file` + `write-tree` = **`b23d03a07264dcbc916dfefcb1789e06f3b89c6e`** (matches claim; real index untouched) | verified |
| EOL churn | `git diff --stat` == `git diff --ignore-cr-at-eol --stat` (25 files, +2304/−131) → **none** | verified |
| `git diff --check` | clean | verified |
| D-087 reviewed tree | `db56b8e…` exists; `git diff db56b8e b23d03a` = 27 files, +2636/−24; every removed line is an extension point (Literal widened, docstring, `max_length` 5→6, provider set widened). No D-087 logic removed | verified |

Freshness of implementer evidence: latest candidate-file mtime is 22:21:52 (+08:00). The full
backend run started 22:22:05, the multi-holder smoke at 22:47 and the full E2E at 22:48 (local),
so all three reflect the current content. The E2E JSON reports `tree` = `HEAD^{tree}` with
`dirty: true` (by design of `run_e2e.py`), not the working tree.

## 2. Checks

### Check 1 — Identity, inventory, EOL, main drift
PASS. See §1.

### Check 2 — Security and provider review of the connector
- **Fixed host/path.** `ACRA_API_MARKETPLACE_MOCK_BASE_URL` + constant
  `/entityQuery/businessProfile`; UEN only via `urlencode` after
  `_require_eligible_identifier` / `is_eligible_singapore_uen`. Query-free provenance only.
  No user-controlled URL or credential. The UEN comes from the trusted scenario catalogue.
- **Official composition only.** `supports_business_profile_evidence` delegates to
  `supports_shareholder_evidence` (`company_shareholders_only` and
  `isinstance(connector, AcraApiMarketplaceMockConnector)`). The onboarding seam returns `None`
  without any call for any other provider (`getattr(..., False)`). The test asserts that a
  non-Marketplace adapter reports `False`.
- **Inherited transport guards.** `fetch_business_profile` uses the same `_get` and
  `_raise_for_status`: the content-type rule, the 256 KiB cap and the status mapping. The test
  `text/html` → malformed and 401 → auth error.
- **Strict decoding.**
  - It requires exactly one same-UEN entity, an explicit empty list → EMPTY, and the category
    allowlist {individual, corporate}.
  - Bounded lengths: max 64 rows and max 16 capital lines.
  - `extra="ignore"` at the untrusted boundary, then `extra="forbid"`, frozen,
    `revalidate_instances` payloads.
  - Officers, addresses, nationality, activities, `statusDate` and
    `dateOfTransferOfRegistration` are never mapped.
  - The test feeds an officer block containing `S0000000Z` and asserts it is absent from the
    dump.
  - **Gap (P2-1):** see the finding. String counts are accepted.
- **Personal identifiers.** The holder source `id` exists only transiently in the connector
  payload. The adapter replaces it with `BP-<sha256(issuer\0ID)[:24]>`. The domain, cache entry,
  discovery record and API carry only the digest. Frontend types do not even declare
  `source_party_id`. The new code adds no logging (none in the diff). The holder *name* is
  retained, as with all existing official shareholder evidence. The repo fixture uses
  `SYNTHETIC ABC HOLDER` / `SYNTHETIC-ABC-HOLDER-1`.
- **Digest deterministic / non-reversible.** It is deterministic and issuer-scoped. It is
  **unkeyed**, so for low-entropy identifiers it is reversible by enumeration (P3-3). An NRIC or
  FIN space is about 5×10^7, and this host measured about 1.65 M SHA-256/s single-threaded in
  Python, so recovery takes roughly 30 s. It is pseudonymisation, not irreversibility. Still,
  it is strictly better than the existing D-081 path, which keeps the source id in clear in
  `_scoped_id`.
- **Live read vs fixture.** The sanitized `acra-discovery\abc_bp_live.json` shows
  1 token POST (200) and 1 GET (200, 1404 B), with one entity, UEN bound. It contains no names
  or ids.

  The fixture `abc_business_profile()` uses the observed field paths, with the officer,
  address, activities, statusDate and nationality blocks omitted:
  - `uen`, `entityName`, `companyType`, `statusOfCompany`;
  - `shareholder[].category/id/principalName/numberOfShares/shareType/currency`;
  - `issuedShareCapital[]` and `paidUpCapital[]`, each with
    `numberOfShares/amount/currency/shareType`.

  Values match: Individual, 1000 (JSON decimal literal; fixture `1000.0`), ORDINARY,
  SINGAPORE DOLLAR, and issued and paid-up 1000/1000, with company labels identical. No row
  status is returned, and none is in the fixture. No observed personal data is in the repo.

### Check 3 — Fail-closed interpretation (mutation testing)
These ran on scratch copies under `qg-d088\mut\<mutant>\apps\backend`, with
`PYTHONPATH=<copy>;<worktree>`. `app.__file__` was asserted to resolve inside each copy. The
targets were `test_business_profile_evidence.py` and `test_opq_garden_abc_scenario.py`
(baseline: 42 passed, 1 skipped). The full table is in §3. Two of the 13 mutants survived, and
neither is equivalent (P3-1 and P3-2). A survivor probe (`qg-d088\probe_m02_m10.py`) confirmed
this against each mutant copy:
- **M02.** The rows 600 ORDINARY + 400 PREFERENCE over 1000 issued ORDINARY → `True` under the
  mutant, `False` at baseline.
- **M10.** `assumed_current=True` with `provider_status="Withdrawn"` is accepted by the mutant
  model and refused at baseline. For M10 the acceptance still fails closed through
  `issued_capital_matches` and `_issued_capital_links_disagree`, so its impact is limited to
  the model-level invariant. No other test file references these guards.

### Check 4 — No global acceptance or readiness bypass
- **Discovery scope.** The BP read happens only inside the
  `rejected == NOT_FOUND → reason == OFFICIAL_SHAREHOLDERS_EMPTY` branch, and only when
  `self._overlay` is set (hybrid lane) and `uen in business_profile_issuers`.
- **Which scenarios read.** Only `OPQ_GARDEN_ABC_SCENARIO` declares issuers. The validators
  require the issuers to be declared non-overlay, non-root holders, and the issued-capital
  assumption requires issuers.
- **Tests.**
  - `test_the_profile_read_never_happens_outside_the_named_issuers`: the five-layer and 100%
    variants make zero BP calls.
  - `test_an_unnamed_holder_is_never_read_or_interpreted`.
  - Default-off and variant switches withdraw authority.
- **Regression subset (my run).** 18 related files: 601 passed, 1 skipped (the physical Mongo
  test, no URI configured).
- **Full backend (implementer, verified from XML).** 3343 tests: 3337 passed, 6 skipped, 0
  failures and 0 errors. The skips are 6 × Tesseract OCR. The physical-Mongo BP cache test ran
  and passed, and 176 `real_mongo` cases are present.
- **Full E2E (verified from JSON).** 115/115 PASS, `mode full`.
- **Smoke C (verified).** 16/16 PASS:
  - accepted, READY, no blockers;
  - waits at TARGET_CONFIRMATION_REQUIRED;
  - the explicit confirmation completes with a `GT-MOCK-` party.
- **D-087 smokes A/B (21/21 PASS) predate D-088.** They are D-087-tree evidence only. The
  combined candidate's A/B behaviour is covered by the backend tests above and by E2E.

### Check 5 — Arithmetic
- **Exact Decimal values.** `50 × 62.5 × 81.818182 = 25.568181875`;
  `50 × 62.5 × 9.090909 = 2.8409090625`; `50 × 37.5 = 18.75`; `50 × 100 = 50`. The sum is 100.
- **Tests and smoke.** The test asserts exact Decimals and the calculation string
  `50% x 62.5% x 81.818182% = 25.568181875%`. Entity values are Garden 50, SIM LIM 31.25 and
  ABC 50. The smoke API returns `25.568181875000000` and `2.840909062500000`.
- **Comparator and rounding.** The comparator is unchanged (inclusive; MET = ABC holder and
  ABCD123). The issued-capital link uses the existing six-decimal `quantized_unit_share` per
  link (1000/1000 = 100 exactly). No effective value is rounded before comparison.
- **Denominator.** ABC's 1000 shares appear only in the ABC → holder component (root = ABC).
  OPQ → ABC is the declared 50%.

### Check 6 — Persistence
- **Case envelope.** Schema 15 is introduced by this same PR (main has ≤14), so the additive
  fields are unreleased.
- **Legacy rejection.** `reject_scenario_poc_legacy_fields` rejects:
  - `official_business_profile` on discovery records;
  - `issued_capital_relationship_ids`;
  - the D-087 intermediate counts.

  This is tested.
- **Cache schema 5.** `RegistrySnapshotEntry` enforces that schema 5 ⇔ the
  `MARKETPLACE_BUSINESS_PROFILE_V1` key ⇔ non-FAILED profile evidence. The entry must also be
  exclusive of acquisition, negative result and shareholder evidence, be Mock, match the
  identifier, provider and environment, and have its anchor equal `retrieved_at`.
- **Codec and physical Mongo.** The codec round-trip test passes. The physical Mongo restart
  test passed in the implementer's full run. I did not run it.
- **Coordinator.**
  - Cache-first under its own key, with the same locks, CAS and flight-failure handling as the
    shareholder contract.
  - COMPLETE follows the freshness policy and EMPTY the negative TTL; FAILED is not written.
  - Tests cover the boundary second for each.

### Check 7 — Frontend wording
- **Labels.**
  - `sourceLabel` appends "· from ACRA Mock business profile" only for
    `LOCAL_POC_ISSUED_CAPITAL_BASIS`.
  - `assumedBasisLabel` returns "ACRA issued-capital POC basis".
- **Accepted banner.** It adds the issued-capital disclosure (no holder status; current is a
  declared POC assumption), the intermediate-role counts and the owner-declared statement.
- **When not accepted.** F3 checks that both OPQ fixtures keep the warn banner and the
  "UBO determination requires review" warning.
- **My runs.** vitest `OwnershipStructure.test.tsx` 31/31; `tsc --noEmit` exit 0.
- **Screenshot `C-hierarchy.png`.** The wording is truthful and no warning banner appears when
  accepted.

### Check 8 — Docs
The DECISION_LOG D-087, D-088 and D-089 entries, the `ACRA_MOCK_API_PROFILE` section,
OWNERSHIP_UBO_PROFILE, the demo §7b, PROJECT_STATE and ARCHITECTURE all match the code. All
are labelled candidate, `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`, with Q-004 and
Q-012 still open. There are two exceptions:
- the "counts must be finite whole numbers" claim is not fully true (P2-1);
- the observed-shape list omits `dateOfTransferOfRegistration` (P3-4).

These checkers PASS (my runs): `check_project_state`, `check_architecture`, `check_secrets`,
`check_policy_authority`, `check_external_provider_readiness` and `check_tooling_config`.

### Check 9 — Static checks
- **ruff 0.16.2.**
  - From the repo root, all 25 changed or new `.py` files: all checks passed.
  - From `apps/backend` (`app`, `tests`): all checks passed.
  - `scripts/five_layer_hybrid_fixture.py` linted with the backend config reports I001. This
    is **pre-existing**: the identical finding occurs on the HEAD blob. It is a config-scope
    artefact, because `app` is first-party under the backend config. Root lint passes.
  - The `.ruff_cache` directories predate this review and are gitignored.
- **mypy (strict + pydantic plugin).** The 11 changed `app` modules: no issues. Tests are
  outside the mypy gate. Running it on the two new tests yields errors mostly from imported
  pre-existing test modules, and this is not a repo gate.
- **Whitespace.** `git diff --check` is clean. The untracked `.py` files have no trailing
  whitespace or CR and end with LF. No untracked Markdown.

### Owner constraints
| Constraint | Result |
|---|---|
| BP strictly Marketplace Mock, fixed host/path, official composition only | Met |
| Original source fields and provenance preserved | Met (company labels, rows, capital as returned; `provider_status` kept; Mock provenance, `evidence_reference`) |
| Single Decimal engine reused | Met (links are ordinary edges; engine diff none) |
| No GoldTier mapping/auth/AI Assistant/unrelated changes | Met (diff limited to 27 paths listed) |
| No global readiness bypass | Met (check 4) |
| Garden identity not reclassified | Met (smoke: OFFICIAL_MOCK_ENTITY_PROFILE / BUSINESS_PARTNERSHIP) |
| POC matches never verified UBOs | Met (REVIEW_REQUIRED everywhere; `provisional_ubo.candidate_count == 0`; "0 provisional UBOs") |
| D-085 safeguards / truthful labels | Met |
| ABC 1000 never OPQ denominator | Met |
| Status-free not globally current | Met (only via `issued_capital_matches` for named issuers; any returned status fails closed) |

## 3. Mutation table

| # | Mutant | Result | Equivalent? |
|---|---|---|---|
| M00 | baseline (no change) | 42 passed / 1 skipped | — |
| M01 | `issued_capital_matches`: drop the sum-equality check | KILLED | — |
| M02 | drop the rows' common class/currency check | **SURVIVED** | **No.** Mixed-class multi-row rows attach (P3-1) |
| M03 | drop the issued-line class/currency compare | KILLED | — |
| M04 | drop both class checks | KILLED | — |
| M05 | drop the returned-status check | KILLED | — |
| M06 | drop the individual-only check | KILLED | — |
| M07 | drop the paid-up agreement check | KILLED | — |
| M08 | discovery: drop the `business_profile_issuers` check | KILLED | — |
| M09 | analysis: drop `_issued_capital_links_disagree` | KILLED | — |
| M10 | domain: drop the `assumed_current` / `provider_status` validator | **SURVIVED** | **No** at model level; the acceptance still fails closed downstream (P3-2) |
| M11 | coordinator caches FAILED | KILLED (the entry validator rejects it) | — |
| M12 | coordinator, entry and evidence validators all allow FAILED caching | KILLED | — |
| M13 | decoder: accept fractional float counts | KILLED | — |

Raw results are in `qg-d088\mutation_results.json` and `qg-d088\mutation_run.log`.

## 4. Not executed (no claim made)
- **Physical Mongo.** Not run by me: no URI is configured in my environment and `.env` was not
  accessed. I rely on the implementer's XML showing the BP physical test passed.
- **Full backend.** Not rerun (24 min). The implementer's run is verified post-content by
  mtime.
- **Frontend.** The full vitest (1084), `tsc -b` and the vite build were not rerun. `tsc -b`
  writes build info into the worktree. I ran vitest for `OwnershipStructure.test.tsx` and
  `tsc --noEmit` only.
- **Full E2E and smokes.** Not rerun; verified from artefacts.
- **Live provider.** No calls. The single owner-authorized live read was not repeated.
- **Hosted CI.** Not assessed.
- **`pre_pr_check.py`.** Not run: the candidate is uncommitted and publication was not
  requested.

## 5. Verdict: **PASS WITH MINOR FIXES**

There are no P0 or P1 findings. The interpretation, scoping, acceptance re-verification,
cache semantics, persistence, arithmetic and labels all behave as authorized and fail closed.
D-087 is preserved.

- **P2-1. Decoder accepts JSON string counts, including fractional ones.**
  - **Location:** `acra_api_marketplace_mock.py` `_exact_count` and `_exact_amount`.
  - **Problem:** Only floats are checked, and a `str` passes through to pydantic lax `Decimal`.
    The probe accepted `"1000.5"`, `"1e3"` and `"1000"` for a row count and `"12.5"` for an
    issued count. This contradicts D-088 ("accepted only as a finite whole number") and the
    `ACRA_MOCK_API_PROFILE` claim ("Counts must be finite whole numbers").
  - **Impact:** Low. The data is Mock-only, the observed shape is numeric, and an attach still
    needs an exact sum match.
  - **Fix:** Accept only `int` (not bool) or a finite whole `float` for counts, reject `str`,
    and add the string cases to `test_malformed_profiles_are_refused`. Decide and document
    whether string amounts are allowed.
- **P3-1. Test gap: no multi-row mixed-class case.** No test has rows of different classes or
  currencies whose total equals the issued count, so M02 survives. Add one, for example
  600 ORDINARY + 400 PREFERENCE over 1000 ORDINARY → RETAINED.
- **P3-2. Test gap: the domain validator is not directly tested.** No direct test covers
  `OfficialBusinessProfileShareholder(assumed_current=True, provider_status=…)` → ValidationError
  (M10 survives). Add a one-line model test.
- **P3-3. The holder digest is pseudonymous, not irreversible.** `BP-` is unkeyed SHA-256 over
  the issuer UEN and source id, so NRIC/FIN-format ids are recoverable by enumeration in
  seconds to minutes. It is acceptable for Mock and better than existing practice. Either say
  "pseudonymous" in D-088 and `ACRA_MOCK_API_PROFILE`, or use an HMAC with a server-held key
  before any non-Mock use.
- **P3-4. Doc nit.** The `ACRA_MOCK_API_PROFILE` observed-shape list omits the observed
  `dateOfTransferOfRegistration` field path.

Observations (not findings):
- The call budget counts once per node across entity, shareholder and BP reads. This matches
  the existing shareholder pattern.
- The ruff I001 on the fixture with the backend config is pre-existing.

Any fix changes reviewed content and requires a fresh independent review of the changed
content. Integration onto `a6e86fc` was not authorized and was not performed. The README-only
drift does not overlap.
