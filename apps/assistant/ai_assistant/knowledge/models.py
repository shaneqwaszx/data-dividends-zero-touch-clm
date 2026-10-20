"""What a knowledge entry is.

Two kinds, kept apart: official guidance (the rulebook) and past resolutions (worked
examples). Every change is a new version of an entry; only the approved, current version of
an entry is ever searched. An entry can also replace a different entry (a newer resolution
that supersedes an older one).
"""

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import StrEnum


class EntryKind(StrEnum):
    GUIDANCE = "guidance"
    RESOLUTION = "resolution"


class EntryStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    # A version that a newer approved version (or another entry) has replaced. Kept for
    # audit, never searched.
    RETIRED = "retired"


@dataclass(frozen=True)
class Visibility:
    """Who may see an entry. Empty means no restriction on that dimension.

    Checked against the role and team the CLM backend reports for the signed-in user, before
    any search runs.
    """

    roles: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()

    def allows(self, role: str | None, team: str | None) -> bool:
        if self.roles and role not in self.roles:
            return False
        return not (self.teams and team not in self.teams)

    def to_json(self) -> str:
        return json.dumps({"roles": list(self.roles), "teams": list(self.teams)})

    @classmethod
    def from_json(cls, text: str | None) -> "Visibility":
        data = json.loads(text) if text else {}
        return cls(roles=tuple(data.get("roles") or ()), teams=tuple(data.get("teams") or ()))


@dataclass(frozen=True)
class Entry:
    entry_id: str
    kind: EntryKind
    title: str
    body: str
    version: int = 0
    status: EntryStatus = EntryStatus.DRAFT
    blocker_codes: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()
    visibility: Visibility = field(default_factory=Visibility)
    # Questions people asked next, so the assistant can answer them up front (resolutions).
    follow_ups: tuple[str, ...] = ()
    effective_from: str | None = None
    # A different entry this one supersedes once approved (the entry's own older versions
    # are always superseded).
    replaces: str | None = None
    author: str = ""
    approver: str | None = None
    approved_at: str | None = None
    # Where a guidance rule comes from, e.g. "docs/decisions/DECISION_LOG.md#D-030".
    source_ref: str | None = None
    # True for demo content that is not a real rule or a real case.
    illustrative: bool = False
    created_at: str | None = None

    @property
    def key(self) -> str:
        """The id of this exact version, used in the vector index."""

        return f"{self.entry_id}@v{self.version}"

    def content_hash(self) -> str:
        """What the entry says (not who reviewed it), to skip unchanged re-ingestion."""

        payload = json.dumps(
            [
                self.kind,
                self.title,
                self.body,
                sorted(self.blocker_codes),
                sorted(self.fields),
                sorted(self.stages),
                self.visibility.to_json(),
                list(self.follow_ups),
                self.effective_from,
                self.replaces,
                self.source_ref,
                self.illustrative,
            ]
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def with_changes(self, **changes: object) -> "Entry":
        return replace(self, **changes)  # type: ignore[arg-type]
