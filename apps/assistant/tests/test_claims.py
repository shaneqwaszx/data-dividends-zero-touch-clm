"""D-115 refinement 2: structured claim checks (ai_assistant/claims.py) on a held-out synthetic
ownership graph that no earlier copilot test uses.

GARDEN BUSINESS is held 50% by KESTREL HOLDINGS PTE. LTD., 20% by MERIDIAN CAPITAL PTE. LTD.,
5% by DANIEL KOH and 25% by WEI JIE CHEN. KESTREL is held 60% by AISHA RAHMAN and 40% by PRIYA
NAIR; MERIDIAN is held 100% by DANIEL KOH. So AISHA has 30% (MET), PRIYA 20% (NOT_MET; the same
20% as MERIDIAN's holding), DANIEL 5% + 20% = 25% (MET at the inclusive boundary, two paths),
WEI JIE 25% (MET at the boundary), and OMAR SAID could not be determined (review required).
"""

from __future__ import annotations

from typing import Any

import pytest

from ai_assistant import claims, copilot

ROOT = "GARDEN BUSINESS"
KESTREL, MERIDIAN = "KESTREL HOLDINGS PTE. LTD.", "MERIDIAN CAPITAL PTE. LTD."


def _path(links: list[tuple[str, str, str]], effective: str) -> dict[str, Any]:
    return {
        "path_id": "path-v1-" + "0" * 64,
        "edges": [
            {
                "relationship_id": f"rel-{i}",
                "parent_party_id": f"p-{h}",
                "parent_display_name": h,
                "child_party_id": f"p-{c}",
                "child_display_name": c,
                "ownership_percent": p,
            }
            for i, (h, c, p) in enumerate(links)
        ],
        "effective_ownership_percent": effective,
        "is_direct": len(links) == 1,
        "calculation": " x ".join(f"{p}%" for _, _, p in links) + f" = {effective}%",
    }


def _person(
    name: str, shares: tuple[str, str, str], result: str, kind: str, paths: list[Any]
) -> dict[str, Any]:
    return {
        "party": {"party_id": f"p-{name}", "display_name": name, "party_type": "NATURAL_PERSON"},
        "direct_ownership_percent": shares[0],
        "indirect_ownership_percent": shares[1],
        "aggregated_ownership_percent": shares[2],
        "threshold_percent": "25",
        "threshold_comparator": "GREATER_THAN_OR_EQUAL_TO",
        "threshold_result": result,
        "classification": kind,
        "paths": paths,
    }


HELD_OUT: dict[str, Any] = {
    "state": "REVIEW_REQUIRED",
    "provider_environment": "MOCK",
    "threshold_percent": "25.00",
    "threshold_comparator": "GREATER_THAN_OR_EQUAL_TO",
    "candidates": [
        _person("AISHA RAHMAN", ("0", "30", "30"), "MET", "PROVISIONAL_UBO_CANDIDATE",
                [_path([("AISHA RAHMAN", KESTREL, "60"), (KESTREL, ROOT, "50")], "30")]),
        _person("PRIYA NAIR", ("0", "20", "20"), "NOT_MET", "BELOW_PROVISIONAL_THRESHOLD",
                [_path([("PRIYA NAIR", KESTREL, "40"), (KESTREL, ROOT, "50")], "20")]),
        _person("DANIEL KOH", ("5", "20", "25"), "MET", "PROVISIONAL_UBO_CANDIDATE",
                [_path([("DANIEL KOH", ROOT, "5")], "5"),
                 _path([("DANIEL KOH", MERIDIAN, "100"), (MERIDIAN, ROOT, "20")], "20")]),
        _person("WEI JIE CHEN", ("25", "0", "25"), "MET", "PROVISIONAL_UBO_CANDIDATE",
                [_path([("WEI JIE CHEN", ROOT, "25")], "25")]),
        _person("OMAR SAID", ("0", "0", "0"), "INDETERMINATE", "REVIEW_REQUIRED", []),
    ],
    "issues": [{"code": "CYCLE_DETECTED", "message": "A loop between two holders was found."}],
    "manual_review_receipt": None,
}
FACTS = {
    "company": {"legal_name": ROOT, "uen": "11111999A"},
    "ownership": copilot.ownership_facts(HELD_OUT),
}


@pytest.mark.parametrize(
    "sentence",
    [
        "AISHA RAHMAN holds 60% of KESTREL HOLDINGS PTE. LTD., which holds 50% of GARDEN BUSINESS.",
        "Through Kestrel Holdings Pte Ltd, Aisha Rahman has an indirect interest of 30% in the "
        "company.",
        "MERIDIAN CAPITAL PTE. LTD. holds 20% of GARDEN BUSINESS, and DANIEL KOH owns 100% of "
        "MERIDIAN.",
        "GARDEN BUSINESS is 20% owned by MERIDIAN CAPITAL.",
        "DANIEL KOH holds 5% directly and 20% through MERIDIAN CAPITAL, 25% in total, which meets "
        "the inclusive 25% threshold.",
        "WEI JIE CHEN holds exactly 25% directly, so the application treats this as a "
        "provisional UBO candidate.",
        "PRIYA NAIR holds 40% of KESTREL, an indirect 20%, which is below the 25% threshold.",
        "PRIYA NAIR is not a UBO candidate because her 20% is below the threshold.",
        "AISHA RAHMAN and DANIEL KOH are provisional UBO candidates; PRIYA NAIR is below the "
        "threshold.",
        "The application lists AISHA RAHMAN, DANIEL KOH and WEI JIE CHEN as provisional UBO "
        "candidates.",
        "OMAR SAID needs a person's review before any conclusion.",
    ],
)
def test_correct_relationships_and_classifications_are_kept(sentence: str) -> None:
    check = copilot.check_answer(sentence, FACTS)
    assert (check.kept, check.left_out) == (1, []), check


@pytest.mark.parametrize(
    ("sentence", "reason"),
    [
        # P1: direction, party, percentage and path, each with figures that exist elsewhere.
        ("KESTREL HOLDINGS PTE. LTD. holds 60% of KESTREL HOLDINGS.", "unsupported_relationship"),
        ("KESTREL HOLDINGS holds 60% of AISHA RAHMAN.", "unsupported_relationship"),
        ("AISHA RAHMAN holds 50% of KESTREL HOLDINGS.", "unsupported_relationship"),
        ("MERIDIAN CAPITAL holds 50% of GARDEN BUSINESS.", "unsupported_relationship"),
        ("GARDEN BUSINESS is 60% owned by AISHA RAHMAN.", "unsupported_relationship"),
        ("PRIYA NAIR holds 20% of the company through MERIDIAN CAPITAL.",
         "unsupported_relationship"),
        ("DANIEL KOH holds 40% of KESTREL HOLDINGS.", "unsupported_relationship"),
        # P2: classifications against the application's result, in any sentence order.
        ("PRIYA NAIR is a provisional UBO candidate.", "ubo_contradicts_calculation"),
        ("PRIYA NAIR meets the threshold through KESTREL.", "ubo_contradicts_calculation"),
        ("DANIEL KOH is below the threshold.", "ubo_contradicts_calculation"),
        ("WEI JIE CHEN does not meet the 25% threshold.", "ubo_contradicts_calculation"),
        ("OMAR SAID qualifies as a provisional candidate.", "ubo_contradicts_calculation"),
        ("PRIYA NAIR and AISHA RAHMAN meet the threshold.", "ubo_contradicts_calculation"),
        ("The UBOs identified by the calculation for this case are AISHA RAHMAN and PRIYA NAIR.",
         "ubo_contradicts_calculation"),
        ("The UBOs, as the application calculated, appear to be AISHA RAHMAN and PRIYA NAIR.",
         "ubo_contradicts_calculation"),
        ("The UBOs are not just AISHA RAHMAN but PRIYA NAIR too.", "ubo_contradicts_calculation"),
    ],
)
def test_wrong_relationships_and_classifications_are_removed(sentence: str, reason: str) -> None:
    check = copilot.check_answer(sentence, FACTS)
    assert (check.kept, check.left_out) == (0, [reason]), check


@pytest.mark.parametrize(
    "sentence",
    [
        "No, the UBO has not been officially verified.",
        "The UBO has not been officially verified yet.",
        "Neither source automatically wins.",
        "Neither source automatically wins—this is a case-specific decision.",
        "The case remains blocked until ownership is confirmed.",
        "It cannot be acted on until ownership evidence is confirmed.",
        "It does not mean she is officially verified or approved.",
        "This is provisional; it is not a final KYC or regulatory approval.",
        "The check has not run in a live environment.",
    ],
)
def test_negated_and_conditional_statements_are_kept(sentence: str) -> None:
    check = copilot.check_answer(sentence, FACTS)
    assert (check.kept, check.left_out) == (1, []), check


@pytest.mark.parametrize(
    "sentence",
    [
        # Earlier reviews' bypasses: the ending says the claim is true now.
        "The UBO had not been officially verified until today.",
        "The UBO had never been officially verified before this week.",
        "Ownership had not been legally confirmed until compliance signed off yesterday.",
        "The UBO has not been officially verified by anyone but compliance.",
        "The record had never been officially approved before today.",
        # A positive claim beside a negated one, or a time word, keeps the sentence out.
        "The UBO has not been verified; the UBO, by the way, is confirmed.",
        "The UBO is not verified, it is officially approved.",
        "The UBO has not been verified and is officially approved.",
        "Neither source automatically wins, but the registry now overrides the document.",
        "The case remains blocked until ownership is confirmed, which happened yesterday.",
        "The UBO has not been officially verified (UEN 99999999Z).",
        "The UBO is officially verified.",
        "The case is connected to the live ACRA registry.",
    ],
)
def test_misleading_negations_and_positive_claims_are_still_removed(sentence: str) -> None:
    assert copilot.check_answer(sentence, FACTS).kept == 0, sentence


def test_without_ownership_facts_no_relationship_is_judged() -> None:
    facts = {"company": FACTS["company"], "ownership": copilot.ownership_facts(None)}
    graph = claims.OwnershipGraph(facts["ownership"], ROOT)
    assert graph.empty
    assert claims.relationship_problem("AISHA RAHMAN holds 60% of KESTREL.", graph) is None


def test_names_are_matched_exactly_after_presentation_is_set_aside() -> None:
    graph = claims.OwnershipGraph(FACTS["ownership"], ROOT)
    found = [m.key for m in graph.mentions("Kestrel Holdings Private Limited and the company")]
    assert found == ["KESTREL HOLDINGS PTE LTD", "GARDEN BUSINESS"]
    # A different full name is not KESTREL HOLDINGS: only its unique first word is matched,
    # and the name check leaves the sentence out.
    assert [m.end for m in graph.mentions("KESTREL HOLDING PTE LTD")] == [len("KESTREL")]
    check = copilot.check_answer("KESTREL HOLDING PTE LTD holds 50% of GARDEN BUSINESS.", FACTS)
    assert check.left_out == ["unsupported_name"]
    assert claims.canonical_name("Lim Choon Huat's") == "LIM CHOON HUAT"


# Found in real ministral-3:8b answers on the held-out case (refinement 2 evaluation).
@pytest.mark.parametrize(
    "sentence",
    [
        "No, Priya Nair does not count as a provisional UBO in this case.",
        "Omar Said is not a UBO candidate because the application could not determine his "
        "ownership.",
        "Aisha Rahman holds 30% indirectly (60% of Kestrel Holdings Pte. Ltd., which holds 50% of "
        "Garden Business), Daniel Koh holds 25% in total (5% directly + 20% indirectly via "
        "Meridian Capital Pte. Ltd.), and Wei Jie Chen holds 25% directly.",
    ],
)
def test_real_model_sentences_that_are_correct_are_kept(sentence: str) -> None:
    check = copilot.check_answer(sentence, FACTS)
    assert (check.kept, check.left_out) == (1, []), check


@pytest.mark.parametrize(
    "sentence",
    [
        "OMAR SAID is below the threshold.",  # undetermined: no threshold result to state
        "DANIEL KOH does not count as a UBO.",
        "AISHA RAHMAN holds 60% of KESTREL, and PRIYA NAIR holds 20% through MERIDIAN CAPITAL.",
    ],
)
def test_contradictions_in_real_model_style_are_removed(sentence: str) -> None:
    assert copilot.check_answer(sentence, FACTS).kept == 0, sentence


def test_short_follow_ups_and_figures_of_the_case_are_in_scope() -> None:
    assert copilot.in_domain("How did the application get 25% for DANIEL KOH?", ongoing=False,
                             case_open=True)
    assert copilot.in_domain("And MERIDIAN?", ongoing=True)
    assert not copilot.in_domain("And the weather tomorrow?", ongoing=True, case_open=True)


@pytest.mark.parametrize(
    "sentence",
    [
        "PRIYA NAIR holds 20% of GARDEN BUSINESS indirectly (40% of KESTREL HOLDINGS PTE. LTD. x "
        "50% of GARDEN BUSINESS).",
        "This is based on the direct ownership fact in the OWNERSHIP FACTS.",
        "This means the application cannot confirm whether OMAR SAID is a UBO or not.",
        "The system needs the shareholders before it can determine who qualifies as a UBO.",
        "No UBO status is verified yet, and OMAR SAID needs a person's review.",
    ],
)
def test_second_real_model_round_sentences_are_kept(sentence: str) -> None:
    check = copilot.check_answer(sentence, FACTS)
    assert (check.kept, check.left_out) == (1, []), check


def test_a_relative_clause_does_not_hedge_a_ubo_conclusion() -> None:
    assert copilot.check_answer("AISHA RAHMAN, who is the UBO, holds 30%.", FACTS).kept == 0
