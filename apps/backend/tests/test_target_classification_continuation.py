"""Classification evidence, local preparation and real retained uncertainty."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures, require_safe_target
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import (
    NoAcra,
    RecordingTarget,
    prepare,
    sandbox_settings,
)

from app.composition import build_onboarding_service
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.clm import ClmSubmissionSnapshot, EvidenceReference, ProvisionalUboSummary
from app.domain.target_submission import GoldTierExecutionLedgerEntry, GoldTierExecutionLedgerState
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.document_processing import DocumentProcessingService


@contextmanager
def runtime(
    company=COMPANIES[0], target=None, *, provider_mode="sandbox", raise_server_exceptions=True
):
    settings = sandbox_settings(goldtier_connector_mode=provider_mode)
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    acra = NoAcra()
    target = target or RecordingTarget(company.name, company.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(
            create_app(settings, acra_connector=acra, goldtier_transport=target),
            raise_server_exceptions=raise_server_exceptions,
        ) as client,
    ):
        yield client, bundle, target, acra


def create(client, company=COMPANIES[0]):
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": company.uen, "legal_name": company.name, "country_of_incorporation": "SG"},
    )
    assert response.status_code == 201, response.json()
    return response.json()


def upload(client, current, profile, company=COMPANIES[0]):
    case_id = current["case"]["case_id"]
    text = "\n".join(
        f"{key}: {value}" for key, value in {**company.fields, **profile}.items()
    ).encode()
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        content=text,
        headers={"Content-Type": "text/plain", "X-Document-Name": "fictional-classification.txt"},
    )
    assert response.status_code == 201, response.json()
    return response.json()


def complete(client, current, count=1):
    response = client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/intake/complete",
        json={"expected_document_count": count},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def save(client, current, kyc="Company - Private", segment="Corporate"):
    return client.put(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/target-classification",
        json={
            "kyc_customer_type": kyc,
            "client_segment": segment,
            "expected_classification_evidence_fingerprint": current["target_classification"].get(
                "evidence_fingerprint"
            ),
            "expected_automation_version": current["version"],
            "expected_case_event_count": len(current["case"]["events"]),
        },
    )


@pytest.mark.parametrize("company", COMPANIES, ids=lambda c: c.code)
def test_auto_bound_evidence_ready_package_final_review_and_zero_attempts(company):
    with runtime(company) as (client, bundle, target, acra):
        current = prepare(client, company)
        cid = UUID(current["case"]["case_id"])
        nodes = {node["node_id"]: node for node in current["processing_pipeline"]}
        assert len(nodes) == 12
        assert nodes["READINESS"]["label"] == "Submission readiness"
        assert nodes["READINESS"]["status"] == nodes["GOLDTIER_TARGET"]["status"] == "COMPLETE"
        assert nodes["READINESS"]["blocker_code"] is None
        assert nodes["GOLDTIER_TARGET"]["safe_result"] == "Prepared target plan retained"
        assert nodes["FINAL_REVIEW_SEND"]["status"] == "REVIEW_REQUIRED"
        assert current["target_submission"]["state"] == "NOT_SUBMITTED"
        assert bundle.target_executions.list_for_case(cid) == ()
        assert [call[0] for call in target.calls] == ["GET"]
        assert acra.calls == []
        for key, value in [
            ("kyc_customer_type", company.kyc_customer_type),
            ("client_segment", company.client_segment),
        ]:
            field = current["target_classification"][key]
            assert field["selected_value"] == value
            assert field["authority"] == "PROJECT_DERIVED_POC"
            audit = field["selection"]
            assert audit["source"] == "DOCUMENT"
            assert (
                audit["policy_version"] == current["case"]["policy_snapshot"]["catalogue_version"]
            )
            assert audit["vocabulary_version"] == "GOLDTIER_OPENAPI_V1_0_0"
            evidence = audit["document_evidence"]
            doc = bundle.documents.get(UUID(evidence["document_id"]))
            assert evidence["document_version"] == doc.document_version == 1
            assert evidence["document_event_count"] == len(doc.events)
            assert evidence["page_number"] == 1
            assert evidence["source_reference"].startswith("PAGE_1_LINE_")
            assert evidence["evidence_score"] >= float(
                current["case"]["policy_snapshot"]["idp_review_confidence_threshold"]
            )
        before = list(target.calls)
        repeated = save(client, current, company.kyc_customer_type, company.client_segment)
        assert repeated.status_code == 200
        assert target.calls == before
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize(
    "profile,expected",
    [
        ({}, (None, None)),
        ({"KYC Customer Type": "Company - Private"}, ("Company - Private", None)),
        ({"Client Segment": "Corporate"}, (None, "Corporate")),
        ({"KYC Customer Type": "Trust", "Client Segment": "Corporate"}, (None, "Corporate")),
        ({"KYC Customer Type": "Individual", "Client Segment": "Corporate"}, (None, "Corporate")),
        ({"KYC Customer Type": "made-up", "Client Segment": "wrong"}, (None, None)),
    ],
)
def test_unsafe_or_partial_labels_retain_only_safe_fields_and_manual_is_local(profile, expected):
    with runtime() as (client, bundle, target, _):
        current = create(client)
        upload(client, current, profile)
        current = complete(client, current)
        fields = current["target_classification"]
        assert (
            fields["kyc_customer_type"]["selected_value"],
            fields["client_segment"]["selected_value"],
        ) == expected
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        before = list(target.calls)
        result = save(client, current)
        assert result.status_code == 200, result.json()
        current = result.json()
        assert [item["blocker_code"] for item in current["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert target.calls == before
        assert bundle.target_executions.list_for_case(UUID(current["case"]["case_id"])) == ()
        for key, value in zip(("kyc_customer_type", "client_segment"), expected, strict=True):
            assert current["target_classification"][key]["selection"]["source"] == (
                "DOCUMENT" if value else "USER"
            )


@pytest.mark.parametrize(
    "variant", ["low", "ambiguous", "conflicting-documents", "untrusted-identity"]
)
def test_uncertain_observations_never_choose_silently(variant):
    with runtime() as (client, bundle, target, _):
        current = create(client)
        upload(client, current, COMPANIES[0].target_profile)
        cid = UUID(current["case"]["case_id"])
        if variant == "conflicting-documents":
            upload(
                client,
                current,
                {"KYC Customer Type": "Government", "Client Segment": "DI - Government"},
            )
        else:
            doc = bundle.documents.list_for_case(cid)[0]
            if variant == "low":
                doc.classification_observations = tuple(
                    obs.model_copy(update={"evidence_score": 0.1})
                    for obs in doc.classification_observations
                )
            elif variant == "ambiguous":
                obs = doc.classification_observations[0]
                doc.classification_observations += (obs.model_copy(update={"value": "Government"}),)
            else:
                doc.fields[0].confidence = 0.1
            bundle.documents.save(doc)
        current = complete(client, current, 2 if variant == "conflicting-documents" else 1)
        assert current["target_classification"]["kyc_customer_type"]["selected_value"] is None
        assert [call[0] for call in target.calls] == ["GET"]
        assert bundle.target_executions.list_for_case(cid) == ()


def test_fixed_values_cannot_be_overridden_and_private_government_fallback_is_rejected():
    with runtime() as (client, bundle, target, _):
        current = create(client)
        upload(
            client,
            current,
            {
                "Policy": "Override",
                "Booking Entity": "Wrong",
                "Registration Type": "Wrong",
                "Customer External System": "Wrong",
            },
        )
        current = complete(client, current)
        values = current["case"]["policy_snapshot"]["goldtier_target"]
        assert {
            key: values[key]["value"]
            for key in ("customer_external_system", "registration_type", "policy", "booking_entity")
        } == {
            "customer_external_system": "DSD",
            "registration_type": "ACRA",
            "policy": "Singapore",
            "booking_entity": "ANZBGL (Singapore Branch)",
        }
        before = list(target.calls)
        response = save(client, current, "Government")
        assert response.status_code == 422
        assert "incompatible" in response.json()["detail"]["message"]
        assert target.calls == before


def test_stale_or_conflicting_automatic_evidence_blocks_final_send_without_mutation():
    with runtime() as (client, bundle, target, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        doc = bundle.documents.list_for_case(cid)[0]
        # A superseding current observation cannot leave the automatic receipt dispatchable.
        doc.superseded_by_document_id = uuid4()
        bundle.documents.save(doc)
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        before = list(target.calls)
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
                json={
                    "expected_automation_version": current["version"],
                    "expected_clm_version": current["clm"]["version"],
                    "expected_case_event_count": len(current["case"]["events"]),
                },
            ).status_code
            == 409
        )
        assert target.calls[: len(before)] == before
        assert all(
            call[0] == "GET" and call[1].endswith("/customers/search") for call in target.calls
        )
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize("operation", ["SHELL", "POLICY"])
def test_real_uncertain_attempt_is_frozen_operation_specific_and_never_replays(operation):
    class Uncertain(RecordingTarget):
        def request(self, method, url, **kwargs):
            suffix = "/create" if operation == "SHELL" else "/createPolicy"
            if method == "POST" and url.endswith(suffix):
                self.calls.append((method, suffix, {}))
                raise httpx.ReadTimeout("controlled fake transport uncertainty")
            return super().request(method, url, **kwargs)

    target = Uncertain(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, acra):
        current = prepare(client, COMPANIES[0])
        assert [call[0] for call in target.calls] == ["GET"]
        current = confirm(client, current)
        cid = UUID(current["case"]["case_id"])
        assert current["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
        assert current["target_submission"]["status_check_available"]
        assert not current["target_classification"]["editable"]
        nodes = {node["node_id"]: node for node in current["processing_pipeline"]}
        assert nodes["FINAL_REVIEW_SEND"]["status"] == "BLOCKED"
        uncertain = next(
            node
            for node in nodes["FINAL_REVIEW_SEND"]["children"]
            if node["operation"] == operation
        )
        assert (
            f"GoldTier {operation.title()} outcome is uncertain from an earlier submission attempt."
            == uncertain["safe_result"]
        )
        entries = bundle.target_executions.list_for_case(cid)
        assert len(entries) == 1 and entries[0].attempted_operations[-1] == operation
        before = list(target.calls)
        response = save(client, current)
        assert response.status_code == 409
        assert "frozen" in response.json()["detail"]["message"].lower()
        assert target.calls == before
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
                json={
                    "expected_automation_version": current["version"],
                    "expected_clm_version": current["clm"]["version"],
                    "expected_case_event_count": len(current["case"]["events"]),
                },
            ).status_code
            == 409
        )
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert current["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
        assert target.calls == before and acra.calls == []


def test_empty_retained_intent_is_not_projected_as_uncertain_mutation():
    with runtime() as (client, bundle, target, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        case = bundle.onboarding.get(cid)
        service = build_onboarding_service(
            settings=sandbox_settings(),
            acra_connector=NoAcra(),
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            goldtier_transport=target,
        )
        target_input = service.build_submission_input(
            case,
            submission_id=uuid4(),
            correlation_id=uuid4(),
            accepted_at=case.created_at,
            provider_mode=service.target_provider_mode,
        )
        own = bundle.ownership.get_for_case(cid)
        clm = bundle.clm.get_for_case(cid)
        clm.submission_snapshot = ClmSubmissionSnapshot(
            snapshot_id=uuid4(),
            target_input=target_input,
            document_references=(),
            ownership_reference=EvidenceReference(
                reference_id=own.analysis_id,
                version=own.version,
                status=own.state.value,
                updated_at=own.updated_at,
            ),
            provisional_ubo=ProvisionalUboSummary(
                candidate_count=2,
                internal_party_ids=tuple(item.party.party_id for item in own.candidates),
            ),
            created_at=datetime.now(UTC),
        )
        bundle.clm.save(clm, expected_version=clm.version)
        bundle.target_executions.create(
            GoldTierExecutionLedgerEntry(
                submission_input=target_input, state=GoldTierExecutionLedgerState.NOT_STARTED
            )
        )
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert current["target_submission"]["state"] == "NOT_SUBMITTED"
        assert [call[0] for call in target.calls] == ["GET"]
        assert save(client, current).status_code == 409


def test_government_document_classification_uses_existing_owners_without_share_graph():
    with runtime() as (client, bundle, target, _), patch(
        "app.connectors.local_ocr.TesseractOcrAdapter.recognize",
        side_effect=AssertionError("Native classification fixture must not invoke OCR"),
    ):
        current = create(client)
        cid = UUID(current["case"]["case_id"])
        case = bundle.onboarding.get(cid)
        case.requested_uen = GOVERNMENT.uen
        case.entity = case.entity.model_copy(
            update={
                "registration_number": GOVERNMENT.uen,
                "legal_name": GOVERNMENT.name,
                "party_type": "GOVERNMENT",
                "registered_address": case.entity.registered_address.model_copy(
                    update={
                        "address_line_1": GOVERNMENT.street,
                        "postal_code": GOVERNMENT.postal_code,
                    }
                ),
            }
        )
        case.registry_acquisition = None
        case.registry_evidence_binding = None
        case.initial_identity = None
        case.initial_target_search = None
        bundle.onboarding.save(case)
        service = build_onboarding_service(
            settings=sandbox_settings(),
            acra_connector=NoAcra(),
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            goldtier_transport=target,
        )
        documents = DocumentProcessingService(
            cases=service,
            idp=LocalPdfTextIdpProvider(),
            repository=bundle.documents,
            max_upload_bytes=1000000,
            review_confidence_threshold=0.85,
        )
        text = "\n".join(
            f"{key}: {value}"
            for key, value in {**GOVERNMENT.fields, **GOVERNMENT.target_profile}.items()
        ).encode()
        doc = documents.create_document(
            case_id=cid,
            display_name="fictional-government.txt",
            content_type="text/plain",
            content=text,
        )
        documents.auto_confirm_document(case_id=cid, document_id=doc.document_id)
        selections = documents.assess_target_classification(case_id=cid).candidates
        selected = service.bind_goldtier_case_classification(
            case_id=cid, document_selections=selections
        )
        assert {item.value for item in selected.target_classification_selections} == {
            "Government",
            "DI - Government",
        }
        assert GOVERNMENT.edges == GOVERNMENT.expected == ()
        assert selected.registry_acquisition is None
        assert bundle.ownership.get_for_case(cid) is None
        assert [call[0] for call in target.calls] == ["GET"]


@pytest.mark.parametrize(
    "explicit", ["target_classification_selections", "classification_observations"]
)
@pytest.mark.parametrize("value", [None, []])
def test_schema9_rejects_explicit_later_evidence_and_does_not_rewrite(explicit, value):
    with runtime() as (client, bundle, _, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        from app.persistence.models import DurableCaseSnapshot

        raw = MongoCaseStore._encode(
            object.__new__(MongoCaseStore),
            DurableCaseSnapshot(
                case_id=cid,
                revision=0,
                onboarding=bundle.onboarding.get(cid),
                documents=tuple(bundle.documents.list_for_case(cid)),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        )
        raw["schema_version"] = 9
        raw["onboarding"]["policy_snapshot"].pop("ownership_discovery")
        raw["onboarding"].pop("target_classification_selections")
        for doc in raw["documents"]:
            doc.pop("classification_observations")
        before = deepcopy(raw)
        decoded = object.__new__(MongoCaseStore)._decode(raw)
        assert raw == before and decoded.schema_version == 13
        assert decoded.onboarding.target_classification_selections == ()
        assert decoded.documents[0].classification_observations == ()
        if explicit == "target_classification_selections":
            raw["onboarding"][explicit] = value
        else:
            raw["documents"][0][explicit] = value
        from app.persistence.errors import PersistenceDataInvalidError

        with pytest.raises(PersistenceDataInvalidError):
            object.__new__(MongoCaseStore)._decode(raw)


def test_atlas_safe_database_format_is_32_bytes_and_old_long_name_refused():
    name = "clm_uat_" + "a" * 24
    assert len(name.encode()) == 32
    require_safe_target(name, app_env="test")
    for name in ("clm_uat_registry_" + "a" * 24, "clm_poc", "production", "clm_uat_" + "A" * 24):
        with pytest.raises(ValueError):
            require_safe_target(name, app_env="test")


@pytest.mark.parametrize("corruption", ["authority", "policy-version", "score", "exact-value"])
def test_current_selection_rejects_corrupt_source_and_policy_binding(corruption):
    from pydantic import ValidationError

    from app.domain.models import OnboardingCase

    with runtime() as (client, bundle, _, _):
        current = prepare(client, COMPANIES[0])
        raw = bundle.onboarding.get(UUID(current["case"]["case_id"])).model_dump(mode="json")
        selection = raw["target_classification_selections"][0]
        if corruption == "authority":
            raw["policy_snapshot"]["goldtier_target"]["kyc_customer_type"]["authority"] = (
                "USER_AUTHORIZED_POC"
            )
        elif corruption == "policy-version":
            selection["policy_version"] += 1
        elif corruption == "score":
            selection["document_evidence"]["evidence_score"] = 0.1
        else:
            selection["document_evidence"]["extracted_exact_value"] = "Government"
        with pytest.raises(ValidationError):
            OnboardingCase.model_validate(raw)


def test_test_mode_settings_factory_never_loads_owner_dotenv(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    with patch("app.config.Settings") as settings:
        get_settings()
        settings.assert_called_once_with(_env_file=None)
    get_settings.cache_clear()


def test_classification_page_reference_does_not_consume_preceding_blank_lines():
    from app.connectors.idp import IdpDocumentInput
    from app.domain.documents import DocumentProfile

    text = "\n\nKYC Customer Type: Company - Private\n\nClient Segment: Corporate\n"
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert {obs.field_key: obs.source_reference for obs in result.classification_observations} == {
        "kyc_customer_type": "PAGE_1_LINE_3",
        "client_segment": "PAGE_1_LINE_5",
    }


def test_fixed_policy_rebind_preserves_automatic_selection_receipts():
    from app.domain.models import OnboardingCase
    from app.domain.policy import PolicyAuthority

    with runtime() as (client, bundle, target, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        case = bundle.onboarding.get(cid)
        prior_receipts = case.target_classification_selections
        current_policy = case.policy_snapshot.model_copy(deep=True)
        target_policy = case.policy_snapshot.goldtier_target
        stale = target_policy.model_copy(
            update={
                "customer_external_system": target_policy.customer_external_system.model_copy(
                    update={"value": "STALE", "authority": PolicyAuthority.PROJECT_DERIVED_POC}
                )
            }
        )
        case.policy_snapshot = case.policy_snapshot.model_copy(update={"goldtier_target": stale})
        bundle.onboarding.save(OnboardingCase.model_validate(case))
        service = build_onboarding_service(
            settings=sandbox_settings(),
            policy_snapshot_provider=lambda: current_policy,
            acra_connector=NoAcra(),
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            goldtier_transport=target,
        )
        before = list(target.calls)
        rebound = service.rebind_case_policy_snapshot(
            case_id=cid,
            actor_id="synthetic-rm",
            rationale="Restore accepted system constant",
            expected_case_event_count=len(case.events),
        )
        assert rebound.policy_snapshot.goldtier_target.customer_external_system.value == "DSD"
        assert rebound.target_classification_selections == prior_receipts
        assert target.calls == before
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize("conflicting", [False, True])
def test_prior_user_selection_must_review_later_trusted_document_conflict(conflicting):
    with runtime() as (client, bundle, target, _):
        current = create(client)
        current = save(
            client,
            current,
            "Partnership - Unregulated" if conflicting else "Company - Private",
            "DI - Government" if conflicting else "Corporate",
        ).json()
        upload(client, current, COMPANIES[0].target_profile)
        current = complete(client, current)
        cid = UUID(current["case"]["case_id"])
        assert bundle.target_executions.list_for_case(cid) == ()
        assert [call[0] for call in target.calls] == ["GET"]
        # Owner follow-up supersedes R1's same-text compatibility: newly trusted
        # evidence requires a fresh review even when the earlier USER value agrees.
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        before = list(target.calls)
        resolved = save(client, current)
        assert resolved.status_code == 200, resolved.json()
        current = resolved.json()
        assert target.calls == before
        assert current["clm"]["readiness"]["blockers"] == []
        assert [e["blocker_code"] for e in current["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert (
            current["target_classification"]["kyc_customer_type"]["selection"]["source"] == "USER"
        )


def add_retained_classification_conflict(bundle, cid):
    doc = bundle.documents.list_for_case(cid)[0]
    original = doc.classification_observations[0]
    doc.classification_observations += (original.model_copy(update={"value": "Government"}),)
    bundle.documents.save(doc)


def test_retained_classification_conflict_blocks_snapshot_start_and_target_writes():
    with runtime() as (client, bundle, target, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        add_retained_classification_conflict(bundle, cid)
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        response = client.post(
            f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
        assert response.status_code == 409
        assert all(call[0] == "GET" for call in target.calls)
        assert bundle.target_executions.list_for_case(cid) == ()
        assert bundle.clm.get_for_case(cid).submission_snapshot is None
        assert bundle.onboarding.get(cid).target_dispatch_confirmation is None


def test_blocked_current_classification_cannot_project_prepared_or_final_send_review():
    with runtime() as (client, bundle, _, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        add_retained_classification_conflict(bundle, cid)
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        nodes = {node["node_id"]: node for node in current["processing_pipeline"]}
        assert nodes["READINESS"]["status"] == "REVIEW_REQUIRED"
        assert nodes["GOLDTIER_TARGET"]["status"] == "REVIEW_REQUIRED"
        assert nodes["GOLDTIER_TARGET"]["safe_result"] != "Prepared target plan retained"
        assert nodes["FINAL_REVIEW_SEND"]["status"] == "BLOCKED"
        assert nodes["FINAL_REVIEW_SEND"]["blocker_code"] == "GOLDTIER_CLASSIFICATION_REQUIRED"
        assert current["target_submission"]["state"] == "NOT_SUBMITTED"


def test_not_started_frozen_snapshot_requires_current_classification_observations():
    from decimal import Decimal

    from app.connectors.mock_ownership import MockOwnershipProvider
    from app.services.clm_orchestration import ClmOrchestrationService
    from app.services.ownership_analysis import OwnershipAnalysisService

    with runtime() as (client, bundle, target, _):
        current = prepare(client, COMPANIES[0])
        cid = UUID(current["case"]["case_id"])
        cases = build_onboarding_service(
            settings=sandbox_settings(),
            acra_connector=NoAcra(),
            repository=bundle.onboarding,
            target_execution_repository=bundle.target_executions,
            goldtier_transport=target,
        )
        documents = DocumentProcessingService(
            cases=cases,
            idp=LocalPdfTextIdpProvider(),
            repository=bundle.documents,
            max_upload_bytes=5 * 1024 * 1024,
            review_confidence_threshold=0.85,
        )
        ownership = OwnershipAnalysisService(
            cases=cases,
            provider=MockOwnershipProvider(),
            repository=bundle.ownership,
            threshold_percent=Decimal("25"),
            max_parties=100,
            max_relationships=200,
            max_depth=8,
            max_paths_per_candidate=64,
            max_total_paths=256,
        )
        clm = ClmOrchestrationService(
            cases=cases,
            documents=documents,
            ownership=ownership,
            repository=bundle.clm,
        )
        record = bundle.clm.get_for_case(cid)
        snapshot, _ = clm._build_snapshot(
            case=bundle.onboarding.get(cid),
            documents=bundle.documents.list_for_case(cid),
            ownership=bundle.ownership.get_for_case(cid),
            submission_plan=record.submission_plan,
        )
        record.submission_snapshot = snapshot
        assert clm._submission_snapshot_is_current(record)
        add_retained_classification_conflict(bundle, cid)
        assert not clm._submission_snapshot_is_current(record)
        assert [call[0] for call in target.calls] == ["GET"]
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize("source", ["DOCUMENT", "USER"])
def test_mock_retained_classification_currentness_blocks_readiness_and_freeze(source):
    with runtime(provider_mode="mock") as (client, bundle, _, _):
        if source == "DOCUMENT":
            current = prepare(client, COMPANIES[0])
            cid = UUID(current["case"]["case_id"])
            add_retained_classification_conflict(bundle, cid)
        else:
            current = create(client)
            selected = save(client, current, "Partnership - Unregulated", "DI - Government")
            assert selected.status_code == 200
            current = selected.json()
            upload(client, current, COMPANIES[0].target_profile)
            current = complete(client, current)
            cid = UUID(current["case"]["case_id"])
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        nodes = {node["node_id"]: node for node in current["processing_pipeline"]}
        assert nodes["READINESS"]["status"] != "COMPLETE"
        assert nodes["GOLDTIER_TARGET"]["safe_result"] != "Prepared target plan retained"
        response = client.post(
            f"/api/clm/zero-touch/cases/{cid}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
        assert response.status_code == 409
        assert bundle.clm.get_for_case(cid).submission_snapshot is None
        assert bundle.onboarding.get(cid).target_dispatch_confirmation is None
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize(
    "profile",
    [
        {"KYC Customer Type": "Company - Private"},
        {"KYC Customer Type": "Government", "Client Segment": "Corporate"},
        {},
    ],
)
def test_mock_explicit_partial_or_incompatible_input_reviews_but_legacy_stays_optional(profile):
    with runtime(provider_mode="mock") as (client, bundle, _, _):
        current = create(client)
        upload(client, current, profile)
        current = complete(client, current)
        if profile:
            assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        else:
            assert current["clm"]["readiness"]["blockers"] == []
            assert (
                bundle.onboarding.get(
                    UUID(current["case"]["case_id"])
                ).target_classification_selections
                == ()
            )
        assert bundle.target_executions.list_for_case(UUID(current["case"]["case_id"])) == ()


class InitialSearchInterruptedTarget(RecordingTarget):
    def request(self, method, url, **kwargs):
        result = super().request(method, url, **kwargs)
        if len(self.calls) == 1:
            raise httpx.ReadTimeout("Synthetic initial Search interruption")
        return result


def test_classification_review_routes_retained_failed_search_to_technical_failure():
    company = COMPANIES[0]
    target = InitialSearchInterruptedTarget(company.name, company.uen)
    with runtime(target=target) as (client, bundle, _, acra):
        current = create(client)
        upload(client, current, {})
        current = complete(client, current)
        cid = UUID(current["case"]["case_id"])
        assert current["status"] == "WAITING_FOR_REVIEW"
        assert [item["blocker_code"] for item in current["active_exceptions"]] == [
            "GOLDTIER_CLASSIFICATION_REQUIRED"
        ]
        checkpoint = current["clm"]["target_search_checkpoint"]
        assert checkpoint["disposition"] == "FAILED"
        assert [call[0] for call in target.calls] == ["GET"]

        reviewed = save(client, current)
        assert reviewed.status_code == 200
        retained = reviewed.json()
        assert retained["status"] == "TECHNICAL_FAILURE"
        assert retained["current_stage"] == "GOLDTIER_SEARCH"
        assert retained["active_exceptions"] == []
        assert retained["technical_failure"]["code"] == checkpoint["code"]
        assert retained["metrics"]["final_outcome"] == "TECHNICAL_FAILURE"
        assert retained["clm"]["target_search_checkpoint"] == checkpoint
        assert (
            retained["target_classification"]["kyc_customer_type"]["selected_value"]
            == "Company - Private"
        )
        assert retained["target_classification"]["client_segment"]["selected_value"] == "Corporate"
        assert retained["timeline"][-1]["event_type"] == "AUTOMATION_TECHNICAL_FAILURE"
        clm_record = bundle.clm.get_for_case(cid)
        assert clm_record is not None and clm_record.submission_snapshot is None
        persisted = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert persisted["status"] == "TECHNICAL_FAILURE"
        assert persisted["version"] == retained["version"]
        assert bundle.target_executions.list_for_case(cid) == ()
        assert [call[0] for call in target.calls] == ["GET"]
        assert acra.calls == []


def test_classification_advance_fault_projects_safe_503_without_target_replay():
    company = COMPANIES[0]
    target = InitialSearchInterruptedTarget(company.name, company.uen)
    with runtime(target=target, raise_server_exceptions=False) as (client, bundle, _, acra):
        current = create(client)
        upload(client, current, {})
        current = complete(client, current)
        cid = UUID(current["case"]["case_id"])
        assert current["status"] == "WAITING_FOR_REVIEW"
        checkpoint = current["clm"]["target_search_checkpoint"]
        assert checkpoint["disposition"] == "FAILED"
        with patch(
            "app.services.clm_orchestration.ClmOrchestrationService.evaluate",
            side_effect=RuntimeError("SYNTHETIC_ADVERSE_SENTINEL"),
        ):
            response = save(client, current)
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "ZERO_TOUCH_UNEXPECTED_FAILURE"
        assert detail["case_id"] == str(cid)
        assert set(detail) == {"code", "message", "case_id", "automation_id"}
        assert "SYNTHETIC_ADVERSE_SENTINEL" not in response.text
        persisted_response = client.get(f"/api/clm/zero-touch/cases/{cid}")
        assert persisted_response.status_code == 200
        persisted = persisted_response.json()
        assert persisted["status"] == "TECHNICAL_FAILURE"
        assert persisted["technical_failure"]["code"] == "ZERO_TOUCH_UNEXPECTED_FAILURE"
        assert persisted["metrics"]["final_outcome"] == "TECHNICAL_FAILURE"
        assert persisted["timeline"][-1]["event_type"] == "AUTOMATION_TECHNICAL_FAILURE"
        assert "SYNTHETIC_ADVERSE_SENTINEL" not in persisted_response.text
        assert persisted["clm"]["target_search_checkpoint"] == checkpoint
        assert (
            persisted["target_classification"]["kyc_customer_type"]["selected_value"]
            == "Company - Private"
        )
        assert persisted["target_classification"]["client_segment"]["selected_value"] == "Corporate"
        clm_record = bundle.clm.get_for_case(cid)
        assert clm_record is not None and clm_record.submission_snapshot is None
        assert bundle.target_executions.list_for_case(cid) == ()
        assert [call[0] for call in target.calls] == ["GET"]
        assert acra.calls == []
