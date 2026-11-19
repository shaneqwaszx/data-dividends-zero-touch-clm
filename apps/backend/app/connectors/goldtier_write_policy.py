"""D-137: the bounded GoldTier Sandbox write window.

Sandbox writes are on only inside one explicit window. The window is made of the write
switch, an allowlist of operations, an optional exact list of case references, and an
optional end time. Staging startup requires all four (see `Settings`); elsewhere only the
switch matters, as before. D-147's standing scope uses the same policy with no case list and
no end time (Sandbox only, explicit operations; also validated in `Settings`). The policy
holds no secret and makes no network call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

WRITE_OPERATIONS: frozenset[str] = frozenset({"SHELL", "POLICY", "AMEND"})
# Engineering bounds, not sponsor terms: one short, named qualification window.
MAX_WRITE_WINDOW = timedelta(hours=24)
MAX_WRITE_CASE_REFERENCES = 10


class GoldTierWritePolicyError(ValueError):
    """The write window is malformed; the composition root refuses to start."""


@dataclass(frozen=True)
class GoldTierSandboxWritePolicy:
    """Decide whether one GoldTier Sandbox mutation may start.

    - `enabled` False refuses every mutation, whatever the other fields say.
    - `operations` limits which mutations may run. Search and exact-ID readback are never
      mutations and are never limited here.
    - `case_references` empty means no case limit; otherwise only exact matches.
    - `not_after` None means no end time; otherwise writes stop at that instant.
    """

    enabled: bool = False
    operations: frozenset[str] = WRITE_OPERATIONS
    case_references: frozenset[str] = frozenset()
    not_after: datetime | None = None

    def __post_init__(self) -> None:
        if not self.operations <= WRITE_OPERATIONS:
            raise GoldTierWritePolicyError("unknown GoldTier write operation")
        if len(self.case_references) > MAX_WRITE_CASE_REFERENCES or any(
            not reference
            or reference != reference.strip()
            or len(reference) > 96
            or any(ord(character) < 33 or ord(character) == 127 for character in reference)
            for reference in self.case_references
        ):
            raise GoldTierWritePolicyError("invalid GoldTier write case reference")
        if self.not_after is not None and self.not_after.utcoffset() is None:
            raise GoldTierWritePolicyError("the GoldTier write window end needs a time zone")

    def open_at(self, now: datetime) -> bool:
        """True while some mutation may run for some case."""
        return (
            self.enabled
            and bool(self.operations)
            and (self.not_after is None or now < self.not_after)
        )

    def permits(self, *, source_case_id: str, operation: str | None, now: datetime) -> bool:
        """Full check before the ledger marks an attempt. `operation` None checks the case."""
        return self.open_at(now) and self.permits_statically(
            source_case_id=source_case_id, operation=operation
        )

    def permits_statically(self, *, source_case_id: str, operation: str | None) -> bool:
        """The time-free part, repeated at the connector as defence in depth.

        The end time is deliberately not re-checked at the connector: an expiry between the
        pre-ledger check and the request must never turn into a burned, failed operation.
        """
        return (
            self.enabled
            and (operation is None or operation in self.operations)
            and (not self.case_references or source_case_id in self.case_references)
        )
