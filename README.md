# Data Dividends — Zero-Touch CLM

Proof of concept for Delta Capita's Singapore new-to-bank flow:

`ACRA Singapore -> EDS/orchestration layer -> GoldTier -> human review gate`

Phase 03 preserves the runnable ACRA-to-Mock-GoldTier slice and adds a separate,
case-linked PDF/Mock-IDP/human-review foundation. Mock ACRA and Mock IDP remain safe
defaults, GoldTier remains fully mocked, uploaded bytes are transient, and no live ACRA,
real OCR, final document contract, or Ready-for-Approval interoperability is claimed.

## Repository layout

- `apps/backend/` — FastAPI application, connectors, orchestration, and unit tests
- `apps/frontend/` — React, TypeScript, and Vite onboarding UI
- `docs/architecture/` — architecture and boundary decisions
- `docs/contracts/` — provisional GoldTier contract and discrepancy catalogue
- `mocks/` — reserved for larger external mock datasets in later phases
- `private/sponsor-artifacts/` — local, gitignored sponsor material
- `scripts/` — repository safety and local contract checks

## Prerequisites

- Python 3.12+
- Node.js 22+
- npm 10+

## Backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\apps\backend[dev]"
uvicorn app.main:app --app-dir apps/backend --reload
```

The backend runs at `http://127.0.0.1:8000` and exposes:

- `GET /health`
- `GET /api/onboarding/mock-scenarios`
- `POST /api/onboarding/cases`
- `GET /api/onboarding/cases/{case_id}`
- `POST /api/onboarding/cases/{case_id}/documents`
- `POST /api/demo/onboarding/cases/{case_id}/documents`
- `GET /api/onboarding/cases/{case_id}/documents`
- `GET /api/onboarding/cases/{case_id}/documents/{document_id}`
- `POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews`

Cases are process-local and are cleared when the backend restarts.
The mock-scenario endpoint returns an object containing the backend simulation profile
and a `scenarios` array. Onboarding UEN input is trimmed and uppercased; blank or values
outside the Phase 01 synthetic `nine digits plus one letter` format return 422. This is
a demo validation rule, not a production ACRA UEN specification.

### ACRA connector modes

`ACRA_CONNECTOR_MODE=mock` is the default and requires no credentials or network.
`ACRA_CONNECTOR_MODE=sandbox` validates an HTTPS base URL, a company path template with
one `{uen}` placeholder, a bounded timeout, and a backend-only authorization provider.
See `.env.example` for names only; populate them only from authorized ACRA subscriber
documentation and never commit `.env`.

The exact ACRA Business Profile operation/auth schema is currently Q-012. The generic
static-header adapter and tracked response fixture are integration seams, not claims
about ACRA's contract. Sandbox mode fails closed if required settings are absent. TLS
verification remains enabled and cannot be disabled.

The provisional decoder trims and rejects blank required company/address text before
canonical mapping. Small source-neutral canonical checks independently prevent blank
minimum business values from reaching Mock GoldTier. Current HTTP/status translations
are project-defined provisional adapter policy pending Q-012, not confirmed ACRA
subscriber semantics. Connector exceptions use fixed public codes/messages; private
diagnostic context is never copied automatically into case history or API errors.

Internal canonical provenance retains the query-free registry endpoint for later proof
mapping. Browser case responses intentionally omit that endpoint and expose only the
source system, source environment, and sourcing timestamp needed by the UI.

Run backend and mock-contract checks:

```powershell
python -m pytest apps/backend/tests
python -m ruff check apps/backend scripts tests
python -m mypy apps/backend/app
python -m unittest discover -s tests/contract -p "test_*.py"
```

## Frontend

With the backend running, use a second terminal:

```powershell
Set-Location apps/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the backend at
`http://127.0.0.1:8000`. A separately hosted frontend can set `VITE_API_BASE_URL` at
build time.

Run frontend checks:

```powershell
npm run typecheck
npm test
npm run build
```

TypeScript strict mode is the frontend static check. A dedicated frontend lint ruleset
remains deferred until the team selects and locks the required packages.

## Mock ACRA scenarios

| UEN | Outcome |
|---|---|
| `202400001A` | Complete happy path |
| `202400002B` | Incomplete entity requiring review |
| `202400003C` | Mock GoldTier policy validation failure |
| `202400004D` | Mock GoldTier partial amend requiring review |
| Any other UEN | Mock ACRA not found |

All scenario data is synthetic. See
`docs/architecture/PHASE_02_ACRA_INGESTION.md` for the current connector, source DTO,
mapping, provenance, error, and mode-switching boundaries.

## Mock IDP document workflow

### Phase 03 demo procedure

1. Start the backend and frontend using the commands above.
2. Create the synthetic case `202400001A`, or reopen an existing case by UUID.
3. In **Document review**, choose one of `ALL_FIELDS_MATCH`, `FIELD_MISMATCH`,
   `LOW_CONFIDENCE`, `MISSING_FIELD`, or `PROCESSOR_FAILURE`.
4. Upload a small synthetic PDF. A minimal development fixture can contain
   `%PDF-1.4`, a newline, and `%%EOF`; never use a sponsor/customer document.
5. Inspect the four provisional candidates, independent confidence, Mock provenance,
   and ACRA/canonical comparison.
6. Accept, reject, or correct every field. Observe that the original IDP suggestion
   remains visible and the document reaches `REVIEWED` only after all four decisions.
7. Reopen the case to confirm that process-local document list/detail state is shown.

The UI uses the dedicated `/api/demo/.../documents` endpoint. It accepts a raw
`application/pdf` body, validates a safe display-only `.pdf` name supplied in
`X-Document-Name`, and selects a fixed synthetic scenario at the Mock-only demo
boundary. The generic `/api/onboarding/.../documents` endpoint uses the composed
provider and exposes no Mock scenario in its contract. `IdpProvider`, its input,
metadata, extraction result, and the processing/review service remain provider-neutral.

The PDF is bounded (5 MiB by default), with each streamed chunk checked against
remaining capacity before buffering, checked for a PDF signature and terminal EOF
marker, retained only for the synchronous request, and never stored or returned. The
validated name is retained only as a display label and never used as a path. These
checks are not antivirus, CDR, or complete production PDF validation. The extraction
values are deterministic synthetic scenario data and are not derived from the file;
scanned PDFs and OCR are not supported.

Every field remains `PENDING` for explicit review. Low confidence and mismatch/missing
comparisons are highlighted. The local UI can accept, reject, or correct each field,
while preserving the original extraction separately; this action has no authenticated
reviewer identity and is not a four-eye or compliance approval. The onboarding case
state and history remain unchanged and document operations make no GoldTier call.

See `docs/architecture/PHASE_03_IDP_REVIEW.md` and
`docs/contracts/IDP_FIELD_PROFILE.md`. The four fields, `0.85` development threshold,
normalization, comparison, and completion rules are PROJECT-DEFINED / PROVISIONAL and
not Delta Capita-approved. Q-003, Q-005, Q-013, and Q-014 block a real document
contract, policy, production upload boundary, and authenticated review flow.

## Optional ACRA sandbox smoke verification

The smoke script is manual, excluded from CI, and disabled by default. Run it only
after Q-012 is resolved and authorized configuration is available locally:

```powershell
$env:ACRA_LIVE_SMOKE_ENABLED="true"
$env:ACRA_SMOKE_UEN="<authorised test UEN>"
python scripts/acra_sandbox_smoke.py
```

It reports only `EXECUTED`, `NOT EXECUTED`, or `FAILED` with a safe summary. It never
prints the UEN, credentials, headers, configuration, or response payload. Its disabled
guard runs before settings validation or connector construction, so missing/invalid
sandbox configuration is contained as a sanitized status rather than an import-time
traceback.

## Secret check

The lightweight scanner checks tracked and non-ignored untracked text files and reports
only a rule, file, and line number—never the matched value. It intentionally does not
open ignored sponsor artefacts.

```powershell
python -m unittest discover -s tests -p "test_check_secrets.py"
python scripts/check_secrets.py
```

Copy `.env.example` to `.env` for local configuration. `.env`, sponsor artefacts,
credentials, tokens, certificates, build outputs, and dependency folders must remain
untracked.

This scanner is a current-worktree guard, not a history/archive/entropy scanner. Use an
approved, pinned mature scanner before higher-trust integration or deployment work.

## Sponsor contract validation

The validator reads private OpenAPI and JSON ZIPs in memory and reports only example
filenames, JSON pointers, and failed rules. It never reads the quarantined
authentication collection or writes sponsor data to tracked output.

```powershell
python -m pip install -r scripts/requirements-contract-validation.txt
python scripts/validate_goldtier_examples.py
```

The Phase 00 baseline result is **19 VALID, 19 INVALID / QUARANTINED, and 48 NOT
VALIDATED**. Invalid examples are expected evidence conflicts and must not become
canonical fixtures. `--if-present` lets public CI skip absent private archives safely.

## Contract and authentication status

The seven-operation GoldTier EDS contract is a provisional development contract for
credential-free mocks, not a sponsor-confirmed correction or real-integration
contract. See `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md` and
`docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`.

The supplied credential-bearing authentication collection is quarantined and must not
be reused. Real GoldTier authentication remains blocked until the sponsor confirms
rotation/revocation, supplies a sanitised reference collection, and provides fresh
credentials through an approved mechanism. This does not block Phase 01 mocks.
