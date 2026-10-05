"""Ordinary authenticated current-evidence review, separate from historical uncertainty."""

from uuid import UUID

import pytest
from scripts.zero_touch_happy_path_fixtures import COMPANIES
from test_target_classification_continuation import complete, create, runtime, save, upload


def conflict_case(client, *, segment_conflict=False):
    current = create(client)
    response = save(client, current)
    assert response.status_code == 200
    current = response.json()
    first_decision = current["target_classification"]["kyc_customer_type"]["selection"]
    upload(client, current, COMPANIES[0].target_profile)
    upload(
        client,
        current,
        {
            "KYC Customer Type": "Company - Private"
            if segment_conflict
            else "Partnership - Unregulated",
            "Client Segment": "DI - Government" if segment_conflict else "Corporate",
        },
    )
    return complete(client, current, 2), first_decision


def assert_no_freeze(client, bundle, current):
    cid = UUID(current["case"]["case_id"])
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


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_prior_user_two_current_trusted_documents_requires_review_before_freeze(mode):
    with runtime(provider_mode=mode) as (client, bundle, target, acra):
        current, _ = conflict_case(client)
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        nodes = {node["node_id"]: node for node in current["processing_pipeline"]}
        assert nodes["READINESS"]["status"] != "COMPLETE"
        assert nodes["GOLDTIER_TARGET"]["safe_result"] != "Prepared target plan retained"
        before = list(target.calls)
        assert_no_freeze(client, bundle, current)
        assert target.calls == before
        assert not any(call[0] != "GET" for call in target.calls)
        assert acra.calls == []


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
@pytest.mark.parametrize("segment_conflict", [False, True])
def test_fresh_same_value_review_binds_current_conflict_then_third_document_stales_it(
    mode, segment_conflict
):
    with runtime(provider_mode=mode) as (client, bundle, target, acra):
        current, old = conflict_case(client, segment_conflict=segment_conflict)
        classification = current["target_classification"]
        assert classification["evidence_state"] == "CONFLICT"
        assert not classification["current"]
        assert classification["review_required"]
        assert old["evidence_fingerprint"] != classification["evidence_fingerprint"]
        calls = list(target.calls)
        response = save(client, current)
        assert response.status_code == 200, response.json()
        reviewed = response.json()
        receipt = reviewed["target_classification"]["kyc_customer_type"]["selection"]
        assert receipt["source"] == "USER"
        assert receipt["actor_id"] == "maya-lim"
        assert receipt["classified_at"] > old["classified_at"]
        assert receipt["evidence_fingerprint"] == classification["evidence_fingerprint"]
        assert reviewed["target_classification"]["current"]
        assert reviewed["clm"]["readiness"]["blockers"] == []
        nodes = {node["node_id"]: node for node in reviewed["processing_pipeline"]}
        assert nodes["READINESS"]["status"] == nodes["GOLDTIER_TARGET"]["status"] == "COMPLETE"
        assert nodes["FINAL_REVIEW_SEND"]["status"] == "REVIEW_REQUIRED"
        cid = UUID(reviewed["case"]["case_id"])
        assert bundle.clm.get_for_case(cid).submission_snapshot is None
        assert bundle.target_executions.list_for_case(cid) == ()
        assert target.calls == calls
        # A new agreeing but relevant trusted document changes the reviewed evidence set.
        upload(client, reviewed, COMPANIES[0].target_profile)
        changed = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert not changed["target_classification"]["current"]
        assert (
            changed["target_classification"]["evidence_fingerprint"]
            != receipt["evidence_fingerprint"]
        )
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in changed["clm"]["readiness"]["blockers"]
        assert_no_freeze(client, bundle, changed)
        assert target.calls == calls
        # Even using fresh aggregate versions cannot save a browser's stale review token.
        changed["target_classification"]["evidence_fingerprint"] = receipt["evidence_fingerprint"]
        stale = save(client, changed)
        assert stale.status_code == 409
        assert target.calls == calls
        assert acra.calls == []


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_automatic_then_new_trusted_conflict_invalidates_automatic_choice(mode):
    with runtime(provider_mode=mode) as (client, bundle, target, _):
        current = create(client)
        upload(client, current, COMPANIES[0].target_profile)
        current = complete(client, current)
        prior = current["target_classification"]["kyc_customer_type"]["selection"]
        assert prior["source"] == "DOCUMENT"
        assert (
            prior["evidence_fingerprint"]
            == current["target_classification"]["evidence_fingerprint"]
        )
        calls = list(target.calls)
        upload(
            client,
            current,
            {"KYC Customer Type": "Partnership - Unregulated", "Client Segment": "Corporate"},
        )
        cid = UUID(current["case"]["case_id"])
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert current["target_classification"]["evidence_state"] == "CONFLICT"
        assert not current["target_classification"]["current"]
        assert current["target_classification"]["kyc_customer_type"]["selected_value"] is None
        assert_no_freeze(client, bundle, current)
        response = save(client, current)
        assert response.status_code == 200, response.json()
        assert response.json()["target_classification"]["current"]
        assert target.calls == calls


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_missing_evidence_is_not_conflict_and_current_unsafe_evidence_does_not_stale_user(mode):
    with runtime(provider_mode=mode) as (client, bundle, target, _):
        current = create(client)
        assert current["target_classification"]["evidence_state"] == "NO_EVIDENCE"
        current = save(client, current).json()
        fingerprint = current["target_classification"]["evidence_fingerprint"]
        upload(client, current, {"KYC Customer Type": "Individual", "Client Segment": "Corporate"})
        cid = UUID(current["case"]["case_id"])
        document = bundle.documents.list_for_case(cid)[0]
        document.classification_observations = tuple(
            obs.model_copy(update={"evidence_score": 0.1})
            for obs in document.classification_observations
        )
        bundle.documents.save(document)
        current = complete(client, current)
        assert current["target_classification"]["evidence_state"] == "UNSAFE"
        assert current["target_classification"]["evidence_fingerprint"] == fingerprint
        assert current["target_classification"]["current"]
        assert current["clm"]["readiness"]["blockers"] == []
        assert bundle.target_executions.list_for_case(cid) == ()
        assert all(call[0] == "GET" for call in target.calls)


def test_supersession_through_existing_document_owner_removes_conflict_and_can_auto_rebind():
    from test_zero_touch_database_happy_path import NoAcra, sandbox_settings

    from app.composition import build_onboarding_service
    from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
    from app.services.document_processing import DocumentProcessingService

    with runtime() as (client, bundle, target, _):
        current = create(client)
        upload(client, current, COMPANIES[0].target_profile)
        upload(
            client,
            current,
            {"KYC Customer Type": "Partnership - Unregulated", "Client Segment": "Corporate"},
        )
        current = complete(client, current, 2)
        cid = UUID(current["case"]["case_id"])
        assert current["target_classification"]["evidence_state"] == "CONFLICT"
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
        conflicting = next(
            doc
            for doc in bundle.documents.list_for_case(cid)
            if any(
                obs.value == "Partnership - Unregulated" for obs in doc.classification_observations
            )
        )
        text = "\n".join(
            f"{k}: {v}" for k, v in {**COMPANIES[0].fields, **COMPANIES[0].target_profile}.items()
        ).encode()
        replacement = documents.replace_document(
            case_id=cid,
            document_id=conflicting.document_id,
            expected_event_count=len(conflicting.events),
            display_name="fictional-replacement.txt",
            content_type="text/plain",
            content=text,
        )
        documents.auto_confirm_document(case_id=cid, document_id=replacement.document_id)
        assessed = documents.assess_target_classification(case_id=cid)
        assert assessed.state == "SAFE_CANDIDATE"
        assert len(assessed.candidates) == 2
        rebound = service.bind_goldtier_case_classification(
            case_id=cid,
            document_selections=assessed.candidates,
        )
        assert assessed.selections_are_current(rebound.target_classification_selections)
        assert len(bundle.documents.list_for_case(cid)) == 3
        assert not bundle.documents.get(conflicting.document_id).is_current_evidence
        assert all(call[0] == "GET" for call in target.calls)
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
@pytest.mark.parametrize(
    "variant",
    [
        "prior-user",
        "retained-document",
        "type-only",
        "segment-only",
        "out-of-scope",
        "low-score",
        "low-quality",
        "unknown-method",
    ],
)
def test_all_mode_adverse_currentness_and_local_compatible_resolution(mode, variant):
    from app.domain.documents import ExtractionMethod, ExtractionQuality

    with runtime(provider_mode=mode) as (client, bundle, target, _):
        current = create(client)
        if variant == "prior-user":
            current = save(client, current, "Partnership - Unregulated", "DI - Government").json()
        profile = {
            "type-only": {"KYC Customer Type": "Company - Private"},
            "segment-only": {"Client Segment": "Corporate"},
            "out-of-scope": {"KYC Customer Type": "Trust", "Client Segment": "Corporate"},
        }.get(variant, COMPANIES[0].target_profile)
        upload(client, current, profile)
        cid = UUID(current["case"]["case_id"])
        if variant in {"low-score", "low-quality", "unknown-method"}:
            doc = bundle.documents.list_for_case(cid)[0]
            update = {
                "low-score": {"evidence_score": 0.1},
                "low-quality": {"extraction_quality": ExtractionQuality.LOW},
                "unknown-method": {"extraction_method": ExtractionMethod.UNKNOWN},
            }[variant]
            doc.classification_observations = tuple(
                obs.model_copy(update=update) for obs in doc.classification_observations
            )
            bundle.documents.save(doc)
        current = complete(client, current)
        if variant == "retained-document":
            upload(
                client,
                current,
                {"KYC Customer Type": "Partnership - Unregulated", "Client Segment": "Corporate"},
            )
            current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        before = list(target.calls)
        assert_no_freeze(client, bundle, current)
        assert target.calls == before
        response = save(client, current)
        assert response.status_code == 200, response.json()
        reviewed = response.json()
        assert reviewed["clm"]["readiness"]["blockers"] == []
        assert reviewed["target_classification"]["current"]
        assert target.calls == before
        assert bundle.target_executions.list_for_case(cid) == ()


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_private_government_incompatible_label_can_be_reviewed_as_private(mode):
    with runtime(provider_mode=mode) as (client, bundle, target, _):
        current = create(client)
        upload(client, current, {"KYC Customer Type": "Government", "Client Segment": "Corporate"})
        current = complete(client, current)
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
        before = list(target.calls)
        response = save(client, current)
        assert response.status_code == 200, response.json()
        assert response.json()["target_classification"]["current"]
        assert response.json()["clm"]["readiness"]["blockers"] == []
        assert target.calls == before
        assert bundle.target_executions.list_for_case(UUID(current["case"]["case_id"])) == ()


@pytest.mark.parametrize("source", ["USER", "DOCUMENT"])
def test_earlier_schema10_missing_review_binding_stays_unknown_without_decode_mutation(source):
    from copy import deepcopy
    from datetime import UTC, datetime

    from app.persistence.models import DurableCaseSnapshot
    from app.persistence.mongo_case_store import MongoCaseStore

    with runtime() as (client, bundle, _, _):
        current = create(client)
        if source == "USER":
            current = save(client, current).json()
        upload(client, current, COMPANIES[0].target_profile)
        current = complete(client, current)
        if source == "USER":
            current = save(client, current).json()
        cid = UUID(current["case"]["case_id"])
        snapshot = DurableCaseSnapshot(
            case_id=cid,
            revision=0,
            onboarding=bundle.onboarding.get(cid),
            documents=tuple(bundle.documents.list_for_case(cid)),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store = object.__new__(MongoCaseStore)
        raw = store._encode(snapshot)
        for selection in raw["onboarding"]["target_classification_selections"]:
            selection.pop("evidence_fingerprint")
            selection.pop("actor_id")
        original = deepcopy(raw)
        restored = store._decode(raw)
        assert restored.schema_version == 10
        assert raw == original
        assert all(
            selection.evidence_fingerprint is None and selection.actor_id is None
            for selection in restored.onboarding.target_classification_selections
        )
        bundle.onboarding.save(restored.onboarding)
        current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert not current["target_classification"]["current"]
        assert "GOLDTIER_CLASSIFICATION_REQUIRED" in current["clm"]["readiness"]["blockers"]
