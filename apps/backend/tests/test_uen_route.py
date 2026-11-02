"""D-114: the UEN's own entity type picks the register (pure routing rule)."""

import pytest

from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.uen_route import UenRoute, route_change_message, route_uen


@pytest.mark.parametrize(
    ("uen", "route", "uen_format", "pq_code"),
    [
        ("11111999A", UenRoute.ACRA, "A", None),  # Format A: Garden business
        ("209990101A", UenRoute.ACRA, "B", None),  # Format B: Alpha local company
        ("T19PF1111A", UenRoute.ACRA, "C", "PF"),  # XYZ ACCOUNTING, Marketplace Mock
        ("T15LL1111W", UenRoute.ACRA, "C", "LL"),
        ("T17LP1111A", UenRoute.ACRA, "C", "LP"),
        ("T13FC1122A", UenRoute.ACRA, "C", "FC"),
        ("T99GB0105G", UenRoute.GOVERNMENT_REGISTER, "C", "GB"),  # Demo Parks
        ("T08GA0001A", UenRoute.GOVERNMENT_REGISTER, "C", "GA"),
        ("S99GB0105G", UenRoute.GOVERNMENT_REGISTER, "C", "GB"),
        ("T09SS0001B", UenRoute.UNSUPPORTED, "C", "SS"),
        ("T09GS0001B", UenRoute.UNSUPPORTED, "C", "GS"),
        ("T09DP0001B", UenRoute.UNSUPPORTED, "C", "DP"),
        ("T99FY0105G", UenRoute.UNSUPPORTED, "C", "FY"),  # the old made-up Demo Parks code
    ],
)
def test_every_row_of_the_routing_table(uen, route, uen_format, pq_code):
    assert is_eligible_singapore_uen(uen)
    decision = route_uen(uen)
    assert decision is not None
    assert (decision.route, decision.uen_format, decision.pq_code) == (route, uen_format, pq_code)
    assert decision.uen == uen and decision.rule_version == "UEN-ROUTE-1"


def test_descriptions_and_unsupported_type_names():
    assert route_uen("T99GB0105G").description == (  # type: ignore[union-attr]
        "Government body (statutory board, code GB) · checked against the government "
        "register, not ACRA"
    )
    assert route_uen("T19PF1111A").description == (  # type: ignore[union-attr]
        "Format C UEN (public accounting firm, code PF) · checked against ACRA"
    )
    assert route_uen("T09SS0001B").entity_type == "society"  # type: ignore[union-attr]
    assert route_uen("T99FY0105G").entity_type == "unlisted entity type, code FY"  # type: ignore[union-attr]


def test_not_a_singapore_uen_shape_has_no_route_and_input_is_normalized():
    assert route_uen("ABC") is None
    assert route_uen("") is None
    assert route_uen(" t99gb0105g ").route == UenRoute.GOVERNMENT_REGISTER  # type: ignore[union-attr]


def test_route_change_message_names_both_registers_and_the_type():
    acra, government = route_uen("209990101A"), route_uen("T99GB0105G")
    assert acra is not None and government is not None
    assert route_change_message(acra, government) == (
        "Route changed from ACRA to government register (UEN type GB)."
    )
    assert route_change_message(government, acra) == (
        "Route changed from government register to ACRA (UEN format B)."
    )
