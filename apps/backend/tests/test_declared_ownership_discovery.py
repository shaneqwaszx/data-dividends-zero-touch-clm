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
