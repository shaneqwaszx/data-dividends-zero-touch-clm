# B0 storage cutover evidence (D-108, D-109) - 2026-10-31

Sanitised record of the owner-approved move of the local AI Assistant stores to a persistent
data root. Evidence class: **Local** (the owner's development machine). No credentials, key
material, workspace identifiers, ledger identifiers, usernames, machine paths, case data or
answer text are recorded here. `<repo>` is the owner's checkout; `<root>` is the per-user data
root (`%LOCALAPPDATA%\DataDividendsCLM\assistant`, expanded). The full evidence (fingerprints,
manifests, hashes) stays in an owner-only folder beside the root.

## 1. Baseline

| Item | Value |
| --- | --- |
| Code | main `d760377` (PR #143, D-108) fast-forwarded into the owner's checkout after the assistant stopped; the uncommitted panel-height CSS was unchanged (file and diff hashes equal before and after) |
| Services | only the assistant (port 8100) was stopped and restarted; the memory-mode backend and the frontend stayed up |
| Tools | `backup_stores.py`, `logical_ro.py` (tracked as `store_fingerprint.py`), `resolve_check.py` (tracked as `check_data_root.py`), the owner-only launcher; two independent reviews, PASS WITH NOTES, no Blocking or Medium findings after remediation |

## 2. Source-to-destination mapping

| Store | Earlier location (kept unchanged) | `<root>` path |
| --- | --- | --- |
| Model state and audit | an earlier manual-test worktree, `apps/assistant/data/models/` | `models/model_admin.sqlite3` |
| Active Claude ledger | `<repo>/apps/assistant/data/budget/` | `budget/anthropic_fyp_ledger.sqlite3` |
| GPT-OSS ledger | the Phase B worktree, `apps/assistant/data/budget/` | `budget/ledger.sqlite3` |
| Earlier Claude ledger | `<repo>/apps/assistant/data/budget/` | `archive/` (no setting reaches it) |
| Profiles, knowledge, Chroma | `<repo>/apps/assistant/data/models/`, `.../knowledge/` | `models/profiles.json`, `knowledge/` |

## 3. Verification (cutover)

- All stores `journal_mode=delete`, `quick_check`/`integrity_check` ok; no hot journal at copy time.
- Logical fingerprints: live before stop = stopped = destination (**0 differences**), covering
  activation, HR enablement, qualifications, spending controls, data access policy, audit
  events, connection tests, ledger meta/calls/operator events, answer records, conversations,
  knowledge tables and Chroma, plus a row count of every table.
- Key state carried over: activation revision 13 (Claude Sonnet 5.5 Fast, qualification basis
  `5dc26b296026…`), HR enablement revision 2, 8 qualifications, 76 audit events, active Claude
  ledger 3 calls / US$0.026588 (breaker closed), GPT-OSS ledger breaker open
  (`routing_anomaly`, one unsettled call), 18 answer records.
- Launcher status check: all 7 resolved store paths under `<root>` (runtime, budget CLI and the
  D-094 path), `.env` read without overriding them; key file = `<repo>/apps/assistant/.env`.
- `<root>` access: owner, SYSTEM and Administrators only (inheritance removed before any copy).
- Earlier stores and existing backups: 30 of 30 file hashes unchanged after the cutover, after
  start-up and after the smoke test.
- Start-up wrote no records (only Chroma's internal `acquire_write` counter moved).

## 4. Smoke test and deviation

| Step | Result |
| --- | --- |
| HR Test Connection (free) | Fast passed; also 7 extra Balanced tests (free, audit rows only) |
| Unapproved Fast requalification | explicitly started by an HR administrator through the paid-confirmation dialog; passed 2/2; 2 paid calls, verified, US$0.022216 on the active Claude ledger; **not activated**; recorded as a deviation |
| HR session key | set, then cleared; the server key from `.env` passed the workspace check |
| Approved paid case question (catalog P01#1, synthetic Garden case) | one call, verified, reserved US$0.044394, charged **US$0.005332**; one answer record; answered by Claude Sonnet 5.5 |
| After the test | active Claude ledger 6 calls / US$0.054136, breaker closed; activation still revision 13 on the original qualification; GPT-OSS, archive, Chroma and earlier stores unchanged |

## 5. Recovery and open items

- Recovery is forward only (D-109 C4): the copy-free rollback closed once the root received new
  ledger and audit records.
- The active Claude ledger was last reconciled 2026-10-31 01:42:37 UTC; under the 7-day rule a
  reconciliation is due before **2026-11-07 09:42:37 SGT** (separate authorisation).
- Local hardening (D-109 C5) is recorded in the owner-only evidence folder.
