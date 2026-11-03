"""D-115: the copilot evaluation (assistant_eval/copilot_eval.py) through the real routes.

Scripted model answers on synthetic cases; no network, no paid call. Every scored dimension of
every scenario must pass. ``pytest -s`` prints the per-dimension summary.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from ai_assistant import copilot
from assistant_eval.copilot_eval import DIMENSIONS, SCENARIOS, Result, Scenario, report, score
from tests.test_ai_assistant import CASE_ID
from tests.test_copilot import CASE_B, Backend, Scripted, app, ask, browser, open_context, stream


class External(Scripted):
    requires_synthetic_boundary = True


def run(scenario: Scenario) -> Result:
    model = External(scenario.answer) if scenario.external_model else Scripted(scenario.answer)
    backend = Backend()
    client = browser(app(model, backend), "rm-a")
    if scenario.id == "cross-case":
        earlier = open_context(client, CASE_ID)
        ask(client, CASE_ID, "Why is it paused? FIRST-TURN-MARKER", earlier)
        client.post(f"/assistant/contexts/{earlier}/close")
    if scenario.case is None:
        context = open_context(client, None)
        for question in scenario.earlier:
            body = {"message": question, "context_id": context}
            stream(client, "/assistant/general/chat/stream", body)
        done = stream(
            client,
            "/assistant/general/chat/stream",
            {"message": scenario.question, "context_id": context},
        )
    else:
        case_id = CASE_ID if scenario.case == "A" else CASE_B
        context = None if scenario.external_model else open_context(client, case_id)
        for question in scenario.earlier:
            ask(client, case_id, question, context)
        ask_body: dict[str, Any] = {"message": scenario.question}
        if context:
            ask_body["context_id"] = context
        done = stream(client, f"/assistant/cases/{case_id}/chat/stream", ask_body)
    calls = len(model.calls) - (1 if scenario.id == "cross-case" else 0) - len(scenario.earlier)
    prompts = json.dumps(model.calls[-1]) if model.calls else ""
    if scenario.redirected:
        prompts = ""
    result = Result(scenario, done["answer"], done["answered_by"], calls, prompts)
    result.scores = score(scenario, done["answer"], calls, prompts, copilot.READ_ONLY_LINE)
    return result


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_each_scenario_passes_every_dimension_it_exercises(scenario: Scenario) -> None:
    result = run(scenario)
    failed = [d for d, ok in result.scores.items() if ok is False]
    assert failed == [], (scenario.id, failed, result.answer)
    assert any(ok is not None for ok in result.scores.values())


def test_the_suite_covers_every_category_and_dimension() -> None:
    results = [run(scenario) for scenario in SCENARIOS]
    summary = json.loads(report(results))
    print("\nCOPILOT_EVAL", json.dumps(summary))
    assert summary["failures"] == []
    assert len(summary["categories"]) == 14
    assert all(summary["dimensions"][d]["scored"] > 0 for d in DIMENSIONS)
