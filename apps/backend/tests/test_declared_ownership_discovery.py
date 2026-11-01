"""D-112: a reviewed declaration plus official Marketplace Mock discovery, for any company.

A creator declares only the case root's own immediate owners (case-bound, document-bound).
A declared corporate holder with a verified UEN is then discovered through the same
official lookups as any issuer. Synthetic declarations; in-memory stores; zero real HTTP.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
import test_poc_ownership_acceptance as t
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_slice_b_registry_demo import confirm, start
from test_zero_touch_exception_remediation import successful

from app.persistence.composition import build_persistence_bundle

GARDEN_PDF = "garden-partnership-reviewed-client.pdf"
OPQ_PDF = "five-layer-marketplace-hybrid-client.pdf"
# Off for these tests only: the legacy Garden supplement must not supply anything.
NO_SUPPLEMENT = "app.connectors.registry_ownership.garden_official_evidence_is_eligible"

PARTIES = {
    "GARDEN": {
        "party_id": "GARDEN",
        "display_name": "GARDEN BUSINESS",
        "party_type": "LEGAL_ENTITY",
        "registration_number": "11111999A",
    },
    "SIMLIM": {
        "party_id": "SIMLIM",
        "display_name": "SIM LIM PTE. LTD.",
        "party_type": "LEGAL_ENTITY",
        "registration_number": "111111111M",
    },
    "ABC": {
        "party_id": "ABC",
        "display_name": "ABC COMPANY",
        "party_type": "LEGAL_ENTITY",
        "registration_number": "201688888A",
    },
    "LCH": {"party_id": "LCH", "display_name": "LIM CHOON HUAT", "party_type": "NATURAL_PERSON"},
}
GARDEN_LEVEL = [("GARDEN", "SIMLIM", "62.500000"), ("GARDEN", "LCH", "37.500000")]


def declare(client: Any, case_id: str, links: list[tuple[str, str, str]], *, root: str) -> Any:
    """The creator's case- and document-bound declaration of the given links only."""

    summary = t.summary_of(client, case_id)
    ownership = t.ownership_of(client, case_id)
    documents = successful(client.get(f"/api/onboarding/cases/{case_id}/documents"))
    [document] = [item for item in documents if not item["superseded_by_document_id"]]
    root_party = next(
        item for item in ownership["parties"] if item["party_id"] == ownership["root_party_id"]
    )
    ids = {root: root_party["party_id"]}
    used = {child for _, child, _ in links} | {parent for parent, _, _ in links}
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json={
            "root_registration_number": summary["case"]["entity"]["registration_number"],
            "evidence_document_id": document["document_id"],
            "evidence_document_version": len(document["events"]),
            "as_of_date": "2026-10-20",
            "rationale": None,
            "root_party_id": root_party["party_id"],
            "parties": [root_party, *(PARTIES[key] for key in sorted(used) if key != root)],
            "relationships": [
                {
                    "relationship_id": f"DECL-{index}",
                    "parent_party_id": ids.get(parent, parent),
                    "child_party_id": ids.get(child, child),
                    "ownership_percent": value,
                }
                for index, (parent, child, value) in enumerate(links, 1)
            ],
            "observed_document_versions": ownership["document_bindings"],
            "selected_observation_ids": [],
            "source_selection": "USER_SUPPLIED_DECLARATION",
            "expected_automation_version": summary["version"],
            "expected_ownership_version": ownership["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def onboard(fields: dict, pdf: str, transport: Any = None) -> tuple[Any, Any, str]:
    settings = t.lane(acra_marketplace_ownership_overlay="garden_legacy_supplement")
    bundle = build_persistence_bundle(settings)
    context = t.runtime(settings, bundle, transport or t.garden_transport())
    client = context.__enter__()
    return context, client, start(client, fields, pdf)["case"]["case_id"]


def facts(client: Any, case_id: str) -> dict[str, Any]:
    ownership = t.ownership_of(client, case_id)
    summary = t.summary_of(client, case_id)
    names = {item["party_id"]: item["display_name"] for item in ownership["parties"]}
    return {
        "ownership": ownership,
        "summary": summary,
        "edges": sorted(
            (
                names[edge["parent_party_id"]],
                names[edge["child_party_id"]],
                Decimal(edge["ownership_percent"]),
                edge["provenance"]["provider"],
            )
            for edge in ownership["relationships"]
        ),
        "ubo": {
            item["party"]["display_name"]: (
                Decimal(item["aggregated_ownership_percent"]),
                item["classification"],
                item["threshold_result"],
            )
            for item in ownership["candidates"]
        },
        "discovery": [
            (item["registration_number"], item["outcome"], item["reason_code"])
            for item in (ownership.get("discovery") or {}).get("records", [])
        ],
        "issues": [item["code"] for item in ownership["issues"]],
        "blockers": summary["clm"]["readiness"]["blockers"],
        "exceptions": [item["exception_type"] for item in summary["active_exceptions"]],
    }


SIM_LEVEL = [
    ("SIMLIM", "ABCD", "81.818182"),
    ("SIMLIM", "TWL", "9.090909"),
    ("SIMLIM", "EFGH", "9.090909"),
]
EXTRA_PARTIES = {
    "ABCD": {"party_id": "ABCD", "display_name": "ABCD123", "party_type": "NATURAL_PERSON"},
    "TWL": {"party_id": "TWL", "display_name": "TAN WEI LING", "party_type": "NATURAL_PERSON"},
    "EFGH": {"party_id": "EFGH", "display_name": "EFGH2345", "party_type": "NATURAL_PERSON"},
}
PARTIES.update(EXTRA_PARTIES)
EXPECTED_GARDEN = {
    "ABCD123": Decimal("51.13636375"),
    "LIM CHOON HUAT": Decimal("37.5"),
    "TAN WEI LING": Decimal("5.681818125"),
    "EFGH2345": Decimal("5.681818125"),
}


def single_class_transport() -> Any:
    """Labelled synthetic test evidence: SIM LIM's units, all one reported class."""

    from test_official_shareholder_evidence import SIM, holder, shareholders

    transport = t.garden_transport()
    transport.shareholders[SIM] = shareholders(
        [
            holder("SYN-FGH", "FGH SERVICES, INC.", "Corporate", 10000, "Withdrawn"),
            holder("SYN-ABCD", "ABCD123", "Individual", 900, "Active"),
            holder("SYN-TWL", "TAN WEI LING", "Individual", 100, "Active"),
            holder("SYN-EFGH", "EFGH2345", "Individual", 100, "Active"),
        ]
    )
    return transport


@pytest.fixture(autouse=True)
def no_supplement() -> Any:
    with patch(NO_SUPPLEMENT, return_value=False):
        yield


def test_a_declared_top_level_combines_with_official_downstream_rows() -> None:
    context, client, case_id = onboard(GARDEN_FIELDS, GARDEN_PDF, single_class_transport())
    response = declare(client, case_id, GARDEN_LEVEL, root="GARDEN")
    found = facts(client, case_id)
    context.__exit__(None, None, None)
    # Each link keeps its true source: the declaration above, official Mock rows below.
    assert found["edges"] == [
        ("GARDEN BUSINESS", "LIM CHOON HUAT", Decimal("37.5"), "MANUAL_DECLARATION_POC"),
        ("GARDEN BUSINESS", "SIM LIM PTE. LTD.", Decimal("62.5"), "MANUAL_DECLARATION_POC"),
        ("SIM LIM PTE. LTD.", "ABCD123", Decimal("81.818182"), "LOCAL_POC_ASSUMED_EQUAL_UNITS"),
        ("SIM LIM PTE. LTD.", "EFGH2345", Decimal("9.090909"), "LOCAL_POC_ASSUMED_EQUAL_UNITS"),
        ("SIM LIM PTE. LTD.", "TAN WEI LING", Decimal("9.090909"), "LOCAL_POC_ASSUMED_EQUAL_UNITS"),
    ]
    assert found["discovery"] == [
        ("111111111M", "PROVIDER_PARTIAL", "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS")
    ]
    # The original multiplication is reproduced without the supplement or a redeclaration.
    assert {name: value[0] for name, value in found["ubo"].items()} == EXPECTED_GARDEN
    # The downstream level rests on the equal-unit assumption, so review is retained:
    # no POC acceptance exists for a declared analysis (an owner policy decision).
    assert response.status_code == 409
    assert found["issues"] == ["OWNERSHIP_DENOMINATOR_REQUIRED"]
    assert all(value[1:] == ("REVIEW_REQUIRED", "INDETERMINATE") for value in found["ubo"].values())
    assert found["ownership"]["poc_basis_accepted"] is False
    assert found["blockers"] == ["OWNERSHIP_REVIEW_REQUIRED"]
    assert found["summary"]["case"].get("goldtier_result") is None


def test_observed_mixed_class_rows_are_never_pooled_below_a_declaration() -> None:
    # SIM LIM's observed Mock rows report Ordinary, Preference and Others (owner O2).
    context, client, case_id = onboard(GARDEN_FIELDS, GARDEN_PDF)
    declare(client, case_id, GARDEN_LEVEL, root="GARDEN")
    found = facts(client, case_id)
    context.__exit__(None, None, None)
    assert found["discovery"] == [
        ("111111111M", "PROVIDER_PARTIAL", "OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE")
    ]
    assert all(edge[3] == "MANUAL_DECLARATION_POC" for edge in found["edges"])
    assert "CORPORATE_OWNERSHIP_UNRESOLVED" in found["issues"]
    assert found["blockers"] == ["OWNERSHIP_REVIEW_REQUIRED"]


@pytest.mark.parametrize(
    ("links", "expected"),
    [
        (
            [("OPQ", "GARDEN", "100.000000")],
            [("11111999A", "PROVIDER_UNSUPPORTED", None)],
        ),
        (
            [("OPQ", "GARDEN", "50.000000"), ("OPQ", "ABC", "50.000000")],
            [
                ("11111999A", "PROVIDER_UNSUPPORTED", None),
                ("201688888A", "NOT_FOUND", "OFFICIAL_SHAREHOLDERS_EMPTY"),
            ],
        ),
    ],
    ids=["opq-100-garden", "opq-50-garden-50-abc"],
)
def test_opq_top_level_declarations_block_where_no_official_register_exists(
    links: list[tuple[str, str, str]], expected: list[tuple[Any, ...]]
) -> None:
    # Garden is a partnership with no official ownership register, and ABC's register is
    # a scenario-only business profile: nothing is borrowed from another onboarding.
    context, client, case_id = onboard(FIVE_LAYER_FIELDS, OPQ_PDF, single_class_transport())
    response = declare(client, case_id, links, root="OPQ")
    found = facts(client, case_id)
    context.__exit__(None, None, None)
    assert response.status_code == 409
    assert found["discovery"] == expected
    assert found["ubo"] == {}
    assert "CORPORATE_OWNERSHIP_UNRESOLVED" in found["issues"]
    assert found["blockers"] == ["OWNERSHIP_REVIEW_REQUIRED"]


@pytest.mark.parametrize(
    ("fields", "pdf", "links", "root", "expected"),
    [
        (GARDEN_FIELDS, GARDEN_PDF, [*GARDEN_LEVEL, *SIM_LEVEL], "GARDEN", EXPECTED_GARDEN),
        (
            FIVE_LAYER_FIELDS,
            OPQ_PDF,
            [("OPQ", "GARDEN", "100.000000"), *GARDEN_LEVEL, *SIM_LEVEL],
            "OPQ",
            EXPECTED_GARDEN,
        ),
    ],
    ids=["garden-full", "opq-100-full"],
)
def test_a_full_declaration_is_unchanged_and_only_a_confirmation_sends(
    fields: dict, pdf: str, links: list, root: str, expected: dict
) -> None:
    # A declared holder with declared owners is never rediscovered or duplicated.
    context, client, case_id = onboard(fields, pdf, single_class_transport())
    response = declare(client, case_id, links, root=root)
    found = facts(client, case_id)
    assert response.status_code == 200, response.text
    assert found["ownership"]["state"] == "ANALYZED"
    assert {edge[3] for edge in found["edges"]} == {"MANUAL_DECLARATION_POC"}
    assert found["discovery"] == []
    assert {name: value[0] for name, value in found["ubo"].items()} == expected
    assert found["blockers"] == []
    assert found["exceptions"] == ["TARGET_CONFIRMATION_REQUIRED"]
    assert found["summary"]["case"].get("goldtier_result") is None
    sent = confirm(client, found["summary"])
    context.__exit__(None, None, None)
    assert sent["status"] == "COMPLETED"


def test_a_found_holder_below_a_declaration_keeps_its_own_review_causes() -> None:
    """QG F1: official evidence discovered below a declaration is retained, never dropped.

    A declared root 100% -> a corporate holder whose official Mock register is FETCHED
    with single-class units 600/300/100 (the recursive-discovery units harness).
    """

    from datetime import UTC, date, datetime
    from uuid import uuid4

    from test_evidence_poc_discovery import UnitsRegistry
    from test_recursive_ownership_discovery import ROOT, Clock, Issuer, company, harness, person

    from app.domain.ownership import ManualOwnershipReviewReceipt

    holder = "300000001B"

    class Declaration:
        metadata = {"provider_name": "MANUAL_DECLARATION_POC", "environment": "LOCAL"}

        def __init__(self, root_party_id: str, root_name: str) -> None:
            self.root_party_id, self.root_name = root_party_id, root_name

        def load(self, request: object) -> dict[str, Any]:
            provenance = {
                "provider": "MANUAL_DECLARATION_POC",
                "environment": "LOCAL",
                "source_reference": "MANUAL_DOC_" + "a" * 32 + "_V1",
                "sourced_at": datetime(2026, 10, 30, tzinfo=UTC),
            }
            return {
                "root_party_id": self.root_party_id,
                "parties": [
                    {
                        "party_id": self.root_party_id,
                        "display_name": self.root_name,
                        "party_type": "LEGAL_ENTITY",
                        "registration_number": ROOT,
                    },
                    {
                        "party_id": "DECLARED_HOLDER",
                        "display_name": "SUB CO",
                        "party_type": "LEGAL_ENTITY",
                        "registration_number": holder,
                        "country": "SG",
                    },
                ],
                "relationships": [
                    {
                        "relationship_id": "DECL-1",
                        "parent_party_id": self.root_party_id,
                        "child_party_id": "DECLARED_HOLDER",
                        "ownership_percent": "100",
                        "provenance": provenance,
                    }
                ],
            }

    clock = Clock()
    issuers = {
        ROOT: Issuer("ROOT CO", (company(holder, "100"),)),
        holder: Issuer("SUB CO", (person("A", "600"), person("B", "300"), person("C", "100"))),
    }
    system = harness(UnitsRegistry(issuers, clock), clock=clock)
    case = system.onboarding.create_staged_case(ROOT)
    system.ownership.load(case_id=case.case_id)
    official = system.ownership.analyze(case_id=case.case_id)
    root = next(item for item in official.parties if item.party_id == official.root_party_id)
    receipt = ManualOwnershipReviewReceipt(
        case_id=case.case_id,
        actor_id="synthetic-reviewer",
        reviewed_at=datetime(2026, 10, 31, tzinfo=UTC),
        evidence_document_id=uuid4(),
        evidence_document_version=1,
        evidence_reference="MANUAL_DOC_" + "a" * 32 + "_V1",
        observed_document_versions=official.document_bindings,
        as_of_date=date(2026, 10, 20),
    )
    declared = system.ownership.replace_review_required_source(
        case_id=case.case_id,
        provider=Declaration(root.party_id, root.display_name),
        review_receipt=receipt,
        expected_version=official.version,
    )
    assert declared.discovery is not None
    assert [(item.registration_number, item.outcome) for item in declared.discovery.records] == [
        (holder, "FETCHED")
    ]
    # The found register's own units are retained with their official provenance...
    units = [item for item in declared.evidence if item.kind == "SHARE_UNITS"]
    assert len(units) == 3
    assert {(item.provider, item.environment) for item in units} == {
        ("ACRA_REGISTRY_ACQUISITION", "MOCK")
    }
    assert {edge.provenance.provider for edge in declared.relationships} == {
        "MANUAL_DECLARATION_POC",
        "LOCAL_POC_ASSUMED_EQUAL_UNITS",
    }
    # ...so the declared analysis stays in review like the official-only analysis of the
    # same register. (Its review cause is the units' unresolved status: the per-issuer POC
    # basis applies only to official-lane analyses, so no POC acceptance can follow.)
    assert "OWNERSHIP_DENOMINATOR_REQUIRED" in {issue.code for issue in official.issues}
    assert declared.state == "REVIEW_REQUIRED"
    assert {issue.code for issue in declared.issues} == {"UBO_REVIEW_REQUIRED"}
    assert all(item.classification != "PROVISIONAL_UBO_CANDIDATE" for item in declared.candidates)
    assert not system.ownership.poc_basis_accepted(declared)


def test_post_discovery_validation_admits_only_official_mock_additions() -> None:
    """QG F6: below a declaration, nothing but official Mock links and evidence passes."""

    from datetime import UTC, datetime

    from app.connectors.ownership import OwnershipProviderMetadata, OwnershipSourceResult
    from app.domain.ownership import OwnershipProvenance, OwnershipRelationship, Party
    from app.domain.ownership_evidence import OwnershipEvidence
    from app.services.ownership_analysis import OwnershipGraphError

    _, service = t.service_lane()
    metadata = OwnershipProviderMetadata(
        provider_name="MANUAL_DECLARATION_POC", environment="LOCAL"
    )
    at = datetime(2026, 11, 1, tzinfo=UTC)

    def source(provider: str, environment: str, evidence_env: str | None = None) -> Any:
        return OwnershipSourceResult(
            root_party_id="ROOT",
            parties=[
                Party(
                    party_id="ROOT",
                    display_name="Root",
                    party_type="LEGAL_ENTITY",
                    registration_number="11111999A",
                ),
                Party(party_id="P", display_name="Person", party_type="NATURAL_PERSON"),
            ],
            relationships=[
                OwnershipRelationship(
                    relationship_id="R1",
                    parent_party_id="ROOT",
                    child_party_id="P",
                    ownership_percent="100",
                    provenance=OwnershipProvenance(
                        provider=provider,
                        environment=environment,
                        source_reference="SYNTHETIC",
                        sourced_at=at,
                    ),
                )
            ],
            evidence=[]
            if evidence_env is None
            else [
                OwnershipEvidence.model_validate(
                    {
                        "evidence_id": "e-1",
                        "entity_identifier": "11111999A",
                        "party_id": "P",
                        "kind": "ROLE",
                        "raw_value": "DIRECTOR",
                        "source_operation": "OFFICERS",
                        "provider": "ACRA_REGISTRY_ACQUISITION",
                        "environment": evidence_env,
                        "retrieved_at": at,
                        "evidence_version": 1,
                    }
                )
            ],
        )

    for allowed in (
        source("ACRA_REGISTRY_ACQUISITION", "MOCK", "MOCK"),
        source("LOCAL_POC_ASSUMED_EQUAL_UNITS", "LOCAL"),
        source("MANUAL_DECLARATION_POC", "LOCAL"),
    ):
        service._validate_source(allowed, metadata, "11111999A", discovered_official=True)
    for refused in (
        source("LOCAL_SYNTHETIC_RELATIONSHIP", "LOCAL"),
        source("ACRA_REGISTRY_ACQUISITION", "SANDBOX"),
        source("ACRA_REGISTRY_ACQUISITION", "MOCK", "SANDBOX"),
    ):
        with pytest.raises(OwnershipGraphError):
            service._validate_source(refused, metadata, "11111999A", discovered_official=True)
    # Without the flag, an official-looking link under a declaration never passes.
    with pytest.raises(OwnershipGraphError):
        service._validate_source(source("ACRA_REGISTRY_ACQUISITION", "MOCK"), metadata, "11111999A")
