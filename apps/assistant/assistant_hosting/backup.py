"""Quiesced backup and restore of the assistant's data root.

    python -m assistant_hosting.backup create  <data-root> <new-backup-folder>
    python -m assistant_hosting.backup verify  <backup-folder>
    python -m assistant_hosting.backup restore <backup-folder> <empty-data-root>

Run these with the service stopped. ``create`` uses the reviewed ``backup_stores.py`` (SQLite
backup API, integrity check, never overwrites, refuses a store left with a journal or WAL).
``restore`` writes only into an existing empty root, through a staging folder inside it, so an
existing volume is never overwritten. Exit 0 is success, 2 a refusal that left nothing behind,
3 an incomplete restore that needs inspection. It prints paths, sizes and hashes only.
"""

import errno
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

BACKUP_TOOL = Path(__file__).resolve().parents[1] / "scripts" / "storage" / "backup_stores.py"
MANIFEST = "manifest.json"
SKIPPED = frozenset({".assistant.lock"})
EXIT_REFUSED = 2
# A restore that failed and could not be fully undone: the destination needs inspection.
EXIT_INCOMPLETE = 3
STAGING_PREFIX = ".restore-staging-"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def create(root: Path, target: Path) -> int:
    if target.exists():
        print("REFUSED backup folder exists")
        return EXIT_REFUSED
    pairs = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if relative.name in SKIPPED or relative.name.startswith(".ready-"):
            continue
        destination = target / "stores" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        pairs.append(f"{path}=>{destination}")
    if not pairs:
        print("REFUSED nothing to back up")
        return EXIT_REFUSED
    return subprocess.run(  # noqa: S603 (fixed tool, arguments are paths)
        [sys.executable, "-I", str(BACKUP_TOOL), str(target / MANIFEST), *pairs], check=False
    ).returncode


def _sqlite_ok(path: Path) -> bool:
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return False
    return row is not None and row[0] == "ok"


class Refused(Exception):
    """A backup that does not match its manifest exactly; the message is a closed reason."""


_HEX64 = re.compile(r"[0-9a-f]{64}")
_METHODS = frozenset({"copy", "sqlite_backup_api"})


def _parts(destination: str) -> tuple[str, ...]:
    # backup_stores.py records resolved absolute paths: POSIX in the container, Windows in
    # local tests. Read each in its own flavour; never resolve it against this machine.
    flavour = PurePosixPath if destination.startswith("/") else PureWindowsPath
    path = flavour(destination)
    if not path.is_absolute():
        raise Refused("manifest destination is not absolute")
    return path.parts


def _expected(manifest: object, found: set[str]) -> dict[str, tuple[str, int, str]]:
    """{relative path under stores/: (sha256, bytes, method)} from the existing manifest format.

    Every destination was written as ``<backup>/stores/<relative>``, an absolute path that keeps
    naming the old place if the backup folder moves, and any of its folders (or the data root's
    own) may also be called ``stores``. Each ``.../stores/`` cut shared by every entry is tried,
    and the one whose relative paths are exactly the files found under this backup's own
    ``stores/`` is used. At most one cut can match (a longer cut prefixes every path with the
    same extra segment, so two cuts cannot give the same finite set); none is refused."""

    if not isinstance(manifest, list) or not manifest:
        raise Refused("manifest is not a non-empty list")
    rows = []
    for entry in manifest:
        if not isinstance(entry, dict):
            raise Refused("manifest entry is not an object")
        destination = entry.get("destination")
        digest = entry.get("destination_sha256")
        size = entry.get("destination_bytes")
        method = entry.get("method")
        if not isinstance(destination, str) or not destination:
            raise Refused("manifest entry has no destination")
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise Refused("manifest entry has no valid destination_sha256")
        if type(size) is not int or size < 0:
            raise Refused("manifest entry has no valid destination_bytes")
        if method not in _METHODS:
            raise Refused("manifest entry has an unknown method")
        rows.append((_parts(destination), digest, size, method))
    shortest = min(len(parts) for parts, *_ in rows)
    cuts = [
        index + 1
        for index in range(1, shortest - 1)
        if rows[0][0][index] == "stores"
        and all(parts[: index + 1] == rows[0][0][: index + 1] for parts, *_ in rows)
    ]
    if not cuts:
        raise Refused("manifest destinations do not share one stores folder")
    matching = [cut for cut in cuts if {"/".join(parts[cut:]) for parts, *_ in rows} == found]
    if len(matching) != 1:
        raise Refused("manifest and copies differ")
    cut = matching[0]
    expected: dict[str, tuple[str, int, str]] = {}
    for parts, digest, size, method in rows:
        relative = parts[cut:]
        if not relative or any(part in ("", ".", "..") for part in relative):
            raise Refused("manifest destination escapes the stores folder")
        key = "/".join(relative)
        if key.casefold() in {name.casefold() for name in expected}:
            raise Refused("manifest names a file twice")
        expected[key] = (digest, size, method)
    return expected


def _checked(backup: Path) -> dict[str, tuple[str, int, str]]:
    """The manifest's files, after proving that ``stores/`` holds exactly those bytes."""

    try:
        manifest = json.loads((backup / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Refused("manifest unreadable") from error
    stores = backup / "stores"
    if stores.is_symlink() or not stores.is_dir():
        raise Refused("stores folder missing")
    base = stores.resolve()
    found: set[str] = set()
    for path in stores.rglob("*"):
        if path.is_symlink():
            raise Refused("backup contains a link")
        if not path.resolve().is_relative_to(base):
            raise Refused("backup path escapes the stores folder")
        if path.is_file():
            found.add(path.relative_to(stores).as_posix())
        elif not path.is_dir():
            raise Refused("backup contains a special file")
    expected = _expected(manifest, found)
    if found != set(expected):
        raise Refused("manifest and copies differ")
    for relative, (digest, size, method) in expected.items():
        path = stores / relative
        if path.stat().st_size != size or sha256(path) != digest:
            raise Refused("copy does not match its manifest hash")
        if (method == "sqlite_backup_api" or path.suffix == ".sqlite3") and not _sqlite_ok(path):
            raise Refused("damaged store")
    return expected


def verify(backup: Path) -> int:
    """Exactly the files the manifest names, each with its recorded size and SHA-256, and every
    SQLite copy sound. Anything else is refused."""

    try:
        expected = _checked(backup)
    except Refused as refused:
        print(f"REFUSED {refused}")
        return EXIT_REFUSED
    print(f"VERIFIED {len(expected)} files")
    return 0


def _tree_matches(folder: Path, expected: dict[str, tuple[str, int, str]]) -> None:
    """``folder`` holds exactly the expected files with their recorded sizes and SHA-256."""

    found: set[str] = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise Refused("restored tree contains a link")
        if path.is_file():
            found.add(path.relative_to(folder).as_posix())
        elif not path.is_dir():
            raise Refused("restored tree contains a special file")
    if found != set(expected):
        raise Refused("restored files differ from the manifest")
    for relative, (digest, size, _method) in expected.items():
        path = folder / relative
        if path.stat().st_size != size or sha256(path) != digest:
            raise Refused("restored copy does not match its manifest hash")


# Indirection points for fault-injection tests only; production uses the standard calls.
_copy = shutil.copy2
_rename = os.rename


def restore(backup: Path, root: Path) -> int:
    """Restore a verified backup into an existing, empty folder (the recovery volume's mount).

    1. Verify the backup. 2. Refuse a destination that is not an existing, empty, real folder;
    hidden leftovers of an earlier attempt count, and are never removed here. 3. Copy into a new
    private staging folder inside the destination (same filesystem), then check the staged set,
    sizes and SHA-256 independently. 4. Promote each top-level entry with a same-filesystem
    rename, never over an existing entry. 5. Check the destination again, then remove the empty
    staging folder, before reporting success.

    Controlled failures before promotion (including a staging folder that cannot be created)
    leave the destination as it was; a failure during promotion, or an I/O error in the final
    check, moves this attempt's entries back and removes the staging folder. If any of that
    cannot be done, or the destination cannot be confirmed empty, the partial contents stay
    where they are and the result is ``INCOMPLETE``. This is not crash-atomic: a process or
    host crash can leave a staging folder or partially promoted entries, which the next attempt
    refuses until an operator has inspected and cleared the volume."""

    try:
        expected = _checked(backup)
    except Refused as refused:
        print(f"REFUSED {refused}")
        return EXIT_REFUSED
    if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
        print("REFUSED data root must be an existing empty folder (inspect any leftovers first)")
        return EXIT_REFUSED
    stores = backup / "stores"
    try:
        staging = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=root))
    except OSError as error:
        reason = f"the staging folder could not be created ({_cause(error)})"
        if _is_empty(root):
            print(f"REFUSED {reason}; nothing was restored")
            return EXIT_REFUSED
        print(
            f"INCOMPLETE {reason}, and the destination could not be confirmed empty."
            " Inspect it before any retry."
        )
        return EXIT_INCOMPLETE

    def incomplete(reason: str) -> int:
        print(
            f"INCOMPLETE {reason}; the destination may hold partial contents"
            f" (staging folder {staging.name}). Inspect it before any retry."
        )
        return EXIT_INCOMPLETE

    try:
        for relative in sorted(expected):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy(stores / relative, destination)
        _tree_matches(staging, expected)
    except (Refused, OSError) as error:
        reason = str(error) if isinstance(error, Refused) else "staging copy failed"
        shutil.rmtree(staging, ignore_errors=True)
        if staging.exists():
            return incomplete(f"{reason}, and the staging folder could not be removed")
        print(f"REFUSED {reason}; nothing was restored")
        return EXIT_REFUSED

    def roll_back(what: str, moved: list[str]) -> int:
        # Move this attempt's promoted entries back into staging, then remove staging. Exit 2
        # only when the destination is re-checked and found empty; otherwise keep everything.
        stuck = []
        for entry in reversed(moved):
            try:
                _rename(root / entry, staging / entry)
            except OSError:
                stuck.append(entry)
        if stuck:
            return incomplete(f"{what} and {len(stuck)} promoted entries could not be moved back")
        shutil.rmtree(staging, ignore_errors=True)
        if staging.exists():
            return incomplete(f"{what} and the staging folder could not be removed")
        if not _is_empty(root):
            return incomplete(f"{what} and the destination is not empty after rollback")
        print(f"REFUSED {what}; it was rolled back and nothing was restored")
        return EXIT_REFUSED

    moved: list[str] = []
    try:
        for entry in sorted(item.name for item in staging.iterdir()):
            target = root / entry
            if target.exists() or target.is_symlink():
                raise FileExistsError(entry)
            _rename(staging / entry, target)
            moved.append(entry)
    except OSError:
        return roll_back("promotion failed", moved)

    # The final check runs while the (now empty) staging folder still exists, so an I/O error
    # can still be rolled back. A content mismatch is kept for inspection, never rolled back.
    try:
        _tree_matches(root, expected)
    except Refused as refused:
        return incomplete(f"the restored destination failed its final check: {refused}")
    except OSError as error:
        return roll_back(f"the final check could not read the destination ({_cause(error)})", moved)
    try:
        staging.rmdir()
    except OSError:
        return incomplete("restored, but the staging folder could not be removed")
    print(f"RESTORED {len(expected)} files")
    return 0


def _cause(error: OSError) -> str:
    """A closed, content-free description of an OS error: its errno name only."""

    return errno.errorcode.get(error.errno, "OSError") if error.errno else "OSError"


def _is_empty(folder: Path) -> bool:
    """True only when ``folder`` was listed and holds nothing; any listing error counts as no."""

    try:
        return not any(folder.iterdir())
    except OSError:
        return False


def main(arguments: list[str]) -> int:
    if len(arguments) == 3 and arguments[0] == "create":
        return create(Path(arguments[1]), Path(arguments[2]))
    if len(arguments) == 2 and arguments[0] == "verify":
        return verify(Path(arguments[1]))
    if len(arguments) == 3 and arguments[0] == "restore":
        return restore(Path(arguments[1]), Path(arguments[2]))
    print(__doc__)
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
