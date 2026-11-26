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
jurisdiction before an eligible read-only GoldTier Search, then acquires required registry
evidence, compares documents, reconciles source observations, and calculates ownership/UBO.
Clean evidence reaches an explicit Review & Send confirmation before the ledger-owned Mock
GoldTier sequence. Permitted blocker resolutions resume through the same backend owners.

`COMPLETED / MOCK_GOLDTIER_SUBMITTED` means configured POC stages and the accepted
Mock target operations/readback completed. Registry evidence retains its synthetic Mock
or official Marketplace Mock identity. It is not customer/compliance approval, Ready-for-Approval, a legal UBO
determination, or live ACRA/GoldTier interoperability.

## Current capabilities

- Clean evidence preparation with zero exception-resolution interventions; explicit Review & Send
  still confirms the prepared target submission.
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
- A separate, read-only AI Assistant service (`apps/assistant`, port 8100) that explains
  one case to the signed-in user from the backend's own case data. It cannot change a
  case and falls back to a case-data answer when no model is available. See
  [apps/assistant/README.md](apps/assistant/README.md).

Live ACRA, live hierarchy, PingFed/real GoldTier, final document/UBO policy, related-
party writes, production reviewer policy, and Ready-for-Approval remain blocked or
unconfirmed. Authenticated POC reviewer roles and backend capability/team checks are implemented. See the [sponsor dependency matrix](docs/sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md).

## Quick start — sponsor demo (Windows and macOS)

Prerequisites: Python 3.12+, Node.js 22+, and npm 10+. Optional: Tesseract for OCR of
image-based documents (`brew install tesseract` on macOS). The backend uses
`LOCAL_OCR_EXECUTABLE` when it is set to an absolute Tesseract path, otherwise
`tesseract` on `PATH`.

Both platforms run the same composition: synthetic ACRA `MOCK`, IDP `LOCAL_PDF_TEXT`,
Mock ownership, GoldTier `MOCK`, and gated developer controls. These process variables
take precedence over `.env`.

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

After pulling a new `main`, rerun the dependency install steps (`pip install -e` for
the backend, and for `apps/assistant` if you run the AI Assistant, plus `npm ci`); new
packages are not installed automatically.

### Windows

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

### macOS

There is no macOS launcher; start the two processes manually. One-time setup from the
repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e "./apps/backend[dev]"
(cd apps/frontend && npm ci)
```

Start the backend in one terminal:

```bash
cd apps/backend
APP_ENV=development \
ACRA_CONNECTOR_MODE=mock \
GOLDTIER_CONNECTOR_MODE=mock \
IDP_CONNECTOR_MODE=local_pdf_text \
OWNERSHIP_CONNECTOR_MODE=mock \
DEMO_CONTROLS_ENABLED=true \
PHASE13_BROWSER_ORIGIN=http://127.0.0.1:5173 \
  ../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd apps/frontend
VITE_DEMO_CONTROLS_ENABLED=true \
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000 \
  node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Stop either process with `Ctrl+C`. Restarting the backend in memory mode is the macOS
equivalent of Reset. These manual commands do not perform the Windows launcher's
port, health, or process-ownership checks: confirm ports `8000` and `5173` are free
first (`lsof -iTCP:8000 -iTCP:5173 -sTCP:LISTEN`) and check the health URL after start.

If your `.env` selects `CLM_PERSISTENCE_MODE=mongo` and Mongo is not reachable, startup
fails closed; add `CLM_PERSISTENCE_MODE=memory` to the backend command to run without
it. `.env` values that are invalid in combination with the Mock ACRA lane (for example
`GARDEN_SUPPLEMENT_ENABLED=true`) also stop startup; these apply on both platforms.

## Signing in

Every page needs a signed-in POC account. The accounts are fixed synthetic profiles:

| User ID | Display name | Role |
|---|---|---|
| `maya-lim` | Maya Lim | Client onboarder |
| `sophia-ng` | Sophia Ng | Client onboarder |
| `ethan-tan` | Ethan Tan | Relationship manager |
| `ryan-lee` | Ryan Lee | Relationship manager |
| `olivia-koh` | Olivia Koh | Director |
| `biz-ops` | POC HR Administrator | HR |
| `support-user` | Support User | Support |

Passwords are never stored in the repository. Each account's scrypt hash is read from
`.env` (`PHASE13_<USER_ID>_PASSWORD_HASH`, for example `PHASE13_MAYA_LIM_PASSWORD_HASH`;
`biz-ops` uses `PHASE14_5_HR_ADMIN_PASSWORD_HASH`). When the backend first creates the
accounts, a missing or malformed hash is a configuration error that names the setting to
fix, and the backend does not start. A new setup therefore needs **all seven** hashes; in
memory mode the accounts are created again on every start, so all seven are always
required. Choose your own passwords and generate the lines to paste into your `.env`:

```powershell
.\.venv\Scripts\python.exe scripts\generate_admin_bootstrap_password_hashes.py
```

In memory mode, to change only some passwords later, regenerate just those lines (keep
the others in `.env`). In Mongo mode, accounts that already exist keep their stored hash,
so editing `.env` does not change their passwords.

```powershell
.\.venv\Scripts\python.exe scripts\generate_admin_bootstrap_password_hashes.py --user maya-lim --user biz-ops
```

The script prompts for each password (input is hidden) and prints only the hash lines.

## Full local stack — Marketplace Mock + AI Assistant (Windows, three terminals)

This is the composition used for the fuller demo: the official ACRA API Marketplace
Mock with the whitelisted direct-holder ownership overlay, local PDF text extraction,
Mock GoldTier, memory persistence, and the AI Assistant. Run each block in its own
PowerShell window from your clone (replace `<repo>` with its path). Process variables
take precedence over `.env`.

Prerequisites beyond the quick start:

- Your **own** ACRA API Marketplace Mock credentials in the root `.env`
  (`ACRA_API_MARKETPLACE_MOCK_CLIENT_ID`, `ACRA_API_MARKETPLACE_MOCK_SECRET_KEY`). Without
  them, in Terminal 1 set `$env:ACRA_CONNECTOR_MODE = "mock"` (the synthetic local
  registry) **and** remove the `ACRA_MARKETPLACE_OWNERSHIP_OVERLAY` line: the hybrid
  overlay is accepted only on the Marketplace Mock lane, so startup stops if both are set.
  Also make sure your `.env` does not set `ACRA_MARKETPLACE_OWNERSHIP_OVERLAY` to
  `hybrid_direct_overlay` or `ACRA_MARKETPLACE_OPQ_SCENARIO` to anything other than
  `five_layer_simulation` (the `.env.example` values are safe). There is no automatic
  fallback.
- The AI Assistant's own dependencies (one time, from the repository root; the quick
  start's `pip install` covers only the backend):

  ```powershell
  .\.venv\Scripts\python.exe -m pip install -e .\apps\assistant
  ```

- Login hashes in `.env` (see [Signing in](#signing-in)).
- For AI answers: [Ollama](https://ollama.com) running with `ollama pull ministral-3:8b`.
  Without a model, the assistant still opens and answers from case data only.

Terminal 1 — backend (port 8000):

```powershell
Set-Location -LiteralPath '<repo>'
$env:APP_ENV = "development"
$env:CLM_PERSISTENCE_MODE = "memory"
$env:ACRA_CONNECTOR_MODE = "api_marketplace_mock"
$env:ACRA_MARKETPLACE_OWNERSHIP_OVERLAY = "hybrid_direct_overlay"
$env:REGISTRY_CACHE_MODE = "auto"
$env:IDP_CONNECTOR_MODE = "local_pdf_text"
$env:GOLDTIER_CONNECTOR_MODE = "mock"
$env:PHASE13_BROWSER_ORIGIN = "http://127.0.0.1:5173"
.\.venv\Scripts\python.exe scripts\dev_preflight.py
if ($LASTEXITCODE -eq 0) {
  Set-Location -LiteralPath '.\apps\backend'
  ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} else {
  Write-Error "Preflight failed; fix the reported configuration first."
}
```

`dev_preflight.py` reports the persistence mode, the configured ACRA and GoldTier modes,
the composed ACRA connector, and whether ACRA credentials are present, without printing
any secret. It exits nonzero when it finds a settings, ACRA credential/connector, or
Mongo problem, and the backend is then not started. It does not check login hashes; a
missing hash is reported when the backend itself starts.

Terminal 2 — frontend (port 5173):

```powershell
Set-Location -LiteralPath '<repo>\apps\frontend'
$env:VITE_BACKEND_PROXY_TARGET = "http://127.0.0.1:8000"
$env:VITE_AI_ASSISTANT_PROXY_TARGET = "http://127.0.0.1:8100"
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Terminal 3 — AI Assistant (port 8100), using a local Ollama model:

```powershell
Set-Location -LiteralPath '<repo>\apps\assistant'
$env:AI_ASSISTANT_CLM_BACKEND_URL = "http://127.0.0.1:8000"
$env:AI_ASSISTANT_LLM_ENABLED = "true"
$env:AI_ASSISTANT_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:AI_ASSISTANT_LLM_MODEL = "ministral-3:8b"
..\..\.venv\Scripts\python.exe -m uvicorn ai_assistant.main:app --host 127.0.0.1 --port 8100
```

Check it with `http://127.0.0.1:8100/assistant/health`, then use **Ask AI Assistant**
(bottom right) on a case page.
Model profiles, model administration, and paid/remote providers (OpenRouter, Claude)
are optional, owner-gated settings described in `apps/assistant/.env.example` and
[AI model configuration](docs/integration/AI_MODEL_CONFIGURATION.md); none is needed
for the local demo, and remote providers spend money on whoever's key is configured.

## Zero-touch demo

1. Leave jurisdiction as **Not specified** (or select **Singapore**), enter synthetic
   UEN `202400001A`, select one or more supported synthetic documents, and choose
   **Start CLM onboarding** once.
3. Observe Registry → Document Verification → Ownership & UBO → Readiness → Mock
   GoldTier.
4. For a clean case, inspect zero exception-resolution interventions, then explicitly Review & Send.
5. Reuse the same UEN with `address-mismatch.pdf` to see PDF-derived source conflict;
   upload `clean-company-profile.pdf` as a replacement to show supersession and
   automatic resume.
6. Use `cycle-uen-clean.pdf` with `202400006F` for the independent ownership-cycle
   case, then `second-case-isolation.pdf` with `202400005E` for existing-party search.

The `20240000x` values above are local synthetic fixtures, not official ACRA API
Marketplace Mock samples. For the official Mock lane, use `11111999A` only for the
Garden entity/basic success path (its shareholder result is empty), `111111111M` only
for the supplied shareholder operation, and `111111111K` only for the supplied capital
operation. Do not combine those operation-specific samples into one ownership case.

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

On macOS:

```bash
.venv/bin/python scripts/dev_preflight.py
.venv/bin/python scripts/dev_preflight.py --persistence-mode memory
.venv/bin/python scripts/dev_preflight.py --persistence-mode mongo
```

Memory mode deliberately skips Mongo connectivity. Mongo mode reports only whether the
configured service is required and reachable; a missing URI or unreachable service
fails the diagnostic without exposing the URI or driver error. The report similarly
shows only ACRA credential presence and the composed connector class.

Registry snapshot reuse is explicitly opt-in with `REGISTRY_CACHE_MODE=mock` and an
`REGISTRY_CACHE_FRESHNESS_SECONDS=7776000` startup setting. New cases freeze the ACTIVE freshness/definitive-negative
TTL policy; historical snapshots keep their original rules. Schema2 reuses successful operation
prefixes and definitive NOT_FOUND evidence across exact provider/environment/contract/dataset/
identifier keys in separate memory/Mongo repositories. Only COMPLETE acquisitions bind to cases;
stale or missing supported operations are fetched through the existing coordinator. Fresh complete
or negative evidence adds zero provider calls. Disabled mode acquires required evidence per case.
Documents, ownership analyses, reconciliation, case state and target outcomes are never cached. See the
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

On macOS, add `CLM_PERSISTENCE_MODE=mongo`, `MONGO_URI=mongodb://127.0.0.1:27017`,
and `MONGO_DATABASE=clm_poc` to the backend command from the macOS quick start, then
stop it with `Ctrl+C` and start it again with the same command.

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

On macOS, use the same commands with `.venv/bin/python` and forward slashes, for
example:

```bash
.venv/bin/python -m pytest apps/backend/tests
.venv/bin/python -m ruff check apps/backend scripts tests
.venv/bin/python -m mypy apps/backend/app
.venv/bin/python scripts/check_secrets.py
(cd apps/frontend && npm run typecheck && npm test && npm run build)
```

`tests.test_demo_lifecycle_windows` and the `*_windows.bat` scripts cover the Windows
launcher only.

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
  orchestration, production SSO/PingFed authentication, and monitoring are not implemented.
  The bounded XPI Sandbox adapter already has verified TLS 1.3 transport; that is not production auth.

See [POC security boundaries](docs/security/POC_SECURITY_BOUNDARIES.md).

## Handing the project over

Do not copy your `.env` (or `apps/assistant/.env`) to someone else. It holds account-
specific secrets: ACRA Marketplace credentials, any AI provider keys (which spend money),
GoldTier sandbox settings, Mongo connection details, and your login password hashes.
Instead give the recipient:

1. The repository (clone from GitHub) and this README.
2. [.env.example](.env.example) and [apps/assistant/.env.example](apps/assistant/.env.example)
   to copy to `.env` / `apps/assistant/.env`. They contain no secrets.
3. Instructions to generate **their own** login hashes (see [Signing in](#signing-in))
   and to obtain **their own** ACRA API Marketplace Mock credentials, or to run with
   `ACRA_CONNECTOR_MODE=mock` without the hybrid overlay, which needs none.

If a shared credential is truly unavoidable, send that single value through a password
manager or another encrypted channel (never email, chat, or a commit), and rotate it once
the handover is complete. Local-only state (`.runtime/`, `apps/assistant/data/`, any
personal worktree paths) is not part of the handover.

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
- `apps/assistant/` — read-only AI Assistant service (FastAPI, port 8100) and tests
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
