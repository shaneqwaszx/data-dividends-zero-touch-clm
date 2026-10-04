"""Offline regressions for final ownership retention and acceptance-exit findings."""

import ast
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError
from scripts import run_s3_sandbox_acceptance as acceptance
from test_manual_ownership_evidence import CASE_ID, FIXED_TIME, Cases, make_case, make_document
from test_s2_ownership_intelligence import DocumentReader, service_for
from test_s2_persistence_security import decision_system as decision_system
from test_s2_persistence_security import logged_in
from test_zero_touch_orchestration import PDF

from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.services.manual_ownership_evidence import (
    ManualEconomicInterest,
    ManualOwnershipDeclaration,
    ManualOwnershipEvidenceProvider,
)


def current_declaration(case, document, current, *, as_of=None):
    return ManualOwnershipDeclaration(
        case_id=case.case_id,
        root_registration_number=case.requested_uen,
        evidence_document_id=document.document_id,
        evidence_document_version=len(document.events),
        source_selection="CURRENT_EVIDENCE",
        observed_document_versions=current.document_bindings,
        as_of_date=FIXED_TIME.date() if as_of is None else as_of,
        rationale="Retain the exact known graph without inferring absent ownership.",
        root_party_id=current.root_party_id,
        parties=tuple(current.parties),
        relationships=tuple(ManualEconomicInterest(
            relationship_id=edge.relationship_id,
            parent_party_id=edge.parent_party_id,
            child_party_id=edge.child_party_id,
            ownership_percent=edge.ownership_percent,
        ) for edge in current.relationships),
    )


@pytest.mark.parametrize("scenario", [
    MockOwnershipScenario.INDIRECT_OWNER,
    MockOwnershipScenario.MULTIPLE_PATHS,
    MockOwnershipScenario.BELOW_THRESHOLD,
])
def test_keep_partial_current_graph_preserves_edges_paths_and_history(scenario):
    case, document = make_case(), make_document()
    cases, documents = Cases(case), DocumentReader(document)
    service = service_for(cases, MockOwnershipProvider(scenario), documents)
    service.load(case_id=CASE_ID)
    current = service.analyze(case_id=CASE_ID)
    assert not current.issues
    declaration = current_declaration(case, document, current)
    provider = ManualOwnershipEvidenceProvider(
        declaration=declaration, reviewed_by_actor_id="rm-a", cases=cases,
        documents=documents, clock=lambda: FIXED_TIME,
    )
    retained = service.replace_review_required_source(
        case_id=CASE_ID, provider=provider, review_receipt=provider.review_receipt,
        expected_version=current.version,
    )
    assert retained.parties == current.parties
    assert [(e.parent_party_id, e.child_party_id, e.ownership_percent)
            for e in retained.relationships] == [
        (e.parent_party_id, e.child_party_id, e.ownership_percent) for e in current.relationships
    ]
    assert retained.candidates == current.candidates
    assert retained.prior_analyses[-1].relationships == tuple(current.relationships)
    assert retained.manual_review_receipt.source_selection == "CURRENT_EVIDENCE"
    for choice in ("USER_SUPPLIED_DECLARATION", "DOCUMENT_OBSERVATIONS"):
        values = declaration.model_dump()
        values["source_selection"] = choice
        with pytest.raises(ValidationError, match="must equal 100"):
            ManualOwnershipDeclaration.model_validate(values)


def test_keep_current_does_not_accept_overfull_parent_totals():
    case, document = make_case(), make_document()
    service = service_for(Cases(case), MockOwnershipProvider(MockOwnershipScenario.DIRECT_OWNER))
    service.load(case_id=CASE_ID)
    current = service.analyze(case_id=CASE_ID)
    values = current_declaration(case, document, current).model_dump()
    values["relationships"][0]["ownership_percent"] = "70"
    with pytest.raises(ValidationError, match="must not exceed 100"):
        ManualOwnershipDeclaration.model_validate(values)


@pytest.mark.parametrize("scenario", [
    MockOwnershipScenario.INDIRECT_OWNER, MockOwnershipScenario.MULTIPLE_PATHS,
])
@pytest.mark.parametrize("change", ["none", "percentage", "stale_version"])
def test_creator_api_retains_partial_current_graph_without_weakening_exactness(
    decision_system, scenario, change,
):
    application, _, zero, documents, target = decision_system
    zero._ownership._provider = MockOwnershipProvider(scenario)  # noqa: SLF001
    client, headers = logged_in(application, "maya-lim")
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"},
                          headers=headers)
    assert created.status_code == 201
    case_id = UUID(created.json()["case"]["case_id"])
    before = zero.attach_document(case_id=case_id, content=PDF,
                                  content_type="application/pdf", display_name="Synthetic.pdf")
    current = zero._ownership.get(case_id=case_id)  # noqa: SLF001
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    document = documents.list_documents(case_id=case_id)[0]
    declaration = current_declaration(case, document, current, as_of=zero._clock().date())  # noqa: SLF001
    payload = declaration.model_dump(mode="json")
    payload.pop("case_id")
    payload.pop("source_type")
    payload.update(expected_automation_version=before.version,
                   expected_ownership_version=current.version,
                   expected_case_event_count=len(case.events))
    if change == "percentage":
        payload["relationships"][0]["ownership_percent"] = "10"
    elif change == "stale_version":
        payload["expected_ownership_version"] -= 1
    calls = list(target.calls)
    result = client.post(f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
                         json=payload, headers=headers)
    assert target.calls == calls
    assert documents.list_documents(case_id=case_id) == [document]
    if change != "none":
        assert result.status_code == 409
        assert result.json()["detail"]["code"] == (
            "OWNERSHIP_SELECTED_SOURCE_MISMATCH" if change == "percentage"
            else "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE"
        )
        assert zero._ownership.get(case_id=case_id) == current  # noqa: SLF001
        assert zero.get(case_id=case_id) == before
    else:
        assert result.status_code == 200
        retained = zero._ownership.get(case_id=case_id)  # noqa: SLF001
        assert retained.candidates == current.candidates
        assert retained.manual_review_receipt.actor_id == "maya-lim"
        assert retained.manual_review_receipt.source_selection == "CURRENT_EVIDENCE"
        assert retained.prior_analyses[-1].relationships == tuple(current.relationships)
        assert zero._cases.get_case(case_id).target_dispatch_confirmation is None  # noqa: SLF001


def run_post_confirmation_proof(tmp_path, *, external, failure=None, final_status="COMPLETED"):
    """Execute the actual runner from its post-confirmation seam, without dispatch/setup.

    The AST retains baseline/restart checks, exception handlers, receipt and exit code.
    Only preparation, dispatch and the earlier human gate are outside this offline seam.
    """
    tree = ast.parse(Path(acceptance.__file__).read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "main")
    attempt = next(node for node in main.body if isinstance(node, ast.Try))
    context = attempt.body[0]
    assert isinstance(context, ast.With)
    retained_at = next(index for index, node in enumerate(context.body)
                       if "ATTEMPT_RETAINED" in ast.unparse(node))
    context.body = context.body[retained_at:]
    main.body = main.body[main.body.index(attempt):]
    main.name = "probe"
    compiled = compile(ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[])),
                       "offline-acceptance-post-confirmation", "exec")
    document, ownership = {"document_version": 1}, {"ownership_version": 5}
    counts = {"SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 1}
    guard = SimpleNamespace(case_id="synthetic-case", counts=counts, events=[],
                            preparation_diagnostics={}, mutations_stopped=False)
    final = {"status": final_status, "target_submission": {"state": "SUBMISSION_CONFIRMED"},
             "target_operations": [], "technical_failure": None}
    opened = 0

    class Client:
        def __init__(self, app):
            nonlocal opened
            opened += 1
            self.restart = opened == 2
            self.headers = {}

        def __enter__(self):
            if self.restart and failure == "restart_startup":
                raise RuntimeError("synthetic restart failure")
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            assert self.restart and url == "/api/auth/login"
            if failure == "restart_login":
                raise acceptance.AcceptanceBlocked("SYNTHETIC_LOGIN_FAILED")
            return response({"csrf_token": "synthetic-test-only"})

        def get(self, url):
            if not self.restart and failure == "baseline":
                raise acceptance.AcceptanceBlocked("SYNTHETIC_BASELINE_FAILED")
            if self.restart and failure == "restart_api":
                return SimpleNamespace(status_code=500)
            if url.endswith("/documents/synthetic-document"):
                return response({} if self.restart and failure == "document" else document)
            if url.endswith("/ownership"):
                return response({} if self.restart and failure == "ownership" else ownership)
            assert self.restart and url.endswith("/synthetic-case")
            if failure == "counts":
                guard.counts["SEARCH"] += 1
            return response(final)

    def response(body):
        return SimpleNamespace(status_code=200, json=lambda: deepcopy(body))

    receipt = {}
    namespace = dict(vars(acceptance), receipt=receipt,
                     args=SimpleNamespace(external=external, receipt=tmp_path / "receipt.json"),
                     settings=None, name="Synthetic", uen="202698761Z", credential="synthetic",
                     guard=guard, final=final, prepared={"document_id": "synthetic-document"},
                     TestClient=Client, create_app=lambda *args, **kwargs: object())
    exec(compiled, namespace)  # noqa: S102 - actual code, isolated no-provider test globals
    exit_code = namespace["probe"]()
    return exit_code, json.loads((tmp_path / "receipt.json").read_text())


@pytest.mark.parametrize("failure", [
    "baseline", "restart_startup", "restart_login", "restart_api",
    "document", "ownership", "counts",
])
def test_post_completion_proof_failure_never_returns_success(tmp_path, failure):
    code, receipt = run_post_confirmation_proof(tmp_path, external=True, failure=failure)
    assert receipt["final_status"] == "COMPLETED"
    assert receipt["phase"] == "BLOCKED"
    assert code != 0
    if failure in {"document", "ownership", "counts"}:
        assert receipt["safe_code"] == "PHYSICAL_RESTART_EVIDENCE_CHANGED"


@pytest.mark.parametrize("external", [False, True])
def test_only_completed_verified_acceptance_returns_zero(tmp_path, external):
    code, receipt = run_post_confirmation_proof(tmp_path, external=external)
    assert code == 0
    assert receipt["phase"] == "ACCEPTANCE_VERIFIED"
    if external:
        assert all(receipt["restart"][key] is True for key in (
            "provider_calls_unchanged", "document_evidence_retained", "ownership_evidence_retained",
        ))


@pytest.mark.parametrize("status", ["RECOVERY_PENDING", "FAILED", "WAITING_FOR_REVIEW"])
def test_incomplete_application_never_returns_success(tmp_path, status):
    code, _ = run_post_confirmation_proof(tmp_path, external=False, final_status=status)
    assert code != 0
