"""C4 closeout (owner-approved 2026-11-19): OPQ PTE. LTD. (201511222D), the D-077 five-layer
Marketplace Mock root, is an approved synthetic company. Exactly that company; every other
company rule is unchanged."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.synthetic_eligibility import _company_problem, manifest
from tests.test_model_management import ME
from tests.test_synthetic_eligibility import GARDEN

OPQ = ("201511222D", "OPQ PTE. LTD.")


def opq_snapshot(**changes: Any) -> CaseSnapshot:
    summary, documents = copy.deepcopy(GARDEN)
    uen, name = changes.pop("identity", OPQ)
    case = summary["case"]
    case["requested_uen"] = changes.pop("requested", uen)
    entity = case.setdefault("entity", {})
    entity.update(registration_number=uen, legal_name=name)
    source = entity.setdefault("source", {})
    source.update(source_system="ACRA", environment=changes.pop("environment", "MOCK"))
    case.setdefault("registry_acquisition", {})["requested_identifier"] = changes.pop(
        "acquired", uen
    )
    assert not changes
    return CaseSnapshot(summary=summary, documents=documents, actor=ME)


def test_opq_is_registered_exactly_once_with_its_marketplace_mock_name() -> None:
    approved = manifest()
    assert OPQ in approved.companies
    assert [c for c in approved.companies if c[0] == OPQ[0]] == [OPQ]
    assert approved.environments == frozenset({"MOCK"})


def test_an_opq_case_from_acra_mock_passes_the_company_check() -> None:
    assert _company_problem(opq_snapshot(), manifest()) is False


@pytest.mark.parametrize(
    "changes",
    [
        {"identity": ("201511222D", "OPQ HOLDINGS PTE. LTD.")},
        {"identity": ("201511223D", "OPQ PTE. LTD.")},
        {"environment": "SANDBOX"},
        {"requested": "201511223D"},
        {"acquired": "201511223D"},
    ],
    ids=["other-name", "other-uen", "sandbox-registry", "requested-mismatch", "acquired-mismatch"],
)
def test_anything_but_the_exact_opq_mock_identity_is_still_refused(changes: dict[str, Any]) -> None:
    assert _company_problem(opq_snapshot(**changes), manifest()) is True
