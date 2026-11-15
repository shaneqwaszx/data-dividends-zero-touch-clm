"""Spending-store health for the hosted provider modes (D-138 R4, owner request 2026-11-15).

Before the service starts in a provider mode, each named provider's D-118 session store is
checked. The check is read-only: nothing is created, recovered, migrated, reset or deleted.

    absent        normal on a genuine first start: the store is created on first use, by the
                  existing guarded actions (Claude's when HR enables Claude, GPT-OSS's at the first
                  passing Test Connection). The parent folder must be writable. Absent AFTER use
                  (the audit shows a passed connection test for that provider, which needs a
                  healthy store) is LEDGER_MISSING_AFTER_USE: a vanished store is never
                  silently replaced by a new one opening at zero
    present       it must be readable and writable, pass SQLite's quick check, be a format-2
                  session store (a format-1 ledger is LEGACY_STORE) and belong to this provider

A blocking code refuses the start (exit 78, through profile.refusals), so a broken store is found
at deployment, before HR tries to set up or activate a model. A warning never blocks: an open
breaker, an open call or an HR reconciliation marker each has its own guarded recovery.

``python -m assistant_hosting.ledger_health`` prints the same report for an operator: codes,
file names and the next action only. It never shows an amount, a key or case data. The
container stops on exit 78, so run it as a one-off container of the same image on the same volume
(apps/assistant/deploy/LEDGER_RECOVERY.md).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ai_assistant import anthropic_runtime
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID as ANTHROPIC_PROFILE_ID
from ai_assistant.anthropic_profiles import PROFILE_IDS as CLAUDE_PROFILE_IDS
from ai_assistant.budget import BudgetLedger, LedgerError
from ai_assistant.config import AiAssistantSettings
from ai_assistant.model_factory import ledger_path
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID

from . import provider

# Blocking codes and the next action for each. The recovery never edits a database file.
ACTIONS: dict[str, str] = {
    "LEDGER_DIR_NOT_WRITABLE": (
        "The service user (uid 10001) cannot create the store. Fix the data volume's"
        " ownership or permissions, then restart."
    ),
    "LEDGER_MISSING_AFTER_USE": (
        "The store is gone although this provider was used (the audit shows a passed connection"
        " test). It is never recreated at zero. Restore this store's file alone from the last"
        " snapshot, then reconcile it against the provider's usage before paid calls resume."
    ),
    "LEDGER_AUDIT_UNREADABLE": (
        "The store is absent and the model-admin audit (models/model_admin.sqlite3) cannot be"
        " read, so a first start cannot be told from a lost store. Restore the audit file from"
        " the last snapshot, or, if the volume is genuinely new, move the empty audit file aside,"
        " then restart."
    ),
    "LEDGER_NOT_WRITABLE": (
        "The store exists but the service user cannot read and write it. Fix its ownership or"
        " permissions (never its contents), then restart."
    ),
    "LEDGER_CORRUPT": (
        "SQLite's quick check failed. Re-run the check with the service stopped (a busy store"
        " can read as corrupt). If it persists, keep the file, restore this store alone from the"
        " last snapshot and reconcile it against the provider's usage before paid calls resume."
    ),
    "LEGACY_STORE": (
        "A format-1 ledger from the earlier design is at the session-store path. It is never"
        " migrated or overwritten. Copy it out with scripts/storage/backup_stores.py, move the"
        " file into the archive folder, then restart: the session store is created on first use."
    ),
    "LEDGER_SCHEMA_UNSUPPORTED": (
        "The store's tables are not the session-store format this image supports (an older"
        " or newer release). Deploy the image that wrote it, or restore the volume from the"
        " snapshot taken with that image."
    ),
    "LEDGER_INCONSISTENT": (
        "The store's sessions and calls do not match. As LEDGER_CORRUPT: keep the file, restore"
        " this store alone and reconcile it against the provider's usage."
    ),
    "LEDGER_PROFILE_MISMATCH": (
        "The store belongs to another provider. Check the ledger path settings; never copy"
        " one provider's store over another's."
    ),
    "LEDGER_UNREADABLE": (
        "The store could not be read (busy, locked by another process or damaged). Stop any"
        " other assistant using this volume, then restart. If it persists, treat it as"
        " LEDGER_CORRUPT."
    ),
}
# Warnings: shown, never blocking; each has an existing guarded recovery.
WARNINGS: dict[str, str] = {
    "LEDGER_CREATED_AT_SETUP": (
        "Not created yet. Normal on a first start. Claude: HR enables Claude in AI Models."
        " GPT-OSS: the first passing Test Connection."
    ),
    "BREAKER_OPEN": (
        "Paid calls are stopped. HR resumes a financial stop in AI Models. A routing or"
        " integrity stop needs the owner, after review: scripts/budget_ledger.py [--anthropic]"
        " resume-after-review --code CODE --confirm-reviewed."
    ),
    "OPEN_CALLS": (
        "A call was open when the service stopped. Its reservation stays charged. When its lease"
        " expires the ledger closes it as abandoned and opens the breaker (abandoned_call);"
        " HR then resumes it in AI Models, keeping the charge."
    ),
    "RECONCILE_INTENT_PRESENT": (
        "An HR reconciliation run was interrupted. Resolve it in AI Models (Resolve). The"
        " owner can close it: scripts/budget_ledger.py --anthropic owner-close RUN --reference REF."
    ),
}


@dataclass(frozen=True)
class StoreHealth:
    provider: str
    path: Path
    state: str  # "absent" or "present"
    blocking: str | None
    warnings: tuple[str, ...]


def stores(settings: AiAssistantSettings) -> dict[str, tuple[Path, str]]:
    """Each provider's configured session store and the profile it must hold."""

    return {
        provider.ANTHROPIC: (anthropic_runtime.ledger_file(settings), ANTHROPIC_PROFILE_ID),
        provider.OPENROUTER: (ledger_path(settings), OPENROUTER_PROFILE_ID),
    }


def _writable_dir(folder: Path) -> bool:
    # The nearest existing folder decides (initialise creates the rest).
    probe = folder
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe.is_dir() and os.access(probe, os.W_OK | os.X_OK)


def used_before(settings: AiAssistantSettings, name: str) -> bool | None:
    """Whether the append-only model-admin audit shows a passed connection test for this
    provider. A passed test needs a healthy store (Claude's ledger.healthy; GPT-OSS's first pass
    creates it), so the store existed. Read-only; no audit store means a genuine first start,
    and an audit that cannot be read is None (it proves neither)."""

    audit = Path(settings.model_admin_db_path)
    if not audit.exists():
        return False
    anthropic = name == provider.ANTHROPIC
    profiles = sorted(CLAUDE_PROFILE_IDS) if anthropic else [OPENROUTER_PROFILE_ID]
    marks = ", ".join("?" for _ in profiles)
    try:
        with sqlite3.connect(f"file:{audit.as_posix()}?mode=ro", uri=True, timeout=10) as db:
            row = db.execute(
                "SELECT 1 FROM events WHERE action = 'CONNECTION_TEST' AND outcome = 'passed'"
                f" AND profile_id IN ({marks}) LIMIT 1",
                profiles,
            ).fetchone()
    except sqlite3.Error:
        # Unreadable, empty or without its tables: it proves neither a first start nor use.
        return None
    return row is not None


def check(
    name: str, path: Path, profile_id: str, *, settings: AiAssistantSettings | None = None
) -> StoreHealth:
    """One store's health, read-only."""

    if not path.exists():
        used = used_before(settings, name) if settings is not None else False
        if used is None:
            return StoreHealth(name, path, "absent", "LEDGER_AUDIT_UNREADABLE", ())
        if used:
            return StoreHealth(name, path, "absent", "LEDGER_MISSING_AFTER_USE", ())
        blocking = None if _writable_dir(path.parent) else "LEDGER_DIR_NOT_WRITABLE"
        return StoreHealth(name, path, "absent", blocking, ("LEDGER_CREATED_AT_SETUP",))
    if not os.access(path, os.R_OK | os.W_OK) or not _writable_dir(path.parent):
        return StoreHealth(name, path, "present", "LEDGER_NOT_WRITABLE", ())
    try:
        # The ledger's own read-only verification (quick check, format, fence, consistency),
        # without recovering it, as anthropic_runtime.ledger_profile does: nothing changes here.
        probe = BudgetLedger(path, busy_timeout=10.0)
        probe.verify()
        status = probe.status()
    except LedgerError as error:
        code = error.code if error.code in ACTIONS else "LEDGER_UNREADABLE"
        return StoreHealth(name, path, "present", code, ())
    except sqlite3.DatabaseError:
        return StoreHealth(name, path, "present", "LEDGER_UNREADABLE", ())
    if status.profile_id != profile_id:
        return StoreHealth(name, path, "present", "LEDGER_PROFILE_MISMATCH", ())
    warnings = []
    if status.breaker_open:
        warnings.append("BREAKER_OPEN")
    if status.open_calls:
        warnings.append("OPEN_CALLS")
    if path.with_name(path.name + ".reconcile.intent").exists():
        warnings.append("RECONCILE_INTENT_PRESENT")
    return StoreHealth(name, path, "present", None, tuple(warnings))


def report(
    settings: AiAssistantSettings, environ: Mapping[str, str] | None = None
) -> list[StoreHealth]:
    """The named provider modes' stores (none when the service is model-free)."""

    names = provider.modes(environ)
    if not names:
        return []
    configured = stores(settings)
    return [check(name, *configured[name], settings=settings) for name in names]


def config_codes(
    settings: AiAssistantSettings, environ: Mapping[str, str] | None = None
) -> list[str]:
    """The blocking codes, for profile.refusals (empty: every named store may be used)."""

    return sorted({item.blocking for item in report(settings, environ) if item.blocking})


def main() -> int:
    settings = AiAssistantSettings()
    if provider.modes() is None:
        print("BLOCKING PROVIDER_MODE_INVALID: the provider mode setting is not valid")
        return 1
    items = report(settings)
    if not items:
        print("no provider mode is named: no spending store is used")
        return 0
    for item in items:
        print(f"{item.provider}: {item.path.name} [{item.state}]")
        if item.blocking:
            print(f"  BLOCKING {item.blocking}: {ACTIONS[item.blocking]}")
        for code in item.warnings:
            print(f"  note {code}: {WARNINGS[code]}")
    return 1 if any(item.blocking for item in items) else 0


if __name__ == "__main__":
    sys.exit(main())
