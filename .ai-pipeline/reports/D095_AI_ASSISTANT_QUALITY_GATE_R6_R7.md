# D-095 AI Assistant — independent Quality Gate R6 and R7 (physical MongoDB test follow-up)

Owner-authorised, test-only follow-up to PR #126 (reviewed HEAD `58f31af`): a dedicated physical
MongoDB suite for backend-computed document digests (case snapshot schema 16). Each round was a
fresh, independent, read-only reviewer agent with no network calls. Earlier rounds:
`D095_AI_ASSISTANT_QUALITY_GATE_R1_R3.md`, `D095_AI_ASSISTANT_QUALITY_GATE_R4.md` (R5 in a PR
comment).

## Change

- New `apps/backend/tests/test_document_digests_real_mongo.py` (5 tests, opt-in through
  `PHASE12_MONGO_URI` like every `*_real_mongo` suite). Each test uses a newly generated
  allowlisted `clm_p12_<24 hex>` database (allowlist not extended), dropped and verified absent
  in a `finally`; synthetic fixtures only; `clm_poc` never referenced.
- `scripts/run_physical_mongo_tests.py`: the suite is added to `PHYSICAL_SUITES` (26 suites), so
  the runner and the CI `phase12-mongo` job run it; `tests/test_run_physical_mongo_tests.py`
  requires it.
- No production source changed (`apps/backend/app`, `apps/assistant` unchanged).

| Scope item | Test |
| --- | --- |
| 1. Schema-16 upload, storage, backend SHA-256, retrieval after restart | `test_the_uploaded_documents_digest_is_stored_and_served_after_a_restart` |
| 2. Schema-15 populated case upgrade: no evidence loss, stale fingerprints or silent rewrite | `test_a_populated_schema_15_case_reads_as_16_without_loss_rewrite_or_stale_evidence` |
| 3. Digests route: same team, cross-team safe 404, unknown case 404 | `test_the_digests_route_keeps_team_scope_and_safe_404s_across_a_restart` |
| 4. Unverified and digest-less documents ineligible for D-095 | `test_only_the_approved_fixture_bytes_match_the_d095_manifest`, `test_the_assistant_eligibility_check_refuses_them_on_the_served_digests` |

Item 2 stores a real conflicting case (open reconciliation discrepancy, backend-only
`raw_value`/`source_record_id` evidence) as a schema-15 writer did, then proves: the store's
decode/re-encode equals the stored envelope plus `schema_version` 16 and null digests; reads and
a restarted process leave the stored bytes unchanged; the pre-upgrade `evidence_fingerprint` still
resolves the discrepancy (200, not stale); the first write stores schema 16 with each legacy
document record unchanged apart from `content_sha256: null`. Item 4 runs the assistant's own
`_verify_documents` on what the backend serves (approved fixture → eligible; one altered byte with
the same name, type and size → `SYNTHETIC_DOCUMENT_NOT_VERIFIED`; schema-15 document →
`SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE`); the module needs only the standard library and httpx, so
it loads from the checkout under the backend-only CI install and is never skipped.

## R6 — FAIL

- **F1 — MAJOR, REQUIRED.** Same-team access was shown only by the case creator (`maya-lim`); a
  creator-only `CaseAccessPolicy.can_access` mutation passed all tests. Fix: also log in
  `ethan-tan` (TEAM_A RM, not the creator) and require the same digests.
- F2 (optional): extra `RawTestClient(owner.app)` clients entered as context managers ran app
  shutdown repeatedly. F3–F5 advisory (the browser-list assertion checks the response shape, the
  exclusion is caught by the stale-fingerprint step; no client-supplied digest attempt, the API has
  no such input; schema-15 envelope fidelity confirmed).
- Mutations M1–M10 caught; M11 (creator-only access) not caught.

## Remediation

F1: test 3 logs in `ethan-tan` in both processes and requires 200 with the fixture digest. F2: the
extra clients are no longer context managers (only the first runs the lifespan). The creator-only
mutation now fails the suite.

## R7 — PASS

- R6-F1 confirmed fixed (creator-only mutation fails at the teammate check); F2 fixed.
- 12 production mutations killed: creator-only access, team check ignored, Director denied, digest
  from the name instead of the bytes, digest not persisted, `exclude=False`, lossy `model_dump`
  upgrade, upgrade altering a field, upgrade inventing a digest, read path rewriting the stored
  envelope, assistant accepting a missing digest, route not case-scoped. Survivors are not gaps:
  two route branches unreachable over HTTP (the case-scope middleware answers 404 first) and the
  assistant media/size check (unit-tested in the assistant suite; not required by item 4).
- Advisory, optional: the Director check asserts status only; the assistant media/size check is
  not exercised here; `ruff format --check` drift in the runner files exists on `origin/main` too
  (added lines add none). Left as is: changing reviewed tests would need another review.
- Safety: generated allowlisted databases only, all dropped; `_env_file=None`; no URI printed; no
  external host. Runner-equivalent environment (`env -i`, plugin autoload off): all 26 suites
  collect (175 tests); new suite with `test_phase12_real_mongo.py`: 28 passed (emulator).
- Reviewed content: HEAD `58f31aff7845fba31cd8f710eb578f34f515ccc2` plus the working tree,
  `test_document_digests_real_mongo.py` `b3b12c909cb12644808f69a4507da9afadf535ab3321e6c76dbabae735c9cf06`,
  `run_physical_mongo_tests.py` `d7d171d868da2c780d62ada1e483fdb5fe09e24f718085690aac1d1306780d9a`,
  `test_run_physical_mongo_tests.py` `1a33d4800f3053fb193db71bd13d5a332eda29edf9e32286fd6e7c6ee771a0ed`
  (unchanged at commit). This report and the one-line `docs/PROJECT_STATE.md` open-item update
  were added after the review and change no test or source.
- `QG VERDICT: PASS` (test content); physical MongoDB execution NOT RUN.

## Evidence classification

- **Physical MongoDB: NOT RUN.** No MongoDB server, Docker daemon or MongoDB download is
  available in the cloud session. Not a pass.
- **Emulator dry run (scratch only, not committed, not physical evidence):** mongomock 4.3.0 in a
  scratch directory, routing `pymongo.MongoClient` to one in-memory server: 5 passed, also with
  the assistant install hidden and plugin autoload disabled. It cannot prove BSON round trips,
  driver CAS behaviour or real restarts.
- **Offline:** without `PHASE12_MONGO_URI` the 5 tests skip; `tests/test_run_physical_mongo_tests.py`
  19 passed; `ruff check` clean; `ruff format --check` clean on the new file; `git diff --check`
  clean; the new file is ASCII, LF, no trailing whitespace.
- No OpenRouter call of any kind.

## Running the physical suite (Windows, repository root, disposable local MongoDB)

```powershell
$env:PHASE12_MONGO_URI = "mongodb://127.0.0.1:27017"
.\.venv\Scripts\python.exe scripts\run_physical_mongo_tests.py --timeout-seconds 1800
Remove-Item Env:PHASE12_MONGO_URI
```

The runner prints `PHYSICAL_MONGO_RESULT=PASSED; SUITES=26; ...` only when every suite ran with no
skip. To run the new suite alone, set the variable as above and, from `apps\backend`, run
`..\..\.venv\Scripts\python.exe -m pytest tests\test_document_digests_real_mongo.py -q -rs`
(5 passed, 0 skipped expected).
