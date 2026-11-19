"""The fifth hosted Claude path, dashboard AI insights (D-130 amendment draft): prepared and
DISABLED by default.

Same harness as the hosted chat-path tests: the real app behind harden(), registered as the
hosted deployment, the R2.1 gate, the hosted guard, an HR-entered sentinel key and a mock
Anthropic transport. No network, no paid call.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

from ai_assistant import anthropic_runtime, hosted_insights
from ai_assistant.anthropic_profiles import BALANCED
from ai_assistant.dashboard_insights import InsightFinding
from tests import test_hosted_claude, test_hosting
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_dashboard_insights import FINDINGS
from tests.test_hosted_claude import (
    Hosted,
    HostedClm,
    hosted_replies,  # noqa: F401 (fixture)
    post_headers,
)

GENERATE = "/assistant/dashboard/insights/generate"
MODE = "/assistant/dashboard/insights/mode"
DECISION = "TEST-D-130-AMENDMENT"
OTHER_CASE = uuid4()
# What the backend's list shows besides the fields the path reads: none of it may reach Claude.
NAMES = ("GARDEN BUSINESS", "Alpha", "team-a", "maya-lim", "Other Holdings", "team-b")
ALLOWED_FACT_KEYS = {
    "open_cases",
    "overdue_cases",
    "at_risk_cases",
    "target",
    "exception",
    "open_cases_with_it",
    "step",
    "open_cases_there",
    "completed_cases",
    "zero_touch_rate",
    # C11: the recent-flow (TURNAROUND) counts.
    "new_this_week",
    "new_last_week",
    "completed_this_week",
    "completed_last_week",
}


def _item(case_id: object, **extra: Any) -> dict[str, Any]:
    summary = test_hosting.SUMMARY
    return {
        "case_id": str(case_id),
        "requested_uen": "202399999X",
        "legal_name": "GARDEN BUSINESS PTE. LTD.",
        "status": summary["status"],
        "current_stage": summary["current_stage"],
        "updated_at": summary["updated_at"],
        "active_exception_count": 1,
        "human_interventions": 2,
        "final_outcome": None,
        "team_id": "team-a",
        "client_scope_label": "Alpha",
        "priority": None,
        "resolved_jurisdiction": "SG",
        "created_at": summary["created_at"],
        "completed_at": None,
        "mock_goldtier_party_id": None,
        "active_exception_types": ["DOCUMENT_SOURCE_CONFLICT"],
        **extra,
    }


class InsightsClm(HostedClm):
    """The hosted mock backend plus the portfolio list: the eligible fixture case and a case
    outside the approved list (another company, another team's label)."""

    listed: list[dict[str, Any]]

    def __init__(self) -> None:
        super().__init__()
        self.listed = [
            _item(test_hosting.CASE_ID),
            _item(
                OTHER_CASE,
                legal_name="Other Holdings Pte Ltd",
                team_id="team-b",
                status="COMPLETED",
                human_interventions=0,
                active_exception_types=["OWNERSHIP_REVIEW_REQUIRED"],
            ),
        ]

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        if request.url.path == "/api/clm/zero-touch/cases" and token in test_hosting.SESSIONS:
            self.requests.append(request)
            return httpx.Response(200, json=self.listed)
        return super().handler(request)


def _insights_reply(body: dict[str, Any]) -> str:
    # A well-formed reply that copies the first finding's numbers (PR #178's checks pass).
    data = next(
        b["text"]
        for b in body.get("system", [])
        if b["text"].startswith(hosted_insights.FINDINGS_HEADER)
    )
    payload = json.loads(data[len(hosted_insights.FINDINGS_HEADER) :])
    first = (payload.get("findings") or [{}])[0]
    numbers = [str(v) for v in first.get("facts", {}).values() if isinstance(v, int)]
    text = "There are " + (numbers[0] if numbers else "no") + " open cases to watch."
    return json.dumps(
        {
            "summary": "The eligible cases are moving.",
            "notes": [{"id": first.get("id", "F1"), "text": text}],
            "actions": [],
        }
    )


@pytest.fixture
def insights_replies(monkeypatch: pytest.MonkeyPatch, hosted_replies: Any) -> Any:  # noqa: F811
    from tests import test_claude_runtime

    earlier = test_claude_runtime._lines

    def lines(body: dict[str, Any]) -> str:
        system = [block["text"] for block in body.get("system", [])]
        if any(text == hosted_insights.INSTRUCTIONS for text in system):
            return _insights_reply(body) + "\n"
        return earlier(body)

    monkeypatch.setattr(test_claude_runtime, "_lines", lines)
    return hosted_replies


class _ListGate:
    """The fifth path's case filter for these tests. Under D-139 the hosted policy admits no
    case to dashboard insights (it has no per-answer check; HOSTED_INSIGHTS_DECISION is None),
    so the path's own mechanics are tested with this explicit one-case filter."""

    def __init__(self) -> None:
        self.refs = frozenset({hashlib.sha256(str(test_hosting.CASE_ID).encode()).hexdigest()[:12]})

    def __call__(self, case_id: object, summary: object) -> str | None:
        ref = hashlib.sha256(str(case_id).encode()).hexdigest()[:12]
        return None if ref in self.refs else "NOT_LISTED"


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    # The test-only decision and the provider approval (C11: both are needed).
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_DECISION", DECISION)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_PROVIDERS", frozenset({"anthropic"}))
    monkeypatch.setattr(test_hosted_claude, "QUALIFICATION_CALLS", 3)


def _disable(monkeypatch: pytest.MonkeyPatch) -> None:
    # C11 P-B: the P-A state (every insights constant unset), for the "disabled" checks.
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_DECISION", None)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_PROVIDERS", frozenset())
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", None)
    monkeypatch.setattr(test_hosted_claude, "QUALIFICATION_CALLS", 2)


def _hosted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> Hosted:
    if enabled:
        _enable(monkeypatch)
    else:
        _disable(monkeypatch)
    hosted = Hosted(tmp_path, monkeypatch, InsightsClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    if enabled:
        hosted.client.app.state.case_gate = _ListGate()  # type: ignore[attr-defined]
    return hosted


def test_under_d139_the_hosted_policy_admits_no_case_to_insights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any
) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", None)
    hosted = Hosted(tmp_path, monkeypatch, InsightsClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    before = len(insights_bodies(hosted))
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 503
    assert reply.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"
    assert len(insights_bodies(hosted)) == before


@pytest.fixture
def enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any) -> Hosted:
    return _hosted(tmp_path, monkeypatch, enabled=True)


@pytest.fixture
def disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any) -> Hosted:
    return _hosted(tmp_path, monkeypatch, enabled=False)


def insights_bodies(hosted: Hosted) -> list[dict[str, Any]]:
    return [
        body
        for body in hosted.claude.messages
        if any(block["text"] == hosted_insights.INSTRUCTIONS for block in body.get("system", []))
    ]


# --- disabled by default: the hard server-side gate ---------------------------------------------


def test_c11_pb_the_code_enables_the_fifth_path_for_claude_only() -> None:
    from ai_assistant import config

    # C11 P-B (owner approval required): decision, Claude only, the aggregate rule.
    assert config.HOSTED_INSIGHTS_DECISION == "D-146"
    assert config.HOSTED_INSIGHTS_PROVIDERS == frozenset({"anthropic"})
    assert "openrouter" not in config.HOSTED_INSIGHTS_PROVIDERS
    assert config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION == "D-146"
    assert "dashboard_insights" not in config.HOSTED_CHAT_PATHS


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", GENERATE),
        ("GET", MODE),
        ("POST", "/assistant/dashboard/insights"),
        ("POST", GENERATE + "/"),
        ("GET", GENERATE),
    ],
)
def test_disabled_no_insights_route_answers_even_with_claude_active_and_a_key(
    disabled: Hosted, method: str, path: str
) -> None:
    hosted = disabled
    before = len(hosted.claude.requests)
    reply = hosted.client.request(method, path, headers=post_headers("rm-a"), json=FINDINGS)
    assert reply.status_code == 503
    assert reply.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"
    assert len(hosted.claude.requests) == before
    # D-142 R4 (R3-1): the general, Support and Try paths are closed to every external model.
    assert anthropic_runtime.hosted_qualification_turns() == ()


# --- enabled (test-only decision): one explicit call, eligible cases only, no names ----------


def test_mode_tells_the_panel_to_offer_generate_and_calls_nothing(enabled: Hosted) -> None:
    hosted = enabled
    before = len(hosted.claude.requests)
    reply = hosted.client.get(MODE, headers=post_headers("rm-a"))
    assert reply.status_code == 200, reply.text
    assert reply.json() == {"mode": "generate", "remaining_user": 3, "remaining_site": 10}
    assert len(hosted.claude.requests) == before


def test_generate_sends_only_enumerated_labels_and_counts_from_eligible_cases(
    enabled: Hosted,
) -> None:
    hosted = enabled
    before = len(insights_bodies(hosted))
    posts = hosted.claude.posts
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["insights"]["notes"] and body["insights"]["model"] == "claude-sonnet-5-5"
    assert hosted.claude.posts == posts + 1  # exactly one provider call
    sent = insights_bodies(hosted)[before:]
    assert len(sent) == 1
    request = sent[0]
    texts = [block["text"] for block in request["system"]]
    assert texts[0] == hosted_insights.INSTRUCTIONS and len(texts) == 2
    assert request["messages"] == [{"role": "user", "content": hosted_insights.QUESTION}]
    payload = json.loads(texts[1][len(hosted_insights.FINDINGS_HEADER) :])
    assert payload["period"] == hosted_insights.PERIOD
    text = json.dumps(request)
    for name in NAMES:
        assert name not in text, name
    assert str(test_hosting.CASE_ID) not in text and str(OTHER_CASE) not in text
    for finding in payload["findings"]:
        assert set(finding["facts"]) <= ALLOWED_FACT_KEYS
        for value in finding["facts"].values():
            assert (
                isinstance(value, int)
                or value
                in {
                    *hosted_insights.EXCEPTION_LABELS.values(),
                    hosted_insights.OTHER_EXCEPTION,
                    *hosted_insights.STAGE_LABELS.values(),
                    hosted_insights.OTHER_STAGE,
                    f"{hosted_insights.SLA_TARGET_DAYS} days",
                }
                or str(value).endswith("%")
            )
    # Only the eligible case counted: the other case (completed, another exception) left out.
    topics = {finding["topic"]: finding["facts"] for finding in payload["findings"]}
    assert topics["SLA_OVERDUE"]["open_cases"] == 1
    assert topics["WAITING_DRIVER"]["exception"] == "Document conflicts with registry"
    assert "ZERO_TOUCH" not in topics


def test_a_case_on_the_list_but_unreadable_or_refused_is_never_counted(
    enabled: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = enabled
    gate = hosted.client.app.state.case_gate
    other_ref = hashlib.sha256(str(OTHER_CASE).encode()).hexdigest()[:12]
    monkeypatch.setattr(gate, "refs", frozenset(gate.refs | {other_ref}))
    before = len(insights_bodies(hosted))
    assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 200
    sent = insights_bodies(hosted)[before]["system"][1]["text"]
    payload = json.loads(sent[len(hosted_insights.FINDINGS_HEADER) :])
    topics = {finding["topic"]: finding["facts"] for finding in payload["findings"]}
    assert topics["SLA_OVERDUE"]["open_cases"] == 1 and "ZERO_TOUCH" not in topics


def test_no_eligible_case_means_no_call(enabled: Hosted) -> None:
    hosted = enabled
    hosted.clm.listed = [hosted.clm.listed[1]]  # only the excluded case is visible
    posts = hosted.claude.posts
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 503 and hosted.claude.posts == posts


def test_access_is_unchanged(enabled: Hosted) -> None:
    hosted = enabled
    posts = hosted.claude.posts
    assert hosted.client.post(GENERATE, headers={"origin": test_hosting.ORIGIN}).status_code == 401
    assert hosted.client.post(GENERATE, headers=post_headers("hr")).status_code == 403
    assert (
        hosted.client.post(
            GENERATE, headers=test_hosting.session("rm-a", origin="https://evil.example")
        ).status_code
        == 403
    )
    assert hosted.claude.posts == posts


def test_the_ticket_is_single_use_for_exactly_these_messages(
    enabled: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant import synthetic_eligibility

    hosted = enabled
    approved: list[str] = []
    real = synthetic_eligibility.approve

    def counting(messages: list[dict[str, str]]) -> None:
        approved.append(json.dumps(messages))
        real(messages)

    monkeypatch.setattr("ai_assistant.main.synthetic_eligibility_approve", counting)
    assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 200
    assert len(approved) == 1
    sent = insights_bodies(hosted)[-1]
    assert json.loads(approved[0])[1]["content"] == sent["system"][1]["text"]
    assert synthetic_eligibility.admitted(json.loads(approved[0])) is False  # already spent


def test_a_cached_reply_makes_no_call_and_is_not_counted(enabled: Hosted) -> None:
    hosted = enabled
    assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 200
    posts = hosted.claude.posts
    again = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert again.status_code == 200 and hosted.claude.posts == posts
    assert hosted.client.get(MODE, headers=post_headers("rm-a")).json()["remaining_user"] == 2


def test_three_per_user_per_day(enabled: Hosted, monkeypatch: pytest.MonkeyPatch) -> None:
    hosted = enabled
    monkeypatch.setattr(hosted_insights, "CACHE_SECONDS", 0)  # every request is new
    for _ in range(3):
        assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 200
    posts = hosted.claude.posts
    fourth = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert fourth.status_code == 429
    assert fourth.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_LIMIT"
    assert hosted.claude.posts == posts
    assert hosted.client.get(MODE, headers=post_headers("rm-a")).json()["remaining_user"] == 0


def test_the_limits_survive_a_restart_and_reset_at_singapore_midnight(tmp_path: Path) -> None:
    now = [datetime(2026, 11, 14, 15, 59, tzinfo=UTC)]  # 23:59 in Singapore
    store = tmp_path / "limits.sqlite3"
    limits = hosted_insights.DailyLimits(store, clock=lambda: now[0])
    for user in ("a", "b", "c"):
        for _ in range(3):
            limits.reserve(user)
    limits.reserve("d")
    with pytest.raises(hosted_insights.LimitReached) as user_limit:
        limits.reserve("a")
    assert user_limit.value.scope == "user"
    with pytest.raises(hosted_insights.LimitReached) as site_limit:
        limits.reserve("e")  # 10 site-wide already
    assert site_limit.value.scope == "site"
    restarted = hosted_insights.DailyLimits(store, clock=lambda: now[0])
    assert restarted.used("a") == (3, 10)
    now[0] = now[0] + timedelta(minutes=2)  # 00:01 the next Singapore day
    assert restarted.used("a") == (0, 0)
    restarted.reserve("a")


@pytest.mark.parametrize(
    "fault",
    [{"status": 500}, {"status": 429}, {"reply_model": "claude-opus-5-5"}, {"finished": False}],
)
def test_a_provider_failure_is_the_unavailable_response_and_no_other_model(
    enabled: Hosted, monkeypatch: pytest.MonkeyPatch, fault: dict[str, Any]
) -> None:
    from ai_assistant.dashboard_insights import DashboardInsights

    hosted = enabled
    monkeypatch.setattr(
        DashboardInsights, "write", lambda *a, **k: pytest.fail("PR #178's route was used")
    )
    monkeypatch.setattr(
        hosted.selector, "local_fallback", lambda: pytest.fail("a local model was considered")
    )
    for name, value in fault.items():
        setattr(hosted.claude, name, value)
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 503
    assert reply.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"


def test_a_reply_that_fails_pr178s_checks_is_the_unavailable_response(
    enabled: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests import test_claude_runtime

    hosted = enabled
    earlier = test_claude_runtime._lines

    def lines(body: dict[str, Any]) -> str:
        if any(b["text"] == hosted_insights.INSTRUCTIONS for b in body.get("system", [])):
            return json.dumps(
                {"summary": "Approve all 99 cases now.", "notes": [{"id": "F1", "text": "999"}]}
            )
        return earlier(body)

    monkeypatch.setattr(test_claude_runtime, "_lines", lines)
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 503


def test_the_qualification_adds_the_fifth_turn_only_when_enabled(enabled: Hosted) -> None:
    hosted = enabled
    # D-142 R4: only the service-built insights turn remains beside the case chat.
    assert anthropic_runtime.hosted_qualification_turns() == ("H-D1",)
    # The enabled fixture qualified with three calls; the third was the insights prompt.
    assert len(insights_bodies(hosted)) >= 1
    overview = hosted.hr("GET", "").json()
    assert overview["active"]["profile_id"] == BALANCED.profile_id


# --- unchanged elsewhere --------------------------------------------------------------------------


def test_outside_the_hosted_service_pr178_is_unchanged(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from ai_assistant.main import create_app

    settings = test_hosting.hosted_settings(tmp_path)
    app = create_app(settings, clm_transport=httpx.MockTransport(test_hosting.Clm().handler))
    client = TestClient(app, base_url="http://clm-assistant-proxy:8100")
    assert client.get(MODE, headers=post_headers("rm-a")).json() == {
        "mode": "auto",
        "remaining_user": None,
        "remaining_site": None,
    }
    assert client.post(GENERATE, headers=post_headers("rm-a")).status_code == 404


def test_derive_uses_only_the_enumerated_fields() -> None:
    now = datetime(2026, 11, 14, tzinfo=UTC)
    request = hosted_insights.derive(
        [
            {
                "status": "WAITING_FOR_REVIEW",
                "current_stage": "OWNERSHIP",
                "created_at": "2026-11-01T00:00:00Z",
                "human_interventions": 1,
                "active_exception_types": ["NOT_A_KNOWN_TYPE"],
                "legal_name": "Secret Holdings",
                "team_id": "team-z",
            },
            {
                "status": "COMPLETED",
                "current_stage": "COMPLETE",
                "created_at": "2026-11-12T00:00:00Z",
                "human_interventions": 0,
                "active_exception_types": [],
            },
        ],
        now,
    )
    assert request is not None
    text = request.model_dump_json()
    assert "Secret" not in text and "team-z" not in text
    facts = {f.topic: f.facts for f in request.findings}
    assert facts["SLA_OVERDUE"] == {
        "open_cases": 1,
        "overdue_cases": 1,
        "at_risk_cases": 0,
        "target": "10 days",
    }
    assert facts["WAITING_DRIVER"]["exception"] == hosted_insights.OTHER_EXCEPTION
    assert facts["STOP_HOTSPOT"] == {"step": "Ownership", "open_cases_there": 1}
    assert facts["ZERO_TOUCH"] == {"completed_cases": 1, "zero_touch_rate": "100%"}
    assert all(isinstance(f, InsightFinding) for f in request.findings)
    assert hosted_insights.derive([], now) is None


# --- C11 P-A: enabling later is a reviewed constant change; until then nothing changes ----------


def test_c11_the_decision_without_an_approved_provider_still_refuses_and_calls_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any
) -> None:
    _disable(monkeypatch)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_DECISION", DECISION)
    hosted = Hosted(tmp_path, monkeypatch, InsightsClm())  # 2-call qualification: no H-D1
    hosted.setup_claude()
    hosted.qualify_and_activate()
    hosted.client.app.state.case_gate = _ListGate()  # type: ignore[attr-defined]
    assert anthropic_runtime.hosted_qualification_turns() == ()
    before = len(hosted.claude.requests)
    for method, path in (("GET", MODE), ("POST", GENERATE)):
        reply = hosted.client.request(method, path, headers=post_headers("rm-a"))
        assert reply.status_code == 503
        assert reply.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"
    assert len(hosted.claude.requests) == before
    assert insights_bodies(hosted) == []


def test_c11_the_hosted_policy_admits_no_case_until_the_aggregate_rule_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from assistant_hosting.eligibility import INSIGHTS_REFUSAL, CasePolicy

    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", None)
    policy = CasePolicy()
    assert policy.aggregate is False
    assert policy(test_hosting.CASE_ID, test_hosting.SUMMARY) == INSIGHTS_REFUSAL
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", "TEST-OD-I2")
    assert policy.aggregate is True
    assert policy(test_hosting.CASE_ID, test_hosting.SUMMARY) is None  # ACRA in MOCK mode
    assert policy(test_hosting.CASE_ID, None) == INSIGHTS_REFUSAL  # unreadable: never counted
    # D-146 C11-2: a summary without registry provenance is uncertain: never counted.
    assert policy(test_hosting.CASE_ID, {"status": "RUNNING"}) == INSIGHTS_REFUSAL
    # The case chat's per-answer external-inference policy is not touched by the rule.
    assert policy.data_policy("anthropic") == "synthetic_only"


def test_c11_eligible_items_drops_the_retired_list_only_under_the_aggregate_rule() -> None:
    first, second = uuid4(), uuid4()
    items = [{"case_id": str(first)}, {"case_id": str(second)}, {"case_id": "not-a-uuid"}, "x"]
    read: list[object] = []

    def load(case_id: object) -> object:
        read.append(case_id)
        if case_id == second:
            raise RuntimeError("404")
        return {"status": "RUNNING"}

    admit = lambda case_id, summary: None  # noqa: E731
    assert hosted_insights.eligible_items(items, admit, frozenset(), load) == []
    assert read == []  # without the rule nothing is even read
    kept = hosted_insights.eligible_items(items, admit, frozenset(), load, aggregate=True)
    assert kept == [{"case_id": str(first)}] and read == [first, second]


def test_c11_with_the_aggregate_rule_the_real_policy_counts_session_visible_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any
) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", "TEST-OD-I2")
    hosted = Hosted(tmp_path, monkeypatch, InsightsClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()  # the real CasePolicy from harden() stays installed
    posts = hosted.claude.posts
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 200, reply.text
    assert hosted.claude.posts == posts + 1
    sent = insights_bodies(hosted)[-1]
    text = json.dumps(sent)
    for name in NAMES:
        assert name not in text, name
    assert str(test_hosting.CASE_ID) not in text and str(OTHER_CASE) not in text
    payload = json.loads(sent["system"][1]["text"][len(hosted_insights.FINDINGS_HEADER) :])
    for finding in payload["findings"]:
        assert set(finding["facts"]) <= ALLOWED_FACT_KEYS
        assert all(isinstance(v, int | str) for v in finding["facts"].values())


def test_c11_pb_with_the_code_values_load_calls_nothing_and_generate_calls_once(
    tmp_path: Path, insights_replies: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No monkeypatched constant: exactly what P-B ships (with the real hosted CasePolicy).
    hosted = Hosted(tmp_path, monkeypatch, InsightsClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    assert anthropic_runtime.hosted_qualification_turns() == ("H-D1",)
    posts = hosted.claude.posts
    mode = hosted.client.get(MODE, headers=post_headers("rm-a"))
    assert mode.json() == {"mode": "generate", "remaining_user": 3, "remaining_site": 10}
    assert hosted.claude.posts == posts  # page load: no call
    assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 200
    assert hosted.claude.posts == posts + 1
    # PR #178's own route stays refused on the hosted service.
    assert hosted.client.post(
        "/assistant/dashboard/insights", headers=post_headers("rm-a"), json=FINDINGS
    ).status_code == 503
    assert hosted.claude.posts == posts + 1


def test_c11_the_qualification_records_the_insights_path(enabled: Hosted) -> None:
    hosted = enabled
    active = hosted.selector.current()
    item = hosted.selector.store.qualification(active.qualification_id)
    assert item is not None and item["status"] == "passed"
    assert {"case_chat", "dashboard_insights"} <= set(item["summary"]["paths"])


def test_c11_a_qualification_without_the_insights_turn_never_writes_insights(
    enabled: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = enabled
    store = hosted.selector.store
    real = store.qualification

    def without(qualification_id: str) -> Any:
        item = real(qualification_id)
        if item and item.get("summary"):
            item["summary"]["paths"] = ["case_chat"]
        return item

    monkeypatch.setattr(store, "qualification", without)
    posts = hosted.claude.posts
    assert hosted.client.get(MODE, headers=post_headers("rm-a")).json()["mode"] == "off"
    assert hosted.client.post(GENERATE, headers=post_headers("rm-a")).status_code == 503
    assert hosted.claude.posts == posts


def test_c11_the_trend_finding_is_counts_per_week_only() -> None:
    now = datetime(2026, 11, 19, tzinfo=UTC)
    request = hosted_insights.derive(
        [
            {"status": "RUNNING", "created_at": "2026-11-17T00:00:00Z", "legal_name": "Secret"},
            {"status": "RUNNING", "created_at": "2026-11-09T00:00:00Z"},
            {
                "status": "COMPLETED",
                "created_at": "2026-11-01T00:00:00Z",
                "completed_at": "2026-11-18T00:00:00Z",
            },
        ],
        now,
    )
    assert request is not None
    facts = {f.topic: f.facts for f in request.findings}
    assert facts["TURNAROUND"] == {
        "new_this_week": 1,
        "new_last_week": 1,
        "completed_this_week": 1,
        "completed_last_week": 0,
    }
    assert "Secret" not in request.model_dump_json()
    old = hosted_insights.derive([{"status": "RUNNING", "created_at": "2026-01-01T00:00:00Z"}], now)
    assert old is not None and "TURNAROUND" not in {f.topic for f in old.findings}


# D-139: these tests treat the fixture case as verified synthetic (the seam in conftest);
# test_hosted_case_policy.py runs the real provenance check.
pytestmark = pytest.mark.usefixtures("hosted_case_eligible")


# --- D-146 C11-2 (owner decision 2): synthetic-provenance aggregates only ----------------------

SANDBOX_CASE = uuid4()
UNKNOWN_CASE = uuid4()


def _summary_with(change: Any) -> dict[str, Any]:
    import copy

    summary = copy.deepcopy(test_hosting.SUMMARY)
    change(summary["case"])
    return summary


def _sandbox(case: dict[str, Any]) -> None:
    case["entity"]["source"]["environment"] = "SANDBOX"


def _unknown(case: dict[str, Any]) -> None:
    case["entity"].pop("source", None)


class MixedClm(InsightsClm):
    """The synthetic fixture case plus two readable cases of the same shape: one from ACRA
    Sandbox (sponsor data) and one with no registry provenance (uncertain)."""

    def __init__(self) -> None:
        super().__init__()
        self.summaries = {
            SANDBOX_CASE: _summary_with(_sandbox),
            UNKNOWN_CASE: _summary_with(_unknown),
        }
        self.listed = [
            _item(test_hosting.CASE_ID),
            _item(SANDBOX_CASE, legal_name="Sandbox Holdings Pte Ltd"),
            _item(UNKNOWN_CASE, legal_name="Unknown Origin Pte Ltd"),
        ]

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        if token in test_hosting.SESSIONS:
            for case_id, summary in self.summaries.items():
                if request.url.path == f"/api/clm/zero-touch/cases/{case_id}":
                    return httpx.Response(200, json=summary)
        return super().handler(request)


def test_c11_2_the_real_policy_admits_only_acra_mock_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from assistant_hosting.eligibility import INSIGHTS_REFUSAL, CasePolicy

    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", "TEST-OD-I2")
    policy = CasePolicy()

    def officer_sandbox(case: dict[str, Any]) -> None:
        case["registry_acquisition"]["officers"] = [
            {"provenance": {"provider": "ACRA", "environment": "SANDBOX"}}
        ]

    def officer_unknown(case: dict[str, Any]) -> None:
        case["registry_acquisition"]["officers"] = [{"provenance": None}]

    def other_registry(case: dict[str, Any]) -> None:
        case["entity"]["source"]["source_system"] = "OTHER"

    assert policy(test_hosting.CASE_ID, test_hosting.SUMMARY) is None
    for change in (_sandbox, _unknown, officer_sandbox, officer_unknown, other_registry):
        assert policy(test_hosting.CASE_ID, _summary_with(change)) == INSIGHTS_REFUSAL, change
    for summary in ({}, {"case": None}, [], "x"):
        assert policy(test_hosting.CASE_ID, summary) == INSIGHTS_REFUSAL


def _aggregate_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clm: InsightsClm
) -> tuple[Hosted, Any]:
    tmp_path.mkdir()
    _enable(monkeypatch)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", "TEST-OD-I2")
    hosted = Hosted(tmp_path, monkeypatch, clm)
    hosted.setup_claude()
    hosted.qualify_and_activate()  # the real CasePolicy from harden() stays installed
    return hosted, hosted.client.post(GENERATE, headers=post_headers("rm-a"))


def test_c11_2_mixed_cases_count_only_the_synthetic_one_and_the_payload_is_otherwise_equal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any
) -> None:
    only = InsightsClm()
    only.listed = [_item(test_hosting.CASE_ID)]
    synthetic, reply = _aggregate_payload(tmp_path / "only", monkeypatch, only)
    assert reply.status_code == 200, reply.text
    expected = insights_bodies(synthetic)[-1]

    hosted, reply = _aggregate_payload(tmp_path / "mixed", monkeypatch, MixedClm())
    assert reply.status_code == 200, reply.text
    sent = insights_bodies(hosted)[-1]
    payload = json.loads(sent["system"][1]["text"][len(hosted_insights.FINDINGS_HEADER) :])
    topics = {finding["topic"]: finding["facts"] for finding in payload["findings"]}
    assert topics["SLA_OVERDUE"]["open_cases"] == 1  # not 3: Sandbox and unknown left out
    # The same labels and counts as when only the synthetic case is visible: nothing else moves.
    assert sent["system"] == expected["system"] and sent["messages"] == expected["messages"]
    text = json.dumps(sent)
    for case_id in (test_hosting.CASE_ID, SANDBOX_CASE, UNKNOWN_CASE):
        assert str(case_id) not in text
    assert "Sandbox" not in text and "Unknown Origin" not in text


def test_c11_2_only_non_synthetic_cases_means_the_fallback_and_no_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, insights_replies: Any
) -> None:
    clm = MixedClm()
    clm.listed = clm.listed[1:]  # Sandbox and unknown provenance only
    _enable(monkeypatch)
    monkeypatch.setattr("ai_assistant.config.HOSTED_INSIGHTS_ELIGIBILITY_DECISION", "TEST-OD-I2")
    hosted = Hosted(tmp_path, monkeypatch, clm)
    hosted.setup_claude()
    hosted.qualify_and_activate()
    posts = hosted.claude.posts
    before = len(insights_bodies(hosted))
    reply = hosted.client.post(GENERATE, headers=post_headers("rm-a"))
    assert reply.status_code == 503
    assert reply.json()["detail"]["code"] == "DASHBOARD_INSIGHTS_UNAVAILABLE"
    assert hosted.claude.posts == posts and len(insights_bodies(hosted)) == before
