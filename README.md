# Data Dividends — Zero-Touch CLM

Proof of concept for Delta Capita's Singapore new-to-bank flow:

`ACRA Singapore → EDS/orchestration → GoldTier → unresolved human approval gate`

The current POC accepts an optional country/jurisdiction, a company registration
identifier (Singapore UEN for the implemented path), and one synthetic PDF. It resolves
jurisdiction before registry selection, then automatically runs registry validation,
deterministic document comparison, ownership/UBO analysis,
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
healthy start only after verified stop; successful reset clears process-local cases
without deleting repository or sponsor files. Lifecycle errors return nonzero and
unowned port occupants are never killed. For recovery and expected outputs, use the
[demo runbook](docs/demo/DEMO_RUNBOOK.md).

## Zero-touch demo

1. Leave jurisdiction as **Not specified** (or select **Singapore**), enter synthetic
   UEN `202400001A`, upload `clean-company-profile.pdf`, and select
   **Start onboarding** once.
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
The current sponsor-readable ACRA field/operation profile is
[ACRA_MOCK_API_PROFILE.md](docs/contracts/ACRA_MOCK_API_PROFILE.md).

## Environment and configuration

Safe normal sponsor defaults are ACRA `MOCK`, IDP `LOCAL_PDF_TEXT` (Local POC),
registry-acquired Mock ownership evidence, and GoldTier `MOCK`.
ACRA also has a sandbox-shaped adapter behind `ACRA_CONNECTOR_MODE=sandbox`; Q-012 still
blocks exact live binding and verification. Its entity-profile seam remains available,
but the Phase 10 expanded sandbox operations fail closed rather than fabricate a
contract. No connector is labeled `LIVE`.

`DEMO_CONTROLS_ENABLED` gates backend demo APIs and
`VITE_DEMO_CONTROLS_ENABLED` controls browser visibility; both default false. Frontend
visibility never bypasses the backend gate. The supported local path uses Vite's API
proxy; production/cross-origin CORS is not configured.

`MONGO_URI` is optional and is used only by `scripts/check_mongodb.py` for a manual
connectivity/read-only diagnostic. MongoDB is not wired into application composition;
the normal onboarding pipeline does not require it and all repositories remain
process-local/in-memory.

See [.env.example](.env.example) and the
[configuration reference](docs/integration/CONFIGURATION_REFERENCE.md). GoldTier/
PingFed placeholders are intentionally unconsumed until a separately authorized real-
adapter task; never populate them from the quarantined collection.

## Tests and checks

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\backend\tests
.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests
.\.venv\Scripts\python.exe -m mypy apps\backend\app
.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"
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
- Current stores, locks, events, bindings, metrics, target ledger, and recovery are
  process-local; restart resets them.
- The default PDF upload limit is 5 MiB (`5242880` bytes); it is a bounded POC setting,
  not a production document policy.
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
