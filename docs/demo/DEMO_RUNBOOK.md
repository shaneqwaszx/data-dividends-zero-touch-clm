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
and Node process trees with ACRA Mock, Local POC text-PDF IDP, input-driven synthetic
ownership, and GoldTier Mock, enables gated developer controls, and waits up to
30 seconds for backend health and the frontend document before reporting success.

- Backend health: `http://127.0.0.1:8000/health`
- Frontend: `http://127.0.0.1:5173`
- API schema: `http://127.0.0.1:8000/docs`

The command returns `0` only after both endpoints are healthy. It returns nonzero and
cleans up the exact partial process tree if startup or health verification fails. Open
the frontend only after `Demo started and verified healthy` appears. The banner must
state ACRA Mock, GoldTier Mock, IDP Local POC (`LOCAL_PDF_TEXT`), and Ownership Mock. The supported local browser
path uses Vite's `/api` proxy; cross-origin deployment/CORS is not configured.

The launcher writes process-management metadata to the Git-ignored fixed path
`.runtime/demo-processes.json`. It contains only a session ID, roles, process/listener
PIDs, creation timestamps, executable/command markers, repository marker, and local
ports. Startup output/error logs are also local under `.runtime/`; use synthetic inputs
only and do not submit those logs as UAT evidence.

## Sponsor inputs and fixtures

Use only files under `apps/backend/tests/fixtures/uat/`; their README maps fixture
names. The ordinary sponsor journey is **UEN + actual PDF + Start**. The local provider
reads the labelled PDF text, so content—not filename or a selected scenario—drives
comparison and exception outcomes. Use `clean-company-profile.pdf`, then
`address-mismatch.pdf` with the same UEN, `cycle-uen-clean.pdf` with `202400006F`, and
`second-case-isolation.pdf` with `202400005E` for the supported demonstration.

Developer/Test Controls are collapsed, explicitly synthetic fault-injection/regression
tools. They do not alter the normal sponsor provider composition.

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
# Optional durable restart demonstration

The default `CLM_PERSISTENCE_MODE=memory` remains process-local. To demonstrate the
Phase 12 local durable POC with an already-running Mongo server, set:

```powershell
$env:CLM_PERSISTENCE_MODE = "mongo"
$env:MONGO_URI = "mongodb://127.0.0.1:27017"
$env:MONGO_DATABASE = "clm_poc"
```

Start the demo, create a case, record its case ID/status, stop the demo, and start it
again. Dashboard/Review and direct case open must show the same case and structured
evidence without provider replay. `reset_demo_windows.bat` restarts processes but does
not delete Mongo data. No general durable-data purge command is supplied.

# Phase 13 authenticated team demo

Before backend startup, run
`python scripts/generate_admin_bootstrap_password_hashes.py`.
Enter and confirm a password for each prompt, then place only the six emitted scrypt
hash assignments in the local untracked `.env`. Do not save plaintext passwords in the
repository, shell history, launcher scripts, screenshots, or UAT evidence. The browser
sign-in user IDs are `maya-lim`, `ethan-tan`, `sophia-ng`, `ryan-lee`, and `olivia-koh`.
These are synthetic POC identities. If a local `.env` contains hashes generated before
the identity remediation, regenerate all six hashes: the old setting names are
intentionally not reused.

Maya Lim and Ethan Tan see only Alpha cases. Sophia Ng and Ryan Lee
see only Beta cases. Olivia Koh has global/cross-team Director
scope and must explicitly select a team when creating. The persisted team IDs remain
`TEAM_A` and `TEAM_B`. Inaccessible case IDs appear unavailable, not forbidden. Priority
is shown as Unset, Low, Medium, or High. Those controls write null, 1, 5, or 10 to the
compatible integer field; existing values 1–3, 4–7, and 8–10 display as Low, Medium,
and High. Portfolio ordering remains backend-owned and priority has no risk, SLA,
routing, escalation, approval, or regulatory meaning.

The sixth bootstrap identity is `hr-admin`. It can administer synthetic users and
teams, but it cannot view cases, Dashboard, Onboarded, Audit, or mutate policy. Policy
values are read from the backend catalogue; only Relationship Manager and Director can
edit the two runtime thresholds. Such an edit affects newly created cases only.

To create the reproducible two-team portfolio through normal authenticated APIs, start
the backend with Demo Controls enabled and run:

```powershell
python scripts/seed_phase13_demo.py --base-url http://127.0.0.1:8000
```

The script prompts for the Director password, signs in, creates or reuses five synthetic
UEN cases per team, supplies priorities `10, 8, 5, 1, unset` atomically when creating,
and drives every missing case through the supported synthetic `STRAIGHT_THROUGH`
document workflow. It prefers an exact successful showcase case if unrelated history
contains the same team/UEN, and exits nonzero unless every intended pair has a correctly
team-owned/prioritised `COMPLETED` / `MOCK_GOLDTIER_SUBMITTED` case. It never deletes or
rewrites colliding history. It neither creates credentials, assigns terminal state, nor
writes Mongo directly.

With `CLM_PERSISTENCE_MODE=memory`, all cases are process-local. Run the seeder after
every backend restart; a second run in the same backend process reuses the ten cases.
With `CLM_PERSISTENCE_MODE=mongo`, the same application model and Dashboard history are
durable. Use only synthetic data.

After sign-in, Dashboard is the default view. Maya/Ethan receive DBS-only totals,
distributions, trend, and case lists; Sophia/Ryan receive OCBC-only data; Olivia receives
both authorized team portfolios. Select **Open** in Highest-priority active cases or
Recent cases to reuse the existing case detail flow. **Refresh** rereads the backend;
it does not run onboarding providers. Factual completion rate has no SLA, regulatory,
approval, risk, or staff-performance meaning.

For an engineering-only repeatable remote validation, explicitly select a newly generated
database matching `clm_p13_<24 lowercase hex>` and run
`python scripts/validate_phase13_mongo_dashboard.py` with `PYTHONPATH=apps/backend;.`.
The script rejects `clm_poc` and every non-allowlisted database before application
composition. It creates ephemeral runtime-only authentication, uses the application APIs
and authenticated seeder, performs projection-limited checks of the disposable
collection, restarts the local validation app, and prints only safe counts. It does not
print the Mongo URI/host or credentials. Physical validation databases use strict
generated `clm_p12_*` / `clm_p13_*` names; cleanup retries, verifies absence, and reports
only a safe exception class on exhaustion. Run physical pytest with `--tb=no` so
driver details cannot enter terminal evidence.
