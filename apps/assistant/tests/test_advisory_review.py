"""D-141 (amends D-121 display only): an advisory ownership review is "review advised", not done.

The backend marks the complete OWNERSHIP_UBO node ``advisory_review``; the assistant must not
call ownership done or let a model sentence say it is complete.
"""

import copy
import json
from pathlib import Path
from typing import Any

from ai_assistant import copilot
from ai_assistant.briefing import opening_message
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import allowed_guidance, guard_answer, ubo_completion_not_offered
from ai_assistant.guide import OWNERSHIP_REVIEW_ADVISED

FIXTURES = Path(__file__).parent / "fixtures"
BASE = json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
ME = json.loads((FIXTURES / "me_client_onboarder.json").read_text())
CLAIMS = (
    "Ownership is complete.",
    "The ownership step is done.",
    "The UBO check is finished.",
    "The UBO check has now been completed.",
    "Ownership has already been completed.",
)


def _summary(advisory: bool | None) -> dict[str, Any]:
    """Ownership complete for readiness; ``advisory`` is the backend's flag on the node."""

    summary = copy.deepcopy(BASE)
    for node in summary["processing_pipeline"]:
        if node["node_id"] == "OWNERSHIP_UBO":
            node.update(status="COMPLETE", advisory_review=advisory, safe_result="Ready")
    readiness = summary["clm"]["readiness"]
    readiness["ownership"] = {"status": "READY", "reference_id": "analysis-1"}
    readiness["blockers"] = [code for code in readiness["blockers"] if code != "OWNERSHIP_REQUIRED"]
    return summary


def _facts(advisory: bool | None) -> dict[str, Any]:
    return build_case_facts(CaseSnapshot(_summary(advisory), [], ME))


def _ownership_step(facts: dict[str, Any]) -> dict[str, Any]:
    return next(step for step in facts["steps"] if step["step"] == "Ownership & UBO")


ADVISED = _facts(True)
CONFIRMED = _facts(None)


def test_an_advisory_case_has_a_review_advised_step_and_readiness() -> None:
    assert _ownership_step(ADVISED)["status"] == "review advised"
    assert ADVISED["readiness"]["sections"]["ownership"] == "REVIEW_ADVISED"
    # Not counted as done.
    assert ADVISED["overall"]["steps_done"] == CONFIRMED["overall"]["steps_done"] - 1
    assert ubo_completion_not_offered(ADVISED)


def test_the_briefing_lists_the_advisory_review() -> None:
    assert OWNERSHIP_REVIEW_ADVISED in opening_message(ADVISED).splitlines()
    assert OWNERSHIP_REVIEW_ADVISED in allowed_guidance(ADVISED)


def test_the_catalog_line_passes_both_modes_on_an_advisory_case() -> None:
    assert guard_answer(OWNERSHIP_REVIEW_ADVISED, ADVISED) == OWNERSHIP_REVIEW_ADVISED
    checked = copilot.check_answer(OWNERSHIP_REVIEW_ADVISED, ADVISED)
    assert checked.text == OWNERSHIP_REVIEW_ADVISED
    assert checked.left_out == []


def test_ownership_is_complete_is_removed_in_exact_line_mode() -> None:
    for claim in CLAIMS:
        assert guard_answer(claim, ADVISED) == ""


def test_ownership_is_complete_is_removed_in_copilot_mode() -> None:
    for claim in CLAIMS:
        checked = copilot.check_answer(claim, ADVISED)
        assert checked.text == "", claim
        assert checked.left_out == ["unsupported_status"], claim


def test_a_negated_ownership_sentence_is_kept_in_copilot_mode() -> None:
    sentence = "Ownership is not verified yet."
    assert copilot.check_answer(sentence, ADVISED).text == sentence


def test_a_confirmed_case_is_unchanged() -> None:
    assert _ownership_step(CONFIRMED)["status"] == "done"
    assert CONFIRMED["readiness"]["sections"]["ownership"] == "READY"
    assert OWNERSHIP_REVIEW_ADVISED not in allowed_guidance(CONFIRMED)
    assert OWNERSHIP_REVIEW_ADVISED not in opening_message(CONFIRMED)
    assert not ubo_completion_not_offered(CONFIRMED)
    for claim in CLAIMS:
        assert copilot.check_answer(claim, CONFIRMED).text == claim


def test_the_flag_counts_only_on_a_complete_ownership_node() -> None:
    summary = _summary(True)
    for node in summary["processing_pipeline"]:
        if node["node_id"] == "OWNERSHIP_UBO":
            node["status"] = "REVIEW_REQUIRED"
        elif node["node_id"] == "ACRA_REGISTRY":
            node["advisory_review"] = True
    facts = build_case_facts(CaseSnapshot(summary, [], ME))
    assert _ownership_step(facts)["status"] == "needs review"
    registry = next(step for step in facts["steps"] if step["step"] == "Registry verification")
    assert registry["status"] == "done"
    assert facts["readiness"]["sections"]["ownership"] == "READY"
