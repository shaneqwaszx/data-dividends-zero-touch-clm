# Spending stores: first start, health and recovery (D-138 R4)

Each paid provider has one D-118 session store in the assistant's data volume:

| Provider | Store |
|---|---|
| Claude | `/data/budget/sessions/anthropic.sqlite3` |
| GPT-OSS | `/data/budget/sessions/openrouter.sqlite3` |

These are the configuration defaults. The compose files set no ledger path. The volume is the explicit, pre-created `ASSISTANT_DATA_VOLUME`, so a restart, an image upgrade or a container rebuild keeps every expenditure record. Never remove the volume. Take a snapshot before every window that changes the assistant.

Never edit a database file, and never copy one store over another. Every recovery below uses an existing guarded control, a supported script, a file move or a single-file restore.

## First start

On a genuine first start the stores are absent. That is normal, and the check shows `LEDGER_CREATED_AT_SETUP`. They are created on first use, by guarded, audited actions:

- **Claude:** HR enables Claude in AI Models (Guided setup). The store opens at zero, with a lifetime cap equal to the lower of the hosted ceiling and the workspace limit.
- **GPT-OSS:** the first passing Test Connection. The store opens from the key's reported usage.

The service never creates a store by itself at start-up. The cap depends on HR's confirmed workspace limit, or on the key's reported usage.

A store that goes missing after use is not a first start. A passed connection test proves the store existed: Claude's test needs a healthy store, and GPT-OSS's first pass creates it. So when the append-only model-admin audit shows such a test for the provider and the store is gone, the check returns `LEDGER_MISSING_AFTER_USE` and refuses the start. That stops a re-enable from opening a new store at zero, which would restart the hosted lifetime ceiling.

## Health check (deployment preflight)

Before the hosted service starts in a provider mode, it runs this check. A blocking code refuses the start with exit 78, and the code appears in the container log. The problem is therefore found before HR sets up or activates a model.

The check is read-only. It creates, recovers, migrates and resets nothing. Opening a store only lets SQLite roll back a half-written transaction that a crash left behind.

The service container stops on exit 78, so run the operator report as a one-off container of the same image on the same volume. It prints codes, file names and actions only. Run it only while the service container is stopped: after exit 78 it already is; otherwise stop it first, because the service holds a fixed network address. `dca` is the four-file compose set from `egress/README.md`:

```sh
dca run --rm --no-deps assistant python -m assistant_hosting.ledger_health
```

Exit 0 means every named store is usable or absent. Exit 1 means a code is blocking, or the provider mode setting is invalid (`PROVIDER_MODE_INVALID`).

## Blocking codes

| Code | Meaning | Recovery |
|---|---|---|
| `LEDGER_DIR_NOT_WRITABLE` | The service user (uid 10001) cannot create the store | Fix the volume's ownership or permissions, then restart |
| `LEDGER_NOT_WRITABLE` | The store exists but cannot be read and written | Fix ownership or permissions (never the contents), then restart |
| `LEDGER_MISSING_AFTER_USE` | The store is gone, although the audit shows this provider was used | Restore this store's file alone (see below). Never let it be recreated at zero. If no snapshot holds it, the owner decides in a recorded decision. Keep the provider disabled until then; the provider's own limit has kept bounding spend all along |
| `LEDGER_AUDIT_UNREADABLE` | The store is absent and the model-admin audit (`models/model_admin.sqlite3`) cannot be read (empty, damaged or without its tables), so a first start cannot be told from a lost store | Restore the audit file from the last snapshot. If the volume is genuinely new and the file is empty, move it aside and restart |
| `LEDGER_CORRUPT` | SQLite's quick check failed | First re-run the check with the service stopped, because a store held busy for a long time can read as corrupt. If it persists, keep the damaged file aside and restore this store alone |
| `LEDGER_INCONSISTENT` | Sessions and calls do not match | As for `LEDGER_CORRUPT` |
| `LEGACY_STORE` | A format-1 ledger from the earlier design is at the session-store path | It is never migrated or overwritten. With the service stopped, copy it out with `dca run --rm --no-deps assistant python -I scripts/storage/backup_stores.py /data/archive/<date>/manifest.json "/data/budget/sessions/anthropic.sqlite3=>/data/archive/<date>/anthropic.sqlite3"` (it copies with the SQLite backup API, checks the copy and never writes the source; it refuses while a `-journal` file is present). Then move the original into `/data/archive/<date>/legacy/` on the volume. That is a file move, not an edit. Then restart. If the audit shows earlier use of a session store, the next start reports `LEDGER_MISSING_AFTER_USE` |
| `LEDGER_SCHEMA_UNSUPPORTED` | Written by an older or newer release | Deploy the image that wrote it. Never downgrade a store in place |
| `LEDGER_PROFILE_MISMATCH` | Another provider's store is at this path | Correct the ledger path settings |
| `LEDGER_UNREADABLE` | Busy, locked by another process, or damaged | Stop any other assistant using the volume, then restart. If it persists, treat it as `LEDGER_CORRUPT` |

## Restoring one store without losing spend

A restore brings back the store as it was at the snapshot. Any spend recorded after the snapshot is missing from it. So:

1. Keep paid calls off. HR disables the provider, or the service stays stopped.
2. Move the damaged file aside into a new archive folder. Never delete it.
3. Restore only that store's file, and its `-journal` file if there is one, from the latest snapshot. Do not restore the whole volume, which would also rewind the conversations and the audit.
4. Read the provider's own cumulative usage: the Anthropic Console for the hosted workspace, or the OpenRouter key page.
5. Reconcile the store against that figure. The command adopts an undercount, opening the breaker if the difference is above US$0.05; it never accepts usage that falls:

   ```sh
   dca run --rm --no-deps assistant python scripts/budget_ledger.py --anthropic reconcile --provider-usage <USD>
   ```

   Drop `--anthropic` for GPT-OSS.
6. HR resumes in AI Models once the breaker shows a financial stop. A routing or integrity stop needs the owner, after review:

   ```sh
   dca run --rm --no-deps assistant python scripts/budget_ledger.py --anthropic resume-after-review --code <CODE> --confirm-reviewed
   ```

Reconciling restores the lifetime figure only. The day's and the paid session's figures still lack the spend made after the snapshot, and that includes the US$3.00 GPT-OSS day. So keep paid calls off until the next Singapore day (00:00 Asia/Singapore) before resuming, or start a new paid session. Use the provider's cumulative usage for the key or workspace, not a month-to-date figure. The provider's own limit stays the hard backstop throughout: the hosted Anthropic workspace limit, or the OpenRouter key's limit.

## Warnings (never blocking)

| Code | Meaning | Recovery |
|---|---|---|
| `LEDGER_CREATED_AT_SETUP` | Not created yet; a genuine first start | Claude: HR enables Claude. GPT-OSS: Test Connection |
| `BREAKER_OPEN` | Paid calls are stopped | HR resumes a financial stop in AI Models. A routing or integrity stop needs the owner: `scripts/budget_ledger.py [--anthropic] resume-after-review --code CODE --confirm-reviewed`, after review |
| `OPEN_CALLS` | A call was open when the service stopped | Its reservation stays charged. When its lease expires, the ledger closes the call as abandoned and opens the breaker (`abandoned_call`). HR then resumes it in AI Models, keeping the charge |
| `RECONCILE_INTENT_PRESENT` | An HR reconciliation run was interrupted | Resolve it in AI Models. Alternatively the owner closes it, with the service stopped, by running `scripts/budget_ledger.py --anthropic owner-close RUN --reference REF` |

## Interrupted operations and locks

- **Reconcile lock:** an operating-system lock, released automatically when the process that held it exits. It cannot go stale.
- **Interrupted call:** a call cut off by a crash or restart keeps its full reservation as a charge (conservative). See `OPEN_CALLS` above.
- **Interrupted reconciliation run:** it leaves the intent marker above, which the existing guarded flow resolves.
- **Interrupted write:** each ledger write is one SQLite transaction, synchronised to disk. SQLite rolls back a half-finished transaction when the store is next opened.

## Development machines

The same rules apply. A launcher that still names the format-1 ledgers (`budget\anthropic_fyp_ledger.sqlite3`, `budget\ledger.sqlite3`) gets `ledger.healthy` refused as `LEGACY_STORE` at Test Connection. The console now shows that reason. Fix it by pointing the launcher at the session stores, which are the defaults. The old files stay where they are as the archived spend record. On a development machine, Claude's store is created in Guided setup with **Confirm and create the session store**.
