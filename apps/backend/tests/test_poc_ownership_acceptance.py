"""Opt-in POC ownership acceptance in the hybrid Marketplace Mock lane (D-082, D-085).

The acceptance is recorded beside an unchanged REVIEW_REQUIRED analysis and grants
readiness only while the current runtime enables the policy. Every journey is offline:
synthetic Marketplace Mock protocol transport, in-memory persistence and Mock GoldTier.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS, OfflineFiveLayerProtocolTransport
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_am18_ownership_checkpoint import current_payload, prepare_case
from test_hybrid_five_layer_overlay import DISCOVERY, case_policy
from test_official_shareholder_evidence import (
    GARDEN,
    LIVE_SHAPE,
    POC_REFUSAL,
    SIM,
    gate_state,
    manual_decision,
    shareholders,
    snapshot_of,
)
from test_slice_b_registry_demo import FIXTURES, confirm, start
from test_zero_touch_exception_remediation import successful

from app.composition import (
    build_acra_connector,
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
)
from app.config import Settings
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_SCENARIO_ID,
    GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
    POC_EQUAL_UNITS_PROVIDER,
    HybridOverlayScenario,
    HybridOwnershipOverlayCatalogue,
    PocAcceptanceDeclaration,
)
from app.connectors.registry_ownership import _evidence_id
from app.domain.ownership import (
    OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
    OwnershipDocumentBinding,
    OwnershipDocumentDiscrepancy,
    OwnershipEnvironment,
    OwnershipIssueCode,
    OwnershipPocAcceptance,
    OwnershipProvenance,
    OwnershipThresholdResult,
    PocAssumption,
)
from app.domain.registry_legal_form import RegistryLegalForm
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.models import (
    DurableCaseSnapshot,
    DurableCaseSnapshotV14,
    reject_scenario_poc_legacy_fields,
    reject_share_class_legacy_fields,
)
from app.persistence.mongo_case_store import _SUPPORTED_SCHEMA_VERSIONS
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.ownership_analysis import (
    OwnershipAnalysisService,
    _officer_role_evidence_id,
    eligible_poc_acceptance,
    poc_acceptance_current,
)
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository

ACCEPT = "accept_eligible_poc"
POC_CODES = [
    "OWNERSHIP_DENOMINATOR_REQUIRED",
    "SYNTHETIC_OWNERSHIP_EVIDENCE",
    "UBO_REVIEW_REQUIRED",
]
GARDEN_ASSUMPTIONS = [
    "DESCRIPTIVE_OFFICER_ROLES",
    "EQUAL_UNIT_DENOMINATOR",
    "SIMULATED_RELATIONSHIPS",
]
# The fixture's four Garden officer roles mirror the observed Mock shape:
# SYNTHETIC-ROLE-1..3 current and SYNTHETIC-ROLE-4 ceased.


def role_id(index: int) -> str:
    return _evidence_id(f"SYNTHETIC-ROLE-{index}", "ROLE")


def garden_scenario() -> HybridOverlayScenario:
    """The trusted catalogue's own Garden declaration."""

    scenario = HybridOwnershipOverlayCatalogue().scenario(GARDEN_DIRECT_OVERLAY_SCENARIO_ID)
    assert scenario is not None and scenario.poc_acceptance is not None
    return scenario


def lane(acceptance: str = ACCEPT, **update: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "app_env": "test",
        "clm_persistence_mode": "memory",
        "registry_cache_mode": "auto",
        "acra_connector_mode": "api_marketplace_mock",
        "acra_marketplace_ownership_overlay": "hybrid_direct_overlay",
        "acra_marketplace_poc_ownership_acceptance": acceptance,
        "goldtier_connector_mode": "mock",
        "idp_connector_mode": "local_pdf_text",
        "demo_controls_enabled": False,
        "acra_api_marketplace_mock_client_id": SecretStr("synthetic-offline-client"),
        "acra_api_marketplace_mock_secret_key": SecretStr("synthetic-offline-key"),
    }
    values.update(update)
    return Settings(**values)


def garden_transport(ceased: tuple[int, ...] = (4,)) -> OfflineFiveLayerProtocolTransport:
    transport = OfflineFiveLayerProtocolTransport()
    transport.shareholders[SIM] = shareholders(LIVE_SHAPE)
    profile: Any = transport.profiles[GARDEN]
    officers = profile["entities"][0]["entityOfficersRecord"]["officerAppointmentDetails"]
    for index in ceased:
        officers[index - 1]["withdrawalDate"] = "2019-06-30"
    return transport


@contextmanager
def runtime(
    settings: Settings, bundle: Any, transport: OfflineFiveLayerProtocolTransport
) -> Iterator[TestClient]:
    """One composition over durable state shared across restarts (the bundle)."""

    marketplace = settings.acra_connector_mode == "api_marketplace_mock"
    connector = (
        build_acra_connector(settings, transport=transport, marketplace_token_transport=transport)
        if marketplace
        else None
    )
    with patch("app.main.build_persistence_bundle", return_value=bundle):
        yield TestClient(
            create_app(settings, acra_connector=connector, e2e_acra_protocol_fixture=marketplace)
        )


def accepted_runtime() -> tuple[Any, TestClient, str, OwnershipAnalysisService]:
    """An accepted Garden case plus its composed ownership owner (runtime authority)."""

    settings = lane()
    bundle = build_persistence_bundle(settings)
    composed: list[OwnershipAnalysisService] = []

    def capture(*args: Any, **kwargs: Any) -> OwnershipAnalysisService:
        composed.append(build_ownership_analysis_service(*args, **kwargs))
        return composed[-1]

    with (
        patch("app.main.build_ownership_analysis_service", side_effect=capture),
        runtime(settings, bundle, garden_transport()) as client,
    ):
        case_id = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")["case"][
            "case_id"
        ]
    [service] = composed
    return bundle, client, case_id, service


def resume(client: TestClient, case_id: str) -> dict:
    current = summary_of(client, case_id)
    return successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/resume",
            headers={
                "X-Automation-Id": current["automation_id"],
                "X-Automation-Version": str(current["version"]),
                "X-Clm-Version": str(current["clm"]["version"]),
                "X-Case-Event-Count": str(len(current["case"]["events"])),
            },
        )
    )


def exception_types(summary: dict) -> list[str]:
    return sorted(item["exception_type"] for item in summary["active_exceptions"])


def ownership_of(client: TestClient, case_id: str) -> dict:
    return successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))


def summary_of(client: TestClient, case_id: str) -> dict:
    return successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))


def stable(ownership: dict) -> dict:
    """Every calculated and evidential value, without per-run identifiers or times."""

    names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
    return {
        "state": ownership["state"],
        "edges": sorted(
            (
                names[edge["parent_party_id"]],
                names[edge["child_party_id"]],
                edge["ownership_percent"],
                edge["provenance"]["provider"],
            )
            for edge in ownership["relationships"]
        ),
        "candidates": sorted(
            (
                item["party"]["display_name"],
                item["direct_ownership_percent"],
                item["indirect_ownership_percent"],
                item["aggregated_ownership_percent"],
                item["threshold_result"],
                item["classification"],
                item["synthetic_basis_threshold_result"],
                tuple(path["effective_ownership_percent"] for path in item["paths"]),
            )
            for item in ownership["candidates"]
        ),
        "issues": [(item["code"], item["message"]) for item in ownership["issues"]],
        "evidence": sorted(
            (
                item["kind"],
                item["raw_value"],
                item["entity_identifier"],
                item["source_operation"],
                item["provider"],
            )
            for item in ownership["evidence"]
        ),
        "discovery": [
            (
                item["display_name"],
                item["outcome"],
                item["reason_code"],
                item["official_shareholder_lookup"],
                [
                    (row["display_name"], row["share_allotted"], row["share_type"])
                    for row in item["official_shareholders"]
                ],
            )
            for item in ownership["discovery"]["records"]
        ],
    }


def accepted_case(
    acceptance: str = ACCEPT,
) -> tuple[Any, OfflineFiveLayerProtocolTransport, TestClient, str]:
    bundle = build_persistence_bundle(lane(acceptance))
    transport = garden_transport()
    with runtime(lane(acceptance), bundle, transport) as client:
        current = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
        return bundle, transport, client, current["case"]["case_id"]


def service_lane(
    acceptance: str = ACCEPT,
    transport: OfflineFiveLayerProtocolTransport | None = None,
    **update: Any,
) -> tuple[Any, OwnershipAnalysisService]:
    settings = lane(acceptance, **update)
    transport = transport or garden_transport()
    onboarding = build_onboarding_service(
        settings=settings,
        acra_transport=transport,
        acra_marketplace_token_transport=transport,
        policy_snapshot_provider=lambda: case_policy(DISCOVERY),
    )
    return onboarding, build_ownership_analysis_service(onboarding, settings)


def accepted_record() -> tuple[Any, OwnershipAnalysisService, OwnershipAnalysisRecord]:
    onboarding, ownership = service_lane()
    case = onboarding.create_staged_case(GARDEN)
    ownership.load(case_id=case.case_id)
    record = ownership.analyze(case_id=case.case_id)
    assert record.poc_acceptance is not None
    return onboarding, ownership, record


# --- Policy authority: opt-in, default off, hybrid Mock lane only -------------------


def test_the_policy_is_opt_in_default_off_and_limited_to_the_hybrid_mock_lane() -> None:
    assert Settings(_env_file=None).acra_marketplace_poc_ownership_acceptance == "disabled"
    assert lane("disabled").acra_marketplace_poc_ownership_acceptance == "disabled"
    for update in (
        {"acra_marketplace_ownership_overlay": "garden_legacy_supplement"},
        {
            "acra_connector_mode": "mock",
            "acra_marketplace_ownership_overlay": "garden_legacy_supplement",
        },
    ):
        with pytest.raises(ValidationError, match="POC ownership acceptance requires"):
            lane(**update)
    with pytest.raises(ValidationError):
        lane("accept_everything")
    # The service refuses the policy without the hybrid overlay owner, whatever settings say.
    with pytest.raises(ValueError, match="requires the hybrid overlay lane"):
        OwnershipAnalysisService(
            cases=object(),  # type: ignore[arg-type]
            provider=object(),  # type: ignore[arg-type]
            repository=InMemoryOwnershipAnalysisRepository(),
            threshold_percent=Decimal("25"),
            poc_acceptance_enabled=True,
            max_parties=100,
            max_relationships=200,
            max_depth=8,
            max_paths_per_candidate=64,
            max_total_paths=256,
        )


def test_default_off_keeps_the_garden_case_blocked_without_any_acceptance() -> None:
    _, _, client, case_id = accepted_case("disabled")
    ownership = ownership_of(client, case_id)
    summary = summary_of(client, case_id)
    assert (ownership["state"], ownership["poc_acceptance"], ownership["poc_basis_accepted"]) == (
        "REVIEW_REQUIRED",
        None,
        False,
    )
    assert ownership["events"][-1]["code"] == "OWNERSHIP_GRAPH_REVIEW_REQUIRED"
    assert (summary["status"], summary["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert summary["case"].get("goldtier_result") is None


# --- Accepted Garden journey: readiness only, every calculation preserved -----------


def test_an_eligible_garden_case_is_accepted_at_readiness_with_every_value_preserved() -> None:
    _, off_transport, off_client, off_case = accepted_case("disabled")
    bundle, transport, client, case_id = accepted_case()
    ownership = ownership_of(client, case_id)
    summary = summary_of(client, case_id)

    # The engine, discovery, quantities, classes, issues and evidence are unchanged.
    assert stable(ownership) == stable(ownership_of(off_client, off_case))
    assert transport.calls == off_transport.calls
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert [item["code"] for item in ownership["issues"]] == POC_CODES
    assert {
        item["party"]["display_name"]: (
            Decimal(item["aggregated_ownership_percent"]),
            item["classification"],
            item["threshold_result"],
            item["synthetic_basis_threshold_result"],
        )
        for item in ownership["candidates"]
    } == {
        "ABCD123": (Decimal("51.13636375"), "REVIEW_REQUIRED", "INDETERMINATE", "MET"),
        "LIM CHOON HUAT": (Decimal("37.5"), "REVIEW_REQUIRED", "INDETERMINATE", "MET"),
        "TAN WEI LING": (Decimal("5.681818125"), "REVIEW_REQUIRED", "INDETERMINATE", "NOT_MET"),
        "EFGH2345": (Decimal("5.681818125"), "REVIEW_REQUIRED", "INDETERMINATE", "NOT_MET"),
    }

    # The acceptance is explicit, auditable and bound to this exact analysis.
    acceptance = ownership["poc_acceptance"]
    assert (
        sorted(
            (item["kind"], item["raw_value"], item["source_status"] or "CURRENT")
            for item in ownership["evidence"]
        )
        == [("ROLE", "OWNER", "CEASED")] + [("ROLE", "OWNER", "CURRENT")] * 3
    )
    assert {
        key: acceptance[key]
        for key in (
            "policy",
            "case_id",
            "analysis_id",
            "ownership_version",
            "identity_registration_number",
            "identity_correction_version",
            "overlay_scenario_id",
            "accepted_issue_codes",
            "poc_relationship_ids",
            "descriptive_current_role_count",
            "descriptive_ceased_role_count",
            "accepted_assumptions",
        )
    } == {
        "policy": "D085_SCENARIO_DECLARED_POC_BASIS_V1",
        "case_id": case_id,
        "analysis_id": ownership["analysis_id"],
        "ownership_version": ownership["version"],
        "identity_registration_number": GARDEN,
        "identity_correction_version": 0,
        "overlay_scenario_id": "GARDEN_DIRECT_OVERLAY_V1",
        "accepted_issue_codes": POC_CODES,
        "poc_relationship_ids": sorted(
            edge["relationship_id"]
            for edge in ownership["relationships"]
            if edge["provenance"]["provider"] == POC_EQUAL_UNITS_PROVIDER
        ),
        "descriptive_current_role_count": 3,
        "descriptive_ceased_role_count": 1,
        "accepted_assumptions": GARDEN_ASSUMPTIONS,
    }
    assert ownership["poc_basis_accepted"] is True
    assert (
        ownership["events"][-1]["event_type"],
        ownership["events"][-1]["outcome"],
        ownership["events"][-1]["code"],
    ) == ("OWNERSHIP_REVIEW_REQUIRED", "REVIEW_REQUIRED", "OWNERSHIP_POC_BASIS_ACCEPTED")

    # Readiness proceeds; target confirmation stays mandatory and nothing is sent.
    assert summary["clm"]["readiness"]["blockers"] == []
    assert summary["clm"]["readiness"]["ownership"] == {
        "status": "READY",
        "reference_id": ownership["analysis_id"],
    }
    assert (summary["status"], summary["current_stage"]) == ("WAITING_FOR_REVIEW", "READINESS")
    assert [item["exception_type"] for item in summary["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    assert summary["case"].get("goldtier_result") is None
    assert summary["clm"]["submission"] is None
    assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
    automation = bundle.automation.get_for_case(UUID(case_id))
    [stage_event] = [item for item in automation.events if item.event_type == "OWNERSHIP_AUTOMATED"]
    assert (stage_event.event_type, stage_event.code) == (
        "OWNERSHIP_AUTOMATED",
        "OWNERSHIP_POC_BASIS_ACCEPTED",
    )
    # The creator's manual form stays available; D-081 Option B still refuses POC links.
    assert summary["ownership_edit_authorized"] is True
    refused = manual_decision(client, case_id)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == POC_REFUSAL
    assert gate_state(summary_of(client, case_id)) == gate_state(summary)
    assert transport.metadata()["external_calls"] == 0


# --- P1 downstream: the Mock target snapshot carries no provisional UBO -------------


def test_a_confirmed_mock_send_carries_no_assumed_basis_ubo_and_never_replays() -> None:
    bundle, _, client, case_id = accepted_case()
    ownership = ownership_of(client, case_id)
    current = summary_of(client, case_id)
    assert current["clm"]["related_party_preparation"] is None
    sent = confirm(client, current)
    assert sent["status"] == "COMPLETED"
    record = bundle.clm.get_for_case(UUID(case_id))
    snapshot = record.submission_snapshot
    assert snapshot is not None
    # Formal classification stays REVIEW_REQUIRED, so no assumed-basis person becomes a
    # provisional UBO in the target snapshot or the related-party preparation.
    assert (
        snapshot.provisional_ubo.candidate_count,
        snapshot.provisional_ubo.internal_party_ids,
    ) == (
        0,
        (),
    )
    assert (
        str(snapshot.ownership_reference.reference_id),
        snapshot.ownership_reference.version,
        snapshot.ownership_reference.status,
    ) == (ownership["analysis_id"], ownership["version"], "REVIEW_REQUIRED")
    preparation = record.related_party_preparation
    assert (preparation.provisional_candidate_count, preparation.internal_party_ids) == (0, ())
    assert sent["clm"]["related_party_preparation"]["provisional_candidate_count"] == 0
    assert sent["case"]["goldtier_result"] is not None
    executions = bundle.target_executions.list_for_case(record.case_id)
    assert len(executions) == 1
    # The ownership analysis and its acceptance are untouched by the send.
    assert ownership_of(client, case_id) == ownership
    # A repeated confirmation with the consumed versions is refused: no replay.
    replay = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": current["version"],
            "expected_clm_version": current["clm"]["version"],
            "expected_case_event_count": len(current["case"]["events"]),
        },
    )
    assert replay.status_code == 409
    assert bundle.target_executions.list_for_case(record.case_id) == executions


# --- P1 revocation: a persisted acceptance grants nothing without current authority --
# The physical Mongo lane proves the same across real application restarts.


def composed(
    onboarding: Any, settings: Settings, ownership_repository: Any, clm_repository: Any
) -> tuple[OwnershipAnalysisService, Any]:
    """One runtime composition over durable ownership and CLM repositories."""

    ownership = build_ownership_analysis_service(
        onboarding, settings, repository=ownership_repository
    )
    documents = build_document_processing_service(onboarding, settings)
    clm = build_clm_orchestration_service(
        onboarding, documents, ownership, repository=clm_repository
    )
    return ownership, clm


def test_readiness_authority_belongs_to_the_current_composition() -> None:
    onboarding, _ = service_lane()
    repositories = (InMemoryOwnershipAnalysisRepository(), InMemoryClmOrchestrationRepository())
    enabled, clm = composed(onboarding, lane(), *repositories)
    case_id = clm.create_case(GARDEN, "SG", legal_name="GARDEN BUSINESS").case_id
    enabled.load(case_id=case_id)
    record = enabled.analyze(case_id=case_id)
    assert record.poc_acceptance is not None and enabled.poc_basis_accepted(record)
    accepted = clm.evaluate(case_id=case_id).readiness
    assert (accepted.ownership.status, accepted.ownership.reference_id) == (
        "READY",
        str(record.analysis_id),
    )
    assert "OWNERSHIP_REVIEW_REQUIRED" not in accepted.blockers
    for settings in (
        lane("disabled"),
        lane("disabled", acra_marketplace_ownership_overlay="garden_legacy_supplement"),
        lane(
            "disabled",
            acra_connector_mode="mock",
            acra_marketplace_ownership_overlay="garden_legacy_supplement",
        ),
    ):
        ownership, restarted = composed(onboarding, settings, *repositories)
        # The persisted acceptance is unchanged audit evidence and grants nothing here.
        assert ownership.get(case_id=case_id) == record
        assert poc_acceptance_current(
            record, garden_scenario()
        ) and not ownership.poc_basis_accepted(record)
        revoked = restarted.evaluate(case_id=case_id).readiness
        assert revoked.ownership.status == "REVIEW_REQUIRED"
        assert "OWNERSHIP_REVIEW_REQUIRED" in revoked.blockers
    # Authority returns only with the opt-in composition itself.
    _, again = composed(onboarding, lane(), *repositories)
    assert "OWNERSHIP_REVIEW_REQUIRED" not in again.evaluate(case_id=case_id).readiness.blockers


def test_enabling_the_policy_never_accepts_an_existing_review_case() -> None:
    onboarding, _ = service_lane("disabled")
    repositories = (InMemoryOwnershipAnalysisRepository(), InMemoryClmOrchestrationRepository())
    disabled, clm = composed(onboarding, lane("disabled"), *repositories)
    case_id = clm.create_case(GARDEN, "SG", legal_name="GARDEN BUSINESS").case_id
    disabled.load(case_id=case_id)
    existing = disabled.analyze(case_id=case_id)
    assert existing.state == OwnershipAnalysisState.REVIEW_REQUIRED
    enabled, clm = composed(onboarding, lane(), *repositories)
    # A terminal analysis is never re-analysed, so it is never silently accepted.
    assert enabled.analyze(case_id=case_id) == existing
    assert repositories[0].get_for_case(case_id) == existing
    assert existing.poc_acceptance is None and not enabled.poc_basis_accepted(existing)
    assert "OWNERSHIP_REVIEW_REQUIRED" in clm.evaluate(case_id=case_id).readiness.blockers


# --- D-085: a reusable scenario-declared contract, evaluated on actual review causes ---


def _role(record: OwnershipAnalysisRecord, **update: Any) -> Any:
    return record.evidence[0].model_copy(update=update)


# Genuine defects, or causes no declaration accepts: every one stays blocking.
BLOCKING: dict[str, Any] = {
    "a duplicated role record": lambda r: {"evidence": (r.evidence[0], *r.evidence[:3])},
    "an evidence id not derived from its officer": lambda r: {
        "evidence": (_role(r, evidence_id=role_id(9)), *r.evidence[1:])
    },
    "an unknown role status": lambda r: {
        "evidence": (*r.evidence[:3], r.evidence[3].model_copy(update={"source_status": "ACTIVE"}))
    },
    "a role bound to another entity": lambda r: {
        "evidence": (_role(r, entity_identifier="201511222D"), *r.evidence[1:])
    },
    "a role from a local source": lambda r: {
        "evidence": (_role(r, provider="LOCAL_SYNTHETIC_RELATIONSHIP"), *r.evidence[1:])
    },
    "a role from another operation": lambda r: {
        "evidence": (_role(r, source_operation="OWNERSHIP_PARTIES"), *r.evidence[1:])
    },
    "a role from a Live provider": lambda r: {
        "evidence": (_role(r, environment="LIVE"), *r.evidence[1:])
    },
    "share-unit evidence": lambda r: {
        "evidence": (*r.evidence[1:], _role(r, kind="SHARE_UNITS", raw_value="1"))
    },
    "unresolved control evidence": lambda r: {
        "evidence": (*r.evidence[1:], _role(r, kind="CONTROL", raw_value="CONTROL"))
    },
    "conflicting evidence": lambda r: {
        "evidence": (*r.evidence[1:], _role(r, kind="CONFLICT", raw_value="CONFLICT"))
    },
    "evidence without an entity binding": lambda r: {
        "evidence": (_role(r, entity_identifier=None), *r.evidence[1:])
    },
    # The review issue then has no remaining cause: the issue set no longer reconciles.
    "no officer role records": lambda r: {"evidence": ()},
    "an unrelated contradiction": lambda r: {
        "issues": [
            *r.issues,
            OwnershipAnalysisIssue(
                code=OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE, message="Synthetic."
            ),
        ]
    },
    "a second review cause": lambda r: {
        "issues": [
            *r.issues,
            OwnershipAnalysisIssue(code=OwnershipIssueCode.UBO_REVIEW_REQUIRED, message="Other."),
        ]
    },
    "an unresolved corporate holder": lambda r: {
        "issues": [
            *r.issues,
            OwnershipAnalysisIssue(
                code=OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED, message="Synthetic."
            ),
        ]
    },
    "an undeclared legal-form issue": lambda r: {
        "issues": [
            *r.issues,
            OwnershipAnalysisIssue(
                code=OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED, message="Synthetic."
            ),
        ]
    },
    "a legal form with no method and no declaration": lambda r: {
        "legal_form": RegistryLegalForm.OTHER
    },
    "no registry legal form": lambda r: {"legal_form": None},
    "no synthetic-evidence marker": lambda r: {
        "issues": [
            item
            for item in r.issues
            if item.code != OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE
        ]
    },
    "a document discrepancy needing review": lambda r: {
        "document_discrepancies": (
            OwnershipDocumentDiscrepancy(
                observation_id="00000000-0000-4000-8000-000000000001",
                document_id="00000000-0000-4000-8000-000000000002",
                agreement="NOT_COMPARABLE",
                reason_code="OWNERSHIP_DOCUMENT_INCOMPLETE",
            ),
        )
    },
    "another overlay scenario": lambda r: {
        "discovery": r.discovery.model_copy(update={"overlay_scenario_id": FIVE_LAYER_SCENARIO_ID})
    },
    "an incomplete topology": lambda r: {
        "discovery": r.discovery.model_copy(update={"topology_complete": False})
    },
    "an unresolved person identity": lambda r: {
        "discovery": r.discovery.model_copy(
            update={"unresolved_person_party_ids": (r.candidates[0].party.party_id,)}
        )
    },
    "an issuer without POC distribution": lambda r: {
        "discovery": r.discovery.model_copy(
            update={
                "records": tuple(
                    item.model_copy(
                        update={"reason_code": OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE}
                    )
                    for item in r.discovery.records
                )
            }
        )
    },
    "a locally named issuer identity": lambda r: {
        "discovery": r.discovery.model_copy(
            update={
                "records": tuple(
                    item.model_copy(update={"identity_basis": "LOCAL_SYNTHETIC_IDENTITY"})
                    for item in r.discovery.records
                )
            }
        )
    },
    "another root": lambda r: {"identity_registration_number": "201511222D"},
    "no identity binding": lambda r: {"identity_correction_version": None},
    "a Live provider": lambda r: {"provider_environment": OwnershipEnvironment.LIVE},
    "a manual provider": lambda r: {"provider_name": "MANUAL_DECLARATION_POC"},
    "a non-overlay link": lambda r: {
        "relationships": [
            r.relationships[0].model_copy(
                update={
                    "provenance": OwnershipProvenance(
                        provider="ACRA_REGISTRY_ACQUISITION",
                        environment=OwnershipEnvironment.MOCK,
                        source_reference="SYNTHETIC",
                        sourced_at=r.relationships[0].provenance.sourced_at,
                    )
                }
            ),
            *r.relationships[1:],
        ]
    },
    "an uncalculated person": lambda r: {
        "candidates": [
            r.candidates[0].model_copy(
                update={"synthetic_basis_threshold_result": OwnershipThresholdResult.INDETERMINATE}
            ),
            *r.candidates[1:],
        ]
    },
    "a provisional classification": lambda r: {
        "candidates": [
            r.candidates[0].model_copy(
                update={
                    "classification": OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
                }
            ),
            *r.candidates[1:],
        ]
    },
}

# D-085 removed the exact Garden identity allowlist: official Mock officer roles of the root
# with a different identity, count or status are still descriptive context. They change the
# analysis content, so a recorded acceptance never survives them.
IDENTITY_ONLY: dict[str, Any] = {
    "a fifth official owner role": lambda r: {
        "evidence": (*r.evidence, _role(r, evidence_id=role_id(5), party_id="SYNTHETIC-ROLE-5"))
    },
    "one substituted identity": lambda r: {
        "evidence": (_role(r, evidence_id=role_id(9), party_id="SYNTHETIC-ROLE-9"), *r.evidence[1:])
    },
    "four unknown identities in the observed shape": lambda r: {
        "evidence": tuple(
            item.model_copy(
                update={
                    "party_id": f"SYNTHETIC-UNKNOWN-{index}",
                    "evidence_id": _evidence_id(f"SYNTHETIC-UNKNOWN-{index}", "ROLE"),
                }
            )
            for index, item in enumerate(r.evidence, start=1)
        )
    },
    "the ceased role becoming current": lambda r: {
        "evidence": (*r.evidence[:3], r.evidence[3].model_copy(update={"source_status": None}))
    },
    "a current role ceasing": lambda r: {
        "evidence": (_role(r, source_status="CEASED"), *r.evidence[1:])
    },
    "only three roles": lambda r: {"evidence": r.evidence[1:]},
    "a partner role": lambda r: {"evidence": (_role(r, raw_value="PARTNER"), *r.evidence[1:])},
}


def _evaluate(record: OwnershipAnalysisRecord, scenario: Any = None) -> Any:
    acceptance = record.poc_acceptance
    assert acceptance is not None
    return eligible_poc_acceptance(
        record,
        scenario=garden_scenario() if scenario is None else scenario,
        accepted_at=acceptance.accepted_at,
        ownership_version=acceptance.ownership_version,
    )


@pytest.mark.parametrize("name", sorted(BLOCKING))
def test_genuine_defects_and_undeclared_causes_stay_blocking(name: str) -> None:
    _, ownership, record = accepted_record()
    assert _evaluate(record) == record.poc_acceptance
    assert poc_acceptance_current(record, garden_scenario())
    mutated = record.model_copy(update=BLOCKING[name](record))
    assert _evaluate(mutated) is None
    assert not poc_acceptance_current(mutated, garden_scenario())
    assert not ownership.poc_basis_accepted(mutated)


@pytest.mark.parametrize("name", sorted(IDENTITY_ONLY))
def test_officer_role_identity_no_longer_gates_acceptance_but_still_revokes(name: str) -> None:
    _, ownership, record = accepted_record()
    mutated = record.model_copy(update=IDENTITY_ONLY[name](record))
    fresh = _evaluate(mutated)
    # The same contract accepts the changed descriptive context on a new analysis...
    assert fresh is not None
    assert fresh.accepted_assumptions == record.poc_acceptance.accepted_assumptions
    assert (fresh.descriptive_current_role_count, fresh.descriptive_ceased_role_count) == (
        sum(1 for item in mutated.evidence if item.source_status is None),
        sum(1 for item in mutated.evidence if item.source_status == "CEASED"),
    )
    # ...but the recorded acceptance is bound to the exact old content and is revoked.
    assert fresh.basis_fingerprint != record.poc_acceptance.basis_fingerprint
    assert not poc_acceptance_current(mutated, garden_scenario())
    assert not ownership.poc_basis_accepted(mutated)


def _declaring(*assumptions: PocAssumption, scenario_id: str | None = None) -> Any:
    base = garden_scenario()
    return HybridOverlayScenario.model_validate(
        {
            **base.model_dump(),
            "scenario_id": scenario_id or base.scenario_id,
            "poc_acceptance": PocAcceptanceDeclaration(
                quantity_basis="OWNER_SUPPLIED_DIRECT_REGISTER",
                accepted_assumptions=frozenset(assumptions),
            ),
        }
    )


def test_acceptance_follows_the_trusted_declaration_not_a_case_field() -> None:
    _, ownership, record = accepted_record()
    every = (
        PocAssumption.SIMULATED_RELATIONSHIPS,
        PocAssumption.EQUAL_UNIT_DENOMINATOR,
        PocAssumption.DESCRIPTIVE_OFFICER_ROLES,
    )
    # Declaring an extra, unexercised assumption changes nothing about the decision.
    assert _evaluate(record, _declaring(*every, PocAssumption.UNCLASSIFIED_LEGAL_FORM)) == (
        record.poc_acceptance
    )
    # Each exercised assumption must be declared; a missing one keeps the case blocked.
    for missing in every:
        declared = [item for item in every if item != missing]
        if PocAssumption.SIMULATED_RELATIONSHIPS not in declared:
            with pytest.raises(ValidationError, match="declares its simulated links"):
                _declaring(*declared)
            continue
        assert _evaluate(record, _declaring(*declared)) is None
    # A scenario without a declaration (the historical five-layer one), an absent scenario
    # or a declaration under another scenario id never accepts.
    assert _evaluate(record, garden_scenario().model_copy(update={"poc_acceptance": None})) is None
    assert eligible_poc_acceptance(
        record,
        scenario=None,
        accepted_at=record.poc_acceptance.accepted_at,
        ownership_version=record.version,
    ) is None
    assert _evaluate(record, _declaring(*every, scenario_id="ANOTHER_SCENARIO_V1")) is None
    # Removing the catalogue declaration at runtime withdraws the readiness authority.
    assert ownership.poc_basis_accepted(record)
    with patch.object(ownership, "_poc_scenario", return_value=None):
        assert not ownership.poc_basis_accepted(record)


def test_the_historical_five_layer_scenario_declares_no_acceptance() -> None:
    catalogue = HybridOwnershipOverlayCatalogue()
    five_layer = catalogue.scenario(FIVE_LAYER_SCENARIO_ID)
    assert five_layer is not None and five_layer.poc_acceptance is None
    assert catalogue.scenario("UNKNOWN_SCENARIO") is None
    assert catalogue.scenario(None) is None


def test_a_legal_form_without_a_method_is_accepted_only_when_declared() -> None:
    _, _, record = accepted_record()
    every = (
        PocAssumption.SIMULATED_RELATIONSHIPS,
        PocAssumption.EQUAL_UNIT_DENOMINATOR,
        PocAssumption.DESCRIPTIVE_OFFICER_ROLES,
    )
    # The single registry review issue is chosen by priority: OTHER masks the role cause.
    other = record.model_copy(
        update={
            "legal_form": RegistryLegalForm.OTHER,
            "issues": [
                OwnershipAnalysisIssue(
                    code=OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED, message="Synthetic."
                )
                if item.code == OwnershipIssueCode.UBO_REVIEW_REQUIRED
                else item
                for item in record.issues
            ],
        }
    )
    assert _evaluate(other, _declaring(*every)) is None
    accepted = _evaluate(other, _declaring(*every, PocAssumption.UNCLASSIFIED_LEGAL_FORM))
    assert accepted is not None
    assert list(accepted.accepted_assumptions) == sorted(
        [*every, PocAssumption.UNCLASSIFIED_LEGAL_FORM]
    )
    assert list(accepted.accepted_issue_codes) == [
        "OWNERSHIP_DENOMINATOR_REQUIRED",
        "OWNERSHIP_METHOD_UNSUPPORTED",
        "SYNTHETIC_OWNERSHIP_EVIDENCE",
    ]
    # A masked genuine defect (unquantified share units) still blocks under OTHER.
    defective = other.model_copy(
        update={"evidence": (*other.evidence[1:], _role(other, kind="SHARE_UNITS", raw_value="1"))}
    )
    assert _evaluate(defective, _declaring(*every, PocAssumption.UNCLASSIFIED_LEGAL_FORM)) is None


def test_the_officer_roles_stay_retained_and_unreconciled() -> None:
    _, _, record = accepted_record()
    acceptance = record.poc_acceptance
    assert acceptance is not None
    assert (
        acceptance.descriptive_current_role_count,
        acceptance.descriptive_ceased_role_count,
    ) == (
        3,
        1,
    )
    # Every official role record, the ceased one included, keeps its truthful provenance.
    assert sorted(
        (
            item.party_id,
            item.source_status,
            item.kind,
            item.raw_value,
            item.provider,
            item.source_operation,
            item.environment,
            item.entity_identifier,
        )
        for item in record.evidence
    ) == [
        (
            f"SYNTHETIC-ROLE-{index}",
            "CEASED" if index == 4 else None,
            "ROLE",
            "OWNER",
            "ACRA_REGISTRY_ACQUISITION",
            "OFFICERS",
            "MOCK",
            GARDEN,
        )
        for index in range(1, 5)
    ]
    # The roles are descriptive context only: no edge, candidate or issue is derived
    # from them, and UBO_REVIEW_REQUIRED stays on the analysis.
    role_parties = {item.party_id for item in record.evidence}
    assert not role_parties & {party.party_id for party in record.parties}
    assert not role_parties & {item.party.party_id for item in record.candidates}
    assert OwnershipIssueCode.UBO_REVIEW_REQUIRED in {item.code for item in record.issues}


def candidate_values(record: OwnershipAnalysisRecord) -> list[tuple]:
    return sorted(
        (
            item.party.display_name,
            item.direct_ownership_percent,
            item.indirect_ownership_percent,
            item.aggregated_ownership_percent,
            item.threshold_result,
            item.classification,
            item.synthetic_basis_threshold_result,
        )
        for item in record.candidates
    )


def analysed(onboarding: Any, ownership: OwnershipAnalysisService) -> OwnershipAnalysisRecord:
    case = onboarding.create_staged_case(GARDEN)
    ownership.load(case_id=case.case_id)
    return ownership.analyze(case_id=case.case_id)


def test_the_ceased_role_never_changes_calculated_ownership() -> None:
    _, _, observed = accepted_record()
    all_current = analysed(*service_lane("disabled", garden_transport(ceased=())))
    assert candidate_values(observed) == candidate_values(all_current)
    assert sorted(
        (edge.relationship_id, edge.ownership_percent) for edge in observed.relationships
    ) == sorted(
        (edge.relationship_id, edge.ownership_percent) for edge in all_current.relationships
    )
    assert [item.code for item in observed.issues] == [item.code for item in all_current.issues]


def test_the_role_set_is_accepted_independent_of_response_order() -> None:
    transport = garden_transport()
    profile: Any = transport.profiles[GARDEN]
    officers = profile["entities"][0]["entityOfficersRecord"]["officerAppointmentDetails"]
    officers.reverse()
    record = analysed(*service_lane(transport=transport))
    assert [item.party_id for item in record.evidence][0] == "SYNTHETIC-ROLE-4"
    assert record.poc_acceptance is not None


@pytest.mark.parametrize("ceased", [(), (1,), (3, 4)], ids=["none", "one-other", "two"])
def test_other_observed_role_statuses_are_accepted_with_truthful_counts(
    ceased: tuple[int, ...],
) -> None:
    _, _, observed = accepted_record()
    record = analysed(*service_lane(transport=garden_transport(ceased=ceased)))
    assert record.poc_acceptance is not None
    assert (
        record.poc_acceptance.descriptive_current_role_count,
        record.poc_acceptance.descriptive_ceased_role_count,
    ) == (4 - len(ceased), len(ceased))
    assert candidate_values(record) == candidate_values(observed)
    assert [item.code for item in record.issues] == POC_CODES


def test_removed_officer_role_settings_are_not_required_and_are_ignored() -> None:
    # Regression 13: no protected officer-role values exist; acceptance needs none.
    assert not {
        "acra_marketplace_poc_officer_role_key",
        "acra_marketplace_poc_officer_role_allowlist",
    } & set(Settings.model_fields)
    record = analysed(*service_lane())
    assert record.poc_acceptance is not None
    # A stale owner .env value is ignored like any unknown setting, never an error.
    with patch.dict(
        "os.environ",
        {
            "ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY": "stale-synthetic-value",
            "ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST": "stale-synthetic-value",
        },
    ):
        settings = lane()
    assert "stale-synthetic-value" not in repr(settings.model_dump())
    example = (Path(__file__).resolve().parents[3] / ".env.example").read_text(encoding="utf-8")
    assert "ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY=" not in example.splitlines()
    assert "ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST=" not in example.splitlines()


def test_the_officer_role_identity_is_the_adapters_stable_id_and_never_exposed() -> None:
    assert _officer_role_evidence_id("SYNTHETIC-ROLE-1") == _evidence_id("SYNTHETIC-ROLE-1", "ROLE")
    _, _, client, case_id = accepted_case()
    ownership = ownership_of(client, case_id)
    # The acceptance itself names no role identity: counts only.
    acceptance = json.dumps(ownership["poc_acceptance"])
    for index in range(1, 5):
        assert role_id(index) not in acceptance
        assert f"SYNTHETIC-ROLE-{index}" not in acceptance


def test_a_recorded_d082_acceptance_is_never_honoured_after_d085() -> None:
    # Regression 18: a historical D-082 record stays readable audit evidence only.
    _, ownership, record = accepted_record()
    acceptance = record.poc_acceptance
    assert acceptance is not None
    legacy = acceptance.model_copy(
        update={"policy": "D082_HYBRID_POC_EQUAL_UNITS_V1", "accepted_assumptions": ()}
    )
    OwnershipPocAcceptance.model_validate(legacy.model_dump())
    historical = record.model_copy(update={"poc_acceptance": legacy})
    assert not poc_acceptance_current(historical, garden_scenario())
    assert not ownership.poc_basis_accepted(historical)


# --- F2 and F6: runtime authority changes against the workflow and target writes ------


def test_toggling_the_policy_keeps_readiness_and_the_workflow_consistent() -> None:
    bundle, client, case_id, service = accepted_runtime()
    assert exception_types(summary_of(client, case_id)) == ["TARGET_CONFIRMATION_REQUIRED"]
    # The composition's runtime authority is withdrawn (the physical lane restarts).
    service._poc_acceptance_enabled = False
    assert (
        "OWNERSHIP_REVIEW_REQUIRED" in summary_of(client, case_id)["clm"]["readiness"]["blockers"]
    )
    held = resume(client, case_id)
    assert (held["status"], held["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")
    assert exception_types(held) == ["OWNERSHIP_INCOMPLETE"]
    assert "OWNERSHIP_REVIEW_REQUIRED" in held["clm"]["readiness"]["blockers"]
    # Re-enabled: the next resume clears the stale hold and returns to target confirmation.
    service._poc_acceptance_enabled = True
    resumed = resume(client, case_id)
    assert (resumed["status"], resumed["current_stage"]) == ("WAITING_FOR_REVIEW", "READINESS")
    assert exception_types(resumed) == ["TARGET_CONFIRMATION_REQUIRED"]
    assert resumed["clm"]["readiness"]["blockers"] == []
    assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
    sent = confirm(client, resumed)
    assert sent["status"] == "COMPLETED"
    snapshot = bundle.clm.get_for_case(UUID(case_id)).submission_snapshot
    assert (
        snapshot.provisional_ubo.candidate_count,
        snapshot.provisional_ubo.internal_party_ids,
    ) == (
        0,
        (),
    )


def test_revoking_the_policy_after_the_freeze_blocks_the_first_target_write() -> None:
    bundle, client, case_id, service = accepted_runtime()
    current = summary_of(client, case_id)
    original = ClmOrchestrationService.confirm_target_dispatch

    def confirm_then_revoke(self: ClmOrchestrationService, **kwargs: Any) -> Any:
        record = original(self, **kwargs)
        service._poc_acceptance_enabled = False
        return record

    with patch.object(ClmOrchestrationService, "confirm_target_dispatch", confirm_then_revoke):
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
    after = summary_of(client, case_id)
    assert after["case"].get("goldtier_result") is None
    assert all(
        not entry.attempted_operations and entry.target_outcome is None
        for entry in bundle.target_executions.list_for_case(UUID(case_id))
    )
    record = bundle.clm.get_for_case(UUID(case_id))
    assert record.status != "MOCK_GOLDTIER_SUBMITTED"
    assert after["technical_failure"] is not None
    assert after["technical_failure"]["code"] == "CLM_NOT_READY"


@pytest.mark.parametrize("journey", ["five-layer", "d079-refusal"])
def test_ineligible_hybrid_journeys_stay_blocked_with_the_policy_enabled(
    journey: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    if journey == "d079-refusal":

        def refuse(*args: object, **kwargs: object) -> None:
            raise ValueError("synthetic refusal")

        monkeypatch.setattr(
            "app.services.ownership_discovery.official_equal_unit_component", refuse
        )
    bundle = build_persistence_bundle(lane())
    with runtime(lane(), bundle, garden_transport()) as client:
        fields, document = (
            (FIVE_LAYER_FIELDS, "five-layer-marketplace-hybrid-client.pdf")
            if journey == "five-layer"
            else (GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
        )
        case_id = start(client, fields, document)["case"]["case_id"]
        ownership = ownership_of(client, case_id)
        summary = summary_of(client, case_id)
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert (ownership["poc_acceptance"], ownership["poc_basis_accepted"]) == (None, False)
    assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
    assert (summary["status"], summary["current_stage"]) == ("WAITING_FOR_REVIEW", "OWNERSHIP")


# --- P2 freshness: bound to case identity, version, content, scenario and policy -----


def test_the_authority_requires_the_current_document_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, ownership, record = accepted_record()
    assert ownership.poc_basis_accepted(record)
    # A document change that rebinds ownership observations makes the analysis stale for
    # every consumer, including the analyze response, before any reload.
    rebound = (OwnershipDocumentBinding(document_id=uuid4(), event_count=1),)
    monkeypatch.setattr(ownership, "_document_inputs", lambda case_id: ((), rebound))
    assert poc_acceptance_current(record, garden_scenario())
    assert not ownership.poc_basis_accepted(record)


def test_the_acceptance_is_bound_to_its_case_version_content_and_identity() -> None:
    _, ownership, record = accepted_record()
    acceptance = record.poc_acceptance
    assert acceptance is not None and ownership.poc_basis_accepted(record)
    tampered_acceptance = acceptance.model_copy(update={"basis_fingerprint": "0" * 64})
    for changed in (
        record.model_copy(update={"version": record.version + 1}),
        record.model_copy(update={"analysis_id": acceptance.case_id}),
        record.model_copy(update={"identity_correction_version": 1}),
        record.model_copy(
            update={
                "document_bindings": (OwnershipDocumentBinding(document_id=uuid4(), event_count=1),)
            }
        ),
        record.model_copy(update={"poc_acceptance": tampered_acceptance}),
        record.model_copy(
            update={"poc_acceptance": acceptance.model_copy(update={"ownership_version": 1})}
        ),
        record.model_copy(update={"state": OwnershipAnalysisState.ANALYZED}),
        record.model_copy(
            update={
                "relationships": [
                    record.relationships[0].model_copy(
                        update={"ownership_percent": Decimal("62.4")}
                    ),
                    *record.relationships[1:],
                ]
            }
        ),
        record.model_copy(update={"poc_acceptance": None}),
    ):
        assert not poc_acceptance_current(changed, garden_scenario())
        assert not ownership.poc_basis_accepted(changed)


def test_a_document_replacement_without_ownership_evidence_keeps_only_the_bound_analysis() -> None:
    bundle, _, client, case_id = accepted_case()
    accepted = ownership_of(client, case_id)
    before = summary_of(client, case_id)
    documents = successful(client.get(f"/api/onboarding/cases/{case_id}/documents"))
    [document] = [item for item in documents if not item["superseded_by_document_id"]]
    replaced = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents/{document['document_id']}/replacement",
        content=(FIXTURES / "garden-partnership-reviewed-client.pdf").read_bytes(),
        headers={
            "Content-Type": "application/pdf",
            "X-Document-Name": "garden-partnership-replacement.pdf",
            "X-Document-Event-Count": str(len(document["events"])),
            "X-Automation-Version": str(before["version"]),
            "X-Clm-Version": str(before["clm"]["version"]),
            "X-Case-Event-Count": str(len(before["case"]["events"])),
        },
    )
    assert replaced.status_code == 200, replaced.text
    # This document carries no ownership observations, so the ownership evidence binding
    # is unchanged and the same exact analysis stays current and accepted. (A change of
    # bound ownership observations makes `get()` stale and reload builds a new analysis
    # without any acceptance; the fingerprint test covers a changed binding.)
    assert accepted["document_bindings"] == []
    assert ownership_of(client, case_id) == accepted
    # The prior target confirmation is consumed by the replacement: never replayed.
    stale = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": before["version"],
            "expected_clm_version": before["clm"]["version"],
            "expected_case_event_count": len(before["case"]["events"]),
        },
    )
    assert stale.status_code == 409
    summary = summary_of(client, case_id)
    assert summary["case"].get("goldtier_result") is None
    assert bundle.target_executions.list_for_case(UUID(case_id)) == ()


def test_a_creator_replacement_supersedes_the_acceptance_and_keeps_it_as_history() -> None:
    bundle, _, client, case_id = accepted_case()
    accepted = ownership_of(client, case_id)
    replaced = manual_decision(
        client,
        case_id,
        source_selection="USER_SUPPLIED_DECLARATION",
        percents={"ABCD123": "60.000000", "TAN WEI LING": "25.000000", "EFGH2345": "15.000000"},
    )
    assert replaced.status_code == 200, replaced.text
    current = ownership_of(client, case_id)
    assert (current["state"], current["provider_name"]) == ("ANALYZED", "MANUAL_DECLARATION_POC")
    assert (current["poc_acceptance"], current["poc_basis_accepted"]) == (None, False)
    record = bundle.ownership.get_for_case(UUID(case_id))
    assert record.prior_analyses[-1].poc_acceptance is not None
    assert str(record.prior_analyses[-1].poc_acceptance.analysis_id) == accepted["analysis_id"]
    assert (
        record.prior_analyses[-1].poc_acceptance.model_dump(mode="json")
        == (accepted["poc_acceptance"])
    )


def test_acceptance_records_validate_their_own_authority_and_binding() -> None:
    _, _, record = accepted_record()
    acceptance = record.poc_acceptance
    assert acceptance is not None
    payload = acceptance.model_dump()
    for update in (
        {"policy": "D083_SOMETHING_ELSE"},
        {"accepted_issue_codes": ("OWNERSHIP_DENOMINATOR_REQUIRED",)},
        {"accepted_issue_codes": (*acceptance.accepted_issue_codes, "CYCLE_DETECTED")},
        {"accepted_issue_codes": tuple(reversed(acceptance.accepted_issue_codes))},
        {"descriptive_current_role_count": 0, "descriptive_ceased_role_count": 0},
        {"poc_relationship_ids": ()},
        {"accepted_assumptions": ()},
        {"accepted_assumptions": tuple(reversed(acceptance.accepted_assumptions))},
        {"accepted_assumptions": ("DESCRIPTIVE_OFFICER_ROLES",)},
        {"accepted_assumptions": (*acceptance.accepted_assumptions, "UNCLASSIFIED_LEGAL_FORM")},
        {"policy": "D082_HYBRID_POC_EQUAL_UNITS_V1"},
        {"basis_fingerprint": "not-a-digest"},
        {"accepted_at": datetime(2026, 10, 24, 12, 0)},
    ):
        with pytest.raises(ValidationError):
            OwnershipPocAcceptance.model_validate({**payload, **update})
    encoded = record.model_dump()
    for update in (
        {"state": OwnershipAnalysisState.ANALYZED},
        {"source_classification": "SINGLE_SOURCE"},
        {"case_id": acceptance.analysis_id},
        {"poc_acceptance": {**payload, "analysis_id": acceptance.case_id}},
    ):
        with pytest.raises(ValidationError, match="binds only its own hybrid review analysis"):
            OwnershipAnalysisRecord.model_validate({**encoded, **update})


def test_the_acceptance_round_trips_in_schema_fifteen_and_never_in_older_schemas() -> None:
    onboarding, ownership, record = accepted_record()
    assert max(_SUPPORTED_SCHEMA_VERSIONS) == 17
    encoded = snapshot_of(onboarding, record).model_dump(mode="json")
    assert encoded["schema_version"] == 17
    restored = DurableCaseSnapshot.model_validate(encoded).ownership
    assert restored == record
    assert restored is not None and ownership.poc_basis_accepted(restored)
    for older in (13, 14):
        with pytest.raises(ValidationError):
            DurableCaseSnapshot.model_validate({**encoded, "schema_version": older})
    # The exact schema-14 reader rejects a D-085 acceptance, on current and prior analyses,
    # and still reads a D-082 one (never honoured by a D-085 runtime).
    with pytest.raises(ValidationError, match="D-085 POC acceptance"):
        DurableCaseSnapshotV14.model_validate({**encoded, "schema_version": 14})
    d085 = encoded["ownership"]["poc_acceptance"]
    for legacy in (
        {"ownership": {"poc_acceptance": d085}},
        {"ownership": {"prior_analyses": [{"poc_acceptance": d085}]}},
        {"ownership": {"poc_acceptance": {"accepted_assumptions": ["SIMULATED_RELATIONSHIPS"]}}},
    ):
        with pytest.raises(ValueError, match="D-085 POC acceptance"):
            reject_scenario_poc_legacy_fields(legacy)
    d082 = {**d085, "policy": "D082_HYBRID_POC_EQUAL_UNITS_V1", "accepted_assumptions": []}
    reject_scenario_poc_legacy_fields({"ownership": {"poc_acceptance": d082}})
    reject_scenario_poc_legacy_fields({"ownership": {"poc_acceptance": None}})
    legacy_case = DurableCaseSnapshotV14.model_validate(
        {
            **encoded,
            "schema_version": 14,
            "ownership": {**encoded["ownership"], "poc_acceptance": d082},
        }
    ).to_current()
    assert legacy_case.ownership is not None
    assert not ownership.poc_basis_accepted(legacy_case.ownership)
    # The exact schema-13 guard rejects the acceptance itself, on current and prior analyses.
    acceptance = encoded["ownership"]["poc_acceptance"]
    for legacy in (
        {"ownership": {"poc_acceptance": acceptance}},
        {"ownership": {"prior_analyses": [{"poc_acceptance": acceptance}]}},
    ):
        with pytest.raises(ValueError, match="POC ownership acceptance"):
            reject_share_class_legacy_fields(legacy)
    reject_share_class_legacy_fields({"ownership": {"poc_acceptance": None}})
    assert datetime.now(UTC) >= record.poc_acceptance.accepted_at


def test_a_non_poc_interrupted_manual_replacement_keeps_its_existing_recovery() -> None:
    # Re-QG N1: the F2 rebuild applies only to an analysis carrying a POC acceptance. An
    # ordinary REVIEW_REQUIRED replacement whose automation write was interrupted keeps the
    # existing restoration: OWNERSHIP stays completed and no target call is made.
    client, zero, _, target, case_id = prepare_case()
    before = zero.get(case_id=case_id)
    assert "OWNERSHIP" in before.completed_stages
    payload = current_payload(client, case_id, complete=False, percent="60")
    with patch.object(zero._repository, "save", side_effect=ValueError("SYNTHETIC")):
        rejected = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence", json=payload
        )
    assert rejected.status_code == 503
    ownership = zero._ownership.get(case_id=case_id)
    assert (ownership.state, ownership.poc_acceptance) == ("REVIEW_REQUIRED", None)
    client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    after = zero.get(case_id=case_id)
    assert "OWNERSHIP" in after.completed_stages
    assert after.status == "WAITING_FOR_REVIEW"
    assert target.calls == ["search"]
