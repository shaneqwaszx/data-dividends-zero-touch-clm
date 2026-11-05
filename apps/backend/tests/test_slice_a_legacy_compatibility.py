"""Slice A synthetic legacy conversion regressions; no retained databases."""

from copy import deepcopy
from typing import Any
from uuid import UUID, uuid4

import pytest
from s2_legacy_schema_fixtures import assert_retained_legacy_content, omit_session2_fields
from test_phase11_reconciliation import FieldOverrideIdp, attach, current_discrepancy
from test_phase12_persistence import _pending_automation_record, _provider_bound_snapshot
from test_zero_touch_orchestration import build_system, policy_rebind_snapshots, start_demo

from app.composition import build_onboarding_service
from app.config import Settings
from app.domain.access import TeamId
from app.domain.documents import DocumentFieldKey
from app.domain.policy import legacy_phase13_policy_snapshot
from app.domain.reconciliation import ReconciliationDecisionAction, ReconciliationField
from app.domain.target_submission import GoldTierProviderMode
from app.persistence.errors import PersistenceDataInvalidError, PersistenceSchemaUnsupportedError
from app.persistence.models import (
    DurableCaseSnapshot,
    DurableCaseSnapshotV7,
    LegacyOnboardingCaseV1,
    LegacyOnboardingCaseV2,
    LegacyOnboardingCaseV3,
    LegacyOnboardingCaseV6,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.policy_management import PolicyManagementService


def populated_v7_raw() -> dict[str, Any]:
    """Minimal genuine v7 shape with required persistence-only automation evidence."""
    case = build_onboarding_service(settings=Settings(_env_file=None)).create_staged_case(
        "202400001A"
    )
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=4,
        onboarding=case,
        automation=_pending_automation_record(case.case_id, updated_at=case.updated_at),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
    raw = object.__new__(MongoCaseStore)._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    return raw


def test_populated_v7_conversion_retains_required_excluded_binding() -> None:
    raw = populated_v7_raw()
    original = deepcopy(raw)
    legacy = DurableCaseSnapshotV7.model_validate(
        {key: value for key, value in raw.items() if key != "_id"}
    )
    assert legacy.automation is not None
    assert legacy.automation.ownership_provider_binding_id == "a" * 32
    assert "ownership_provider_binding_id" not in legacy.automation.model_dump()

    current = legacy.to_current()

    assert current.schema_version == 19
    assert current.automation is not None
    assert current.automation.ownership_provider_binding_id == "a" * 32
    assert raw == original


def historical_raw(version: int) -> dict[str, Any]:
    """Explicit version-specific absent fields, rather than fabricated newer evidence."""
    raw = populated_v7_raw()
    raw["schema_version"] = version
    omit_session2_fields(raw)
    onboarding = raw["onboarding"]
    historical_policy, _ = policy_rebind_snapshots()
    onboarding["policy_snapshot"] = historical_policy.model_dump(mode="json")
    if version <= 4:
        raw.pop("intelligence")
        onboarding["policy_snapshot"].pop("intelligence")
    if version <= 2:
        onboarding.pop("policy_snapshot")
    legacy_models = {
        1: LegacyOnboardingCaseV1,
        2: LegacyOnboardingCaseV2,
        3: LegacyOnboardingCaseV3,
        6: LegacyOnboardingCaseV6,
    }
    if version in legacy_models:
        allowed = legacy_models[version].model_fields
        for key in set(onboarding) - set(allowed):
            onboarding.pop(key)
    elif version <= 5:
        for key in (
            "initial_identity",
            "initial_target_search",
            "existing_target_state",
            "identity_corrections",
            "initial_target_search_attempts",
            "target_dispatch_confirmation",
            "policy_snapshot_revision",
            "policy_rebind_history",
        ):
            onboarding.pop(key)
    if version <= 5:
        automation = raw["automation"]
        automation.pop("stage_order_version")
        automation["completed_stages"].remove("GOLDTIER_SEARCH")
        automation["metrics"]["automated_stages_completed"] = 1
    return raw


class ReadOnlyCollection:
    """Ordinary store reads must never request a collection mutation."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = deepcopy(raw)

    def find_one(self, query: dict[str, Any]) -> dict[str, Any]:
        assert query == {"_id": self.raw["_id"]}
        return deepcopy(self.raw)


@pytest.mark.parametrize("version", range(1, 9))
def test_schema_matrix_preserves_history_without_active_policy_or_read_rewrite(
    version: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = historical_raw(version)
    original = deepcopy(raw)

    def forbid_active_policy(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Legacy read consulted ACTIVE policy")

    monkeypatch.setattr(PolicyManagementService, "case_snapshot", forbid_active_policy)
    store = object.__new__(MongoCaseStore)
    collection = ReadOnlyCollection(raw)
    store._collection = collection  # type: ignore[assignment]  # noqa: SLF001
    current = store.get(UUID(raw["case_id"]))

    assert current is not None
    assert current.schema_version == 19 and current.revision == raw["revision"]
    assert str(current.case_id) == raw["_id"]
    assert current.created_at.isoformat().replace("+00:00", "Z") == raw["created_at"]
    assert current.updated_at.isoformat().replace("+00:00", "Z") == raw["updated_at"]
    assert current.automation is not None
    assert (
        current.automation.ownership_provider_binding_id
        == raw["automation"]["ownership_provider_binding_id"]
    )
    policy = current.onboarding.policy_snapshot
    if version <= 2:
        assert policy == legacy_phase13_policy_snapshot(current.onboarding.created_at)
    else:
        assert str(policy.idp_review_confidence_threshold) == "0.81"
        assert str(policy.ubo_threshold_percent) == "27"
        assert policy.snapshot_label == "LEGACY_SG_TARGET_VALUES_V0"
        assert policy.goldtier_target is not None
        assert policy.goldtier_target.policy.value == "LEGACY_SINGAPORE"
    assert policy.registry is None and policy.evidence_classifier is None
    assert policy.policy_identity is None
    assert current.onboarding.identity_corrections == ()
    assert current.onboarding.initial_target_search_attempts == ()
    assert current.onboarding.target_dispatch_confirmation is None
    assert current.onboarding.policy_rebind_history == ()
    assert current.intelligence is None
    if version <= 4:
        assert policy.intelligence is None
    assert raw == original == collection.raw


def rich_v7_snapshot(scenario: str) -> DurableCaseSnapshot:
    """Frozen old policy plus populated domain evidence, including excluded fields."""
    legacy_policy, _ = policy_rebind_snapshots()
    client, zero, documents, _, _ = build_system(
        require_confirmation=scenario != "CONFIRMED",
        policy_snapshot_provider=lambda: legacy_policy,
    )
    if scenario == "IDENTITY":
        created_response = client.post(
            "/api/clm/zero-touch/cases",
            json={"uen": "202400001A", "legal_name": "MERLION CIRCULAR LABS PTE. LTD."},
        )
        assert created_response.status_code == 201
        before = created_response.json()
        case_id = UUID(before["case"]["case_id"])
        repaired = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
            json={
                "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                "registration_number": "202400001A",
                "country_of_incorporation": "SG",
                "expected_automation_version": before["version"],
                "expected_clm_version": before["clm"]["version"],
                "expected_case_event_count": len(before["case"]["events"]),
            },
        )
        assert repaired.status_code == 200
        attach(zero, case_id, FieldOverrideIdp({}))
    elif scenario == "RECONCILIATION":
        created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
        attach(
            zero,
            created.case_id,
            FieldOverrideIdp(
                {
                    DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD.",
                    DocumentFieldKey.REGISTERED_ADDRESS: "99 OTHER ROAD, 999999, SG",
                }
            ),
        )
        record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
        assert record is not None
        first = current_discrepancy(record, ReconciliationField.LEGAL_NAME)
        zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
            case_id=created.case_id,
            discrepancy_id=first.discrepancy_id,
            action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
            expected_version=record.version,
            evidence_fingerprint=first.evidence_fingerprint,
        )
        case_id = created.case_id
    else:
        result = start_demo(
            client,
            "STRAIGHT_THROUGH" if scenario in {"PENDING", "CONFIRMED"} else scenario,
            confirm_if_required=scenario == "CONFIRMED",
        )
        case_id = UUID(result["case"]["case_id"])
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    automation = zero._repository.get_for_case(case_id)  # noqa: SLF001
    clm = zero._clm.get(case_id=case_id)  # noqa: SLF001
    assert case is not None and automation is not None
    ledger = ()
    if clm is not None and clm.submission_snapshot is not None:
        entry = zero._cases.get_target_execution_entry(  # noqa: SLF001
            clm.submission_snapshot.target_input.submission_id
        )
        if entry is not None:
            ledger = (entry,)
    return DurableCaseSnapshot(
        case_id=case_id,
        revision=9,
        onboarding=case,
        documents=tuple(documents.list_documents(case_id=case_id)),
        ownership=zero._ownership.get(case_id=case_id),  # noqa: SLF001
        reconciliation=zero._reconciliation.get(case_id=case_id),  # noqa: SLF001
        clm=clm,
        automation=automation,
        target_executions=ledger,
        created_at=case.created_at,
        updated_at=automation.updated_at,
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "RECONCILIATION",
        "PENDING",
        "CONFIRMED",
        "OWNERSHIP_INCOMPLETE",
        "LOW_CONFIDENCE",
        "IDENTITY",
    ],
)
def test_actual_v7_preserves_populated_hidden_evidence_and_confirmation(scenario: str) -> None:
    snapshot = rich_v7_snapshot(scenario)
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    original = deepcopy(raw)
    legacy = DurableCaseSnapshotV7.model_validate(
        {key: value for key, value in raw.items() if key != "_id"}
    )
    current = codec._decode(raw)  # noqa: SLF001

    assert_retained_legacy_content(current, snapshot)
    assert raw == original
    rewritten = codec._encode(current)  # noqa: SLF001
    omit_session2_fields(rewritten)
    assert rewritten == {**original, "schema_version": 19}
    assert legacy.automation is not None and current.automation is not None
    assert current.automation.ownership_provider_binding_id
    assert current.automation.exceptions
    assert all(item.authoritative_evidence_digest for item in current.automation.exceptions)
    public = current.model_dump(mode="json")
    public_automation = public["automation"]
    assert "ownership_provider_binding_id" not in public_automation
    assert all(
        "authoritative_evidence_digest" not in item for item in public_automation["exceptions"]
    )
    reconciliation = current.reconciliation
    assert reconciliation is not None and reconciliation.evidence_fingerprint
    assert "evidence_fingerprint" not in public["reconciliation"]
    for field in reconciliation.fields:
        assert field.observations
        for observation in field.observations:
            assert "raw_value" not in observation.model_dump()
            assert "source_record_id" not in observation.model_dump()
    if scenario == "RECONCILIATION":
        assert reconciliation.discrepancies
        decisions = [item.decision for item in reconciliation.discrepancies if item.decision]
        assert decisions and all(item.evidence_fingerprint for item in decisions)
        assert any(
            observation.raw_value and observation.source_record_id
            for field in reconciliation.fields
            for observation in field.observations
        )
    if scenario == "CONFIRMED":
        assert current.onboarding.target_dispatch_confirmation is not None
        assert current.target_executions
    if scenario == "PENDING":
        assert current.onboarding.target_dispatch_confirmation is None
        assert current.automation.status == "WAITING_FOR_REVIEW"


@pytest.mark.parametrize("version", range(1, 9))
@pytest.mark.parametrize("fault", ["missing_binding", "unknown_nested", "cross_case", "uuid"])
def test_all_supported_versions_reject_corrupt_evidence_without_mutation(
    version: int, fault: str
) -> None:
    raw = historical_raw(version)
    if fault == "missing_binding":
        raw["automation"].pop("ownership_provider_binding_id")
    elif fault == "unknown_nested":
        raw["automation"]["metrics"]["untrusted_extra"] = True
    elif fault == "cross_case":
        raw["automation"]["case_id"] = str(uuid4())
    else:
        raw["_id"] = raw["_id"].replace("-", "")
    original = deepcopy(raw)
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001
    assert raw == original


@pytest.mark.parametrize("version", range(1, 8))
@pytest.mark.parametrize("parameter", ["registry", "evidence_classifier", "policy_identity"])
def test_old_envelopes_reject_phase24c_parameter_smuggling(version: int, parameter: str) -> None:
    raw = historical_raw(version)
    policy = raw["onboarding"].setdefault(
        "policy_snapshot",
        {
            "catalogue_version": 0,
            "idp_review_confidence_threshold": "0.85",
        },
    )
    policy[parameter] = {}
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("version", range(1, 8))
def test_old_envelopes_reject_semantic_v2_tag_even_when_nested(version: int) -> None:
    raw = historical_raw(version)
    raw["automation"]["rule_version"] = "ownership-semantic-rules-v2"
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("version", [None, True, "7", 7.0, 0, 20])
def test_invalid_schema_discriminators_fail_closed(version: object) -> None:
    raw = populated_v7_raw()
    raw["schema_version"] = version
    omit_session2_fields(raw)
    with pytest.raises((PersistenceDataInvalidError, PersistenceSchemaUnsupportedError)):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("version", [6, 7, 8])
def test_actual_envelopes_reject_forged_target_provider_binding(version: int) -> None:
    snapshot = _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.MOCK, execution_mode=GoldTierProviderMode.MOCK
    )
    raw = object.__new__(MongoCaseStore)._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = version
    omit_session2_fields(raw)
    if version == 6:
        allowed = LegacyOnboardingCaseV6.model_fields
        raw["onboarding"] = {
            key: value for key, value in raw["onboarding"].items() if key in allowed
        }
    raw["clm"]["submission_snapshot"]["target_input"]["provider_mode"] = "SANDBOX"
    raw["target_executions"][0]["submission_input"]["provider_mode"] = "SANDBOX"
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


def test_actual_v7_preserves_identity_corrections_search_and_pending_confirmation() -> None:
    snapshot = rich_v7_snapshot("IDENTITY")
    assert snapshot.onboarding.identity_corrections
    assert snapshot.onboarding.initial_target_search_attempts
    assert snapshot.onboarding.target_dispatch_confirmation is None
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    original = deepcopy(raw)
    current = codec._decode(raw)  # noqa: SLF001
    assert_retained_legacy_content(current, snapshot)
    assert raw == original


@pytest.mark.parametrize("missing", ["digest", "record", "discrepancy", "decision"])
def test_populated_v7_rejects_missing_mandatory_excluded_evidence(missing: str) -> None:
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(rich_v7_snapshot("RECONCILIATION"))  # noqa: SLF001
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    if missing == "digest":
        raw["automation"]["exceptions"][0].pop("authoritative_evidence_digest")
    elif missing == "record":
        raw["reconciliation"].pop("evidence_fingerprint")
    elif missing == "discrepancy":
        raw["reconciliation"]["discrepancies"][0].pop("evidence_fingerprint")
    else:
        decision = next(
            item["decision"]
            for item in raw["reconciliation"]["discrepancies"]
            if item["decision"] is not None
        )
        decision.pop("evidence_fingerprint")
    original = deepcopy(raw)
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(raw)  # noqa: SLF001
    assert raw == original


def test_actual_semantic_v2_tag_is_valid_in_v8_but_forbidden_in_v7() -> None:
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(rich_v7_snapshot("OWNERSHIP_INCOMPLETE"))  # noqa: SLF001
    raw["ownership"]["tagging"] = {
        "tags": [
            {
                "tag": "INSUFFICIENT_EVIDENCE",
                "evidence_ids": ["synthetic-one"],
                "reason_code": "SYNTHETIC_TEST",
                "rule_version": "ownership-semantic-rules-v2",
                "score": "0.70",
                "threshold": "0.60",
                "policy_version": 1,
                "reason_codes": ["SYNTHETIC_TEST"],
                "confidence": "0.9",
                "provider": "MOCK_OWNERSHIP",
                "environment": "MOCK",
                "case_version": 0,
                "evidence_version": 1,
            }
        ],
    }
    assert codec._decode(raw).ownership is not None  # noqa: SLF001
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(raw)  # noqa: SLF001


def test_missing_schema_discriminator_fails_closed() -> None:
    raw = populated_v7_raw()
    raw.pop("schema_version")
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001
