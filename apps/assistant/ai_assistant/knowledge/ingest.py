"""Load official guidance from markdown files, and optional synthetic past resolutions.

Each guidance file has a small header, then the guidance text:

    ---
    id: guidance.address-mismatch
    title: Registered address differs from ACRA
    blocker_codes: DOCUMENT_SOURCE_CONFLICT
    fields: registered_address
    stages: Document verification
    source: docs/decisions/DECISION_LOG.md#D-030
    illustrative: false
    ---
    Guidance text ...

Lists are comma-separated. ``roles`` and ``teams`` (optional) limit who may see an entry.

Re-ingesting is safe: an unchanged file is skipped, a changed file becomes a new version
that replaces the old one, and guidance whose file was removed is retired. Once guidance has
been changed in the app (HR proposes, a Director approves), its file no longer overrides it.
Guidance loaded here is approved by the recorded decision it cites (``source``), shown as approver
``recorded-decision``; illustrative entries are approved as ``illustrative-seed``.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import Entry, EntryKind, EntryStatus, Visibility
from .service import KnowledgeBase

GUIDANCE_DIR = Path(__file__).parent / "guidance"
SYNTHETIC_RESOLUTIONS = Path(__file__).parent / "seed" / "synthetic_resolutions.json"

REPOSITORY_AUTHOR = "repository"
DECISION_APPROVER = "recorded-decision"
ILLUSTRATIVE_APPROVER = "illustrative-seed"
SYNTHETIC_AUTHOR = "synthetic-seed"
SYNTHETIC_APPROVER = "synthetic-director"

_HEADER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_LIST_KEYS = {"blocker_codes", "fields", "stages", "roles", "teams", "follow_ups"}


class GuidanceFileError(ValueError):
    """A guidance file is not in the expected format."""


@dataclass
class IngestReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    # Guidance changed in the app (by HR, approved by a Director): the file no longer wins.
    kept_app_version: list[str] = field(default_factory=list)


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def parse_guidance(path: Path) -> Entry:
    text = path.read_text(encoding="utf-8")
    match = _HEADER.match(text)
    if match is None:
        raise GuidanceFileError(f"{path.name}: missing the --- header ---")
    header: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise GuidanceFileError(f"{path.name}: cannot read header line {line.strip()!r}")
        header[key.strip()] = value.strip()
    # Notes for editors inside <!-- ... --> are not guidance: never searched or sent.
    body = re.sub(r"<!--.*?-->", "", match.group(2), flags=re.DOTALL).strip()
    for required in ("id", "title", "source"):
        if not header.get(required):
            raise GuidanceFileError(f"{path.name}: header needs '{required}'")
    if not body:
        raise GuidanceFileError(f"{path.name}: no guidance text")
    unknown = set(header) - {"id", "title", "source", "illustrative", "effective_from"} - _LIST_KEYS
    if unknown:
        raise GuidanceFileError(f"{path.name}: unknown header keys {sorted(unknown)}")
    return Entry(
        entry_id=header["id"],
        kind=EntryKind.GUIDANCE,
        title=header["title"],
        body=body,
        blocker_codes=_split(header.get("blocker_codes", "")),
        fields=_split(header.get("fields", "")),
        stages=_split(header.get("stages", "")),
        visibility=Visibility(
            roles=_split(header.get("roles", "")), teams=_split(header.get("teams", ""))
        ),
        effective_from=header.get("effective_from") or None,
        source_ref=header["source"],
        illustrative=header.get("illustrative", "false").lower() == "true",
        author=REPOSITORY_AUTHOR,
    )


def _load(kb: KnowledgeBase, entry: Entry, approver: str, report: IngestReport) -> None:
    current = kb.store.current(entry.entry_id)
    if current is not None and current.author != entry.author:
        report.kept_app_version.append(entry.entry_id)
        return
    if current is not None and current.content_hash() == entry.content_hash():
        report.unchanged.append(entry.entry_id)
        return
    pending = kb.store.add_version(entry, status=EntryStatus.PENDING_REVIEW)
    kb.store.decide(
        pending.entry_id,
        pending.version,
        reviewer=approver,
        approve=True,
        notes=f"loaded from {entry.source_ref or 'seed data'}",
    )
    (report.updated if current is not None else report.added).append(entry.entry_id)


def ingest_guidance(kb: KnowledgeBase, directory: Path = GUIDANCE_DIR) -> IngestReport:
    report = IngestReport()
    entries = [parse_guidance(path) for path in sorted(directory.glob("*.md"))]
    ids = [entry.entry_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise GuidanceFileError("two guidance files use the same id")
    for entry in entries:
        approver = ILLUSTRATIVE_APPROVER if entry.illustrative else DECISION_APPROVER
        _load(kb, entry, approver, report)
    for current in kb.store.entries(status=EntryStatus.APPROVED, kind=EntryKind.GUIDANCE):
        if current.author == REPOSITORY_AUTHOR and current.entry_id not in ids:
            kb.store.retire(current.entry_id, by=REPOSITORY_AUTHOR, notes="guidance file removed")
            report.retired.append(current.entry_id)
    kb.sync()
    return report


def ingest_synthetic_resolutions(
    kb: KnowledgeBase, path: Path = SYNTHETIC_RESOLUTIONS
) -> IngestReport:
    """Made-up past resolutions for the demo (labelled illustrative, no real clients)."""

    report = IngestReport()
    for item in json.loads(path.read_text(encoding="utf-8")):
        entry = Entry(
            entry_id=item["id"],
            kind=EntryKind.RESOLUTION,
            title=item["title"],
            body=item["body"],
            blocker_codes=tuple(item.get("blocker_codes", ())),
            fields=tuple(item.get("fields", ())),
            stages=tuple(item.get("stages", ())),
            follow_ups=tuple(item.get("follow_ups", ())),
            visibility=Visibility(
                roles=tuple(item.get("roles", ())), teams=tuple(item.get("teams", ()))
            ),
            source_ref="synthetic demo data",
            illustrative=True,
            author=SYNTHETIC_AUTHOR,
        )
        _load(kb, entry, SYNTHETIC_APPROVER, report)
    kb.sync()
    return report
