"""Subprocess worker for the ADR-017 multi-process fence test (disposable MongoDB only).

Usage: python adr017_fence_worker.py <uri-env-key> <database> <case_id> <submission_id> <go_at>
It waits until ``go_at`` (epoch seconds), runs the full D1-D5 fence once, and prints one
JSON line: {"result": "WRITTEN"|"REFUSED", "code": ...}. It never prints the URI.
"""

from __future__ import annotations

import json
import os
import sys
import time
from uuid import UUID

from pymongo import MongoClient

from app.domain.target_submission import GoldTierOperationMarker
from app.domain.workflows import ONBOARDING_WORKFLOW_ID
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowStore,
)
from app.persistence.repositories import MongoTargetExecutionRepository
from app.services.dispatch_fence import DispatchFence, FenceHealth
from app.services.errors import DispatchFenceRefusedError


def main() -> int:
    key, database, case_id, submission_id, go_at = sys.argv[1:6]
    client: MongoClient = MongoClient(os.environ[key])
    try:
        store = MongoCaseStore(client, database=database, collection="clm_case_snapshots")
        workflows = MongoWorkflowStore(
            client, database=database, definitions_collection="clm_workflow_definitions",
            runs_collection="clm_workflow_runs",
        )
        fence = DispatchFence(
            ledger=MongoTargetExecutionRepository(store),
            definitions=MongoWorkflowDefinitionRepository(workflows),
            workflow_id=ONBOARDING_WORKFLOW_ID,
            hold=lambda _case_id: None,
            health=lambda: FenceHealth(available=True),
        )
        while time.time() < float(go_at):
            time.sleep(0.001)
        try:
            fence.authorise_first_write(
                case_id=UUID(case_id), submission_id=UUID(submission_id),
                operation=GoldTierOperationMarker.SHELL,
            )
            print(json.dumps({"result": "WRITTEN"}))
        except DispatchFenceRefusedError as exc:
            print(json.dumps({"result": "REFUSED", "code": exc.code}))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
