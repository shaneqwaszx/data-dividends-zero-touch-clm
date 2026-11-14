"""Local release state: per-release records, the known-good pointer, used approvals, the lock.

The state directory lives outside the repository (by default under ``%LOCALAPPDATA%``). It
holds no credential: only manifests, approvals, redacted audit logs and result records.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .core import Clock, StopCondition, canonical_hash, format_utc, read_json, utc_now, write_json

# Result states. Only ACCEPTED moves the known-good pointer.
PLANNED = "PLANNED"
DRY_RUN_OK = "DRY_RUN_OK"
FAILED_NO_CHANGE = "FAILED_NO_CHANGE"
DEPLOYED_AWAITING_ACCEPTANCE = "DEPLOYED_AWAITING_ACCEPTANCE"
ACCEPTED = "ACCEPTED"
ACCEPTANCE_FAILED = "ACCEPTANCE_FAILED"
ROLLED_BACK = "ROLLED_BACK"
FAILED_HELD = "FAILED_HELD"  # changed and not rolled back: stopped for an owner decision
# Written to disk BEFORE the first rollback step. A record found in this state while no
# release command is running means the tool died mid-rollback: the host state is unknown.
ROLLBACK_IN_PROGRESS = "ROLLBACK_IN_PROGRESS"
# A rollback ended without a verified outcome (interrupt, crash, or an unreadable host).
ROLLBACK_INTERRUPTED = "ROLLBACK_INTERRUPTED"
ROLLBACK_UNFINISHED = frozenset({ROLLBACK_IN_PROGRESS, ROLLBACK_INTERRUPTED})
# States in which this release is (or may be) what the host is running, or has been accepted.
# A later run that changes nothing must not replace such a standing record.
LIVE = frozenset(
    {
        DEPLOYED_AWAITING_ACCEPTANCE,
        ACCEPTED,
        ACCEPTANCE_FAILED,
        FAILED_HELD,
        ROLLBACK_IN_PROGRESS,
        ROLLBACK_INTERRUPTED,
    }
)


def default_state_dir() -> Path:
    override = os.environ.get("CLM_RELEASE_STATE_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "DataDividendsCLM" / "release-controller"


class StateStore:
    def __init__(self, root: Path, clock: Clock = utc_now) -> None:
        self.root = root
        self.clock = clock

    def release_dir(self, release_id: str) -> Path:
        if not release_id.startswith("rel-") or "/" in release_id or "\\" in release_id:
            raise StopCondition("RELEASE_ID_INVALID", "not a release id")
        path = self.root / "releases" / release_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    # -- results -------------------------------------------------------------------------

    def write_result(
        self, release_id: str, result: dict[str, Any], *, standing: bool = True
    ) -> Path:
        """Append-only: each result gets its own numbered file; ``result.json`` is the release's
        standing record. With ``standing=False`` the attempt is kept as a numbered file only,
        and the standing record is left as it is."""

        directory = self.release_dir(release_id)
        result = {**result, "recorded_at": format_utc(self.clock())}
        number = len(list(directory.glob("result-*.json"))) + 1
        write_json(directory / f"result-{number:03d}.json", result)
        if standing:
            write_json(directory / "result.json", result)
        return directory / "result.json"

    def journal(self, release_id: str, entry: dict[str, Any], rollback: dict[str, Any]) -> None:
        """Record a rollback step BEFORE it is issued: append it to the release's journal and
        refresh the latest result, both flushed to disk. A process that dies straight after
        therefore leaves a record that already names the step it was about to take."""

        directory = self.release_dir(release_id)
        line = json.dumps({**entry, "at": format_utc(self.clock())}, sort_keys=True)
        for attempt in range(40):  # same transient Windows sharing violation as write_json
            try:
                with (directory / "rollback-journal.jsonl").open(
                    "a", encoding="utf-8", newline="\n"
                ) as handle:
                    handle.write(line + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                break
            except PermissionError:
                if attempt == 39:
                    raise
                time.sleep(0.05)
        latest = directory / "result.json"
        if latest.exists():
            current = read_json(latest)
            current["rollback"] = rollback
            write_json(latest, current)

    def read_result(self, release_id: str) -> dict[str, Any] | None:
        path = self.release_dir(release_id) / "result.json"
        return read_json(path) if path.exists() else None

    # -- known good ----------------------------------------------------------------------

    def known_good(self) -> dict[str, Any] | None:
        path = self.root / "known-good.json"
        if not path.exists():
            return None
        return read_json(path)["current"]  # type: ignore[no-any-return]

    def record_known_good(self, manifest: dict[str, Any]) -> dict[str, Any]:
        path = self.root / "known-good.json"
        document = read_json(path) if path.exists() else {"current": None, "history": []}
        if document["current"] is not None:
            document["history"].append(document["current"])
        document["current"] = {
            "release_id": manifest["release_id"],
            "manifest_sha256": canonical_hash(manifest),
            "accepted_at": format_utc(self.clock()),
            "previous": manifest.get("previous_known_good"),
        }
        write_json(path, document)
        return document["current"]  # type: ignore[no-any-return]

    # -- approvals -----------------------------------------------------------------------

    def consumed_approvals(self) -> frozenset[str]:
        path = self.root / "consumed-approvals.json"
        return frozenset(read_json(path)) if path.exists() else frozenset()

    def consume_approval(self, approval_id: str, action: str) -> None:
        path = self.root / "consumed-approvals.json"
        write_json(path, sorted(self.consumed_approvals() | {f"{approval_id}:{action}"}))

    # -- lock ----------------------------------------------------------------------------

    @contextlib.contextmanager
    def lock(self, release_id: str) -> Iterator[None]:
        """One release operation at a time on this machine. A stale lock is never stolen."""

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / "release.lock"
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            holder = ""
            with contextlib.suppress(OSError, ValueError):
                holder = json.loads(path.read_text(encoding="utf-8")).get("release_id", "")
            raise StopCondition(
                "RELEASE_IN_PROGRESS",
                f"another release operation holds the lock ({holder or 'unknown'}); "
                "if it is stale, remove it with the unlock command after checking the host",
            ) from exc
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "release_id": release_id,
                        "pid": os.getpid(),
                        "at": format_utc(self.clock()),
                    },
                    stream,
                )
            yield
        finally:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()

    def unlock(self) -> bool:
        path = self.root / "release.lock"
        if path.exists():
            path.unlink()
            return True
        return False
