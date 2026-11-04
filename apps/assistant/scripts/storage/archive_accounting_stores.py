"""D-118 amendment P3: archive the earlier design's accounting stores (owner only; non-destructive).

Usage (from apps/assistant, assistant service stopped):
    python -I scripts/storage/archive_accounting_stores.py <data-root> <new archive folder>

Finds the earlier-design ledgers under the data root (budget/ledger.sqlite3,
budget/anthropic_fyp_ledger.sqlite3, budget/anthropic_ledger.sqlite3) and the D-110 reconcile
intent markers beside them, and copies them into the new archive folder with the reviewed
backup_stores.py (SQLite backup API, integrity check, never overwrites, never writes a source).
Every table's rows in each copy are then compared with its source, read-only. A manifest
(SHA-256 of each copy) is written by backup_stores.py. Nothing is moved, changed or deleted: the
simplified runtime uses new session stores (budget/sessions/...), so these files are history.
Refuses (exit 2) when the archive folder exists or no legacy store is found. Prints paths only.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

LEGACY = (
    "budget/ledger.sqlite3",
    "budget/anthropic_fyp_ledger.sqlite3",
    "budget/anthropic_ledger.sqlite3",
)
MARKER_SUFFIX = ".reconcile.intent"


def rows(path: Path) -> dict[str, list[tuple[object, ...]]]:
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                " ORDER BY name"
            )
        ]
        return {
            table: connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            for table in tables
        }
    finally:
        connection.close()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: archive_accounting_stores.py <data-root> <new archive folder>")
        return 2
    root, archive = Path(argv[0]).resolve(), Path(argv[1]).resolve()
    if not root.is_dir():
        print(f"REFUSED: no data root {root}")
        return 2
    if archive.exists():
        print(f"REFUSED: the archive folder exists {archive}")
        return 2
    stores = [root / name for name in LEGACY if (root / name).is_file()]
    if not stores:
        print("REFUSED: no earlier-design accounting store under the data root")
        return 2
    pairs = []
    for store in stores:
        target = archive / store.relative_to(root)
        pairs.append(f"{store}=>{target}")
        marker = store.with_name(store.name + MARKER_SUFFIX)
        if marker.is_file():
            pairs.append(f"{marker}=>{target.with_name(target.name + MARKER_SUFFIX)}")
    backup = Path(__file__).with_name("backup_stores.py")
    result = subprocess.run(
        [sys.executable, "-I", str(backup), str(archive / "manifest.json"), *pairs], check=False
    )
    if result.returncode != 0:
        print("REFUSED: the copy did not complete; the sources are unchanged")
        return 2
    for store in stores:
        copy = archive / store.relative_to(root)
        if rows(copy) != rows(store):
            print(f"FAIL: the copy of {store.name} differs from its source")
            return 1
        print(f"archived {store} -> {copy} (every row equal)")
    print("sources unchanged; point the launcher at budget/sessions/ to start the POC runtime")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
