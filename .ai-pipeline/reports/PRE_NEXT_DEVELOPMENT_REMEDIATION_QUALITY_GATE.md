# Pre-Next-Development Baseline Remediation — Independent Quality Gate

**Gate date:** 2026-08-28  
**Branch:** `chore/pre-next-baseline-remediation`  
**Baseline / HEAD:** `7199c94f4a823d421649d3bcaf7ccf3d4abdc020`  
**Review boundary:** complete working tree against `7199c94`, including untracked files  
**Implementation performed by gate:** none

## 1. Verdict

**PASS**

The remediation returns the repository to a trustworthy green local POC baseline. The
complete backend, focused POC catalogue, contracts, frontend, lifecycle, static,
dependency, security, GoldTier, delivery-asset, and whitespace checks pass when run in
the permissions required by the maintained Windows process and esbuild checks.

No Critical, High, or Medium finding remains. The strict PDF provider was not weakened;
the intended tracked fixtures parse under `strict=True`, malformed input still fails
safely, and the delivered cycle fixture reaches `OWNERSHIP_CYCLE` with no target call.
MongoDB remains an optional connectivity/read-only diagnostic and is not application
persistence. No jurisdiction or registry-routing implementation was introduced.

## 2. Scope Reviewed

The gate independently reviewed:

- `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, decisions, open sponsor questions, pipeline
  roles, the Phase 08 gate, and the three applicable repository skills/checklists;
- the supplied independent-gate brief;
- `.ai-pipeline/reports/PRE_NEXT_DEVELOPMENT_BASELINE.md` and
  `.ai-pipeline/reports/PRE_NEXT_DEVELOPMENT_REMEDIATION.md`;
- the full tracked and untracked working-tree delta against `7199c94`;
- PDF/Git attributes, the production local PDF provider, changed PDF/cycle tests, and
  malformed-document boundaries;
- the UTF-8 contract reader and equivalent repository source readers;
- Mongo configuration, dependency declaration, client lifecycle, diagnostic script,
  tests, imports/composition, error output, and documentation;
- the zero-touch review panel, separate legacy document review, replacement flow,
  backend-authorized actions, frontend tests, and upload-limit copy;
- current configuration, persistence, IDP, security, and production-boundary docs;
- the complete configured regression and quality command set.

The implementation was checked for, and did not add, jurisdiction resolution, registry
routing, a foreign provider, expanded ACRA acquisition, ACRA+, Mongo onboarding
persistence, GoldTier expansion, ownership/UBO redesign, workflow-engine redesign, or
sponsor-unconfirmed source precedence.

## 3. Diff Assessment

`HEAD` and the baseline are the same commit, so `7199c94...HEAD` is intentionally empty.
The remediation is an uncommitted working-tree change and was therefore reviewed with
`git diff`, direct reads of untracked files, raw Git-blob comparisons, staged-state
inspection, and untracked-file inspection.

The material delta is bounded to:

- `.gitattributes` for binary PDF checkout behavior;
- Mongo diagnostic comments/script/tests and configuration documentation;
- strict-fixture and Windows UTF-8 regression tests;
- zero-touch frontend review-action removal, upload copy, and frontend regressions;
- current README/configuration and recent UI-narrative corrections;
- the baseline and execution reports.

The tracked textual diff is 13 files, 98 insertions, and 93 deletions. Eight valid UAT
PDFs appear modified in `git status` after regeneration/attribute reevaluation, but each
raw working-tree hash exactly equals its `7199c94` Git blob. Each has zero CR bytes and
32 LF bytes. The material repository-boundary fix is the untracked `*.pdf binary`
attribute. `invalid-document.pdf` remains outside the intended valid-pack change and
remains invalid.

No backend workflow, domain model, ACRA connector, GoldTier connector, target mapper,
ownership rule, route contract, or application repository changed. Searches found no
application import of `app.mongo` outside the diagnostic/tests.

Git state at the end of review, before adding this report:

- branch `chore/pre-next-baseline-remediation`, `HEAD` `7199c94`;
- no staged changes;
- 21 tracked working-tree entries reported modified, including the eight byte-identical
  valid PDF entries;
- untracked baseline report, execution report, `.gitattributes`, and Mongo test;
- pre-existing inaccessible untracked
  `apps/frontend/pytest-cache-files-89airr88/` warning retained;
- no implementation fix, commit, push, merge, rebase, stash, reset, clean, checkout, or
  next-phase work performed by this gate;
- this quality-gate report is the sole file created by the gate.

## 4. Backend Regression Review

**PASS.**

- `apps/backend/app/connectors/local_pdf_idp.py:50` still constructs
  `PdfReader(BytesIO(content), strict=True)`. Page and extracted-text bounds remain in
  force. No parser tolerance or special-case production branch was added.
- `.gitattributes:2` sets `*.pdf binary`, protecting xref byte offsets from Git newline
  conversion on Windows.
- `apps/backend/tests/test_phase_08_input_driven.py:140` sends all eight intended valid
  tracked fixtures through `LocalPdfTextIdpProvider`, rather than testing only the cycle
  file or bypassing the production provider.
- Existing invalid-upload and processing-failure tests retain safe
  `DOCUMENT_STRUCTURE_INVALID` / `IDP_PROCESSING_FAILED` behavior, retrievable terminal
  failure where processing was accepted, and downstream-call stopping.
- An independent API probe using the actual `invalid-document.pdf` returned
  `422 / DOCUMENT_STRUCTURE_INVALID` without advancing the journey.
- The actual `cycle-uen-clean.pdf` probe reached
  `WAITING_FOR_REVIEW / OWNERSHIP / OWNERSHIP_CYCLE`, and every Mock GoldTier operation
  remained `NOT_ATTEMPTED`.
- The 197-test focused catalogue and 509-test backend suite preserve straight-through,
  document blocker/replacement, cycle/incomplete/multiple-path ownership, existing-party,
  target failure/partial result, recovery, adapter-label, call-stopping, isolation, and
  false-completion coverage. The catalogue was not changed by this remediation or gate.

## 5. Contract Encoding Review

**PASS.**

`tests/contract/test_phase_04_ownership_contract.py:61` explicitly reads `App.tsx` as
UTF-8. The UTF-8 source characters remain in the frontend; the remediation did not
delete or ASCII-normalize the triggering content. A source search under `tests`,
`apps/backend/tests`, and `scripts` found no remaining zero-argument
`Path.read_text()` call. Contract discovery passes 44/44 on Windows.

## 6. Mongo Dependency / Security Review

**PASS within the connectivity-only boundary.**

- `apps/backend/pyproject.toml:13` declares exactly `pymongo==4.15.1`; the active
  environment imports version `4.15.1`, strict mypy passes, and `pip check` reports no
  broken requirements.
- `apps/backend/app/config.py:41` retains the optional URI as `SecretStr | None`.
- `apps/backend/app/mongo.py` uses a five-second server-selection timeout, pings before
  the read-only `FYP.users` count, and closes the client in `finally` on success and
  failure.
- `scripts/check_mongodb.py` reports only a success count or safe exception class. The
  focused tests inject a URI-like private server detail and prove it is not printed.
- With no configured `MONGO_URI`, the actual script exited 1 with exactly
  `MongoDB check failed: ValueError`. This is the expected fail-closed diagnostic result,
  not an application failure and not a skipped local dependency check.
- No URI, hostname, credential, raw server exception, payload, or KYC/PII was found in
  tracked changes, command output, API/UI paths, or normal application logs.
- No FastAPI composition, startup hook, health gate, domain service, case/document/
  ownership/CLM/zero-touch repository, provider binding, or target ledger imports or
  calls the Mongo module. All application persistence remains process-local/in-memory.

Live Mongo connectivity was not run and is not an acceptance requirement because no
authorized URI is configured. This gate makes no production-persistence or Mongo
interoperability claim.

## 7. Frontend Review-Action Assessment

**PASS.**

- The zero-touch `HumanReviewPanel` no longer accepts an `onManualEdit` callback and no
  longer renders local manual correction fields or calls the legacy `CORRECTED` review
  endpoint.
- Resolution buttons are sourced only from backend-authored
  `exception.available_actions`; non-actionable exceptions say that no authorized action
  exists.
- Same-case/version-bound document replacement remains available for eligible document
  exceptions and continues to refetch the authoritative automation response.
- The separate Phase 03 legacy `DocumentReviewSummary` retains its supported
  accept/reject/correct behavior; this is not projected as a zero-touch resume action.
- Frontend tests explicitly prove the zero-touch surface omits `Manual correction` and
  `Save correction`, preserves `KEEP_REGISTRY_VALUE`, and preserves replacement UI.
- No local-only correction state or handler remains that can mark a zero-touch exception
  resolved. Backend state remains authoritative.
- `DOCUMENT_TOO_LARGE` now states the supported/default `5 MiB`, matching
  `IDP_MAX_UPLOAD_BYTES=5242880`. The backend bound itself was not changed.

## 8. Documentation Assessment

**PASS.**

README, `.env.example`, and the configuration reference now consistently state:

- normal document processing is `LOCAL_PDF_TEXT`; Mock IDP is developer/test fault
  injection;
- `MONGO_URI` is an optional secret used only by the manual connectivity/read-only
  diagnostic;
- MongoDB is not wired to onboarding persistence;
- application repositories remain process-local/in-memory;
- the default PDF upload bound is 5 MiB; and
- production RBAC, production PDF security, durable orchestration/persistence, real
  ACRA/GoldTier/PingFed integration, and production readiness are not implemented.

The dated UI narrative files retain historical discussion, but their current-baseline
clarifications and corrected current claims prevent them from overriding the
authoritative architecture/configuration/runtime documentation. Historical phase and
gate results were correctly left historical.

## 9. Full Test Results

| Exact command / probe | Independent result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider apps\backend\tests` | PASS — 509 passed; one existing Starlette/httpx deprecation warning |
| `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider apps\backend\tests\test_zero_touch_orchestration.py apps\backend\tests\test_phase_07_uat.py apps\backend\tests\test_phase_08_input_driven.py apps\backend\tests\test_phase06_provider_conformance.py` | PASS — 197 passed; one existing warning |
| Direct actual-fixture FastAPI probe for `cycle-uen-clean.pdf` and `invalid-document.pdf` | PASS — cycle stopped at `OWNERSHIP_CYCLE` with zero target operations; invalid returned `422 / DOCUMENT_STRUCTURE_INVALID` |
| `.\.venv\Scripts\python.exe -m ruff check --no-cache apps\backend scripts tests` | PASS |
| `.\.venv\Scripts\python.exe -m mypy --no-incremental apps\backend\app` | PASS — 57 source files |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | PASS — 44/44 |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS — no supported secret patterns found |
| `.\.venv\Scripts\python.exe -m unittest tests.test_validate_goldtier_examples -v` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS expected classification — 19 valid, 19 invalid/quarantined, 48 not validated |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| `.\.venv\Scripts\python.exe -c "import pymongo; print(pymongo.__version__)"` | PASS — `4.15.1` |
| `.\.venv\Scripts\python.exe scripts\check_mongodb.py` | EXPECTED UNAVAILABLE — exit 1, safe `ValueError`; live connectivity not required |
| `npm.cmd run typecheck` in `apps/frontend` | PASS |
| `npm.cmd test` in `apps/frontend` | PASS — 42/42 with required esbuild child-process permission |
| `npm.cmd run build -- --outDir <temporary-directory>` in `apps/frontend` | PASS — 29 modules; output outside the repository |
| `npm.cmd ls --all` in `apps/frontend` | PASS — exit 0; absent optional platform/feature packages are expected |
| `.\.venv\Scripts\python.exe -m unittest tests.test_phase_07_delivery_assets -v` | PASS — 4/4 |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13/13 in 196.139 seconds with exact-process permission; final owned processes stopped |
| `git diff --check` and `git diff --cached --check` | PASS |

The first sandboxed frontend test/build attempts failed before product execution with
esbuild `spawn EPERM`; unchanged commands passed when child-process execution was
allowed. The first sandboxed lifecycle attempt likewise failed during setup because
Windows process inspection/termination was denied; it retained exact owned metadata,
and the unchanged authorized run first cleaned that partial tree and then passed 13/13.
These permission failures are recorded, not converted into product failures or hidden.

## 10. Findings by Severity

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

No new Low defect requiring remediation was found. The inaccessible untracked frontend
cache directory is an inherited repository-hygiene/scan-coverage warning and was not
created or modified by this remediation. Accessible tracked and untracked changes were
covered by the configured scanner and direct diff review.

## 11. Remaining Technical Debt

- Mongo live connectivity remains unverified and optional; there is no authorized
  service configuration and no application persistence design.
- The 5 MiB frontend copy reflects the supported/default backend configuration rather
  than a server-projected dynamic upload limit. A future configurable production UI
  should obtain the effective limit from an approved public configuration contract.
- The existing Starlette/httpx TestClient deprecation warning remains non-failing.
- The pre-existing inaccessible `apps/frontend/pytest-cache-files-89airr88/` directory
  remains outside Git/secret-scanner visibility until its permissions or cleanup are
  separately authorized.
- Live ACRA, real GoldTier/PingFed, sponsor-approved IDP/source-authority/UBO/reviewer
  policy, durable persistence/orchestration, production RBAC/PDF controls, and the
  Ready-for-Approval transition remain documented later dependencies, not regressions.
- The future jurisdiction planner must still define the omitted-input/source-evidence
  rule; this remediation correctly does not guess or implement it.

## 12. Jurisdiction-Phase Readiness

The baseline is ready for the next **planning** step. Jurisdiction planning may begin,
but this verdict does not authorize implementation and does not imply live ACRA,
foreign-registry, Mongo persistence, or real GoldTier readiness. The planner must first
make the omitted-jurisdiction evidence/default rule explicit and keep the existing
ACRA-only runtime behavior truthful until a separately approved implementation phase.

PASS — READY FOR NEXT DEVELOPMENT PLANNING
