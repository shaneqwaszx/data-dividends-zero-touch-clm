# Data Dividends — Zero-Touch CLM

Proof-of-concept foundation for Delta Capita's Singapore new-to-bank flow:

`ACRA Singapore -> EDS/orchestration layer -> GoldTier -> human review gate`

Phase 00 contains only a runnable FastAPI health service and a React status shell. It
does not contain live ACRA or GoldTier integration, onboarding workflow logic, IDP, or
UBO calculation.

## Repository layout

- `apps/backend/` — FastAPI application and unit tests
- `apps/frontend/` — React, TypeScript, and Vite application shell
- `docs/architecture/` — architecture and boundary decisions
- `docs/contracts/` — provisional GoldTier contract and discrepancy catalogue
- `mocks/` — reserved for mock connector data in later phases
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

The health endpoint is available at `http://127.0.0.1:8000/health`.

Run backend checks:

```powershell
python -m pytest apps/backend/tests
python -m ruff check apps/backend
python -m mypy apps/backend/app
```

## Frontend

```powershell
Set-Location apps/frontend
npm install
npm run dev
```

Run frontend checks:

```powershell
npm run typecheck
npm test
npm run build
```

TypeScript strict mode is the frontend static check in Phase 00. A dedicated frontend
lint ruleset is deferred until the team selects and can lock the required packages.

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

This scanner is deliberately a current-worktree guard, not a history/archive/entropy
scanner. No mature history-capable scanner is installed in the Phase 00 environment;
adding an unpinned external action or unavailable service would weaken reproducibility.
Use an approved, pinned mature scanner before higher-trust integration/deployment work.

## Sponsor contract validation

The validator reads the private OpenAPI and JSON ZIPs in memory and reports only
example filenames, JSON pointers, and failed rules. It never reads the quarantined
authentication collection or writes sponsor data to tracked output.

```powershell
python -m pip install -r scripts/requirements-contract-validation.txt
python scripts/validate_goldtier_examples.py
```

Current Phase 00 result: **19 VALID, 19 INVALID / QUARANTINED, and 48 NOT
VALIDATED**. Invalid examples are expected evidence conflicts and must not become
canonical fixtures. `--fail-on-invalid` is available for a future corrected sponsor
suite. `--if-present` exits successfully with `NOT VALIDATED` when the private archives
are absent, so public CI never requires sponsor material.

## Contract and authentication status

The seven-operation GoldTier EDS contract is a **provisional development contract for
credential-free mocks**, not a sponsor-confirmed correction or a real-integration
contract. See `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md` and
`docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`.

The supplied credential-bearing authentication collection is quarantined. Its material
must not be reused. Real GoldTier authentication remains blocked until the sponsor
confirms rotation/revocation, supplies a sanitised reference collection, and provides
fresh credentials through an approved mechanism when sandbox integration begins. This
does not block Phase 01 mock development.
