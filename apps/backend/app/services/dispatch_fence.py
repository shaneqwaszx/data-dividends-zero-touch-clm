"""ADR-017 section 3.3 send dispatch fence: the only path to a first GoldTier write.

D1  read the authoritative ``active_version`` V and evaluate the send hold (advisory)
D2  claim the ledger entry: TENTATIVE {token, V, server lease}
D3  linearisation point on the workflow definition (``$inc dispatch_authorisation_seq``)
D4  TENTATIVE -> AUTHORISED {token, V, d3_at, new lease}
D5  record the first write attempt marker with V and a receipt, in the same write
D6  the provider call, made by the caller only after D5 returned its own post-image

Every step must succeed before the next. Any ambiguous outcome stops before D6, and any
unavailable guarantee (unsupported topology, missing or unverified definition) refuses.
There are no confirming writes (the ADR-017 CT-16 fallback mode).
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierOperationMarker,
)
from app.persistence.errors import PersistenceOutcomeAmbiguousError
from app.services.errors import DispatchFenceRefusedError

LOGGER = logging.getLogger(__name__)

HOLD_INCOMPLETE = "WORKFLOW_STAGE_INCOMPLETE"
CHECK_UNAVAILABLE = "WORKFLOW_STAGE_CHECK_UNAVAILABLE"
RECONFIRMATION_REQUIRED = "WORKFLOW_DISPATCH_RECONFIRMATION_REQUIRED"
MAX_D3_ATTEMPTS = 3


class FenceLedgerPort(Protocol):
    def fence_claim(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None: ...

    def fence_authorise(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None: ...

    def fence_first_write(
        self, submission_id: UUID, *, token: str, operation: GoldTierOperationMarker
    ) -> GoldTierExecutionLedgerEntry | None: ...


class FenceDefinitionPort(Protocol):
    def dispatch_active_version(self, workflow_id: str) -> int | None:
        """The stored top-level ``active_version``; None when missing or unbackfilled."""

    def authorise_dispatch(self, workflow_id: str, version: int) -> bool:
        """D3. True only when durably acknowledged and one document was modified."""


@dataclass(frozen=True)
class FenceHealth:
    available: bool
    reason: str | None = None


class DispatchFence:
    def __init__(
        self,
        *,
        ledger: FenceLedgerPort,
        definitions: FenceDefinitionPort,
        workflow_id: str,
        hold: Callable[[UUID], str | None],
        health: Callable[[], FenceHealth],
        on_hold: Callable[[UUID, str], None] | None = None,
    ) -> None:
        self._ledger = ledger
        self._definitions = definitions
        self._workflow_id = workflow_id
        self._hold = hold
        self._health = health
        self._on_hold = on_hold

    def authorise_first_write(
        self,
        *,
        case_id: UUID,
        submission_id: UUID,
        operation: GoldTierOperationMarker,
    ) -> GoldTierExecutionLedgerEntry:
        """Run D1-D5; return the entry carrying the durable first write attempt marker."""

        health = self._health()
        if not health.available:
            LOGGER.warning("dispatch fence unavailable", extra={"reason": health.reason})
            raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)
        token = secrets.token_hex(16)
        try:
            for _ in range(MAX_D3_ATTEMPTS):
                version = self._definitions.dispatch_active_version(self._workflow_id)  # D1
                if version is None:
                    raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)
                hold = self._hold(case_id)
                if hold is not None:
                    # RD-3: only a newly applicable requirement supersedes a confirmation;
                    # an unreadable check refuses without touching it (QG R0 P3-1).
                    if self._on_hold is not None and hold == HOLD_INCOMPLETE:
                        self._on_hold(case_id, hold)
                    raise DispatchFenceRefusedError(hold)
                claimed = self._ledger.fence_claim(  # D2
                    submission_id, token=token, version=version
                )
                if claimed is None:
                    raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)
                if not self._definitions.authorise_dispatch(self._workflow_id, version):  # D3
                    continue
                authorised = self._ledger.fence_authorise(  # D4
                    submission_id, token=token, version=version
                )
                if authorised is None:
                    raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)
                written = self._ledger.fence_first_write(  # D5
                    submission_id, token=token, operation=operation
                )
                if written is None:
                    raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)
                return written
        except PersistenceOutcomeAmbiguousError:
            raise DispatchFenceRefusedError(CHECK_UNAVAILABLE) from None
        raise DispatchFenceRefusedError(CHECK_UNAVAILABLE)


def default_memory_fence(
    ledger: FenceLedgerPort, clock: Callable[[], datetime]
) -> DispatchFence:
    """A process-local fence for a service built without the application (memory mode).

    It has its own provisioned onboarding definition (``active_version: 0``: no active
    version holds nothing, D-136 E2) and no send hold. ``create_app`` always binds the real
    fence over the application's workflow store instead.
    """

    from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition
    from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository

    definitions = InMemoryWorkflowDefinitionRepository()
    now = clock()
    definitions.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID, name="Corporate onboarding",
            use_case="Corporate onboarding", country="Singapore", created_at=now,
            updated_at=now,
        )
    )
    return DispatchFence(
        ledger=ledger,
        definitions=definitions,
        workflow_id=ONBOARDING_WORKFLOW_ID,
        hold=lambda _case_id: None,
        health=lambda: FenceHealth(available=True),
    )
