"""D-145 (owner decision F-6, 2026-11-19; project-defined, not sponsor-confirmed).

UBO_CALCULATION may explain a REVIEW_REQUIRED analysis that the backend did not POC-accept when
the backend's own D-121 advisory verdict holds for that same analysis (the readiness
``reference_id`` equals the loaded ``analysis_id``, the Ownership & UBO step is COMPLETE with
``advisory_review``, readiness ownership is REVIEW_ADVISED). Only the canonical question and the
same ownership projection leave; the backend's threshold comparison is service text shown
locally; U-5 still removes any outcome the model writes; every other exclusion stands.

The figures are the backend's own OPQ ``garden_abc_multi_holder`` and Garden direct results
(outputs/overnight-20261119/verify-opq, re-run for D-145); the names are the test suite's
synthetic ones.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import controlled_intents as ci
from ai_assistant import copilot
from ai_assistant import privacy_boundary as pb
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from tests import test_conversational_external
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_copilot import ALPHA, BETA, ROOT, _candidate, _path
from tests.test_hosted_case_policy import WAITING_ID as WAITING
from tests.test_hosted_claude import Hosted, done, hosted_replies  # noqa: F401 (fixture)
from tests.test_hosted_privacy import OUTSIDE, PrivateClm, build, sent_since
from tests.test_privacy_r4 import _garden_facts
from tests.test_ubo_calculation_intent import OWNERSHIP, _Owned

CANONICAL = ci.CANONICAL[ci.UBO_CALCULATION]
ANALYSIS_ID = "bd793f66-0000-4c5a-8594-801d406cbfb7"
REVIEW = "REVIEW_REQUIRED"
GAMMA = "GAMMA VENTURES PTE. LTD."


def _review(candidate: dict[str, Any], assumed: str | None) -> dict[str, Any]:
    candidate.update(classification=REVIEW, threshold_result="INDETERMINATE")
    candidate["synthetic_basis_threshold_result"] = assumed
    return candidate


def _opq_abc() -> dict[str, Any]:
    """OPQ garden_abc_multi_holder as the backend calculates it (DEMO, advisory mode)."""

    return {
        "analysis_id": ANALYSIS_ID,
        "state": REVIEW,
        "provider_environment": "MOCK",
        "threshold_percent": "25.000000",
        "threshold_comparator": "GREATER_THAN_OR_EQUAL_TO",
        "poc_basis_accepted": False,
        "candidates": [
            _review(
                _candidate(
                    "LIM CHOON HUAT",
                    ("0", "25.568181875", "25.568181875"),
                    "INDETERMINATE",
                    REVIEW,
                    [
                        _path(
                            [
                                ("LIM CHOON HUAT", GAMMA, "81.818182"),
                                (GAMMA, ALPHA, "62.5"),
                                (ALPHA, ROOT, "50"),
                            ],
                            "25.568181875",
                        )
                    ],
                ),
                "MET",
            ),
            _review(
                _candidate(
                    "NG MEI LING",
                    ("0", "18.75", "18.75"),
                    "INDETERMINATE",
                    REVIEW,
                    [_path([("NG MEI LING", ALPHA, "37.5"), (ALPHA, ROOT, "50")], "18.75")],
                ),
                "NOT_MET",
            ),
            _review(
                _candidate(
                    "TAN WEI LING",
                    ("0", "50", "50"),
                    "INDETERMINATE",
                    REVIEW,
                    [_path([("TAN WEI LING", BETA, "100"), (BETA, ROOT, "50")], "50")],
                ),
                "MET",
            ),
        ],
        "issues": [
            {"code": "OWNERSHIP_DENOMINATOR_REQUIRED", "message": "backend text"},
            {"code": "SYNTHETIC_OWNERSHIP_EVIDENCE", "message": "backend text"},
            {"code": "OWNERSHIP_METHOD_UNSUPPORTED", "message": "backend text"},
        ],
        "manual_review_receipt": None,
    }


def _garden_direct() -> dict[str, Any]:
    """Garden direct (GARDEN BUSINESS root) as the backend calculates it (advisory mode)."""

    out = _opq_abc()
    out["candidates"] = [
        _review(
            _candidate(
                "LIM CHOON HUAT",
                ("0", "51.13636375", "51.13636375"),
                "INDETERMINATE",
                REVIEW,
                [
                    _path(
                        [("LIM CHOON HUAT", GAMMA, "81.818182"), (GAMMA, ROOT, "62.5")],
                        "51.13636375",
                    )
                ],
            ),
            "MET",
        ),
        _review(
            _candidate(
                "NG MEI LING",
                ("37.5", "0", "37.5"),
                "INDETERMINATE",
                REVIEW,
                [_path([("NG MEI LING", ROOT, "37.5")], "37.5")],
            ),
            "MET",
        ),
    ]
    out["issues"][2] = {"code": "UBO_REVIEW_REQUIRED", "message": "backend text"}
    return out


def _summary(
    *,
    status: str = "READY",
    reference: str | None = ANALYSIS_ID,
    node_status: str = "COMPLETE",
    flag: Any = True,
) -> dict[str, Any]:
    """The case summary with the backend's D-121/D-141 advisory verdict (or a variation)."""

    summary = copy.deepcopy(OUTSIDE)
    summary["clm"]["readiness"]["ownership"] = {"status": status, "reference_id": reference}
    for node in summary["processing_pipeline"]:
        if node["node_id"] == "OWNERSHIP_UBO":
            node["status"] = node_status
            node["advisory_review"] = flag
    return summary


ADVISED = _summary()


def _facts(analysis: Any, summary: dict[str, Any] = ADVISED) -> dict[str, Any]:
    facts = build_case_facts(CaseSnapshot(summary, [], {"profile": {}}))
    facts["ownership"] = copilot.ownership_facts(
        analysis, review_advisory=copilot.advisory_review_current(summary, analysis)
    )
    return facts


# --- admission on the backend's advisory verdict for the same analysis --------------------------


@pytest.mark.parametrize("analysis", [_opq_abc(), _garden_direct()], ids=["opq-abc", "garden"])
def test_an_advisory_review_of_the_same_analysis_is_admitted(analysis: dict[str, Any]) -> None:
    facts = _facts(analysis)
    assert facts["readiness"]["sections"]["ownership"] == "REVIEW_ADVISED"
    assert facts["ownership"]["review_advisory"] is True
    assert facts["ownership"]["poc_basis_accepted"] is False
    assert ci.ubo_advisory_admission(facts) and ci.ubo_calculation_ready(facts)
    for question in ("Explain the UBO calculation", "How were the ownership paths calculated?"):
        found = ci.recognise(facts, question)
        assert found.intent == ci.Intent(ci.UBO_CALCULATION)
        assert found.intent.question == CANONICAL


@pytest.mark.parametrize(
    "summary",
    [
        _summary(
            status="REVIEW_REQUIRED", reference=None, node_status="REVIEW_REQUIRED", flag=None
        ),
        _summary(reference="another-analysis"),  # a newer or other analysis
        _summary(reference=None),
        _summary(flag=None),  # no D-141 flag on the step
        _summary(flag="true"),  # never inferred from a string
        _summary(node_status="REVIEW_REQUIRED"),
        _summary(status="REVIEW_REQUIRED"),
        OUTSIDE,
    ],
    ids=[
        "blocking-mode",
        "other-analysis",
        "no-reference",
        "no-flag",
        "flag-string",
        "step-not-complete",
        "readiness-not-ready",
        "plain-summary",
    ],
)
def test_without_the_same_analysis_verdict_nothing_is_admitted(summary: dict[str, Any]) -> None:
    facts = _facts(_opq_abc(), summary)
    assert facts["ownership"]["review_advisory"] is False
    assert not ci.ubo_calculation_ready(facts)
    assert ci.recognise(facts, "Explain the UBO calculation") == ci.Recognised(None, ci.UNSUPPORTED)


def test_the_verdict_needs_the_analysis_id_and_a_review_required_analysis() -> None:
    assert not copilot.advisory_review_current(ADVISED, {**_opq_abc(), "analysis_id": None})
    assert not copilot.advisory_review_current(ADVISED, {**_opq_abc(), "state": "ANALYZED"})
    assert not copilot.advisory_review_current(None, _opq_abc())
    assert not copilot.advisory_review_current(ADVISED, None)
    # The projection keeps the flag only as a literal true on a REVIEW_REQUIRED analysis.
    analysed = {**_opq_abc(), "state": "ANALYZED"}
    assert copilot.ownership_facts(analysed, review_advisory=True)["review_advisory"] is False
    assert copilot.ownership_facts(_opq_abc())["review_advisory"] is False


def test_a_flag_set_in_the_facts_without_the_readiness_verdict_is_refused() -> None:
    # Both sources must agree: the flag alone (for example forged into the facts) is not enough.
    facts = _garden_facts()
    facts["ownership"] = copilot.ownership_facts(_opq_abc(), review_advisory=True)
    assert facts["readiness"]["sections"].get("ownership") != "REVIEW_ADVISED"
    assert not ci.ubo_calculation_ready(facts)


def _cut(change: Any) -> dict[str, Any]:
    analysis = _opq_abc()
    change(analysis)
    return analysis


@pytest.mark.parametrize(
    "analysis",
    [
        _cut(lambda a: a["candidates"][0].update(synthetic_basis_threshold_result=None)),
        _cut(lambda a: a["candidates"][0].update(synthetic_basis_threshold_result="INDETERMINATE")),
        _cut(lambda a: a["candidates"][0].update(synthetic_basis_threshold_result="met")),
        _cut(lambda a: a["candidates"][1].update(classification="INDETERMINATE")),
        _cut(lambda a: a["candidates"][0].update(aggregated_ownership_percent=None)),
        _cut(lambda a: a["candidates"][0].update(paths=[])),
        _cut(
            lambda a: a["candidates"][0]["paths"][0].update(
                edges=a["candidates"][0]["paths"][0]["edges"] * 4
            )
        ),
        _cut(
            lambda a: a["candidates"][0].update(
                paths=a["candidates"][0]["paths"] * copilot.MAX_PATHS
            )
        ),
        _cut(lambda a: a.update(candidates=a["candidates"] * 5)),  # people not shown
        _cut(lambda a: a.update(issues=a["issues"] * 4)),  # issues cut at their bound
        _cut(lambda a: a.update(threshold_percent=None)),
        _cut(lambda a: a.update(candidates=[])),
    ],
    ids=[
        "no-comparison",
        "indeterminate-comparison",
        "unknown-comparison-value",
        "indeterminate-person",
        "no-aggregated",
        "no-path",
        "links-not-shown",
        "paths-at-bound",
        "people-not-shown",
        "issues-at-bound",
        "no-threshold",
        "nobody",
    ],
)
def test_every_exclusion_is_kept_on_the_advisory_path(analysis: dict[str, Any]) -> None:
    facts = _facts(analysis)
    assert not ci.ubo_calculation_ready(facts)
    assert ci.recognise(facts, "Explain the UBO calculation") == ci.Recognised(None, ci.UNSUPPORTED)


def test_a_withheld_upload_still_withholds_an_advisory_analysis() -> None:
    from ai_assistant.main import OWNERSHIP_WITHHELD

    facts = _facts(_opq_abc())
    facts["ownership"] = dict(OWNERSHIP_WITHHELD)
    assert ci.recognise(facts, "Explain the UBO calculation").intent is None


def test_u3_is_unchanged_for_an_accepted_analysis() -> None:
    accepted = {**_opq_abc(), "poc_basis_accepted": True}
    facts = _facts(accepted, OUTSIDE)
    assert ci.ubo_review_admission(facts) and not ci.ubo_advisory_admission(facts)
    assert ci.ubo_calculation_ready(facts)


# --- the service's threshold comparison and the disclosures ------------------------------------


def test_the_threshold_lines_quote_the_backends_comparison_only() -> None:
    lines = copilot.ubo_threshold_lines(_facts(_opq_abc())["ownership"])
    assert lines is not None
    rows = lines.splitlines()
    assert rows[0].startswith("Threshold comparison") and "not a UBO determination" in rows[0]
    assert rows[1] == (
        "- LIM CHOON HUAT: 25.568181875% meets the 25% threshold on the application's assumed "
        "POC basis; the formal comparison is not determined."
    )
    assert rows[2].startswith("- NG MEI LING: 18.75% does not meet the 25% threshold")
    assert rows[3].startswith("- TAN WEI LING: 50% meets the 25% threshold")
    assert "no person is named as a confirmed, legal or provisional UBO" in rows[-1]
    # A formal result, when the backend gives one, is used as is.
    formal = _cut(lambda a: a["candidates"][1].update(threshold_result="NOT_MET"))
    row = copilot.ubo_threshold_lines(_facts(formal)["ownership"]).splitlines()[2]
    assert row == "- NG MEI LING: 18.75% does not meet the 25% threshold."
    # Never from anything but the backend's values: no comparison, no lines.
    missing = _cut(lambda a: a["candidates"][0].update(synthetic_basis_threshold_result=None))
    assert copilot.ubo_threshold_lines(_facts(missing)["ownership"]) is None


def test_the_local_only_keys_never_reach_a_model() -> None:
    facts = _facts(_opq_abc())
    assert facts["ownership"]["people"][0]["assumed_basis_threshold_result"] == "MET"
    out = pb.minimise_facts(facts, known_labels=frozenset())
    text = json.dumps(out)
    assert "assumed_basis" not in text and "review_advisory" not in text
    assert "synthetic_basis" not in text
    assert set(out["ownership"]) <= set(pb.OWNERSHIP_FIELDS)
    # The figures the model explains are still there.
    assert out["ownership"]["people"][0]["aggregated_percent"] == "25.568181875"


@pytest.mark.parametrize(
    "sentence",
    [
        "LIM CHOON HUAT meets the 25% threshold.",
        "TAN WEI LING is a provisional UBO candidate.",
        "LIM CHOON HUAT is the confirmed UBO.",
        "Two people qualify as UBOs.",
        "LIM CHOON HUAT is the legal beneficial owner.",
    ],
)
def test_u5_still_removes_any_outcome_the_model_writes(sentence: str) -> None:
    facts = _facts(_opq_abc())
    required = [
        copilot.UBO_PROVISIONAL_NOTE,
        copilot.UBO_REVIEW_NOTE,
        copilot.UBO_ADVISORY_NOTE,
        copilot.ubo_threshold_lines(facts["ownership"]),
    ]
    check = copilot.check_answer(
        "One path is 50% x 62.5% x 81.818182% = 25.568181875%. " + sentence,
        facts,
        required=required,
    )
    assert sentence not in check.text
    assert "25.568181875%" in check.text
    assert check.text.startswith("\n\n".join(required))


# --- the wire: only the canonical question, the same projection -------------------------------


class AdvisedClm(_Owned, PrivateClm):
    analysis = {
        **copy.deepcopy(OWNERSHIP),
        "analysis_id": ANALYSIS_ID,
        "state": REVIEW,
        "poc_basis_accepted": False,
    }
    summary: dict[str, Any] = ADVISED

    def __init__(self) -> None:
        super().__init__()
        for candidate, basis in zip(
            self.analysis["candidates"], ("MET", "MET", "NOT_MET"), strict=True
        ):
            _review(candidate, basis)

    def handler(self, request: Any) -> Any:
        import httpx

        response = super().handler(request)
        if (
            request.url.path == f"/api/clm/zero-touch/cases/{WAITING}"
            and response.status_code == 200
        ):
            return httpx.Response(200, json=self.summary)
        return response


class BlockingClm(AdvisedClm):
    summary = _summary(
        status="REVIEW_REQUIRED", reference=None, node_status="REVIEW_REQUIRED", flag=None
    )


def _hosted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clm: Any, reply: str) -> Hosted:
    from ai_assistant.privacy_boundary import PSEUDONYMISED

    monkeypatch.setitem(test_conversational_external.SCRIPT, CANONICAL, reply)
    hosted = build(tmp_path, monkeypatch, PSEUDONYMISED, decision=True, clm=clm)
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "TEST-OWNER-APPROVAL")
    hosted.settings.answer_mode = "copilot"
    return hosted


def test_an_advisory_analysis_is_explained_through_the_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> None:
    reply = (
        "One path is 80% x 50% = 40%. The threshold is 25%. LIM CHOON HUAT meets the 25% threshold."
    )
    hosted = _hosted(tmp_path, monkeypatch, AdvisedClm(), reply)
    before = len(hosted.claude.messages)
    typed = "Can you explain how the UBO percentages were calculated?"
    status, events = hosted.ask(typed, case_id=WAITING)
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "model", answer
    text = answer["answer"]
    assert text.startswith(
        "\n\n".join(
            [copilot.UBO_PROVISIONAL_NOTE, copilot.UBO_REVIEW_NOTE, copilot.UBO_ADVISORY_NOTE]
        )
    )
    assert (
        "- LIM CHOON HUAT: 40% meets the 25% threshold on the application's assumed POC basis"
        in text
    )
    assert "- TAN WEI LING: 10% does not meet the 25% threshold" in text
    assert "80% x 50% = 40%" in text
    assert "LIM CHOON HUAT meets the 25% threshold." not in text  # the model's own outcome
    # Removed by the U-5 graph (every person UNDETERMINED) or the review-state rule.
    assert answer["checks"]["removed"] in (["ubo_contradicts_calculation"], ["ubo_review_state"])
    body = hosted.claude.messages[-1]
    assert body["messages"] == [{"role": "user", "content": CANONICAL}]
    payload = sent_since(hosted, before)
    assert typed not in payload
    assert "LIM CHOON HUAT" not in payload and "p-LIM CHOON HUAT" not in payload
    assert "assumed_basis" not in payload and "review_advisory" not in payload
    assert "synthetic_basis" not in payload and "Threshold comparison" not in payload
    assert ANALYSIS_ID not in payload


def test_blocking_mode_keeps_the_case_data_answer_and_sends_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> None:
    hosted = _hosted(tmp_path, monkeypatch, BlockingClm(), "unused")
    posts = hosted.claude.posts
    status, events = hosted.ask("How were the ownership paths calculated?", case_id=WAITING)
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data"
    assert ci.UNSUPPORTED in (answer["notice"] or "")
    assert copilot.UBO_REVIEW_NOTE in answer["answer"]
    assert copilot.UBO_ADVISORY_NOTE not in answer["answer"]
    assert "Threshold comparison" not in answer["answer"]
    assert hosted.claude.posts == posts  # nothing reserved or sent
