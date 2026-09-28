# Data Dividends — Zero-Touch CLM

## Start here for development

New coding agents and developers should read, in order:

1. [AGENTS.md](AGENTS.md)
2. [Current Project State](docs/PROJECT_STATE.md)
3. [Architecture](docs/ARCHITECTURE.md)
4. [Development Workflow](docs/DEVELOPMENT_WORKFLOW.md)

Then run `python scripts/dev_context.py` and load only the relevant contract, sponsor
question, repository skill, source and tests. Historical phase reports are consulted on
demand, not reconstructed at every task start.

Proof of concept for Delta Capita's Singapore new-to-bank flow:

`ACRA Singapore → EDS/orchestration → GoldTier → unresolved human approval gate`

The current POC accepts an optional country/jurisdiction, a company registration
identifier (Singapore UEN for the implemented path), and a bounded set of synthetic
PDF, DOCX, or UTF-8 TXT documents. It resolves
jurisdiction before registry selection, then automatically runs registry validation,
deterministic document comparison, source-neutral reconciliation, ownership/UBO analysis,
readiness, and a Mock GoldTier sequence. It pauses only for a typed exception and
automatically resumes after a permitted resolution.

`COMPLETED / MOCK_GOLDTIER_SUBMITTED` means the credential-free synthetic path
completed. It is not customer/compliance approval, Ready-for-Approval, a legal UBO
determination, or live ACRA/GoldTier interoperability.

## Current capabilities

- Clean straight-through journey with `Human interventions after Start: 0`.
- Document discrepancy, low-confidence, and multiple-blocker review behavior.
- Decimal direct/indirect ownership paths, cycle/incomplete safety, and provisional UBO
  candidates.
- Search-first Mock GoldTier ordering, existing-party and partial-result review, strict
  call stopping, response validation, and replay-free finalization recovery.
- Safe sponsor summary, metrics, warnings, timeline, environment labels, deterministic
  presets, synthetic fixture pack, and whitelisted UAT JSON export.
- Replaceable Registry, IDP, Ownership, and GoldTier interfaces with conformance tests.
- Source-aware jurisdiction observations with no implicit precedence: Singapore routes
  to ACRA; unresolved/conflicting evidence and recognised AU/MY/HK requests stop in a
  controlled Registry-stage review state without downstream calls.
- Four project-owned Mock ACRA acquisition operations with strict bounded DTOs,
  operation-level status/provenance, truthful empty/partial/failure display, and
  registry ownership evidence feeding the existing deterministic ownership engine.
- Four-field Registry/Document reconciliation with no automatic source precedence,
  first-class discrepancies, backend-authorized bounded decisions, evidence-preserving
  canonical legal-name update, and idempotent resume before Ownership.
- A backend-authored case history and review queue with explicit process-local memory
  mode or schema-versioned Mongo durable POC mode. Mongo mode survives backend restart;
  neither mode is production case management or a regulatory audit repository.
- Explicit multi-document intake completion, per-document provenance, safe PDF/DOCX/TXT
  media routing, and aggregation across every current document before Ownership or
  Mock GoldTier may proceed. The Start workspace shows the accepted document count and
  selected byte total against the 25 MiB technical limit.

Live ACRA, live hierarchy, PingFed/real GoldTier, final document/UBO policy, related-
party writes, authenticated reviewer roles, and Ready-for-Approval remain blocked or
unconfirmed. See the [sponsor dependency matrix](docs/sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md).

## Quick start — Windows sponsor demo

Prerequisites: Python 3.12+, Node.js 22+, and npm 10+.

One-time setup from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\backend[dev]"
Set-Location apps\frontend
npm ci
Set-Location ..\..
```

Start both processes with the supported synthetic sponsor composition and gated developer controls:

```powershell
.\scripts\start_demo_windows.bat
```

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

Reset all process-local synthetic state or stop the launcher-owned demo processes:

```powershell
.\scripts\reset_demo_windows.bat
.\scripts\stop_demo_windows.bat
```

The scripts install nothing and embed no credentials. Startup verifies Python/Node/npm,
dependencies, free ports, exact launcher-owned process identities, backend health, and
frontend reachability before returning success. Safe process metadata is stored only in
Git-ignored `.runtime/demo-processes.json`.

Stop validates PID, creation time, executable, project command markers, listener, and
port before terminating only that owned process tree. A `RUNNING` session must contain
exactly one backend and one frontend record; incomplete/corrupt metadata fails closed,
is retained, and prevents Reset from starting. Reset otherwise proceeds to a fresh
healthy start only after verified stop; successful reset clears cases only in memory
mode and never drops durable Mongo data, repository files, or sponsor files. Lifecycle
errors return nonzero and
unowned port occupants are never killed. For recovery and expected outputs, use the
[demo runbook](docs/demo/DEMO_RUNBOOK.md).

## Zero-touch demo

1. Leave jurisdiction as **Not specified** (or select **Singapore**), enter synthetic
   UEN `202400001A`, select one or more supported synthetic documents, and choose
   **Start CLM onboarding** once.
3. Observe Registry → Document Verification → Ownership & UBO → Readiness → Mock
   GoldTier.
4. For the clean case, confirm zero human interventions.
5. Reuse the same UEN with `address-mismatch.pdf` to see PDF-derived source conflict;
   upload `clean-company-profile.pdf` as a replacement to show supersession and
   automatic resume.
6. Use `cycle-uen-clean.pdf` with `202400006F` for the independent ownership-cycle
   case, then `second-case-isolation.pdf` with `202400005E` for existing-party search.

Developer/Test Controls are fault-injection and regression tooling only. They do not
select or alter the provider used by normal sponsor cases.

Use the [5–10 minute sponsor script](docs/demo/SPONSOR_DEMO_SCRIPT.md) and the complete
[UAT catalogue](docs/uat/PHASE_07_UAT_CATALOGUE.md).

## Architecture

```text
optional jurisdiction + registration identifier/UEN + PDF + Start
        |
ZeroTouchOrchestrator
  +-- jurisdiction resolver -> registry router
  +-- Singapore ACRA provider -> profile/officers/owners/relationships -> canonical evidence
  +-- IDP provider -> document evidence/comparison
  +-- reconciliation -> observations/discrepancies/explicit decision
  +-- Ownership provider -> deterministic Decimal paths
  +-- CLM readiness -> immutable target snapshot
  `-- GoldTier connector -> retained outcome/recovery
        |
exception-only HITL or MOCK_GOLDTIER_SUBMITTED
```

External payloads never become business authority directly. Every boundary uses strict
validation and the flow `source payload → canonical/internal model → target mapping`.
Replacing a provider occurs at its interface/composition seam, not in generic
orchestration. See [final architecture](docs/architecture/FINAL_POC_ARCHITECTURE.md)
and [Phase 09 jurisdiction gateway](docs/architecture/PHASE_09_JURISDICTION_GATEWAY.md).
Phase 10 acquisition details are in
[Phase 10 expanded registry acquisition](docs/architecture/PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md).
Phase 11 review/resume is described in
[Phase 11 reconciliation](docs/architecture/PHASE_11_RECONCILIATION_REVIEW_RESUME.md).
The current sponsor-readable ACRA field/operation profile is
[ACRA_MOCK_API_PROFILE.md](docs/contracts/ACRA_MOCK_API_PROFILE.md).

## Environment and configuration

Safe normal sponsor defaults are ACRA `MOCK`, IDP `LOCAL_PDF_TEXT` (Local POC),
registry-acquired Mock ownership evidence, and GoldTier `MOCK`. The official
non-production ACRA API Marketplace Mock is selected only with
`ACRA_CONNECTOR_MODE=api_marketplace_mock` and the dedicated backend-only
`ACRA_API_MARKETPLACE_MOCK_CLIENT_ID` and `ACRA_API_MARKETPLACE_MOCK_SECRET_KEY`
settings. It has no fallback to the synthetic local Mock. Its observed entity-basic and
shareholder operations are bounded Mock interoperability evidence; they are not a
Production/Live ACRA integration. The separate generic `sandbox` seam remains
fail-closed where its contract is unresolved. No connector is labelled `LIVE`.

`DEMO_CONTROLS_ENABLED` gates backend demo APIs and
`VITE_DEMO_CONTROLS_ENABLED` controls browser visibility; both default false. Frontend
visibility never bypasses the backend gate. The supported local path uses Vite's API
proxy; production/cross-origin CORS is not configured.

`CLM_PERSISTENCE_MODE=memory` is the default and is cleared by backend restart.
`CLM_PERSISTENCE_MODE=mongo` requires `MONGO_URI` and stores one schema-versioned
structured envelope per case in `MONGO_DATABASE` / `MONGO_CASE_COLLECTION`. Mongo mode
fails closed at startup and during writes; it never silently falls back to memory.
Database names, URIs, credentials, raw uploads, complete extracted text, and raw
Registry payloads are not exposed through the execution profile or case APIs.

Before local startup, inspect the selected composition without printing secrets or
connection strings:

```powershell
.\.venv\Scripts\python.exe scripts\dev_preflight.py
# Diagnose an explicit teammate profile without changing .env:
.\.venv\Scripts\python.exe scripts\dev_preflight.py --persistence-mode memory
.\.venv\Scripts\python.exe scripts\dev_preflight.py --persistence-mode mongo
```

Memory mode deliberately skips Mongo connectivity. Mongo mode reports only whether the
configured service is required and reachable; a missing URI or unreachable service
fails the diagnostic without exposing the URI or driver error. The report similarly
shows only ACRA credential presence and the composed connector class.

Synthetic Mock ACRA snapshot reuse is separately opt-in with
`REGISTRY_CACHE_MODE=mock` and the exact provisional POC setting
`REGISTRY_CACHE_FRESHNESS_SECONDS=7776000`. Disabled mode retains one acquisition per
case and has no cache startup dependency. Enabled mode shares complete normalized Mock
bundles only, using a separate memory/Mongo repository and exact provider, environment,
contract, dataset, and identifier identity. It adds no API or frontend control and does
not cache documents, reconciliation, ownership, case state, or target outcomes. See the
[registry cache freshness profile](docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md).

Mongo storage requires the document `_id` to be the canonical UUID string for the same
envelope `case_id`; missing, malformed, noncanonical, or cross-case identities stop
startup/reads as corrupt persistence. If restart finds a current document interrupted
before structured evidence was retained, that document becomes
`FAILED / DOCUMENT_REUPLOAD_REQUIRED` and automation returns to
`PENDING_INPUTS / DOCUMENT`. Only targeted same-case retry of each affected document is
accepted until all mandatory reuploads are resolved; completed documents and Registry
evidence are reused.

To demonstrate restart durability on Windows with a local Mongo server:

```powershell
$env:CLM_PERSISTENCE_MODE = "mongo"
$env:MONGO_URI = "mongodb://127.0.0.1:27017"
$env:MONGO_DATABASE = "clm_poc"
.\scripts\start_demo_windows.bat
# create a case, record its case ID, stop, then start again
.\scripts\stop_demo_windows.bat
.\scripts\start_demo_windows.bat
```

Reopen the same case ID or check Dashboard/Review. Do not use
`reset_demo_windows.bat` as a data purge: durable-data deletion is deliberately not
implemented.

Document-intake technical defaults are 20 files per case, 5 MiB per file, and 25 MiB
total. `IDP_MAX_FILES_PER_CASE`, `IDP_MAX_UPLOAD_BYTES`, and
`IDP_MAX_TOTAL_INTAKE_BYTES` may tune those safeguards within validated bounds. These
are project POC controls, not sponsor policy.

See [.env.example](.env.example) and the
[configuration reference](docs/integration/CONFIGURATION_REFERENCE.md). The optional
GoldTier XPI sandbox lane is explicitly configured and remains `SANDBOX_PARTIAL`; Mock
stays the default. PingFed/production placeholders remain unconsumed. Never populate
either family from quarantined material.

## Tests and checks

The [development tooling runbook](docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md)
documents authenticated browser smoke, read-only GitHub check observation, physical
Mongo opt-in, and project-scoped Codex MCP safety. Safe entry commands are:

```bat
npm.cmd --prefix apps\frontend run e2e:list
.venv\Scripts\python.exe scripts\run_e2e.py
.venv\Scripts\python.exe scripts\github_pr_ci.py
.venv\Scripts\python.exe scripts\check_tooling_config.py
```

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\backend\tests
.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests
.\.venv\Scripts\python.exe -m mypy apps\backend\app
.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"
.\.venv\Scripts\python.exe -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v
.\.venv\Scripts\python.exe scripts\check_project_state.py
.\.venv\Scripts\python.exe scripts\check_architecture.py
.\.venv\Scripts\python.exe scripts\dev_context.py
.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v
.\.venv\Scripts\python.exe scripts\check_secrets.py
.\.venv\Scripts\python.exe -m pip check
```

```powershell
Set-Location apps\frontend
npm run typecheck
npm test
npm run build
npm ls --all
```

GoldTier sponsor-example validation is optional when private archives are absent:

```powershell
.\.venv\Scripts\python.exe -m pip install -r scripts\requirements-contract-validation.txt
.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present
```

The expected private classification remains 19 valid, 19 invalid/quarantined, and 48
not validated. Contradictory examples must not become canonical fixtures.

## Security and data boundary

- Use synthetic fixtures only; uploaded bytes and raw provider output are not retained.
- Never track `.env`, secrets, tokens, certificates, sponsor credentials, or
  `private/sponsor-artifacts/`.
- Normal logs/events/export contain safe IDs, statuses, correlation, timings, and
  sanitized summaries—not KYC/PII or payloads.
- In memory mode, stores and recovery state are process-local. In Mongo mode, bounded
  structured case/evidence/decision/workflow/target state survives restart through one
  per-case envelope; locks and connector objects remain runtime-only.
- Mongo durability is a local POC recovery feature, not production HA, distributed
  exactly-once execution, regulatory retention, or a production audit record.
- Supported uploads are `.pdf`/`application/pdf`, `.docx`/the standard OOXML DOCX MIME,
  and `.txt`/`text/plain` with UTF-8 content. Extension, MIME, structure/content,
  filename, per-file size, count, and total bytes are all checked. ZIP, macro-enabled
  Office files, embedded DOCX objects, images, and arbitrary binary formats are rejected.
- PDF structure is parsed strictly before IDP invocation; header/trailer markers alone
  are insufficient. DOCX member names are rejected when rooted, UNC-like,
  drive-qualified, traversal-containing, NUL-containing, or backslash-based. These are
  bounded POC checks, not antivirus, CDR, or production document forensics.
- Production RBAC, PDF antivirus/CDR, durable encrypted audit storage, distributed
  orchestration, real auth/TLS, and monitoring are not implemented.

See [POC security boundaries](docs/security/POC_SECURITY_BOUNDARIES.md).

## Handoff documents

- [Final deliverable index](docs/FINAL_DELIVERABLE_INDEX.md)
- [Integration handoff](docs/integration/INTEGRATION_HANDOFF.md)
- [API handoff](docs/integration/API_HANDOFF.md)
- [Adapter conformance checklist](docs/integration/ADAPTER_CONFORMANCE_CHECKLIST.md)
- [Failure/recovery guide](docs/integration/FAILURE_RECOVERY_GUIDE.md)
- [Open sponsor questions](docs/sponsor-questions/OPEN_QUESTIONS.md)

## Repository layout

- `apps/backend/` — FastAPI domain, connectors, orchestration, and tests
- `apps/frontend/` — React/TypeScript/Vite sponsor UI and tests
- `docs/` — architecture, contracts, UAT, demo, security, and integration handoff
- `.ai-pipeline/` — phase planners and quality/review reports
- `scripts/` — demo lifecycle, secret, smoke, and contract validation tools
- `private/sponsor-artifacts/` — local ignored sponsor material; never tracked
## Phase 08 input-driven demo

The normal sponsor demo is input-driven: different synthetic UENs retrieve different
Mock registry, ownership, and GoldTier records, and different uploaded text-based PDFs
genuinely produce document-verification outcomes. The local provider reads PDF text and
uses a deterministic labelled-field parser with project-defined POC extraction
confidence; it is not production OCR or AI validation. Developer/Test Controls are
environment-gated fault-injection tooling only and do not determine normal sponsor
onboarding outcomes.
