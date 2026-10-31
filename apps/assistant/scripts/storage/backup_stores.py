"""B0 cutover: consistent copies of the stopped assistant's stores (stdlib only; run with -I).

Usage: backup_stores.py <manifest.json> <src>=><dst> [<src>=><dst> ...]

- SQLite (*.sqlite3): source opened read-only (mode=ro), copied with the backup API, then
  PRAGMA integrity_check on the copy. Hashes are NOT compared with the source (the backup
  API may rewrite pages); logical equality is checked separately with store_fingerprint.py.
- Other files: shutil.copy2, SHA-256 must equal the source.
All-or-nothing staging: every copy is first written to "<dst>.partial" and verified; only
when all pairs succeed is each renamed to its final name (a rename never replaces an
existing file). On a staging failure this run's own .partial files are removed and no
final destination or manifest is written, so a retry with the same paths is possible.
Publication itself is not atomic across pairs: if a rename fails part-way, the earlier
destinations stay published, the rest stay as .partial and no manifest is written; then
inspect and retry into a fresh folder.
Refuses (exit 2, nothing written) if the manifest or any destination (or its .partial)
already exists, two destinations resolve to the same file, a destination equals a source,
a source is missing, or a source has a -journal/-wal file (service not stopped cleanly).
Never writes to a source. Prints paths, sizes and hashes only.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def partial(dst: Path) -> Path:
    return dst.with_name(dst.name + ".partial")


def refuse(message: str) -> int:
    print(f"REFUSED: {message}")
    return 2


def main() -> int:
    manifest_path = Path(sys.argv[1])
    raw = [arg.split("=>", 1) for arg in sys.argv[2:]]
    if not raw or any(len(p) != 2 for p in raw):
        return refuse("bad pair syntax")
    if manifest_path.exists():
        return refuse(f"manifest exists {manifest_path}")
    pairs = [(Path(s).resolve(), Path(d).resolve()) for s, d in raw]
    sources = {src for src, _ in pairs}
    seen = set()
    for src, dst in pairs:
        key = os.path.normcase(str(dst))
        if key in seen:
            return refuse(f"duplicate destination {dst}")
        seen.add(key)
        if dst in sources:
            return refuse(f"destination is a source {dst}")
        if not src.is_file():
            return refuse(f"source missing {src}")
        if dst.exists() or partial(dst).exists():
            return refuse(f"destination exists {dst}")
        for suffix in ("-journal", "-wal"):
            if Path(str(src) + suffix).exists():
                return refuse(f"{src}{suffix} present (stop the service cleanly first)")

    temps = []  # this run's own .partial files
    ready = []  # (tmp, dst, entry) verified, not yet published
    try:
        for src, dst in pairs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = partial(dst)
            entry = {
                "source": str(src),
                "destination": str(dst),
                "source_bytes": src.stat().st_size,
            }
            if src.suffix == ".sqlite3":
                source = sqlite3.connect(f"{src.as_uri()}?mode=ro", uri=True, timeout=5)
                with open(tmp, "xb"):  # exclusive create: never replaces a file
                    pass
                temps.append(tmp)
                target = sqlite3.connect(str(tmp))
                try:
                    with target:
                        source.backup(target)
                    check = target.execute("PRAGMA integrity_check").fetchone()[0]
                    mode = target.execute("PRAGMA journal_mode").fetchone()[0]
                finally:
                    target.close()
                    source.close()
                entry.update(method="sqlite_backup_api", integrity=check, journal_mode=mode)
                if check != "ok":
                    raise RuntimeError(f"integrity {dst}: {check}")
            else:
                with open(tmp, "xb"):
                    pass
                temps.append(tmp)
                shutil.copyfile(src, tmp)
                shutil.copystat(src, tmp)
                entry.update(method="copy", source_sha256=sha256(src))
            for suffix in ("-journal", "-wal"):
                if Path(str(tmp) + suffix).exists():
                    raise RuntimeError(f"leftover {tmp}{suffix}")
            entry.update(destination_bytes=tmp.stat().st_size, destination_sha256=sha256(tmp))
            if entry["method"] == "copy" and entry["source_sha256"] != entry["destination_sha256"]:
                raise RuntimeError(f"hash {dst}")
            ready.append((tmp, dst, entry))
    except Exception as exc:  # remove only this run's own .partial files
        for tmp in temps:
            tmp.unlink(missing_ok=True)
        print(f"FAILED (nothing published): {type(exc).__name__}: {exc}")
        return 1

    entries = []
    for tmp, dst, entry in ready:
        if dst.exists():  # re-check at the moment of publication
            print(f"FAILED: destination appeared during the run {dst} (staged copy left at {tmp})")
            return 1
        tmp.rename(dst)  # Windows: raises if dst exists; never overwrites
        entries.append(entry)
        print(
            f"ok {entry['method']:<18} {dst} {entry['destination_bytes']} "
            f"{entry['destination_sha256'][:16]}"
        )
    with open(manifest_path, "x", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2)
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
