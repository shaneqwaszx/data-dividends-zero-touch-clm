# Pre-Next-Development Baseline Remediation

**Execution date:** 2026-08-28  
**Branch:** `chore/pre-next-baseline-remediation`  
**Baseline commit:** `7199c94f4a823d421649d3bcaf7ccf3d4abdc020`  
**Scope:** bounded baseline remediation only

## 1. Executive Summary

The regressions introduced after the accepted Phase 08 baseline have been remediated
without changing the onboarding architecture or beginning jurisdiction work.

- The tracked synthetic PDF pack is now protected from Git line-ending conversion,
  all eight intended valid fixtures pass the pinned strict parser, and the ownership-
  cycle fixture reaches `OWNERSHIP_CYCLE` after document processing as intended.
- The Windows contract harness explicitly reads frontend source as UTF-8.
- The existing `pymongo==4.15.1` declaration was retained and the local editable
  environment was synchronized. Mongo remains an optional connectivity/read-only
  diagnostic only; no application repository or FastAPI composition uses it.
- The zero-touch Review surface no longer exposes the legacy `CORRECTED` field action.
  It renders only backend-advertised actions plus the already supported replacement-
  document path. The separate legacy document-review UI remains available where it was
  already supported.
- The frontend upload message and current documentation now state the 5 MiB default,
  the Local PDF Text normal provider, in-memory persistence, and the non-production POC
  boundary.

The final full backend result is 509 passed. Contract discovery, Ruff, strict mypy,
frontend typecheck/tests/build, security checks, GoldTier validation, POC regressions,
Windows lifecycle, delivery assets, and dependency checks are green. A live MongoDB
connection was not required or attempted because `MONGO_URI` is not configured; the
diagnostic failed closed with only `ValueError` exposed.

## 2. Baseline Issues Addressed

| Baseline issue | Root cause | Disposition |
|---|---|---|
| Cycle UEN fixture failed strict PDF parsing | Git treated PDFs as text on Windows, converting LF to CRLF without recalculating xref byte offsets | Added binary PDF attributes, regenerated/verified the complete generated pack, and added a strict-pack regression |
| Contract discovery failed under CP1252 | One source-inspection `Path.read_text()` omitted encoding | Added `encoding="utf-8"`; all relevant source-inspection reads are now explicit |
| Mongo imports/mypy/check were red | `pymongo` was declared but the editable environment metadata/install was stale | Reinstalled the existing backend `dev` extra; imports and strict mypy pass |
| Mongo boundary was undocumented/untested | Connectivity helper landed without focused tests or configuration guidance | Added safe check entry point, six focused tests, `.env.example`, README and configuration-reference guidance |
| Zero-touch UI exposed unsupported correction | New UI called the legacy document review endpoint outside the zero-touch server-authorized action/resume model | Removed that zero-touch control/handler; preserved backend actions, replacements and the separate legacy review UI |
| UI reported a 25 MB limit | Recent frontend copy diverged from the backend default of 5 MiB | Updated runtime copy and relevant current UI documentation to 5 MiB |
| Recent UI narratives overstated runtime/readiness | Documents described normal Mock IDP, absent Mongo configuration, or production readiness | Corrected current-baseline statements while preserving historical phase reports |

## 3. Files Changed

### Runtime and support code

- `.gitattributes` — treats PDFs as binary so Git cannot rewrite xref offsets.
- `apps/backend/app/mongo.py` — clarifies the diagnostic-only boundary.
- `scripts/check_mongodb.py` — exposes a testable `main()` returning a safe exit code;
  output contains only a count on success or exception class on failure.
- `apps/frontend/src/App.tsx` — removes unsupported zero-touch field correction,
  retains replacement/server actions, and reports the 5 MiB upload default.

### Tests and fixtures

- `apps/backend/tests/test_phase_08_input_driven.py` — verifies all eight intended
  valid tracked UAT PDFs through `LocalPdfTextIdpProvider` strict parsing.
- `apps/backend/tests/test_mongo.py` — new focused configuration, ping, closure,
  diagnostic count, safe failure-output, and success-output tests.
- `tests/contract/test_phase_04_ownership_contract.py` — reads `App.tsx` as UTF-8.
- `apps/frontend/src/App.test.tsx` — proves zero-touch manual correction is absent,
  backend-authorized action remains, and replacement remains presented.
- The eight generated valid PDFs under `apps/backend/tests/fixtures/uat/` were
  regenerated and verified. Their LF byte content matches the existing tracked blobs;
  the material repository fix is the new binary attribute preventing Windows checkout
  conversion. `invalid-document.pdf` remains intentionally invalid and unchanged.

### Configuration and documentation

- `.env.example`
- `README.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `docs/UI_IMPROVEMENTS_SUMMARY.md`
- `COMPREHENSIVE_UI_AUDIT_REPORT.md`
- `EXECUTION_SUMMARY.md`
- `UI_IMPROVEMENTS_INDEX.md`
- `.ai-pipeline/reports/PRE_NEXT_DEVELOPMENT_REMEDIATION.md`

The pre-existing untracked
`.ai-pipeline/reports/PRE_NEXT_DEVELOPMENT_BASELINE.md` was preserved and not
overwritten. Nothing was staged, committed, pushed, merged, rebased, stashed, reset,
cleaned, or discarded.

## 4. Backend PDF/Test Remediation

The PDF generator calculates a correct xref table over LF bytes. Without a repository
attribute, Git's Windows checkout converted those bytes to CRLF while leaving the
embedded offsets unchanged. Direct strict parsing showed `Broken xref table` for all
eight generated UAT PDFs, not only `cycle-uen-clean.pdf`.

The remediation preserves `PdfReader(..., strict=True)` and the actual document stage:

```text
202400006F + cycle-uen-clean.pdf
  -> LocalPdfTextIdpProvider strict parse
  -> matching four-field document evidence
  -> InputDrivenOwnershipProvider cycle graph
  -> WAITING_FOR_REVIEW / OWNERSHIP_CYCLE
  -> zero Mock GoldTier operations
```

`*.pdf binary` now prevents newline normalization. The generator was rerun for the
complete generated pack, and the new focused test processes all eight valid fixtures
through the production provider boundary. The intentionally invalid signature fixture
was excluded from the valid-pack assertion and remains covered by rejection tests.

## 5. Contract Encoding Remediation

The only relevant unsafe repository-source read was:

`tests/contract/test_phase_04_ownership_contract.py` reading `App.tsx` without an
encoding. It now uses `read_text(encoding="utf-8")`. A repository search found no
remaining zero-argument `read_text()` source-inspection calls under `tests`, backend
tests, or scripts. Valid UTF-8 UI content was retained.

Contract discovery now passes 44/44 on Windows.

## 6. Mongo Dependency / Configuration Reconciliation

`pymongo==4.15.1` was already correctly declared once in
`apps/backend/pyproject.toml`; no competing dependency declaration was added. The
existing virtual environment was synchronized with:

```text
.\.venv\Scripts\python.exe -m pip install -e ".\apps\backend[dev]"
```

The first sandboxed attempt could not write pip's host temporary build directory. The
same unmodified command succeeded with the required environment permission, installing
`pymongo 4.15.1` and `dnspython 2.8.0` and refreshing editable package metadata.

Focused tests prove missing optional configuration, ping success, server failure,
client closure, the read-only diagnostic count, safe failure output, and success
output. The script catches configuration/server errors and reports only their class;
it does not print a URI, hostname, credentials, or raw server exception.

**Mongo remains connectivity-only. It has not become application persistence.**

`app.mongo` is not imported by FastAPI composition or application repositories. The
normal pipeline requires no `MONGO_URI`; cases, documents, ownership, checkpoints,
provider bindings, target ledger and recovery remain process-local/in-memory. No
schema, migration, write repository, collection design, startup hook, or health gate
was introduced. The existing read-only `FYP.users` count is a manual diagnostic only.

Dependency/import correctness: PASS (`pymongo 4.15.1`).  
Unit-test correctness: PASS (6/6 focused Mongo tests).  
Live connectivity: NOT REQUIRED / NOT RUN; `MONGO_URI` is absent. The actual script
exited 1 with the safe output `MongoDB check failed: ValueError`, as designed.

## 7. Frontend Review-Action Reconciliation

The zero-touch `HumanReviewPanel` formerly accepted `onManualEdit` for any field
evidence and called the Phase 03 legacy review endpoint with `CORRECTED`. That action
was not present in `exception.available_actions`, did not use the zero-touch resolution
fingerprint/version contract, and did not resume the orchestrator.

The zero-touch manual-edit prop, form, handler and callback were removed. The panel now:

- renders action buttons only from backend-authored `available_actions`;
- retains `KEEP_REGISTRY_VALUE` where the server advertises it;
- retains same-case/version-bound replacement upload at document exceptions;
- states that replacement evidence is required when it is the supported path; and
- states that no backend-authorized action is available for non-actionable exceptions.

The separate legacy `DocumentReviewSummary` and its existing `reviewDocument` calls
were not removed or redesigned. Frontend tests prove the zero-touch surface has no
`Manual correction` or `Save correction`, while backend-authorized retention and
replacement presentation remain.

The friendly `DOCUMENT_TOO_LARGE` message now reports `5 MiB`, matching the backend
default `IDP_MAX_UPLOAD_BYTES=5242880`. The backend limit was not changed.

## 8. Documentation Corrections

Current documentation now states:

- `MONGO_URI` is optional, secret, and used only for the manual connectivity/read-only
  diagnostic;
- MongoDB is not wired to onboarding persistence and all application repositories are
  in-memory;
- normal document processing is `LOCAL_PDF_TEXT`; Mock IDP remains developer/test-only;
- the default upload bound is 5 MiB; and
- UI polish and a successful production bundle do not make the synthetic,
  process-local POC production-ready.

Corrections were limited to README/configuration sources and recent UI narratives that
made current-runtime claims. Historical phase plans and quality-gate reports were not
rewritten.

## 9. Test / Quality Results

| Exact command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests` | PASS — 509 passed, 1 upstream Starlette/httpx deprecation warning |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_mongo.py` | PASS — 6 passed |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_zero_touch_orchestration.py apps\backend\tests\test_phase_07_uat.py apps\backend\tests\test_phase_08_input_driven.py apps\backend\tests\test_phase06_provider_conformance.py` | PASS — 197 passed, 1 upstream warning |
| `.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests` | PASS |
| `.\.venv\Scripts\python.exe -m mypy --no-incremental apps\backend\app` | PASS — 57 source files |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | PASS — 44/44, 1 upstream warning |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS — no supported secret patterns found |
| `.\.venv\Scripts\python.exe -m unittest tests.test_validate_goldtier_examples -v` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS expected normal classification — 19 valid, 19 invalid/quarantined, 48 not validated |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| `.\.venv\Scripts\python.exe -c "import pymongo; print(pymongo.__version__)"` | PASS — `4.15.1` |
| `.\.venv\Scripts\python.exe scripts\check_mongodb.py` | EXPECTED UNAVAILABLE — exit 1, safe `ValueError`; no `MONGO_URI`, live service not required |
| `npm.cmd run typecheck` (`apps/frontend`) | PASS |
| `npm.cmd test` (`apps/frontend`) | PASS — 42/42 after allowing bundled esbuild child-process execution; initial sandbox-only `spawn EPERM` was not a product failure |
| `npm.cmd run build -- --outDir <temporary-directory>` (`apps/frontend`) | PASS — 29 modules, output outside repository; initial sandbox-only `spawn EPERM` was not a product failure |
| `npm.cmd ls --all` (`apps/frontend`) | PASS — exit 0; expected optional platform/feature dependencies reported absent |
| `.\.venv\Scripts\python.exe -m unittest tests.test_phase_07_delivery_assets -v` | PASS — 4/4 |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13/13 in 180.956 seconds; final owned processes stopped |
| `git diff --check` and `git diff --cached --check` | PASS |

POC regression catalogue: no change. The 197-test focused run and 509-test full run
retain exact assertions for straight-through completion; document conflict/low
confidence/multiple blockers; ownership cycle/incomplete/multiple paths; existing
party; target failures/partial outcomes; finalization recovery; alternate adapters;
provider labelling; call stopping; and no false completion. The regenerated cycle
fixture specifically reaches document success then `OWNERSHIP_CYCLE` with no target
call. UI/API claims remain Mock/local POC bounded.

An initial focused command used a nonexistent filename
`test_provider_conformance.py` and collected no tests; it was immediately corrected to
the repository's actual `test_phase06_provider_conformance.py`, producing the 197-pass
result above.

## 10. Remaining Known Issues

- Live MongoDB connectivity is unverified because no authorized/configured instance is
  required for this repository. This does not block the application or quality gate.
- FastAPI's current TestClient import emits the existing Starlette/httpx deprecation
  warning. It is non-failing and no dependency upgrade was authorized.
- Git still warns that the pre-existing untracked
  `apps/frontend/pytest-cache-files-89airr88/` directory is inaccessible. No cleanup or
  permission mutation was authorized; tracked files and accessible additions passed
  the secret scan.
- Live ACRA, real GoldTier/PingFed, sponsor-approved IDP/source-authority/UBO policy,
  durable persistence, production RBAC/PDF controls, and Ready-for-Approval remain the
  documented pre-existing sponsor/POC limitations. This remediation did not attempt to
  close them.
- The Planner still needs to define the omitted-jurisdiction evidence rule before the
  future jurisdiction phase. That planning dependency is unchanged and is not a
  blocker to this remediation quality gate.

No remaining issue discovered in this task blocks independent quality-gate review.

## 11. Scope Confirmation

**NO jurisdiction or registry-routing functionality was implemented.**

The pipeline remains:

```text
UEN
  -> ACRA profile
  -> canonical entity
  -> document / Local PDF Text IDP
  -> ownership / deterministic UBO analysis
  -> readiness
  -> Mock GoldTier
```

There is no jurisdiction input/resolver, country/provider gateway, registry router,
unsupported-country state, expanded ACRA acquisition, ACRA+/foreign provider, Mongo
repository, workflow-engine redesign, new GoldTier behavior, or UBO rule change.

## 12. Readiness

All assigned baseline regressions are remediated and the required repository quality,
security, regression and lifecycle checks are green. The live Mongo diagnostic is
correctly classified as optional/unavailable rather than an application failure.

READY FOR PRE-NEXT-DEVELOPMENT QUALITY GATE
