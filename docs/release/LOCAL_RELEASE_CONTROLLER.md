# Local release controller

| Field | Value |
|---|---|
| Status | Implemented and tested locally (`tools/release/controller.py`). Not scheduled; not installed as a service |
| Runs on | This Windows 11 machine. **Nothing runs while it is off, asleep or signed out** |
| Needs GitHub Actions | No. It works with every Actions job blocked: preparation never leaves the machine |
| Auto-promotion | **Not authorised and not implemented.** The controller cannot publish, approve or deploy |

## 1. What one tick does

```powershell
.\tools\release.ps1 controller tick
```

1. Reads `origin/main` as last fetched and records a notice when it has moved
   (`seen-main.json`). The notice starts nothing: a new commit says nothing about which
   services change or what the rollback is.
2. For each new request file in `<state-dir>\inbox\`:
   verify the exact commit and a clean checkout, run the selected checks, accept or build the
   images, prove their content, read the previous known-good release, validate the manifest
   and the effective Compose configuration, and write `releases\<release id>\manifest.json`.
3. Writes `requests\<request id>\status.json`:
   - `PROMOTION_READY`, with the manifest hash, risk class, services, the checks that were
     **not run**, and the next step for the owner; or
   - `FAILED`, with a stable code.
4. Stops.

A request is processed once. A failed request is never retried by itself:
`.\tools\release.ps1 controller retry --request-id <id>` allows one more attempt and keeps the
failed status file. `controller status` lists every request.

The controller runs in `local` mode: the gate refuses every host, registry and public request
in that mode, so even a programming error could not publish or deploy from a tick. It takes
the same local lock as a deployment, so the two never overlap.

## 2. From promotion-ready to deployed

Promotion is always a person running commands with an owner approval record
(`RELEASE_AUTOMATION_RUNBOOK.md`, sections 3 to 5). The deployment command records its own
result: `DRY_RUN_OK`, `FAILED_NO_CHANGE`, `DEPLOYED_AWAITING_ACCEPTANCE`, `ROLLED_BACK`,
`FAILED_HELD`, then `ACCEPTED` or `ACCEPTANCE_FAILED`. Each result is a numbered file; none is
overwritten. `known-good.json` moves only on `ACCEPTED` and keeps its history.

## 3. Detecting work

| Trigger | First version |
|---|---|
| New approved commit | `git fetch origin` by the engineer, then a tick records the new head. The engineer writes the request |
| New request | A JSON file placed in the inbox |
| New approval | Not watched. The operator passes the approval file to `publish` or `deploy` |

The checkout the controller works in must already be at the request's commit and clean. The
controller does not switch branches or create worktrees: Git mutations stay with the
coordinating session (`AGENTS.md`).

## 4. Optional scheduling (not installed)

A Windows Task Scheduler entry could run a tick every 30 minutes while the owner is signed in:

```powershell
schtasks /Create /SC MINUTE /MO 30 /TN "CLM release controller tick" `
    /TR "pwsh -NoProfile -File <repo>\tools\release.ps1 controller tick"
```

This is a first-install step that needs owner approval. It only prepares; it changes nothing
outside this machine. Without it, run a tick by hand.

## 5. A separate always-on runner (evaluation only; nothing built)

| Option | For | Against |
|---|---|---|
| **A. This Windows machine (current)** | No new infrastructure, cost or credential location. The owner's own machine is already the trust anchor for approvals | Nothing happens while it is off. Docker Desktop must be running. One machine holds the publish token |
| **B. A small dedicated machine the owner controls** (a mini PC, or a second cloud instance used only for building and publishing) | Always on; builds on Linux, the deployment platform; the developer machine no longer holds the publish token | A second machine to patch and secure; the publish token moves to an always-on, network-reachable place; cost; it would still need the owner's approval for every promotion, so it saves waiting time, not decisions |
| **C. A self-hosted GitHub Actions runner** | Familiar workflow files | It is not established that self-hosted jobs start while the account's Actions billing block is in place, and the requirement is not to depend on fixing that. A runner executes whatever a workflow says, so it must never see untrusted pull requests |
| **D. A runner on the production Lightsail host** | None | **Rejected.** A build runner or any workflow on the production host puts build tools, source and a registry credential next to the database, and makes a compromised build a compromised host |

**Recommendation.** Stay with option A for the project's remaining life. The release rate is low
and every promotion waits for the owner anyway. Revisit option B only if
unattended overnight preparation becomes a real need. If B is ever chosen: a dedicated
machine, not the production host; preparation and publication only; the pull identity and
deployment stay with the host operator; approval stays explicit.
