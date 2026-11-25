"""Test-only workflow publication helpers (ADR-017; no production caller).

``publish_governed`` publishes through the real P2-1 path (HR proposes and submits, a
Director approves) and is the helper for any test that later starts an application.

``publish_draft`` is a raw test seed kept ONLY for service-level rebase tests that build a
``WorkflowManagementService`` directly: it writes a memory repository's payload without
provenance, baseline or history, so the P2-1 startup verification would refuse the result.
It must never be used before ``create_app`` or any other startup verification.
``publish_stored_draft_mongo`` writes only a freshly generated, allowlisted disposable test
database (``scripts.mongo_test_safety``) and is kept for its safety-guard test.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from app.domain.workflows import WorkflowStage, WorkflowVersion
from app.persistence.composition import WorkflowPersistence
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

_STORES: dict[int, WorkflowPersistence] = {}


def memory_workflow_store() -> WorkflowPersistence:
    return WorkflowPersistence(
        definitions=InMemoryWorkflowDefinitionRepository(),
        runs=InMemoryWorkflowRunRepository(),
        close=lambda: None,
    )


@contextmanager
def capturing_workflow_store(store: WorkflowPersistence | None = None) -> Iterator[
    WorkflowPersistence
]:
    """Make ``create_app`` use (and expose to the test) a known memory workflow store."""

    active = store or memory_workflow_store()
    with patch("app.main.build_workflow_persistence", return_value=active):
        yield active


def register_app_store(app: Any, store: WorkflowPersistence) -> None:
    _STORES[id(app)] = store


def store_for(client_or_app: Any) -> WorkflowPersistence:
    app = getattr(client_or_app, "app", client_or_app)
    return _STORES[id(app)]


def publish_draft(
    definitions: Any,
    workflow_id: str,
    *,
    actor_id: str = "d-director",
    stages: tuple[WorkflowStage, ...] | None = None,
    now: datetime | None = None,
) -> Any:
    """Raw test seed: append ``stages`` as version ``latest_version + 1``, bypassing
    governance. Service-level rebase tests only; never before startup verification."""

    if not isinstance(definitions, InMemoryWorkflowDefinitionRepository):
        raise TypeError("test publication writes memory repositories only")
    with definitions._lock:  # noqa: SLF001
        current = definitions._items[workflow_id]  # noqa: SLF001
        number = (current.latest_version or 0) + 1
        moment = now or datetime.now(UTC)
        version = WorkflowVersion(
            version=number,
            stages=current.draft_stages if stages is None else stages,
            activated_at=moment,
            activated_by=actor_id,
        )
        published = current.model_copy(
            update={
                "versions": (*current.versions, version),
                "revision": current.revision + 1,
                "updated_at": moment,
                "write_nonce": secrets.token_hex(16),
                "stored_active_version": number,
                "latest_version": number,
            }
        )
        definitions._items[workflow_id] = published  # noqa: SLF001
        return published


def publish_governed(
    store: WorkflowPersistence,
    workflow_id: str,
    stages: tuple[WorkflowStage, ...],
    *,
    now: datetime | None = None,
) -> Any:
    """Publish ``stages`` through the real P2-1 path (memory stores): HR proposes and
    submits, a Director approves with the exact permanent-obligation acknowledgement."""

    from threading import RLock

    from app.api_workflow_governance_models import (
        CreateProposalRequest,
        DecisionRequest,
        SubmitProposalRequest,
    )
    from app.domain.access import AuthenticatedActor, Role, UserProfile
    from app.domain.workflow_governance import DecisionOutcome
    from app.services.workflow_governance import WorkflowGovernanceService
    from app.services.workflow_management import governance_store

    repository = governance_store(store.definitions)
    if repository is None:
        raise TypeError("governed publication needs a governance repository")
    moment = now or datetime.now(UTC)
    service = WorkflowGovernanceService(
        repository=repository, runs=store.runs, lock=RLock(), clock=lambda: moment
    )

    def actor(user_id: str, role: Role) -> Any:
        profile = UserProfile(user_id=user_id, display_name=user_id, role=role, team_id=None)
        return AuthenticatedActor.model_construct(profile=profile)

    hr, director = actor("biz-ops", Role.HR), actor("olivia-koh", Role.DIRECTOR)
    revision = store.definitions.get(workflow_id).revision
    created = service.create_proposal(
        lambda: hr,
        workflow_id,
        CreateProposalRequest(expected_workflow_revision=revision, stages=stages),
    )
    report = service.validate(hr, workflow_id, created.proposal_id, _empty_validation())
    submitted = service.submit_proposal(
        lambda: hr,
        workflow_id,
        created.proposal_id,
        SubmitProposalRequest(
            expected_workflow_revision=store.definitions.get(workflow_id).revision,
            expected_proposal_revision=created.revision,
            content_hash=report.content_hash,
        ),
    )
    return service.decide(
        lambda: director,
        workflow_id,
        created.proposal_id,
        DecisionRequest(
            outcome=DecisionOutcome.APPROVE,
            reason="Approved for this test run.",
            expected_workflow_revision=store.definitions.get(workflow_id).revision,
            expected_proposal_revision=submitted.revision,
            content_hash=report.content_hash,
            acknowledged_permanent_obligations=tuple(
                item.key for item in report.permanent_obligations
            ),
        ),
    )


def _empty_validation() -> Any:
    from app.api_workflow_governance_models import ValidateProposalRequest

    return ValidateProposalRequest()


def publish_stored_draft_mongo(
    mongo_uri: str,
    database: str,
    collection: str,
    workflow_id: str,
    *,
    actor_id: str,
    now: datetime | None = None,
) -> int:
    """Physical-test counterpart of ``publish_draft`` (F-6), for a disposable database only.

    Publishes the stored draft the way governed publication will: one durable
    revision-and-nonce compare-and-set that appends version ``latest_version + 1`` and sets
    ``active_version`` and ``latest_version`` to it (ADR-017 sections 3.1, 3.2, 3.5). It never
    calls the frozen activation route and has no production caller. Returns the new version.
    """

    from pymongo import MongoClient, WriteConcern
    from scripts.mongo_test_safety import require_ephemeral_mongo_database

    from app.domain.workflows import WorkflowDefinition

    # Refuse before any connection: only a name generated by
    # ``generate_ephemeral_mongo_database`` (clm_<phase>_<24 hex>) is writable here, so
    # ``clm_poc``, ``clm_staging`` and every other database are refused.
    require_ephemeral_mongo_database(database)
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        definitions = client[database][collection]
        raw = definitions.find_one({"_id": workflow_id})
        if raw is None:
            raise LookupError(workflow_id)
        current = WorkflowDefinition.model_validate(raw["payload"])
        latest = raw.get("latest_version")
        if type(latest) is not int:
            raise ValueError("definition is not provisioned or backfilled")
        number = latest + 1
        moment = now or datetime.now(UTC)
        version = WorkflowVersion(
            version=number, stages=current.draft_stages, activated_at=moment, activated_by=actor_id
        )
        published = current.model_copy(
            update={
                "versions": (*current.versions, version),
                "revision": current.revision + 1,
                "updated_at": moment,
            }
        )
        nonce = raw.get("write_nonce")
        result = definitions.with_options(
            write_concern=WriteConcern(w="majority", j=True, wtimeout=5_000)
        ).update_one(
            {
                "_id": workflow_id,
                "revision": raw["revision"],
                "write_nonce": nonce if nonce is not None else {"$exists": False},
                "latest_version": latest,
            },
            {
                "$set": {
                    "payload": published.model_dump(mode="json"),
                    "revision": published.revision,
                    "write_nonce": secrets.token_hex(16),
                    "active_version": number,
                    "latest_version": number,
                }
            },
        )
        if result.modified_count != 1:
            raise RuntimeError("test publication lost a compare-and-set")
        return number
    finally:
        client.close()


def bind_test_fence(service: Any) -> Any:
    """Bind a fence for a service built without ``create_app`` (tests only).

    Production binds the application's fence over its workflow store; a service with a
    durable ledger and no fence refuses every first write (fail closed). Tests that drive
    such a service directly bind this one: the service's own (possibly Mongo) ledger, with a
    process-local provisioned onboarding definition (``active_version: 0``, holds nothing).
    """

    from app.services.dispatch_fence import default_memory_fence

    service.bind_dispatch_fence(
        default_memory_fence(service.target_execution_repository, lambda: datetime.now(UTC))
    )
    return service
