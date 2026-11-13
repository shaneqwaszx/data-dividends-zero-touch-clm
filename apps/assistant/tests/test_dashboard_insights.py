"""ADR-015 dashboard AI insights: bounded input, local model only, checked output, no storage."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.dashboard_insights import (
    DashboardInsights,
    InsightsRejected,
    InsightsRequest,
    InsightsUnavailable,
    check_reply,
)
from ai_assistant.data_access import SyntheticOnlyModel
from ai_assistant.main import create_app
from ai_assistant.remote_test import RemoteTestModel
from tests.test_ai_assistant import ME, ORIGIN, FakeBackend, FakeModel, _client

PATH = "/assistant/dashboard/insights"

FINDINGS: dict[str, Any] = {
    "period": "Last 30 days",
    "findings": [
        {
            "id": "F1",
            "topic": "SLA_OVERDUE",
            "severity": "CRITICAL",
            "actionable": True,
            "facts": {
                "overdue_cases": 3,
                "at_risk_cases": 1,
                "oldest_open": "26d 2h",
                "target": "10 days",
            },
        },
        {
            "id": "F2",
            "topic": "WAITING_DRIVER",
            "severity": "WARNING",
            "actionable": True,
            "facts": {
                "exception": "Ownership review required",
                "share_of_fix_time": "43%",
                "total_fix_time": "2d 20h",
            },
        },
        {
            "id": "F3",
            "topic": "ZERO_TOUCH",
            "severity": "INFO",
            "actionable": False,
            "facts": {"zero_touch_rate": "65%", "weekly_low": "40%", "weekly_high": "86%"},
        },
    ],
}


def reply(**overrides: Any) -> str:
    body: dict[str, Any] = {
        "summary": (
            "3 cases are overdue against the 10 days target; "
            "waiting on ownership reviews drives most delay."
        ),
        "notes": [
            {"id": "F1", "text": "3 cases are past the 10 days target and 1 is at risk."},
            {"id": "F2", "text": "Ownership review required takes 43% of blocker fix time."},
            {"id": "F3", "text": "Zero-touch rate is 65%, ranging from 40% to 86% by week."},
        ],
        "actions": [
            {
                "id": "F1",
                "text": "Clear the overdue cases first, starting with the oldest at 26d 2h.",
            },
            {"id": "F2", "text": "Review what evidence closes ownership reviews."},
        ],
    }
    body.update(overrides)
    return json.dumps(body)


def post(client: TestClient, body: dict[str, Any] = FINDINGS) -> httpx.Response:
    return client.post(PATH, json=body)


def test_writes_checked_insights_from_the_supplied_findings_only() -> None:
    model = FakeModel(answer=reply())
    response = post(_client(FakeBackend(), model))

    assert response.status_code == 200
    body = response.json()
    assert body["summary"].startswith("3 cases are overdue")
    assert [item["id"] for item in body["notes"]] == ["F1", "F2", "F3"]
    assert [item["id"] for item in body["actions"]] == ["F1", "F2"]
    assert body["model"] == "fake-model"
    # The prompt is the fixed instructions plus exactly the supplied findings.
    system, user = model.calls[0]
    assert system["role"] == "system" and "Copy every number exactly" in system["content"]
    assert json.loads(user["content"]) == FINDINGS


def test_items_with_foreign_numbers_ids_actions_or_wording_are_dropped() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    text = reply(
        notes=[
            {"id": "F1", "text": "4 cases are overdue."},  # 4 is not in F1's facts
            {"id": "F9", "text": "Unknown finding."},
            {"id": "F2", "text": "Ownership review required takes 43% of fix time."},
            {"id": "F2", "text": "A second note for F2 is ignored."},
            {"id": "F3", "text": "Marine Parade Wellness Pte. Ltd. is fine."},  # invented company
        ],
        actions=[
            {"id": "F3", "text": "Not actionable."},
            {"id": "F1", "text": "Approve the overdue cases."},
            {"id": "F2", "text": "Review ownership guidance."},
        ],
    )
    result = check_reply(request, text, "m")
    assert [(item.id, item.text) for item in result.notes] == [
        ("F2", "Ownership review required takes 43% of fix time."),
    ]
    assert [item.id for item in result.actions] == ["F2"]


def test_summary_may_use_numbers_from_any_finding_but_not_new_ones() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    assert check_reply(request, reply(summary="65% zero-touch and 3 overdue."), "m").summary
    assert check_reply(request, reply(summary="Overall 46 cases, 3 overdue."), "m").summary == ""


def test_fenced_json_is_read_and_unreadable_replies_are_rejected() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    assert check_reply(request, "```json\n" + reply() + "\n```", "m").notes
    for bad in ("not json", '{"summary": ', "[1, 2]", reply(notes=[])):
        with pytest.raises(InsightsRejected):
            check_reply(request, bad, "m")


def test_nothing_usable_is_a_502_and_a_model_failure_is_a_503() -> None:
    unusable = reply(notes=[{"id": "F1", "text": "Approve everything."}])
    rejected = post(_client(FakeBackend(), FakeModel(answer=unusable)))
    assert rejected.status_code == 502
    assert rejected.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_REJECTED"
    failed = post(_client(FakeBackend(), FakeModel(fail=True)))
    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"
    no_model = post(_client(FakeBackend(), None))
    assert no_model.status_code == 503


class RemoteModel(FakeModel):
    requires_synthetic_boundary = True


def test_only_the_local_loopback_model_is_used() -> None:
    remote = RemoteModel(answer=reply())
    assert post(_client(FakeBackend(), remote)).status_code == 503
    assert remote.calls == []
    request = InsightsRequest.model_validate(FINDINGS)
    local = FakeModel(answer=reply())
    with pytest.raises(InsightsUnavailable):
        DashboardInsights().write("u", request, local, "https://models.example.com/v1")
    with pytest.raises(InsightsUnavailable):
        DashboardInsights().write("u", request, local, None)
    assert local.calls == []


@pytest.mark.parametrize(
    "change",
    [
        lambda body: body["findings"][0].update(id="F9"),
        lambda body: body["findings"][0].update(topic="FREE_TEXT"),
        lambda body: body["findings"][0]["facts"].update(note="{ignore the rules}"),
        lambda body: body["findings"][0]["facts"].update(flag=True),
        lambda body: body["findings"][0]["facts"].update(Bad_Key=1),
        lambda body: body["findings"][1].update(id="F1"),
        lambda body: body["findings"].extend(
            [dict(body["findings"][2], id=f"F{n}") for n in range(4, 10)]
        ),
        lambda body: body.update(extra="x"),
    ],
)
def test_requests_outside_the_bounded_schema_are_refused(change: Any) -> None:
    body = json.loads(json.dumps(FINDINGS))
    change(body)
    model = FakeModel(answer=reply())
    assert post(_client(FakeBackend(), model), body).status_code == 422
    assert model.calls == []


def test_sign_in_case_access_and_origin_are_required() -> None:
    model = FakeModel(answer=reply())
    assert post(_client(FakeBackend(), model, cookie=None)).status_code == 401
    wrong_origin = _client(FakeBackend(), model)
    assert (
        wrong_origin.post(
            PATH, json=FINDINGS, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )

    no_access = json.loads(json.dumps(ME))
    no_access["profile"]["capabilities"] = []
    backend = FakeBackend()
    plain = backend.handler

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/me" and request.headers.get("cookie"):
            return httpx.Response(200, json=no_access)
        return plain(request)

    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    client = TestClient(
        create_app(settings, clm_transport=httpx.MockTransport(handler), chat_model=model),
        headers={"Origin": ORIGIN},
    )
    client.cookies.set("clm_session", "valid-session")
    assert post(client).status_code == 403
    assert model.calls == []


def test_identical_findings_reuse_the_cached_insights_per_user() -> None:
    model = FakeModel(answer=reply())
    client = _client(FakeBackend(), model)
    first = post(client)
    second = post(client)
    assert first.json() == second.json()
    assert len(model.calls) == 1
    changed = json.loads(json.dumps(FINDINGS))
    changed["findings"][0]["facts"]["overdue_cases"] = 4
    assert post(client, changed).status_code in (200, 502)
    assert len(model.calls) == 2

    insights = DashboardInsights()
    request = InsightsRequest.model_validate(FINDINGS)
    local = FakeModel(answer=reply())
    insights.write("a", request, local, "http://127.0.0.1:11434/v1")
    insights.write("b", request, local, "http://127.0.0.1:11434/v1")
    assert len(local.calls) == 2


def test_backend_is_only_asked_who_the_user_is() -> None:
    backend = FakeBackend()
    post(_client(backend, FakeModel(answer=reply())))
    assert {request.url.path for request in backend.requests} == {"/api/auth/me"}
    assert all(request.method == "GET" for request in backend.requests)


def test_summary_is_optional_but_notes_are_required() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    result = check_reply(request, reply(summary="Overall 46 cases."), "m")
    assert result.summary == ""
    assert [item.id for item in result.notes] == ["F1", "F2", "F3"]


def test_ids_and_markdown_are_stripped_and_nouns_like_approvals_are_allowed() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    text = reply(
        notes=[{"id": "F1", "text": "**3 cases** are overdue (F1)."}],
        actions=[
            {"id": "F2", "text": "Streamline ownership approvals (F2)."},
            {"id": "F1", "text": "Reject the oldest case."},
        ],
    )
    result = check_reply(request, text, "m")
    assert result.notes[0].text == "3 cases are overdue."
    assert [(item.id, item.text) for item in result.actions] == [
        ("F2", "Streamline ownership approvals."),
    ]


def test_common_json_slips_from_a_local_model_are_repaired() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    missing_comma = (
        '{"summary": "3 cases are overdue."\n\n  "notes": [{"id": "F1", "text": "3 overdue."},],'
        '\n  "actions": []}'
    )
    result = check_reply(request, missing_comma, "m")
    assert result.summary == "3 cases are overdue."
    assert [item.text for item in result.notes] == ["3 overdue."]


class FlakyModel(FakeModel):
    def __init__(self, answers: list[str]) -> None:
        super().__init__(answer=answers[-1])
        self.answers = answers

    def complete(self, messages: list[dict[str, str]]) -> Any:
        from ai_assistant.llm import ModelAnswer

        self.calls.append(messages)
        return ModelAnswer(self.answers[min(len(self.calls), len(self.answers)) - 1])


def test_one_retry_after_an_unusable_reply_and_no_more() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    recovering = FlakyModel(["not json", reply()])
    result = DashboardInsights().write("u", request, recovering, "http://127.0.0.1:11434/v1")
    assert result.notes and len(recovering.calls) == 2
    broken = FlakyModel(["not json", "still not json", reply()])
    with pytest.raises(InsightsRejected):
        DashboardInsights().write("u", request, broken, "http://127.0.0.1:11434/v1")
    assert len(broken.calls) == 2


def test_director_topics_are_accepted_and_worded() -> None:
    body = json.loads(json.dumps(FINDINGS))
    body["findings"][2] = {
        "id": "F3",
        "topic": "DIRECTOR_RECOVERY",
        "severity": "WARNING",
        "actionable": True,
        "facts": {"recovery_cases": 2, "oldest_waiting": "9d 4h", "overdue_among_them": 0},
    }
    request = InsightsRequest.model_validate(body)
    text = reply(
        notes=[{"id": "F3", "text": "2 cases wait for your GoldTier recovery decision."}],
        actions=[{"id": "F3", "text": "Decide the 2 recovery cases, oldest first at 9d 4h."}],
    )
    result = check_reply(request, text, "m")
    assert [item.id for item in result.actions] == ["F3"]


def test_one_model_run_at_a_time_and_identical_requests_share_it() -> None:
    import threading

    request = InsightsRequest.model_validate(FINDINGS)
    running = 0
    peak = 0
    guard = threading.Lock()

    class SlowModel(FakeModel):
        def complete(self, messages: list[dict[str, str]]) -> Any:
            nonlocal running, peak
            with guard:
                running += 1
                peak = max(peak, running)
            time.sleep(0.05)
            with guard:
                running -= 1
            return super().complete(messages)

    model = SlowModel(answer=reply())
    insights = DashboardInsights()
    url = "http://127.0.0.1:11434/v1"
    users = ["a", "a", "a", "b", "c"]
    threads = [
        threading.Thread(target=insights.write, args=(user, request, model, url)) for user in users
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert peak == 1
    assert len(model.calls) == 3  # one per distinct user; the repeats reuse "a"'s answer


def test_decision_verbs_in_any_form_are_dropped_but_the_nouns_stay() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    forbidden = [
        "Get the overdue cases approved today.",
        "These should be rejected.",
        "Approving the oldest case first helps.",
        "Close them out by Friday.",
        "Close out these cases this week.",
        "The overdue cases can be deleted.",
        "Ownership checks are overridden too often.",
    ]
    for text in forbidden:
        result = check_reply(
            request,
            reply(notes=[{"id": "F1", "text": "3 overdue."}], actions=[{"id": "F1", "text": text}]),
            "m",
        )
        assert result.actions == (), text
    kept = check_reply(
        request,
        reply(actions=[{"id": "F2", "text": "Review what slows ownership approval."}]),
        "m",
    )
    assert [item.id for item in kept.actions] == ["F2"]


def test_numbers_in_words_are_checked_and_ratio_words_are_refused() -> None:
    request = InsightsRequest.model_validate(FINDINGS)

    def note(text: str) -> list[str]:
        try:
            notes = check_reply(request, reply(notes=[{"id": "F1", "text": text}]), "m").notes
        except InsightsRejected:  # the only note was dropped
            return []
        return [item.text for item in notes]

    assert note("Three cases are past the target and one is at risk.")  # 3 and 1 are facts
    for text in [
        "Four cases are overdue.",
        "Twice as many cases are overdue as at risk.",
        "A dozen cases are close to the target.",
        "Half of the open cases are overdue.",
        "Overdue cases tripled.",
    ]:
        assert note(text) == [], text
    summary = check_reply(request, reply(summary="Fifty cases are open."), "m").summary
    assert summary == ""


def test_waiting_is_bounded_and_a_newer_request_replaces_an_older_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading

    from ai_assistant import dashboard_insights as module

    started, release = threading.Event(), threading.Event()

    class HeldModel(FakeModel):
        def complete(self, messages: list[dict[str, str]]) -> Any:
            if not started.is_set():
                started.set()
                release.wait(5)
            return super().complete(messages)

    url = "http://127.0.0.1:11434/v1"
    request = InsightsRequest.model_validate(FINDINGS)
    newer_body = json.loads(json.dumps(FINDINGS))
    newer_body["findings"][2]["facts"]["zero_touch_rate"] = "66%"
    newer = InsightsRequest.model_validate(newer_body)

    def wait_for(insights: DashboardInsights, waiting: int) -> None:
        deadline = time.monotonic() + 5
        while insights._waiting != waiting and time.monotonic() < deadline:
            time.sleep(0.01)
        assert insights._waiting == waiting

    # A newer, different request from the same user drops the older one still waiting.
    model = HeldModel(answer=reply())
    insights = DashboardInsights()
    outcome: dict[str, str] = {}

    def run(name: str, user: str, body: InsightsRequest) -> None:
        try:
            insights.write(user, body, model, url)
            outcome[name] = "written"
        except InsightsUnavailable:
            outcome[name] = "unavailable"

    holder = threading.Thread(target=run, args=("holder", "other", request))
    holder.start()
    assert started.wait(5)
    older = threading.Thread(target=run, args=("older", "a", request))
    older.start()
    wait_for(insights, 1)
    latest = threading.Thread(target=run, args=("newer", "a", newer))
    latest.start()
    wait_for(insights, 2)
    release.set()
    for thread in (holder, older, latest):
        thread.join(5)
    assert outcome == {"holder": "written", "older": "unavailable", "newer": "written"}
    assert len(model.calls) == 2

    # A full queue and a long wait both give up instead of holding a worker.
    monkeypatch.setattr(module, "MAX_WAITING", 1)
    monkeypatch.setattr(module, "WAIT_SECONDS", 0.2)
    started.clear()
    release.clear()
    model = HeldModel(answer=reply())
    insights = DashboardInsights()
    outcome.clear()
    holder = threading.Thread(target=run, args=("holder", "other", request))
    holder.start()
    assert started.wait(5)
    waiter = threading.Thread(target=run, args=("waiter", "b", request))
    waiter.start()
    wait_for(insights, 1)
    with pytest.raises(InsightsUnavailable):
        insights.write("c", request, model, url)  # queue full
    waiter.join(5)
    assert outcome["waiter"] == "unavailable"  # waited longer than WAIT_SECONDS
    release.set()
    holder.join(5)
    assert outcome["holder"] == "written"


LOCAL_URL = "http://127.0.0.1:11434/v1"


class PaidModel(RemoteTestModel):
    """An API-key model (classed as GPT-OSS): it answers only messages holding a ticket."""

    def __init__(self, *, refuse: bool = False, answer: str | None = None) -> None:
        # The real constructor builds a provider client; none is needed here.
        self.answer = answer or reply()
        self.refuse = refuse
        self.calls: list[list[dict[str, str]]] = []
        self.ticketed: list[bool] = []

    @property
    def name(self) -> str:
        return "paid-model"

    def complete(self, messages: list[dict[str, str]]) -> Any:
        from ai_assistant import synthetic_eligibility
        from ai_assistant.llm import LlmUnavailableError, ModelAnswer

        self.ticketed.append(synthetic_eligibility.admitted(messages))
        self.calls.append(messages)
        if self.refuse or not self.ticketed[-1]:
            raise LlmUnavailableError("refused")  # e.g. over its spending limit
        return ModelAnswer(self.answer)


class LocalModel(FakeModel):
    name = "local-model"


def test_an_api_key_model_writes_insights_with_a_ticket_when_external_answers_are_on() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    paid, local = PaidModel(), LocalModel(answer=reply())
    result = DashboardInsights().write(
        "u", request, paid, "https://api.example.com", fallback=(local, LOCAL_URL), external=True
    )
    assert result.model == "paid-model"
    assert paid.ticketed == [True] and local.calls == []


def test_a_refused_or_rejected_api_key_call_falls_back_to_the_local_model_once() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    insights = DashboardInsights()
    paid, local = PaidModel(refuse=True), LocalModel(answer=reply())
    first = insights.write(
        "u", request, paid, "https://api.example.com", fallback=(local, LOCAL_URL), external=True
    )
    assert first.model == "local-model" and len(paid.calls) == 1 and len(local.calls) == 1
    # The local answer is reused: the paid model is not tried again for the same figures.
    again = insights.write(
        "u", request, paid, "https://api.example.com", fallback=(local, LOCAL_URL), external=True
    )
    assert again == first and len(paid.calls) == 1 and len(local.calls) == 1

    # An unusable paid reply gets one try only (it costs money); the local model is the retry.
    unusable = PaidModel(answer="not json")
    local = LocalModel(answer=reply())
    result = DashboardInsights().write(
        "u",
        request,
        unusable,
        "https://api.example.com",
        fallback=(local, LOCAL_URL),
        external=True,
    )
    assert result.model == "local-model" and unusable.ticketed == [True]


def test_without_external_answers_or_a_local_model_the_api_key_model_is_not_enough() -> None:
    request = InsightsRequest.model_validate(FINDINGS)
    paid, local = PaidModel(), LocalModel(answer=reply())
    result = DashboardInsights().write(
        "u", request, paid, "https://api.example.com", fallback=(local, LOCAL_URL)
    )
    assert result.model == "local-model" and paid.ticketed == []
    with pytest.raises(InsightsUnavailable):
        DashboardInsights().write("u", request, paid, "https://api.example.com")
    refusing = PaidModel(refuse=True)
    with pytest.raises(InsightsUnavailable):
        DashboardInsights().write("u", request, refusing, "https://api.example.com", external=True)
    # A fallback that is not on this machine is never used.
    remote_local = LocalModel(answer=reply())
    with pytest.raises(InsightsUnavailable):
        DashboardInsights().write(
            "u",
            request,
            refusing,
            "https://api.example.com",
            fallback=(remote_local, "https://models.example.com/v1"),
            external=True,
        )
    assert remote_local.calls == []


def test_only_claude_or_gpt_oss_count_as_paid_and_an_it_endpoint_is_never_used() -> None:
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    request = InsightsRequest.model_validate(FINDINGS)
    it_model = SyntheticOnlyModel(LocalModel(answer=reply()), settings, local=False)
    gated = RemoteModel(answer=reply())  # gated, but neither Claude nor GPT-OSS
    for model, url in [(it_model, "https://it.example.com/v1"), (gated, LOCAL_URL)]:
        assert DashboardInsights.candidates((model, url), external=True) == []
        with pytest.raises(InsightsUnavailable):
            DashboardInsights().write("u", request, model, url, external=True)
    assert it_model.inner.calls == [] and gated.calls == []


def test_a_policy_restricted_local_fallback_is_used_under_d122_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The suite runs without D-122 (conftest); this test opts in, as the running service has it.
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "D-122")
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    request = InsightsRequest.model_validate(FINDINGS)
    inner = LocalModel(answer=reply())
    restricted = SyntheticOnlyModel(inner, settings)
    result = DashboardInsights().write(
        "u",
        request,
        PaidModel(refuse=True),
        "https://api.example.com",
        fallback=(restricted, LOCAL_URL),
        external=True,
    )
    assert result.model == "local-model" and len(inner.calls) == 1
    assert DashboardInsights.candidates((None, None), (restricted, LOCAL_URL)) == []
