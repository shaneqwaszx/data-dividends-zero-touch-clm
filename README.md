# Data Dividends — Zero-Touch CLM

Proof of concept for Delta Capita's Singapore new-to-bank flow:

`ACRA Singapore -> EDS/orchestration layer -> GoldTier -> human review gate`

Phase 06 composes the registry, document, deterministic ownership/UBO, readiness, and
Mock GoldTier foundations into one server-driven workflow started with a UEN and one
PDF. It runs straight through when the narrow provisional policy is satisfied, or
pauses at a typed human exception and resumes automatically after an allowed resolution.
Mock providers remain safe defaults. No live hierarchy, sponsor-approved document/UBO
policy, real GoldTier, or Ready-for-Approval interoperability is claimed.

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
- `POST /api/onboarding/cases/{case_id}/ownership/load`
- `POST /api/demo/onboarding/cases/{case_id}/ownership/load`
- `POST /api/onboarding/cases/{case_id}/ownership/analyze`
- `GET /api/onboarding/cases/{case_id}/ownership`
- `GET /api/onboarding/cases/{case_id}/ubo-candidates`
- `POST /api/clm/cases`
- `GET /api/clm/cases/{case_id}`
- `POST /api/clm/cases/{case_id}/readiness/evaluate`
- `GET /api/clm/cases/{case_id}/submission-plan`
- `POST /api/clm/cases/{case_id}/submit`
- `POST /api/clm/zero-touch/cases`
- `POST /api/clm/zero-touch/cases/{case_id}/documents`
- `GET /api/clm/zero-touch/cases/{case_id}`
- `POST /api/clm/zero-touch/cases/{case_id}/start`
- `POST /api/clm/zero-touch/cases/{case_id}/resume`
- `POST /api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve`

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
| `202400005E` | Existing Mock GoldTier party requiring sponsor policy |
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

## Mock ownership and provisional UBO workflow

### Phase 04 demo procedure

1. Start the backend and frontend, then create or reopen synthetic case `202400001A`.
2. In **Ownership & UBO**, choose `DIRECT_OWNER`, `INDIRECT_OWNER`, `MULTIPLE_PATHS`,
   `BELOW_THRESHOLD`, `INCOMPLETE_CHAIN`, `CYCLE`, or `PROVIDER_FAILURE`.
3. Select **Load synthetic ownership**. The dedicated demo endpoint configures the Mock
   provider; the generic ownership API contains no scenario input.
4. For a `LOADED` record, select **Analyze ownership paths**.
5. Inspect owned-party -> owner relationships, intermediate legal entities, natural
   persons, safe provenance, direct/indirect paths, path multiplication, aggregated
   ownership, and the provisional threshold classification.
6. Use `MULTIPLE_PATHS` to see independent paths aggregate once, `INCOMPLETE_CHAIN` and
   `CYCLE` to see truthful `REVIEW_REQUIRED`, and `PROVIDER_FAILURE` to see a retrievable
   sanitized `FAILED` record.

The calculation engine uses Decimal arithmetic and retains deterministic evidence; the
frontend does not recalculate percentages. The default
`UBO_OWNERSHIP_THRESHOLD_PERCENT=25` and inclusive `aggregated ownership >= threshold`
comparator are **PROJECT-DEFINED / PROVISIONAL / PENDING Q-004**. `ANALYZED` means only
that the ownership calculation completed. A `PROVISIONAL_UBO_CANDIDATE` is not a legal
UBO/controller finding, compliance approval, GoldTier approval, or Ready-for-Approval.

Phase 04 quality-gate remediation also enforces legal-entity owned parents, fresh nested
revalidation of every untrusted provider result, opaque server-only source references,
atomic versioned terminal-state writes, bounded digest path IDs, six-decimal threshold
configuration, and exact string-based Decimal display. Concurrent duplicate operations
return a conflict rather than overwriting an accepted terminal result.

Graph limits default to 100 parties, 200 relationships, depth 8, 64 paths per candidate,
and 256 total paths. Excess depth/path enumeration routes to review instead of silently
truncating a definitive result; malformed/oversized provider graphs fail safely. The
ownership workflow never mutates the canonical ACRA entity, onboarding state, or Phase
03 documents and makes no ACRA/GoldTier call.

See `docs/architecture/PHASE_04_RELATED_PARTIES_UBO.md` and
`docs/contracts/OWNERSHIP_UBO_PROFILE.md`. Q-002/Q-004/Q-006/Q-007 still block an
authoritative hierarchy adapter, sponsor-approved UBO policy, related-party writes, and
final Singapore mappings.

## Phase 05 staged CLM demo

1. Start the backend and frontend, then create staged case `202400001A` through the UI
   or `POST /api/clm/cases`.
2. Upload a synthetic PDF and explicitly review all document fields.
3. Load and analyze the `DIRECT_OWNER` synthetic ownership scenario.
4. Evaluate the current backend readiness. The five stages are Registry, Document
   Review, Ownership & UBO, Readiness, and Mock GoldTier.
5. When the backend returns `READY_FOR_MOCK_SUBMISSION`, submit once to Mock GoldTier.
   The happy path runs search, conditional shell creation, policy creation, and amend,
   then returns `MOCK_GOLDTIER_SUBMITTED` in the unified CLM summary.

Other principal statuses are `COLLECTING_EVIDENCE`, `REVIEW_REQUIRED`, `SUBMITTING`,
and `FAILED`. Current canonical data and document/ownership evidence are revalidated by
the backend immediately before submission; React does not decide eligibility. Mock
submission is snapshot-bound and recoverable after process-local terminal-finalization
failure without repeating the accepted business sequence.

`MOCK_GOLDTIER_SUBMITTED` means only that credential-free synthetic Mock operations
completed. It is not real GoldTier interoperability, customer/compliance approval, or
Ready-for-Approval. Sponsor questions still block the final IDP/readiness and UBO
policies, live ACRA binding, seeded hierarchy retrieval, related-party writes, PingFed,
real GoldTier, and the approval transition.

See `docs/architecture/PHASE_05_CLM_ORCHESTRATION.md`,
`docs/contracts/CLM_READINESS_POLICY.md`, and
`docs/contracts/GOLDTIER_SUBMISSION_PREPARATION.md` for the detailed boundaries.

## Phase 06 zero-touch demo

1. Start the backend and frontend, choose a synthetic UEN and PDF, then select the
   single **Start zero-touch onboarding** action.
2. The browser polls only while the server reports `RUNNING` or `RESUMING`. Registry,
   document, ownership, readiness, and Mock GoldTier decisions remain server-owned.
3. `202400001A` with matching synthetic evidence reaches `COMPLETED` with zero human
   interventions. Mismatch and low-confidence cases stop at **Human review required**
   and offer only actions returned by the server. `KEEP_REGISTRY_VALUE` applies only to
   source conflict; low-confidence-only/missing evidence has no provisional action.
4. Ownership cycle/incomplete, existing-party, and partial-target outcomes stop without
   an unsafe approval action. Provider/target failures are shown separately as technical
   failures. Manual scenario controls are hidden unless
   `VITE_DEMO_CONTROLS_ENABLED=true` and remain under **Demo/Test Controls**.

The generic API contains no scenario selector. Dedicated `/api/demo/clm/zero-touch/...`
routes provide the synthetic `STRAIGHT_THROUGH`, document discrepancy/low confidence,
ownership cycle/incomplete, existing party, target failure, and provider failure
matrix. All demo discovery/selection routes fail closed when
`DEMO_CONTROLS_ENABLED=false`; both backend and browser flags default false.

See `docs/architecture/PHASE_06_ZERO_TOUCH_ORCHESTRATION.md`,
`docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`, and
`docs/contracts/INTEGRATION_ADAPTER_CONTRACTS.md`. State, locks, events, metrics, and
target recovery are process-local POC facilities and do not claim durable restart or
exactly-once processing.

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
