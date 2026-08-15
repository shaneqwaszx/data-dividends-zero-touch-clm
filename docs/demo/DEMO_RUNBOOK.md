# Demo Runbook

## Prerequisites

- Windows with PowerShell/cmd.
- Python 3.12+ and Node.js 22+/npm 10+ available.
- Repository checked out on the intended branch.
- No real customer/sponsor document used.

One-time setup from repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\backend[dev]"
Set-Location apps\frontend
npm ci
Set-Location ..\..
```

No script installs software automatically.

## Start

```powershell
.\scripts\start_demo_windows.bat
```

The script verifies Python 3.12+, Node.js 22+, npm 10+, the backend imports, the locked
frontend dependency tree, and free ports. It then starts hidden launcher-owned Python
and Node process trees with safe Mock modes, enables both demo controls, and waits up to
30 seconds for backend health and the frontend document before reporting success.

- Backend health: `http://127.0.0.1:8000/health`
- Frontend: `http://127.0.0.1:5173`
- API schema: `http://127.0.0.1:8000/docs`

The command returns `0` only after both endpoints are healthy. It returns nonzero and
cleans up the exact partial process tree if startup or health verification fails. Open
the frontend only after `Demo started and verified healthy` appears. The banner must
state ACRA Mock, GoldTier Mock, IDP Mock, and Ownership Mock. The supported local browser
path uses Vite's `/api` proxy; cross-origin deployment/CORS is not configured.

The launcher writes process-management metadata to the Git-ignored fixed path
`.runtime/demo-processes.json`. It contains only a session ID, roles, process/listener
PIDs, creation timestamps, executable/command markers, repository marker, and local
ports. Startup output/error logs are also local under `.runtime/`; use synthetic inputs
only and do not submit those logs as UAT evidence.

## Scenarios and fixtures

Open **Demo/Test Controls** and select an integrated preset. Use only files under
`apps/backend/tests/fixtures/uat/`; their README maps fixture names. The Mock provider
does not OCR those file contents—the file is realistic upload evidence and the gated
preset controls deterministic output.

Primary demonstrations:

- `STRAIGHT_THROUGH`
- `DOCUMENT_DISCREPANCY`
- `MULTIPLE_DOCUMENT_BLOCKERS`
- `LOW_CONFIDENCE`
- `OWNERSHIP_CYCLE`
- `OWNERSHIP_INCOMPLETE`
- `MULTIPLE_OWNERSHIP_PATHS`
- `EXISTING_PARTY`
- `TARGET_FAILURE`
- `PARTIAL_AMEND`
- `RECOVERY`

Historical aliases remain API-compatible but are not the preferred presenter labels.

## Evidence export

After a synthetic case is visible, select **Export safe UAT evidence**. The downloaded
JSON is safe for project submission within the synthetic POC boundary. Verify case ID,
scenario, final state, blockers, interactions, target operation names, timings,
warnings, environment, and timestamp. It intentionally excludes PDF/provider payloads.

## Reset and shutdown

All state is in memory. A backend restart clears cases, documents, ownership graphs,
automation, provider bindings, target ledger, and recovery state. It does not delete
files or sponsor material.

```powershell
.\scripts\reset_demo_windows.bat
```

Reset performs verified stop → verified fresh start → health checks. It returns nonzero
without starting if stop ownership/shutdown verification fails. A successful reset
changes the launcher session and backend process and makes every earlier process-local
case return `404`; it does not delete files. To stop:

```powershell
.\scripts\stop_demo_windows.bat
```

Stop validates each recorded PID using its creation time, executable, fixed project
command/working-directory markers, role, descendant listener, and port before using
`taskkill /PID <owned-pid> /T /F`. It never selects `python.exe`, `node.exe`, a window
title, or a port occupant broadly. It returns `0` only after the recorded process trees
and their listeners are gone. A `RUNNING` record is valid only when it contains exactly
one backend and one frontend role. Missing, duplicate, or unknown roles make Stop and
Reset fail nonzero before any termination; the metadata is retained for safe recovery,
and Reset does not start a replacement session. With no metadata it is an idempotent
success and states that no process was stopped; any unowned port occupant is reported
and left alive.

## Expected clean output

- Status: `COMPLETED`.
- Mock target: `MOCK_GOLDTIER_SUBMITTED`.
- Completed stages: Registry, Document, Ownership, Readiness, Mock GoldTier.
- Human interventions after Start: `0`.
- Target calls in export: `SEARCH, SHELL, POLICY, AMEND`.
- Warnings retain provisional/live limitations.

## Troubleshooting

| Symptom | Safe action |
|---|---|
| Backend port 8000 occupied | Startup aborts nonzero and does not terminate the occupant; stop the known process yourself, then rerun |
| Frontend port 5173 occupied | Startup aborts nonzero and does not terminate the occupant; free the port, then rerun |
| `.venv` missing | Run one-time Python setup; script does not install automatically |
| `node_modules` missing | Run `npm ci` in `apps/frontend` |
| Demo controls hidden | Use the start script or set both `DEMO_CONTROLS_ENABLED=true` and `VITE_DEMO_CONTROLS_ENABLED=true` before starting the respective processes |
| Demo API returns `DEMO_CONTROLS_DISABLED` | Backend flag is false; frontend visibility alone cannot enable routes |
| Invalid fixture | Use a `.pdf` fixture with signature/EOF; `invalid-document.pdf` is intentionally rejected |
| Health fails | Read the backend console's safe local startup error; verify dependency install and port |
| Banner remains unavailable | Confirm `/api/system/execution-profile` through the frontend proxy and backend health |
| `RECOVERY_PENDING` | Select **Complete safe recovery** once; do not restart if you want to preserve that case's process-local ledger |
| Runtime metadata exists | Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\demo_lifecycle.ps1 -Action Status`, then the normal stop command |
| Stale nonexistent PIDs | Normal stop verifies they are absent and clears only the fixed metadata file |
| Incomplete/corrupt `RUNNING` metadata | Stop/reset reports `DEMO_RUNTIME_STATE_INCOMPLETE`, kills nothing, and retains the file. Do not infer ownership from a port. Restore the exact original launcher metadata if available, then use normal stop; otherwise stop only independently verified launcher-owned trees and keep the state for diagnosis until both endpoints and ports are clean |
| PID/command/creation mismatch | Stop/reset fails safe, retains metadata, and kills nothing. Confirm both POC endpoints are unavailable and the ports are not owned by the old POC before manually removing only `.runtime\demo-processes.json`; never edit a PID to force termination |

Every lifecycle command propagates a nonzero exit code on ownership, port, startup,
health, or shutdown failure. Do not treat an error followed by a shell prompt as success.

## Clean-room audit limitation

Phase 07 remediation executed start, stop, reset, occupied-port, unrelated-process,
stale/PID-mismatch, process-local case clearing, and repeated lifecycle checks in the
available Windows workspace. It does not prove a separate physical clean machine,
production deployment, external network, or live credentials. A sponsor/evaluator
should repeat the one-time setup and UAT-01 from a fresh clone as the independent
reproducibility check.
