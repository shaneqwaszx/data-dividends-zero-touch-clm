"""D-081 / D-120: POC-assumed interests stay unsupported whatever replaces their analysis.

A POC-assumed link is an interest, not a pair of generated IDs, and its record is durable: the
same value for the same issuer or holder is refused as a manual declaration however the
parties are re-keyed and however many declarations came between. Selecting current document
observations is the evidence route, including when they equal the simulation, and no decision
clears the ledger. Synthetic rows, in-memory stores, offline protocol transport and Mock
GoldTier only.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import test_declared_ownership_discovery as d
import test_poc_ownership_acceptance as t
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from test_evidence_poc_discovery import UnitsRegistry
from test_official_shareholder_evidence import (
    POC_REFUSAL,
    SIM,
    gate_state,
    shareholders,
    snapshot_of,
)
from test_opq_garden_abc_scenario import EXPECTED, MULTI, transport
from test_recursive_ownership_discovery import ROOT, Clock, Issuer, company, harness, person
from test_slice_b_registry_demo import confirm, start
from test_zero_touch_exception_remediation import successful

from app.connectors.hybrid_ownership_overlay import POC_EQUAL_UNITS_PROVIDER
from app.connectors.ownership import OwnershipSourceResult
from app.domain.ownership import (
    POC_INTEREST_LEDGER_LIMIT,
    ManualOwnershipReviewReceipt,
    OwnershipBasis,
    OwnershipEnvironment,
    OwnershipPocInterest,
    OwnershipProvenance,
    OwnershipRelationship,
    OwnershipRelationshipType,
    Party,
)
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.ownership_analysis import (
    _known_poc_interests,
    _merged_poc_interests,
    _replays_poc_interest,
)
from app.services.ownership_errors import OwnershipRequestError
from app.services.ownership_repository import poc_ledger_preserved

OPQ_PDF = "five-layer-marketplace-hybrid-client.pdf"
AS_OF = "2026-10-20"
HOLDER_UEN = "300000001B"
CORRECTED = {"ABCD123": "70", "TAN WEI LING": "20", "EFGH2345": "10"}


class Lane:
    """One disposable in-memory hybrid case held for ownership review."""

    def __init__(self, client: Any, bundle: Any) -> None:
        self.client = client
        self.bundle = bundle
        self.case_id = self.new_case()

    def new_case(self) -> str:
        return start(self.client, FIVE_LAYER_FIELDS, OPQ_PDF)["case"]["case_id"]

    def ownership(self) -> dict[str, Any]:
        return t.ownership_of(self.client, self.case_id)

    def summary(self) -> dict[str, Any]:
        return t.summary_of(self.client, self.case_id)

    def documents(self, case_id: str | None = None) -> list[dict[str, Any]]:
        found = successful(
            self.client.get(f"/api/onboarding/cases/{case_id or self.case_id}/documents")
        )
        return [item for item in found if not item["superseded_by_document_id"]]

    def upload(self, text: str, case_id: str | None = None) -> dict[str, Any]:
        """A labelled synthetic evidence file, through the existing case intake."""

        return successful(
            self.client.post(
                f"/api/clm/zero-touch/cases/{case_id or self.case_id}/intake/documents",
                content=text.encode(),
                headers={"Content-Type": "text/plain", "X-Document-Name": "evidence.txt"},
            ),
            201,
        )

    def submit(self, parties: list[dict], relationships: list[dict], **update: Any) -> Any:
        summary, ownership = self.summary(), self.ownership()
        document = next(
            (item for item in self.documents() if item["ownership_observations"]),
            self.documents()[0],
        )
        return self.client.post(
            f"/api/clm/zero-touch/cases/{self.case_id}/manual-ownership-evidence",
            json={
                "root_registration_number": FIVE_LAYER_FIELDS["UEN"],
                "evidence_document_id": document["document_id"],
                "evidence_document_version": len(document["events"]),
                "as_of_date": AS_OF,
                "rationale": None,
                "root_party_id": ownership["root_party_id"],
                "parties": parties,
                "relationships": relationships,
                "observed_document_versions": ownership["document_bindings"],
                "selected_observation_ids": [],
                "source_selection": "USER_SUPPLIED_DECLARATION",
                "expected_automation_version": summary["version"],
                "expected_ownership_version": ownership["version"],
                "expected_case_event_count": len(summary["case"]["events"]),
                **update,
            },
        )

    def declare(
        self,
        *,
        percents: dict[str, str] | None = None,
        rekey: bool = False,
        rename: dict[str, str] | None = None,
        drop_registrations: bool = False,
        reregister: dict[str, str] | None = None,
        graph: dict[str, Any] | None = None,
    ) -> Any:
        """The held graph redeclared, optionally re-keyed or re-spelt; never new owners."""

        ownership = graph or self.ownership()
        root = ownership["root_party_id"]
        ids = {
            party["party_id"]: (
                f"NEW_{index}" if rekey and party["party_id"] != root else party["party_id"]
            )
            for index, party in enumerate(ownership["parties"])
        }
        names = {party["party_id"]: party["display_name"] for party in ownership["parties"]}
        parties = [
            {
                **party,
                "party_id": ids[party["party_id"]],
                "display_name": (rename or {}).get(party["display_name"], party["display_name"]),
                "registration_number": (
                    None
                    if drop_registrations and party["party_id"] != root
                    else (reregister or {}).get(
                        party["registration_number"], party["registration_number"]
                    )
                ),
            }
            for party in ownership["parties"]
        ]
        relationships = [
            {
                "relationship_id": f"DECLARED_{index}",
                "parent_party_id": ids[edge["parent_party_id"]],
                "child_party_id": ids[edge["child_party_id"]],
                "ownership_percent": (percents or {}).get(
                    names[edge["child_party_id"]], edge["ownership_percent"]
                ),
            }
            for index, edge in enumerate(ownership["relationships"])
        ]
        return self.submit(parties, relationships)

    def declare_root_links(self, graph: dict[str, Any]) -> Any:
        """Only the root's own links, leaving the rest of the original graph undeclared."""

        root = graph["root_party_id"]
        links = [edge for edge in graph["relationships"] if edge["parent_party_id"] == root]
        kept = {root, *(edge["child_party_id"] for edge in links)}
        return self.submit(
            [party for party in graph["parties"] if party["party_id"] in kept],
            [
                {
                    "relationship_id": f"SUBSET_{index}",
                    "parent_party_id": edge["parent_party_id"],
                    "child_party_id": edge["child_party_id"],
                    "ownership_percent": edge["ownership_percent"],
                }
                for index, edge in enumerate(links)
            ],
        )

    def observation_rows(
        self, percents: dict[str, str] | None = None, *, root_links_only: bool = False
    ) -> str:
        """Labelled rows for every held link, as a client's register would state them."""

        ownership = self.ownership()
        parties = {party["party_id"]: party for party in ownership["parties"]}
        labels = ("Legal Name", "UEN", "Country")
        lines = [f"{label}: {FIVE_LAYER_FIELDS[label]}" for label in labels]
        for edge in ownership["relationships"]:
            if root_links_only and edge["parent_party_id"] != ownership["root_party_id"]:
                continue
            owner = parties[edge["child_party_id"]]
            owned = parties[edge["parent_party_id"]]
            value = (percents or {}).get(owner["display_name"], edge["ownership_percent"])
            cells = [
                f"Shareholder: {owner['display_name']}",
                f"Type: {owner['party_type']}",
                f"Percentage: {value}%",
                f"Owned Entity: {owned['display_name']}",
                f"Owned Entity Registration Number: {owned['registration_number']}",
                f"As Of: {AS_OF}",
            ]
            if owner["registration_number"]:
                cells.insert(2, f"Registration Identifier: {owner['registration_number']}")
            lines.append(" | ".join(cells))
        return "\n".join(lines)

    def select_observations(self, *, rekey: bool = False, **update: Any) -> Any:
        """The creator's selection of every current observation, matched by the server."""

        ownership = self.ownership()
        observations = [
            item for doc in self.documents() for item in doc["ownership_observations"]
        ]
        root = ownership["root_party_id"]
        by_uen = {
            party["registration_number"]: party
            for party in ownership["parties"]
            if party["registration_number"]
        }
        by_name = {party["display_name"]: party for party in ownership["parties"]}
        ids = {
            party["party_id"]: (
                f"DOC_{index}" if rekey and party["party_id"] != root else party["party_id"]
            )
            for index, party in enumerate(ownership["parties"])
        }

        def owner_of(item: dict[str, Any]) -> dict[str, Any]:
            registration = item["owner_registration_identifier"]
            return by_uen[registration] if registration else by_name[item["owner_name"]]

        used = {root}
        for item in observations:
            used.add(owner_of(item)["party_id"])
            used.add(by_uen[item["owned_entity_registration_identifier"]]["party_id"])
        values: dict[str, Any] = {
            "source_selection": "DOCUMENT_OBSERVATIONS",
            "selected_observation_ids": [item["observation_id"] for item in observations],
            **update,
        }
        return self.submit(
            [
                {**party, "party_id": ids[party["party_id"]]}
                for party in ownership["parties"]
                if party["party_id"] in used
            ],
            [
                {
                    "relationship_id": f"DOCUMENT_EDGE_{index}",
                    "parent_party_id": ids[
                        by_uen[item["owned_entity_registration_identifier"]]["party_id"]
                    ],
                    "child_party_id": ids[owner_of(item)["party_id"]],
                    "ownership_percent": item["explicit_percentage"],
                }
                for index, item in enumerate(observations)
            ],
            **values,
        )

    def assert_unsent(self) -> None:
        summary = self.summary()
        assert summary["case"].get("goldtier_result") is None
        assert summary["clm"]["submission"] is None
        assert self.bundle.target_executions.list_for_case(UUID(self.case_id)) == ()


@pytest.fixture
def held() -> Iterator[Lane]:
    settings = t.lane(**MULTI)
    bundle = build_persistence_bundle(settings)
    with t.runtime(settings, bundle, transport()) as client:
        yield Lane(client, bundle)


def assert_refused_unchanged(lane: Lane, response: Any, before: dict, gate: tuple) -> None:
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == POC_REFUSAL
    assert lane.ownership() == before
    assert gate_state(lane.summary()) == gate
    lane.assert_unsent()


def ubos(ownership: dict[str, Any]) -> dict[str, Decimal]:
    return {
        item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
        for item in ownership["candidates"]
    }


def test_the_poc_links_are_present_on_the_held_case(held: Lane) -> None:
    ownership = held.ownership()
    assert POC_EQUAL_UNITS_PROVIDER in {
        edge["provenance"]["provider"] for edge in ownership["relationships"]
    }
    assert ownership["state"] == "REVIEW_REQUIRED"
    assert ubos(ownership) == EXPECTED
    assert "OWNERSHIP_REVIEW_REQUIRED" in held.summary()["clm"]["readiness"]["blockers"]


@pytest.mark.parametrize(
    "change",
    [
        {},
        {"rekey": True},
        {"rekey": True, "drop_registrations": True},
        {"rekey": True, "rename": {"ABCD123": "abcd-123", "SIM LIM PTE. LTD.": "Sim Lim Pte Ltd"}},
        {"rekey": True, "percents": {"ABCD123": "81.8181820"}},
        {"rekey": True, "reregister": {"111111111M": "111111111-M"}},
        {
            "rekey": True,
            "drop_registrations": True,
            "rename": {"SIM LIM PTE. LTD.": "SIM LIM PRIVATE LIMITED"},
        },
        {
            "rekey": True,
            "rename": {
                "TAN WEI LING": "WEI LING TAN",
                "ABCD123": "ABCD 123 HOLDER",
                "EFGH2345": "EFGH2345 NOMINEES",
            },
        },
        {
            "rekey": True,
            "rename": {"TAN WEI LING": "MS TAN WEI LING"},
            "percents": {"ABCD123": "80", "EFGH2345": "10.909091"},
        },
    ],
    ids=[
        "original-ids",
        "renamed-ids",
        "recreated-without-registrations",
        "recreated-with-respelt-names",
        "same-value-different-scale",
        "punctuated-registration",
        "issuer-renamed-registration-dropped",
        "every-holder-renamed",
        "one-holder-renamed-others-corrected",
    ],
)
def test_the_same_poc_interests_are_refused_under_any_party_ids(
    held: Lane, change: dict[str, Any]
) -> None:
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(**change), before, gate)


def test_a_single_replayed_poc_interest_is_refused_among_corrected_ones(held: Lane) -> None:
    before, gate = held.ownership(), gate_state(held.summary())
    response = held.declare(
        rekey=True, percents={"TAN WEI LING": "12.181818", "EFGH2345": "6.000000"}
    )
    assert_refused_unchanged(held, response, before, gate)


def test_an_intervening_declaration_does_not_erase_the_poc_lineage(held: Lane) -> None:
    held_graph = held.ownership()
    # A corrected declaration is a reviewed decision and stays allowed without a document.
    assert held.declare(rekey=True, percents=CORRECTED).status_code == 200
    # Its graph holds no POC link, but the values behind it are still the unsupported ones.
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(graph=held_graph), before, gate)
    assert_refused_unchanged(held, held.declare(graph=held_graph, rekey=True), before, gate)


def test_repeated_declarations_cannot_age_out_the_poc_interests(held: Lane) -> None:
    held_graph = held.ownership()
    for step in range(1, 8):
        corrected = {"ABCD123": str(70 + step), "TAN WEI LING": str(20 - step), "EFGH2345": "10"}
        assert held.declare(graph=held_graph, rekey=True, percents=corrected).status_code == 200
        before, gate = held.ownership(), gate_state(held.summary())
        assert_refused_unchanged(held, held.declare(graph=held_graph), before, gate)
        # The analysis history stays bounded; the protection no longer depends on it.
        assert len(before["prior_analyses"]) <= 4
    assert held_graph["analysis_id"] not in {
        item["analysis_id"] for item in held.ownership()["prior_analyses"]
    }
    held.assert_unsent()


def test_a_subset_of_the_original_links_leaves_the_rest_protected(held: Lane) -> None:
    held_graph = held.ownership()
    response = held.declare_root_links(held_graph)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED"
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(graph=held_graph, rekey=True), before, gate)


def test_replacing_a_holder_at_the_same_percentage_needs_evidence(held: Lane) -> None:
    before, gate = held.ownership(), gate_state(held.summary())
    response = held.declare(
        rekey=True,
        rename={"TAN WEI LING": "SOMEONE ELSE"},
        percents={"ABCD123": "80", "EFGH2345": "10.909091"},
    )
    assert_refused_unchanged(held, response, before, gate)


def test_a_company_with_no_registration_cannot_carry_a_poc_value(held: Lane) -> None:
    # Both sides renamed and the UEN dropped: identity is not established, so review it.
    before, gate = held.ownership(), gate_state(held.summary())
    response = held.declare(
        rekey=True,
        drop_registrations=True,
        rename={
            "SIM LIM PTE. LTD.": "UNRELATED HOLDINGS",
            "ABCD123": "PERSON ONE",
            "TAN WEI LING": "PERSON TWO",
            "EFGH2345": "PERSON THREE",
        },
    )
    assert_refused_unchanged(held, response, before, gate)


def test_a_document_stating_other_values_does_not_clear_the_poc_interests(held: Lane) -> None:
    held_graph = held.ownership()
    held.upload(held.observation_rows(CORRECTED))
    assert held.select_observations().status_code == 200
    # The only evidence on file contradicts the POC values, so they stay unsupported.
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(graph=held_graph), before, gate)
    assert_refused_unchanged(held, held.declare(graph=held_graph, rekey=True), before, gate)


def test_a_document_silent_on_the_poc_links_does_not_clear_them(held: Lane) -> None:
    held_graph = held.ownership()
    held.upload(held.observation_rows(root_links_only=True))
    # The partial graph is refused for review, yet still becomes the current analysis.
    partial = held.select_observations()
    assert partial.status_code == 409, partial.text
    assert partial.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED"
    assert held.ownership()["manual_review_receipt"]["source_selection"] == (
        "DOCUMENT_OBSERVATIONS"
    )
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(graph=held_graph), before, gate)


def test_a_corrected_declaration_stays_available_without_a_document(held: Lane) -> None:
    # D-081 restricts POC-derived values only; no upload becomes universally required.
    assert [item["ownership_observations"] for item in held.documents()] == [[]]
    response = held.declare(rekey=True, percents=CORRECTED)
    assert response.status_code == 200, response.text
    ownership = held.ownership()
    assert ownership["state"] == "ANALYZED"
    assert ownership["manual_review_receipt"]["source_selection"] == "USER_SUPPLIED_DECLARATION"
    held.assert_unsent()


@pytest.mark.parametrize("rekey", [False, True], ids=["current-ids", "new-ids"])
def test_evidence_equal_to_the_simulation_is_accepted_and_nothing_is_sent(
    held: Lane, rekey: bool
) -> None:
    held.upload(held.observation_rows())
    response = held.select_observations(rekey=rekey)
    assert response.status_code == 200, response.text
    ownership = held.ownership()
    receipt = ownership["manual_review_receipt"]
    assert (ownership["state"], receipt["source_selection"]) == (
        "ANALYZED",
        "DOCUMENT_OBSERVATIONS",
    )
    assert len(receipt["selected_observation_ids"]) == len(ownership["relationships"])
    assert receipt["observed_document_versions"] == ownership["document_bindings"]
    # The unchanged Decimal engine: the same totals, and every owned entity still totals 100.
    assert ubos(ownership) == EXPECTED
    summary = held.summary()
    assert summary["clm"]["readiness"]["blockers"] == []
    assert [item["exception_type"] for item in summary["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    # Only the explicit confirmation sends.
    held.assert_unsent()
    assert confirm(held.client, summary)["status"] == "COMPLETED"


def test_a_document_decision_clears_nothing_and_can_be_made_again(held: Lane) -> None:
    held.upload(held.observation_rows())
    assert held.select_observations().status_code == 200
    # The evidence supports the selection itself; it is not a licence to declare the values.
    before, gate = held.ownership(), gate_state(held.summary())
    assert_refused_unchanged(held, held.declare(rekey=True), before, gate)
    response = held.select_observations()
    assert response.status_code == 200, response.text
    assert held.ownership()["state"] == "ANALYZED"


def test_client_stated_evidence_keeps_its_manual_local_label(held: Lane) -> None:
    held.upload(held.observation_rows())
    assert held.select_observations().status_code == 200
    ownership = held.ownership()
    assert (ownership["provider_name"], ownership["provider_environment"]) == (
        "MANUAL_DECLARATION_POC",
        "LOCAL",
    )
    assert {edge["provenance"]["provider"] for edge in ownership["relationships"]} == {
        "MANUAL_DECLARATION_POC"
    }
    assert ownership["manual_review_receipt"]["source_type"] == "USER_SUPPLIED_DECLARATION"


def test_corrected_percentages_with_evidence_are_accepted(held: Lane) -> None:
    held.upload(held.observation_rows(CORRECTED))
    response = held.select_observations()
    assert response.status_code == 200, response.text
    ownership = held.ownership()
    assert ownership["state"] == "ANALYZED"
    values = ubos(ownership)
    assert values["ABCD123"] == Decimal("21.875")
    assert values["TAN WEI LING"] == Decimal("6.25")
    assert values["EFGH2345"] == Decimal("3.125")
    assert values["LIM CHOON HUAT"] == EXPECTED["LIM CHOON HUAT"]
    held.assert_unsent()


def test_another_cases_observations_and_document_are_refused(held: Lane) -> None:
    other = held.new_case()
    rows = held.observation_rows()
    foreign = held.upload(rows, other)
    foreign_ids = [
        item["observation_id"]
        for document in held.documents(other)
        for item in document["ownership_observations"]
    ]
    assert foreign_ids
    held.upload(rows)
    before, gate = held.ownership(), gate_state(held.summary())
    wrong_ids = held.select_observations(selected_observation_ids=foreign_ids)
    assert wrong_ids.status_code == 409, wrong_ids.text
    assert wrong_ids.json()["detail"] == {
        "code": "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
        "message": "Selected document observations are no longer current.",
    }
    wrong_document = held.select_observations(evidence_document_id=foreign["document_id"])
    assert wrong_document.status_code == 409, wrong_document.text
    assert wrong_document.json()["detail"]["code"] == "MANUAL_OWNERSHIP_DOCUMENT_NOT_FOUND"
    assert held.ownership() == before
    assert gate_state(held.summary()) == gate
    held.assert_unsent()


def test_stale_observation_bindings_are_refused(held: Lane) -> None:
    held.upload(held.observation_rows())
    before, gate = held.ownership(), gate_state(held.summary())
    [binding] = before["document_bindings"]
    stale = held.select_observations(
        observed_document_versions=[{**binding, "event_count": binding["event_count"] - 1}]
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"] == {
        "code": "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
        "message": "Current document ownership evidence changed before the decision.",
    }
    assert held.ownership() == before
    assert gate_state(held.summary()) == gate
    held.assert_unsent()


class Declaration:
    """A reviewed declaration at service level."""

    metadata = {"provider_name": "MANUAL_DECLARATION_POC", "environment": "LOCAL"}

    def __init__(self, root: Any, parties: list[dict], links: list[tuple[str, str, str]]) -> None:
        self.root, self.parties, self.links = root, parties, links

    def load(self, request: object) -> dict[str, Any]:
        provenance = {
            "provider": "MANUAL_DECLARATION_POC",
            "environment": "LOCAL",
            "source_reference": "MANUAL_DOC_" + "a" * 32 + "_V1",
            "sourced_at": datetime(2026, 10, 30, tzinfo=UTC),
        }
        return {
            "root_party_id": self.root.party_id,
            "parties": [self.root.model_dump(mode="json"), *self.parties],
            "relationships": [
                {
                    "relationship_id": f"DECLARED_{index}",
                    "parent_party_id": parent,
                    "child_party_id": child,
                    "ownership_percent": value,
                    "provenance": provenance,
                }
                for index, (parent, child, value) in enumerate(self.links)
            ],
        }


def person_party(name: str) -> dict[str, Any]:
    return {"party_id": f"DECLARED_{name}", "display_name": name, "party_type": "NATURAL_PERSON"}


def company_party(party_id: str, name: str, registration: str) -> dict[str, Any]:
    return {
        "party_id": party_id,
        "display_name": name,
        "party_type": "LEGAL_ENTITY",
        "registration_number": registration,
        "country": "SG",
    }


class Generic:
    """A generic official-lane case: POC links at the root and below its corporate holder."""

    def __init__(self, extra: dict[str, Issuer] | None = None, *, lone: bool = False) -> None:
        clock = Clock()
        owners = (company(HOLDER_UEN, "100"),) if lone else (
            company(HOLDER_UEN, "100"),
            person("Z", "100"),
        )
        issuers = {
            ROOT: Issuer("ROOT CO", owners),
            HOLDER_UEN: Issuer(
                "SUB CO", (person("A", "600"), person("B", "300"), person("C", "100"))
            ),
            **(extra or {}),
        }
        self.system = harness(UnitsRegistry(issuers, clock), clock=clock)
        self.case = self.system.onboarding.create_staged_case(ROOT)
        self.system.ownership.load(case_id=self.case.case_id)
        self.current = self.system.ownership.analyze(case_id=self.case.case_id)
        self.root = next(
            item for item in self.current.parties if item.party_id == self.current.root_party_id
        )

    def declare(self, parties: list[dict], links: list[tuple[str, str, str]]) -> None:
        self.current = self.system.ownership.replace_review_required_source(
            case_id=self.case.case_id,
            provider=Declaration(self.root, parties, links),
            review_receipt=ManualOwnershipReviewReceipt(
                case_id=self.case.case_id,
                actor_id="synthetic-reviewer",
                reviewed_at=datetime(2026, 10, 31, tzinfo=UTC),
                evidence_document_id=uuid4(),
                evidence_document_version=1,
                evidence_reference="MANUAL_DOC_" + "a" * 32 + "_V1",
                observed_document_versions=self.current.document_bindings,
                as_of_date=date(2026, 10, 20),
            ),
            expected_version=self.current.version,
        )

    def links(self, holder: str, first: str, second: str) -> list[tuple[str, str, str]]:
        return [
            (self.root.party_id, holder, first),
            (self.root.party_id, "DECLARED_Z", second),
            (holder, "DECLARED_A", "70"),
            (holder, "DECLARED_B", "25"),
            (holder, "DECLARED_C", "5"),
        ]

    def assert_root_replay_refused(self, holder: str = "DECLARED_SUB") -> None:
        people = [person_party(name) for name in "ZABC"]
        sub = company_party(holder, "SUB CO", HOLDER_UEN)
        with pytest.raises(OwnershipRequestError) as refused:
            self.declare([sub, *people], self.links(holder, "50", "50"))
        assert refused.value.code == POC_REFUSAL


def test_five_declarations_with_rekeyed_holders_cannot_age_out_the_source() -> None:
    case = Generic()
    sizes = []
    for step in range(1, 7):
        case.declare(
            [
                company_party(f"HOLDER_{step}", "SUB CO", HOLDER_UEN),
                {**person_party("Z"), "party_id": f"Z_{step}"},
            ],
            [
                (case.root.party_id, f"HOLDER_{step}", "60"),
                (case.root.party_id, f"Z_{step}", "40"),
            ],
        )
        assert case.current.poc_interest_ledger is not None
        sizes.append(len(case.current.poc_interest_ledger))
    assert len(case.current.prior_analyses) == 4
    case.assert_root_replay_refused("HOLDER_NEW")
    # Re-keyed links are the same interests, so the ledger does not grow with the IDs.
    assert len(set(sizes)) == 1


def test_more_than_four_distinct_declaration_sets_cannot_age_out_the_source() -> None:
    registrations = [f"30000000{index}C" for index in range(2, 8)]
    case = Generic(
        {
            item: Issuer(f"K{index} CO", (person(f"K{index}A", "700"), person(f"K{index}B", "300")))
            for index, item in enumerate(registrations)
        }
    )
    for index, item in enumerate(registrations):
        case.declare(
            [company_party(f"K_{index}", f"K{index} CO", item), person_party("Z")],
            [(case.root.party_id, f"K_{index}", "60"), (case.root.party_id, "DECLARED_Z", "40")],
        )
    assert len(case.current.prior_analyses) == 4
    case.assert_root_replay_refused()
    assert case.current.poc_interest_ledger is not None
    assert len(case.current.poc_interest_ledger) > 5


def test_a_later_subset_generation_keeps_the_source_interests() -> None:
    case = Generic()
    people = [person_party(name) for name in "ZABC"]
    sub = company_party("DECLARED_SUB", "SUB CO", HOLDER_UEN)
    case.declare(
        [sub, people[0]],
        [(case.root.party_id, "DECLARED_SUB", "60"), (case.root.party_id, "DECLARED_Z", "40")],
    )
    for _ in range(6):
        case.declare([sub, *people], case.links("DECLARED_SUB", "60", "40"))
    case.assert_root_replay_refused()


def test_a_lone_100_percent_holder_needs_evidence_or_a_correction() -> None:
    case = Generic(lone=True)
    sub = company_party("NEW_HOLDER", "SUB CO", HOLDER_UEN)
    with pytest.raises(OwnershipRequestError) as refused:
        case.declare([sub], [(case.root.party_id, "NEW_HOLDER", "100")])
    assert refused.value.code == POC_REFUSAL
    # A correction naming another owner is an ordinary declaration.
    case.declare(
        [sub, person_party("Z")],
        [(case.root.party_id, "NEW_HOLDER", "60"), (case.root.party_id, "DECLARED_Z", "40")],
    )


def test_an_interest_is_matched_by_either_side_and_by_registration() -> None:
    issuer = Party(
        party_id="ISSUER",
        display_name="SYNTHETIC ISSUER",
        party_type="LEGAL_ENTITY",
        registration_number="209900001A",
    )
    holder = Party(
        party_id="HOLDER",
        display_name="OLD NAME CO",
        party_type="LEGAL_ENTITY",
        registration_number="209900003C",
    )
    interest = OwnershipPocInterest(
        case_identity="209900001A",
        issuer=issuer,
        holder=holder,
        ownership_percent=Decimal("40"),
        provenance=OwnershipProvenance(
            provider=POC_EQUAL_UNITS_PROVIDER,
            environment=OwnershipEnvironment.LOCAL,
            source_reference="MANUAL_DOC_" + "a" * 32 + "_V1",
            sourced_at=datetime(2026, 10, 20, tzinfo=UTC),
        ),
        source_analysis_id=uuid4(),
    )

    def declared(root_uen: str, name: str, registration: str, percent: str = "40") -> Any:
        return OwnershipSourceResult(
            root_party_id="NEW_ROOT",
            parties=[
                Party(
                    party_id="NEW_ROOT",
                    display_name="UNRELATED ROOT",
                    party_type="LEGAL_ENTITY",
                    registration_number=root_uen,
                ),
                Party(
                    party_id="NEW_HOLDER",
                    display_name=name,
                    party_type="LEGAL_ENTITY",
                    registration_number=registration,
                ),
            ],
            relationships=[
                OwnershipRelationship(
                    relationship_id="DECLARED_1",
                    parent_party_id="NEW_ROOT",
                    child_party_id="NEW_HOLDER",
                    ownership_percent=Decimal(percent),
                    relationship_type=OwnershipRelationshipType.OWNERSHIP,
                    basis=OwnershipBasis.ECONOMIC_INTEREST,
                    provenance=OwnershipProvenance(
                        provider="MANUAL_DECLARATION_POC",
                        environment=OwnershipEnvironment.LOCAL,
                        source_reference="MANUAL_DOC_" + "a" * 32 + "_V1",
                        sourced_at=datetime(2026, 10, 20, tzinfo=UTC),
                    ),
                )
            ],
        )

    other = "209900004D"
    assert _replays_poc_interest(declared(other, "NEW NAME", "209900003-c"), (interest,))
    assert _replays_poc_interest(declared("209900001A", "NEW NAME", "209900005E"), (interest,))
    assert not _replays_poc_interest(declared(other, "NEW NAME", "209900005E"), (interest,))
    assert not _replays_poc_interest(
        declared("209900001A", "OLD NAME CO", "209900003C", "41"), (interest,)
    )


# --- Durability and compatibility ------------------------------------------------------


def codec() -> MongoCaseStore:
    return object.__new__(MongoCaseStore)


def case_with_history() -> Generic:
    case = Generic()
    people = [person_party(name) for name in "ZABC"]
    sub = company_party("DECLARED_SUB", "SUB CO", HOLDER_UEN)
    for _ in range(5):
        case.declare([sub, *people], case.links("DECLARED_SUB", "60", "40"))
    return case


def test_the_ledger_survives_the_case_envelope_and_stays_out_of_dumps() -> None:
    case = Generic()
    record = case.current
    assert record.poc_interest_ledger
    assert "poc_interest_ledger" not in record.model_dump()
    assert "poc_interest_ledger" not in repr(record)
    encoded = codec()._encode(snapshot_of(case.system.onboarding, record))  # noqa: SLF001
    assert encoded["schema_version"] == 19
    decoded = codec()._decode(encoded)  # noqa: SLF001
    assert decoded.ownership is not None
    assert decoded.ownership.poc_interest_ledger == record.poc_interest_ledger
    assert {item.provenance.provider for item in record.poc_interest_ledger} == {
        POC_EQUAL_UNITS_PROVIDER
    }


def test_the_browser_contract_does_not_gain_the_ledger(held: Lane) -> None:
    assert "poc_interest_ledger" not in held.ownership()


def legacy_envelope(case: Generic) -> dict[str, Any]:
    """The same case exactly as a schema-18 writer stored it."""

    encoded = codec()._encode(snapshot_of(case.system.onboarding, case.current))  # noqa: SLF001
    encoded["schema_version"] = 18
    encoded["ownership"].pop("poc_interest_ledger")
    return encoded


def test_a_schema_18_case_reads_without_a_ledger_and_is_not_rewritten() -> None:
    envelope = legacy_envelope(Generic())
    stored = deepcopy(envelope)
    decoded = codec()._decode(envelope)  # noqa: SLF001
    assert decoded.schema_version == 19
    assert decoded.ownership is not None and decoded.ownership.poc_interest_ledger is None
    assert envelope == stored


@pytest.mark.parametrize("value", [None, []], ids=["null", "empty"])
def test_a_schema_18_envelope_cannot_carry_the_ledger_key(value: Any) -> None:
    envelope = legacy_envelope(Generic())
    envelope["ownership"]["poc_interest_ledger"] = value
    with pytest.raises(PersistenceDataInvalidError):
        codec()._decode(envelope)  # noqa: SLF001


def test_a_missing_ledger_on_a_current_envelope_is_not_an_empty_one() -> None:
    case = Generic()
    encoded = codec()._encode(snapshot_of(case.system.onboarding, case.current))  # noqa: SLF001
    encoded["ownership"].pop("poc_interest_ledger")
    decoded = codec()._decode(encoded)  # noqa: SLF001
    assert decoded.ownership is not None
    assert decoded.ownership.poc_interest_ledger is None
    # An absent ledger is recovered from the history, never read as "no POC interests".
    assert _known_poc_interests(decoded.ownership) == case.current.poc_interest_ledger


def as_legacy(case: Generic) -> None:
    """The stored record as schema 18 left it; only a test may do this to a store."""

    stored = case.system.ownership._repository._records[case.case.case_id]  # noqa: SLF001
    legacy = stored.model_copy(update={"poc_interest_ledger": None}, deep=True)
    case.system.ownership._repository._records[case.case.case_id] = legacy  # noqa: SLF001
    case.current = legacy


def test_a_legacy_case_with_complete_history_is_still_protected_and_then_recorded() -> None:
    case = Generic()
    as_legacy(case)
    case.assert_root_replay_refused()
    # The first permitted decision records what the retained history established.
    people = [person_party(name) for name in "ZABC"]
    sub = company_party("DECLARED_SUB", "SUB CO", HOLDER_UEN)
    case.declare([sub, *people], case.links("DECLARED_SUB", "60", "40"))
    assert case.current.poc_interest_ledger
    case.assert_root_replay_refused()


def test_a_legacy_case_with_a_trimmed_history_requires_evidence() -> None:
    case = case_with_history()
    as_legacy(case)
    people = [person_party(name) for name in "ZABC"]
    sub = company_party("DECLARED_SUB", "SUB CO", HOLDER_UEN)
    # Even an ordinary correction, because the interests cannot be known. Nothing changes.
    with pytest.raises(OwnershipRequestError) as refused:
        case.declare([sub, *people], case.links("DECLARED_SUB", "61", "39"))
    assert refused.value.code == POC_REFUSAL
    assert "cannot be fully checked" in refused.value.public_message


def test_a_legacy_case_under_review_is_reestablished_by_an_evidence_upload(held: Lane) -> None:
    held_graph = held.ownership()
    rows = held.observation_rows()
    for _ in range(5):
        assert held.declare_root_links(held_graph).status_code == 409
    records = held.bundle.ownership._records  # noqa: SLF001
    case_id = UUID(held.case_id)
    records[case_id] = records[case_id].model_copy(
        update={"poc_interest_ledger": None}, deep=True
    )
    before, gate = held.ownership(), gate_state(held.summary())
    refused = held.declare(graph=held_graph, rekey=True, percents=CORRECTED)
    assert_refused_unchanged(held, refused, before, gate)
    assert "cannot be fully checked" in refused.json()["detail"]["message"]
    # The workflow offers an upload here; it reloads the source and restores certainty.
    assert any(
        action["target"] == "OWNERSHIP_UPLOAD"
        for item in held.summary()["interventions"]
        for action in item["evidence_actions"]
    )
    held.upload(rows)
    assert held.ownership()["provider_name"] == "ACRA_REGISTRY_ACQUISITION"
    assert held.declare(graph=held_graph, rekey=True).status_code == 409
    response = held.select_observations()
    assert response.status_code == 200, response.text
    held.assert_unsent()


def test_renaming_a_declared_issuer_does_not_grow_the_ledger() -> None:
    case = Generic()
    sizes = []
    for step in range(1, 9):
        case.declare(
            [company_party("RENAMED", f"SUB CO VARIANT {step}", HOLDER_UEN), person_party("Z")],
            [(case.root.party_id, "RENAMED", "60"), (case.root.party_id, "DECLARED_Z", "40")],
        )
        assert case.current.poc_interest_ledger is not None
        sizes.append(len(case.current.poc_interest_ledger))
    assert len(set(sizes)) == 1
    case.assert_root_replay_refused()


def test_the_ledger_stops_growing_at_its_limit_without_raising() -> None:
    case = Generic()
    entry = case.current.poc_interest_ledger[0]  # type: ignore[index]
    many = tuple(
        entry.model_copy(update={"ownership_percent": Decimal(index) / 10})
        for index in range(1, POC_INTEREST_LEDGER_LIMIT + 50)
    )
    merged = _merged_poc_interests((), many)
    assert merged == many[:POC_INTEREST_LEDGER_LIMIT]
    assert _merged_poc_interests(merged, many) == merged


def test_a_full_ledger_refuses_declarations_but_never_jams_the_case(
    held: Lane, monkeypatch: pytest.MonkeyPatch
) -> None:
    held_graph = held.ownership()
    rows = held.observation_rows()
    held.upload(rows)
    records = held.bundle.ownership._records  # noqa: SLF001
    ledger = records[UUID(held.case_id)].poc_interest_ledger
    assert ledger
    monkeypatch.setattr(
        "app.services.ownership_analysis.POC_INTEREST_LEDGER_LIMIT", len(ledger)
    )
    before, gate = held.ownership(), gate_state(held.summary())
    refused = held.declare(graph=held_graph, rekey=True, percents=CORRECTED)
    assert_refused_unchanged(held, refused, before, gate)
    assert "cannot be fully checked" in refused.json()["detail"]["message"]
    assert held.summary()["ownership_edit_authorized"] is True
    # The evidence route stays open, and the case ends terminal rather than loading.
    response = held.select_observations()
    assert response.status_code == 200, response.text
    assert held.ownership()["state"] == "ANALYZED"
    held.assert_unsent()


def test_a_ledger_that_fills_during_a_replacement_still_finishes_the_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extra = "300000009C"
    case = Generic({extra: Issuer("OTHER CO", (person("K1", "700"), person("K2", "300")))})
    assert case.current.poc_interest_ledger is not None
    monkeypatch.setattr(
        "app.services.ownership_analysis.POC_INTEREST_LEDGER_LIMIT",
        len(case.current.poc_interest_ledger) + 1,
    )
    # Discovery brings two new interests and only one fits: no exception, no stuck LOADING.
    case.declare(
        [company_party("OTHER", "OTHER CO", extra), person_party("Z")],
        [(case.root.party_id, "OTHER", "60"), (case.root.party_id, "DECLARED_Z", "40")],
    )
    assert case.current.state in {"ANALYZED", "REVIEW_REQUIRED"}
    case.assert_root_replay_refused()
    with pytest.raises(OwnershipRequestError) as refused:
        case.declare(
            [company_party("OTHER", "OTHER CO", extra), person_party("Z")],
            [(case.root.party_id, "OTHER", "61"), (case.root.party_id, "DECLARED_Z", "39")],
        )
    assert refused.value.code == POC_REFUSAL
    assert "cannot be fully checked" in refused.value.public_message


def interest(
    issuer: str = "ISSUER CO",
    issuer_uen: str | None = "209900001A",
    holder: str = "HOLDER ONE",
    holder_uen: str | None = None,
    percent: str = "40",
    case_identity: str = "209900009Z",
) -> OwnershipPocInterest:
    return OwnershipPocInterest(
        case_identity=case_identity,
        issuer=Party(
            party_id="I",
            display_name=issuer,
            party_type="LEGAL_ENTITY",
            registration_number=issuer_uen,
        ),
        holder=Party(
            party_id="H",
            display_name=holder,
            party_type="LEGAL_ENTITY" if holder_uen else "NATURAL_PERSON",
            registration_number=holder_uen,
        ),
        ownership_percent=Decimal(percent),
        provenance=OwnershipProvenance(
            provider=POC_EQUAL_UNITS_PROVIDER,
            environment=OwnershipEnvironment.LOCAL,
            source_reference="MANUAL_DOC_" + "a" * 32 + "_V1",
            sourced_at=datetime(2026, 10, 20, tzinfo=UTC),
        ),
        source_analysis_id=uuid4(),
    )


@pytest.mark.parametrize(
    "other",
    [
        {"issuer_uen": "209900002B"},
        {"issuer_uen": None},
        {"issuer": "OTHER CO", "issuer_uen": None},
        {"holder": "HOLDER TWO"},
        {"holder_uen": "209900003C"},
        {"percent": "41"},
        {"case_identity": "209900008Y"},
    ],
    ids=[
        "same-name-different-issuer-uen",
        "same-name-issuer-uen-missing",
        "different-name-issuer-uen-missing",
        "different-holder-name",
        "holder-registered-on-one-side-only",
        "different-percentage",
        "different-case-identity",
    ],
)
def test_entries_are_kept_unless_certainly_the_same_interest(other: dict[str, Any]) -> None:
    assert len(_merged_poc_interests((interest(),), (interest(**other),))) == 2


def test_a_shared_name_never_merges_registered_holders() -> None:
    first = interest(holder="SAME CO", holder_uen="209900003C")
    second = interest(holder="SAME CO", holder_uen="209900004D")
    assert len(_merged_poc_interests((first,), (second,))) == 2


@pytest.mark.parametrize(
    "other",
    [
        {"issuer": "RENAMED CO"},
        {"issuer_uen": "2099-00001a"},
        {"holder": "holder-one"},
    ],
    ids=["issuer-renamed-same-uen", "same-uen-respelt", "unregistered-holder-respelt"],
)
def test_entries_that_are_certainly_the_same_interest_merge(other: dict[str, Any]) -> None:
    assert len(_merged_poc_interests((interest(),), (interest(**other),))) == 1


def test_two_unregistered_issuers_compare_by_name() -> None:
    first = interest(issuer_uen=None)
    assert len(_merged_poc_interests((first,), (interest(issuer_uen=None),))) == 1
    assert len(_merged_poc_interests((first,), (interest("NEW CO", None),))) == 2


@pytest.mark.parametrize("misnamed", [True, False], ids=["borrowed-name", "honest-name"])
def test_a_second_company_cannot_be_hidden_behind_another_issuers_name(misnamed: bool) -> None:
    """QG F1, over HTTP: a real company's POC values must stay bound to its own UEN."""

    sister = "201688888A"
    protocol = d.single_class_transport()
    rows = protocol.shareholders[SIM]["entities"][0]["shareholders"]["individual"]
    protocol.shareholders[sister] = shareholders(rows, uen=sister)
    protocol.profiles[sister] = json.loads(json.dumps(protocol.profiles[SIM]).replace(SIM, sister))
    added = {
        "SISTER": {
            "party_id": "SISTER",
            "display_name": "SIM LIM PTE. LTD." if misnamed else "ABC COMPANY",
            "party_type": "LEGAL_ENTITY",
            "registration_number": sister,
        },
        "RENAMED": {
            "party_id": "RENAMED",
            "display_name": "RENAMED COMPANY",
            "party_type": "LEGAL_ENTITY",
            "registration_number": sister,
        },
        **{
            f"P{index}": {
                "party_id": f"P{index}",
                "display_name": f"PERSON {index}",
                "party_type": "NATURAL_PERSON",
            }
            for index in (1, 2, 3)
        },
    }
    with patch.dict(d.PARTIES, added), patch(d.NO_SUPPLEMENT, return_value=False):
        context, client, case_id = d.onboard(d.GARDEN_FIELDS, d.GARDEN_PDF, protocol)
        try:
            # SIM LIM's interests enter the ledger, then the sister company's under its UEN.
            d.declare(client, case_id, d.GARDEN_LEVEL, root="GARDEN")
            d.declare(
                client,
                case_id,
                [("GARDEN", "SISTER", "62.500000"), ("GARDEN", "LCH", "37.500000")],
                root="GARDEN",
            )
            ownership = t.ownership_of(client, case_id)
            parties = {item["party_id"]: item for item in ownership["parties"]}
            values = [
                edge["ownership_percent"]
                for edge in ownership["relationships"]
                if parties[edge["parent_party_id"]]["registration_number"] == sister
                and edge["provenance"]["provider"] == POC_EQUAL_UNITS_PROVIDER
            ]
            assert len(values) == 3
            before, summary = ownership, t.summary_of(client, case_id)
            response = d.declare(
                client,
                case_id,
                [
                    ("GARDEN", "RENAMED", "62.500000"),
                    ("GARDEN", "LCH", "37.500000"),
                    *(
                        ("RENAMED", f"P{index}", value)
                        for index, value in enumerate(values, 1)
                    ),
                ],
                root="GARDEN",
            )
            assert response.status_code == 409, response.text
            assert response.json()["detail"]["code"] == POC_REFUSAL
            assert t.ownership_of(client, case_id) == before
            assert gate_state(t.summary_of(client, case_id)) == gate_state(summary)
            assert summary["case"].get("goldtier_result") is None
        finally:
            context.__exit__(None, None, None)


def test_the_repository_refuses_to_shrink_or_drop_an_established_ledger() -> None:
    case = case_with_history()
    record = case.current
    ledger = record.poc_interest_ledger
    assert ledger
    grown = record.model_copy(update={"poc_interest_ledger": (*ledger, ledger[0])})
    assert poc_ledger_preserved(record, grown)
    for broken in (None, (), ledger[1:], tuple(reversed(ledger))):
        assert not poc_ledger_preserved(
            record, record.model_copy(update={"poc_interest_ledger": broken})
        )
    legacy = record.model_copy(update={"poc_interest_ledger": None})
    assert poc_ledger_preserved(legacy, record)
