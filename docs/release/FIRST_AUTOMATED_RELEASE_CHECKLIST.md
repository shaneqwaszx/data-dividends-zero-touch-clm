# First pipeline-assisted release: checklist

| Field | Value |
|---|---|
| Status | **Draft checklist. Authorises nothing.** No step here has been run against the host or the registry |
| Intended first use | The simplest real release: **frontend-only** (LOW) or **assistant-only** (MEDIUM), one service |
| Operator | The existing exclusive host operator session, in its own owner-approved window. No other session contacts the host |
| Principle | First use is supervised: dry runs first, and every existing owner gate still applies |

`[owner]` marks a step only the owner can do. A failed step is a stop.

## A. One-time setup

| # | Step | Needs owner approval |
|---|---|---|
| A1 | The pipeline branch is reviewed and merged to `main` by the owner | yes `[owner]` |
| A2 | On this machine: `.\tools\release.ps1 status` and `.\tools\release.ps1 baseline` both succeed | no |
| A3 | Create the two GHCR tokens and run `creds bootstrap` for `publish` and `pull` (`GHCR_CREDENTIAL_GUIDE.md`) | yes `[owner]` (creates credentials) |
| A4 | Write the operator configuration file outside the repository: SSH destination, key path, the host directory that holds the Mongo archives | no (the host operator session writes it; it holds no secret) |
| A5 | Confirm with the host operator that `/etc/clm/mongo.uri`, `/etc/clm/compose.env` and `/opt/clm` are where `catalog.HostProfile` says, and that `/run/lock` is writable | no (read-only on the host, by the host operator) |

## B. Prepare the release (this machine only)

| # | Step | Pass condition |
|---|---|---|
| B1 | `git fetch origin`; check out the approved commit in a clean checkout; `release.ps1 verify-source --commit <sha> --tree <tree>` | `PASS` |
| B2 | `release.ps1 checks --change-class <class>` | No `FAIL`. Every `NOT_RUN` is understood and, where the class needs it, run by hand |
| B3 | `release.ps1 image --service <service> --commit <sha> --reference <tag> --image-id <id>` | File equality `PASS`; for the assistant the fingerprint equals the reviewed value |
| B4 | Write the release request: one service, risk class, rollback target, smoke expectations, QG verdicts | The rollback target is the digest currently pinned on the host, confirmed by the host operator, not copied from an old document |
| B5 | `release.ps1 manifest --request <file>`, `validate`, `plan` | The plan changes exactly one service; `services_must_not_change` lists all the others |
| B6 | Independent Quality Gate reads the manifest, the plan and the image evidence | `PASS` or `PASS WITH NOTES` with no open P0 to P2 |

## C. Publish

| # | Step | Pass condition |
|---|---|---|
| C1 | `[owner]` `release.ps1 approve ... --action publish` | Record written; window is short |
| C2 | `release.ps1 publish --manifest <manifest> --approval <record> --dry-run` | `DRY_RUN_OK`; the list shows one login, one push per image, one logout |
| C3 | `release.ps1 publish ... --execute` | `manifest.published.json` written; the registry config digest equals the qualified image |
| C4 | On GitHub, confirm the package is still **private** and no `latest` tag exists | As stated |

## D. Deploy (host operator session, owner-approved window)

| # | Step | Pass condition |
|---|---|---|
| D1 | `[owner]` `release.ps1 approve --manifest manifest.published.json ... --action deploy [--auto-rollback]` | Record written for the **published** manifest |
| D2 | `release.ps1 deploy ... --operator-config <file> --dry-run` | `DRY_RUN_OK`. Every preflight row is `PASS`, or `SKIPPED` with a stated reason (backups, for a frontend-only release). **Read the rows.** This is the first time the tool reads the real host: compare each value with what the operator sees by hand |
| D3 | Compare the host steps in the plan with the Approval B scripts line by line | Same commands, same order |
| D4 | `[owner]` go-ahead after D2 and D3 (kept for the first use, whatever the class) | Given |
| D5 | `release.ps1 deploy ... --execute` | Exit code 0, state `DEPLOYED_AWAITING_ACCEPTANCE` |
| D6 | By hand on the host, read-only: container ids of every other service unchanged; `compose.env` differs from its backup by one line | As stated (the tool has checked this; the first use checks the tool) |

## E. Acceptance and record

| # | Step | Pass condition |
|---|---|---|
| E1 | `[owner]` works through `BROWSER_ACCEPTANCE_RUNSHEET.md` | Every row as expected |
| E2 | `[owner]` `release.ps1 accept --manifest ... --result pass --accepted-by <owner>` | `known_good` now names this release |
| E3 | Copy the release's state folder (manifest, approvals, plan, results, audit log, runsheet) into the release evidence | Contains no credential (`check_secrets.py` passes on the copy) |
| E4 | Note every difference between what the tool reported and what the host showed | Each one becomes a fix or a documented limitation before the second use |

## F. If something stops

| State | Do |
|---|---|
| Refused before starting (exit 3) | Fix the cause. Nothing was contacted |
| `FAILED_NO_CHANGE` | Nothing changed. If no host change had begun the approval is still usable in its window |
| `ROLLED_BACK` | The previous image is serving. Stop; investigate; a new attempt needs a new approval |
| `FAILED_HELD` | **Run nothing else.** Tell the owner the `held_reason`. For an assistant: `dca stop assistant` is the safe action. For a frontend: the previous digest is in `pins_before` |

## G. Not for the first use

Backend releases, more than one service, the hosted provider overlay, the GoldTier overlay
being active, archive transfer (`--transfer load`), and unattended runs.
