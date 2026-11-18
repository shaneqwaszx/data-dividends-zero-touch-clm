"""Data access policy ("Restrict AI to verified synthetic cases") and the live Garden Business
prompt, offline: the fake CLM backend, a mock OpenRouter, a mock Anthropic API, a counting local
baseline and synthetic fixtures only. The suite guard refuses any non-local connection and
nothing spends."""

import copy
import sqlite3
import threading
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import (
    anthropic_runtime,
    data_access,
    privacy_boundary,
    remote_test,
    synthetic_eligibility,
)
from ai_assistant.anthropic_runtime import NOTICES as CLAUDE_NOTICES
from ai_assistant.context import build_case_facts
from ai_assistant.data_access import IT_NOTICES, LOCAL_NOTICES, SyntheticOnlyModel
from ai_assistant.guardrails import validate_answer
from ai_assistant.llm import LlmUnavailableError, ModelCallError
from ai_assistant.main import INTENT_NOTICE, REMOTE_ELIGIBILITY_NOTICE, create_app
from ai_assistant.model_admin import MESSAGES
from ai_assistant.model_admin_store import ModelAdminStore, RevisionConflict
from ai_assistant.model_profiles import ProfileConfigError
from ai_assistant.model_qualification import BASIS_FILES
from ai_assistant.prompts import build_messages
from ai_assistant.synthetic_boundary import check as d094_check
from ai_assistant.synthetic_boundary import check_messages
from ai_assistant.synthetic_eligibility import check
from tests.test_claude_runtime import Claude, ClaudeJourney, claude_config, claude_ledger
from tests.test_claude_runtime import _ask as ask_claude
from tests.test_claude_runtime import _model as claude_model
from tests.test_model_management import API, CASE_ID, ORIGIN, Backend, Baseline
from tests.test_remote_test import Journey, OpenRouter, config
from tests.test_synthetic_eligibility import (
    D095,
    GARDEN,
    _fixture,
    _snapshot,
    _tampered,
    digests_for,
    serve,
)
from tests.test_synthetic_eligibility import _model as openrouter_model

POLICY = f"{API}/data-access"
ACTION = "DATA_ACCESS_POLICY_CHANGED"
# The event the backend adds once onboarding intelligence is evaluated
# (apps/backend/app/services/zero_touch_orchestration.py); the saved fixtures predate it.
V1_EVENT = "Advisory onboarding intelligence was evaluated under policy catalogue v1."
QUESTION = "What should I do next?"


def live_garden() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The Garden case as a live onboarding shows it: the tracked Garden fixture document and
    the onboarding intelligence event (``v1``) at the end of the timeline."""

    summary, documents = copy.deepcopy(GARDEN)
    last = summary["timeline"][-1]
    summary["timeline"].append(
        {
            **last,
            "sequence": int(last["sequence"]) + 1,
            "event_type": "INTELLIGENCE_EVALUATED",
            "code": "INTELLIGENCE_EVALUATED",
            "message": V1_EVENT,
        }
    )
    return summary, documents


LIVE_GARDEN = live_garden()
# A non-synthetic company with no document: what an authorised real case looks like here.
REAL = copy.deepcopy(LIVE_GARDEN)
for _case in (REAL[0]["case"], REAL[0]["clm"]["case"]):
    _case["entity"]["source"]["environment"] = "LIVE"
REAL = (REAL[0], [])


def _messages(case: Any = LIVE_GARDEN, question: str = QUESTION) -> tuple[Any, Any, Any]:
    snapshot = _snapshot(case)
    facts = build_case_facts(snapshot)
    return snapshot, facts, build_messages(facts, [], question)


def _put(journey: Journey, **body: Any) -> httpx.Response:
    return journey.client.put(POLICY, json=body)


def _restrict(journey: Journey, *, revision: int = 0) -> dict[str, Any]:
    reply = _put(journey, expected_revision=revision, restrict_local=True)
    assert reply.status_code == 200, reply.text
    return reply.json()


def _events(journey: Journey) -> list[dict[str, Any]]:
    return [e for e in journey.client.get(f"{API}/audit").json()["events"] if e["action"] == ACTION]


# --- Phase 5: the live Garden prompt (the ``v1`` refusal) ---------------------------------------


def test_the_live_garden_prompt_carries_v1_in_the_system_facts() -> None:
    _, _, messages = _messages()
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert V1_EVENT in system


def test_d094_still_refuses_the_live_garden_prompt_for_the_v1_token() -> None:
    # D-094 is the fixed-fixture regression mode: its vocabulary never held "v1", so the live
    # timeline event is outside its boundary. This is why every live Garden question was refused.
    snapshot, facts, messages = _messages()
    assert d094_check(snapshot, facts, messages, []) is not None
    assert check_messages(messages) == "SYNTHETIC_TEXT_NOT_APPROVED"
    without = [
        {**m, "content": m["content"].replace(V1_EVENT, "")} if m["role"] == "system" else m
        for m in messages
    ]
    assert check_messages(without) is None  # "v1" is the only word outside the boundary


def test_d095_admits_the_genuinely_eligible_live_garden_prompt() -> None:
    snapshot, facts, messages = _messages()
    assert check(snapshot, facts, messages, [], digests=digests_for(GARDEN[1])) is None
    assert synthetic_eligibility.admitted(messages)


@pytest.mark.parametrize(
    ("case", "digests", "question", "code"),
    [
        (REAL, [], QUESTION, "SYNTHETIC_CASE_NOT_APPROVED"),
        (
            LIVE_GARDEN,
            "tampered",
            QUESTION,
            "SYNTHETIC_DOCUMENT_NOT_VERIFIED",
        ),
        (LIVE_GARDEN, "missing", QUESTION, "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE"),
        (
            LIVE_GARDEN,
            None,
            "Is Tan Ah Kow, NRIC S1234567D, a director here?",
            "SYNTHETIC_TEXT_NOT_APPROVED",
        ),
        (LIVE_GARDEN, None, "Email jane.doe@example.com the report", "SYNTHETIC_TEXT_NOT_APPROVED"),
    ],
)
def test_the_live_garden_prompt_is_still_refused_when_not_genuinely_eligible(
    case: Any, digests: Any, question: str, code: str
) -> None:
    snapshot, facts, messages = _messages(case, question)
    name = GARDEN[1][0]["display_name"]
    if digests == "tampered":
        digests = digests_for(GARDEN[1], **{name: _tampered(_fixture(name))})
    elif digests == "missing":
        digests = None
    elif digests is None:
        digests = digests_for(GARDEN[1])
    assert check(snapshot, facts, messages, [], digests=digests) == code
    assert not synthetic_eligibility.admitted(messages)


def test_the_same_live_garden_prompt_is_eligible_for_gpt_oss_and_claude(tmp_path: Path) -> None:
    # Equivalent shared policy: one eligibility check, then each provider's own runtime takes
    # the same exact messages with their single-use ticket.
    snapshot, facts, messages = _messages()
    openrouter = OpenRouter()
    gpt_oss = openrouter_model(tmp_path / "openrouter", openrouter)
    assert check(snapshot, facts, messages, [], digests=digests_for(GARDEN[1])) is None
    gpt_oss.complete(privacy_boundary.admit(messages, person_written=False))  # R1, R4
    assert len(openrouter.chats) == 1

    settings = claude_config(tmp_path / "anthropic", **D095)
    claude_ledger(settings)
    claude = Claude()
    assert check(snapshot, facts, messages, [], digests=digests_for(GARDEN[1])) is None
    pieces, error = ask_claude(claude_model(settings, claude), messages)
    assert error is None and claude.posts == 1
    # Approved-line output restriction intact: only lines the guard allows are shown.
    text = "".join(piece.text for piece in pieces)
    validation = validate_answer(text, facts)
    assert validation.text and all(line in text for line in validation.text.splitlines())


# --- D-104 A1: provider-neutral D-095 mode -----------------------------------------------------

NO_OPENROUTER = {"local_api_test_owner_attests": "", "openrouter_endpoint": ""}


def test_claude_admits_the_live_garden_prompt_without_any_openrouter_configuration(
    tmp_path: Path,
) -> None:
    # Neither the OpenRouter attestations nor its endpoint are configured: GPT-OSS is not
    # ready and its D-095 mode is off, but Claude's (on the shared interlocks) is on.
    settings = claude_config(tmp_path, **D095, **NO_OPENROUTER)
    assert remote_test.readiness(settings) is not None
    assert not synthetic_eligibility.mode(settings)
    assert synthetic_eligibility.shared_mode(settings)
    assert anthropic_runtime.readiness(settings) is None
    claude_ledger(settings)
    claude = Claude()
    model = claude_model(settings, claude)
    assert model.development_mode()
    snapshot, facts, messages = _messages()
    assert check(snapshot, facts, messages, [], digests=digests_for(GARDEN[1])) is None
    _, error = ask_claude(model, messages)
    assert error is None and claude.posts == 1
    _, error = ask_claude(model, messages)  # the ticket was used once
    assert error is not None and claude.posts == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"local_api_test_owner_attests": ""},
        {"openrouter_endpoint": ""},
        {"local_api_test_owner_attests": "auto_topup_off"},
    ],
)
def test_gpt_oss_keeps_every_openrouter_requirement(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    settings = config(tmp_path, **D095, **changes)
    assert synthetic_eligibility.shared_mode(settings)
    assert remote_test.readiness(settings) is not None
    assert not synthetic_eligibility.mode(settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"synthetic_dev_decision": ""},
        {"local_api_test_decision": ""},
        {"remote_inference_decision": ""},
        {"remote_live_decision": ""},
        {"llm_enabled": False},
        {"clm_backend_url": "http://10.0.0.5:8000"},
        {"allowed_origins": ["https://clm.example.com"]},
        {"allowed_origins": []},
    ],
)
def test_the_shared_d095_mode_needs_every_shared_interlock(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    assert synthetic_eligibility.shared_mode(claude_config(tmp_path, **D095))
    assert not synthetic_eligibility.shared_mode(claude_config(tmp_path, **{**D095, **changes}))


def test_claude_keeps_its_own_safeguards_under_the_shared_mode(tmp_path: Path) -> None:
    for changes, code in (
        ({"anthropic_owner_attests": ""}, "ANTHROPIC_ATTESTATION_MISSING"),
        ({"anthropic_workspace_id": ""}, "WORKSPACE_NOT_ATTESTED"),
        ({"anthropic_decision": ""}, "ANTHROPIC_NOT_AUTHORISED"),
    ):
        settings = claude_config(tmp_path, **D095, **NO_OPENROUTER, **changes)
        assert synthetic_eligibility.shared_mode(settings)
        assert anthropic_runtime.readiness(settings) == code
        with pytest.raises(ProfileConfigError):
            claude_model(settings, Claude())


def test_the_same_ineligible_prompt_is_refused_for_both_providers(tmp_path: Path) -> None:
    name = GARDEN[1][0]["display_name"]
    tampered = digests_for(GARDEN[1], **{name: _tampered(_fixture(name))})
    snapshot, facts, messages = _messages()
    openrouter = OpenRouter()
    gpt_oss = openrouter_model(tmp_path / "openrouter", openrouter)
    settings = claude_config(tmp_path / "anthropic", **D095)
    claude_ledger(settings)
    claude = Claude()
    claude_side = claude_model(settings, claude)
    for _ in range(2):  # one check per provider: the same closed reason, no ticket
        assert check(snapshot, facts, messages, [], digests=tampered) == (
            "SYNTHETIC_DOCUMENT_NOT_VERIFIED"
        )
    with pytest.raises(ModelCallError):
        gpt_oss.complete(messages)
    _, error = ask_claude(claude_side, messages)
    assert error is not None
    assert openrouter.chats == [] and claude.requests == []


def test_the_rm_chat_uses_claude_on_live_garden_without_openrouter_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, **D095, **NO_OPENROUTER)
    journey.activate_claude()
    sent = journey.claude.posts
    serve(monkeypatch, LIVE_GARDEN)
    reply = journey.ask(stream=True)
    assert reply["answered_by"] == "model", reply
    assert reply["notice"].startswith(CLAUDE_NOTICES.dev_answered)
    assert journey.claude.posts == sent + 1
    name = GARDEN[1][0]["display_name"]
    for case, digests, question in (
        (LIVE_GARDEN, digests_for(GARDEN[1], **{name: _tampered(_fixture(name))}), QUESTION),
        (REAL, [], QUESTION),
        (LIVE_GARDEN, None, "Is Tan Ah Kow, NRIC S1234567D, a director?"),
    ):
        serve(monkeypatch, case, digests)
        reply = journey.ask(question, stream=True)
        assert reply["answered_by"] == "case_data"
        # D-142 R4: a question with no supported intent is refused before the eligibility check.
        assert reply["notice"].startswith((CLAUDE_NOTICES.eligibility, INTENT_NOTICE))
    assert journey.claude.posts == sent + 1
    assert journey.openrouter.chats == [] and journey.baseline.calls == 0


# --- Phase 2: the HR policy ----------------------------------------------------------------------


def test_the_default_policy_is_todays_behaviour_and_external_models_are_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    view = journey.client.get(POLICY).json()
    assert view["status"] == "default" and view["revision"] == 0
    assert view["classes"] == [
        {"provider_class": "openrouter", "restricted": True, "locked": True},
        {"provider_class": "anthropic", "restricted": True, "locked": True},
        {"provider_class": "it_configured", "restricted": True, "locked": True},
        {"provider_class": "local_internal", "restricted": False, "locked": False},
    ]
    assert view["active_class"] == "local_internal" and not view["active_restricted"]
    assert view["verification"] == "D-095"
    assert journey.client.get(API).json()["data_access"] == view
    (tmp_path / "d094").mkdir()
    d094 = Journey(tmp_path / "d094", monkeypatch)
    assert d094.client.get(POLICY).json()["verification"] == "D-094"


def test_hr_restricts_and_broadening_needs_confirmation_all_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    view = _restrict(journey)
    assert view["status"] == "stored" and view["revision"] == 1 and view["active_restricted"]
    refused = _put(journey, expected_revision=1, restrict_local=False)
    assert refused.status_code == 400
    assert refused.json()["detail"]["code"] == "WIDEN_CONFIRMATION_REQUIRED"
    assert journey.client.get(POLICY).json()["revision"] == 1
    applied = _put(journey, expected_revision=1, restrict_local=False, confirm_widen=True)
    assert applied.status_code == 200 and not applied.json()["active_restricted"]
    events = _events(journey)
    assert [(e["outcome"], e["code"], e["actor"], e["revision"]) for e in reversed(events)] == [
        ("applied", "LOCAL_DEFAULT_ALL_CASES_TO_LOCAL_SYNTHETIC_ONLY", "hr-admin", 1),
        ("refused", "WIDEN_CONFIRMATION_REQUIRED", "hr-admin", None),
        ("applied", "LOCAL_SYNTHETIC_ONLY_TO_LOCAL_ALL_CASES", "hr-admin", 2),
    ]
    assert all(e["at"] for e in events)


def test_external_models_cannot_be_unrestricted_by_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    for body in (
        {"expected_revision": 0, "restrict_local": False, "restrict_external": False},
        {
            "expected_revision": 0,
            "restrict_local": False,
            "restrict_external": False,
            "confirm_widen": True,
        },
    ):
        reply = _put(journey, **body)
        assert reply.status_code == 409
        assert reply.json()["detail"]["code"] == "EXTERNAL_DATA_POLICY_LOCKED"
    # No other field can name a provider or carry a different shape.
    for body in (
        {"expected_revision": 0, "restrict_local": False, "restrict_openrouter": False},
        {"expected_revision": 0, "restrict_local": "false"},
        {"expected_revision": 0, "restrict_local": 0},
        {"expected_revision": -1, "restrict_local": True},
        {"expected_revision": 0},
    ):
        assert _put(journey, **body).status_code == 422
    assert journey.client.get(POLICY).json()["status"] == "default"


def test_a_stale_view_is_refused_and_nothing_is_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    _restrict(journey)
    stale = _put(journey, expected_revision=0, restrict_local=False, confirm_widen=True)
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "DATA_ACCESS_POLICY_CONFLICT"
    assert journey.client.get(POLICY).json()["classes"][3]["restricted"]


def test_only_hr_may_read_or_change_the_policy_from_the_ai_models_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    for session in ("rm-session", "co-session", "director-session"):
        journey.client.cookies.set("clm_session", session)
        assert journey.client.get(POLICY).status_code == 403
        reply = _put(journey, expected_revision=0, restrict_local=True)
        assert reply.status_code == 403
        assert reply.json()["detail"]["code"] == "MODEL_CONFIG_FORBIDDEN"
    journey.client.cookies.set("clm_session", "hr-session")
    no_origin = TestClient(journey.app)
    no_origin.cookies.set("clm_session", "hr-session")
    reply = no_origin.put(POLICY, json={"expected_revision": 0, "restrict_local": True})
    assert reply.status_code == 403 and reply.json()["detail"]["code"] == "ORIGIN_REQUIRED"
    assert journey.client.get(POLICY).json()["status"] == "default"


def test_the_policy_survives_a_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    _restrict(journey)
    restarted = create_app(journey.settings)
    selector = restarted.state.model_selector
    assert data_access.local_restricted(selector.data_access_policy())
    assert isinstance(selector.current().model, SyntheticOnlyModel)


def test_an_unreadable_policy_restricts_local_models_and_refuses_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    with sqlite3.connect(journey.settings.model_admin_db_path) as db:
        # A row no writer could store (the table's CHECK refuses it): tampered or corrupted.
        db.execute("DROP TABLE data_access_policy")
        db.execute(
            "CREATE TABLE data_access_policy (id INTEGER PRIMARY KEY, revision INTEGER,"
            " local_restricted INTEGER, changed_at TEXT, changed_by TEXT)"
        )
        db.execute("INSERT INTO data_access_policy VALUES (1, 3, 7, 'x', 'y')")
    view = journey.client.get(POLICY).json()
    assert view["status"] == "unavailable" and view["classes"][3]["restricted"]
    reply = _put(journey, expected_revision=3, restrict_local=False, confirm_widen=True)
    assert reply.status_code == 409
    assert reply.json()["detail"]["code"] == "DATA_ACCESS_POLICY_UNAVAILABLE"
    serve(monkeypatch, REAL, [])
    assert journey.ask()["answered_by"] == "case_data"
    assert journey.baseline.calls == 0


def test_every_policy_refusal_has_a_fixed_message() -> None:
    for code in (
        "EXTERNAL_DATA_POLICY_LOCKED",
        "DATA_ACCESS_POLICY_UNAVAILABLE",
        "DATA_ACCESS_POLICY_CONFLICT",
        "WIDEN_CONFIRMATION_REQUIRED",
    ):
        assert code in MESSAGES


# --- enforcement in the RM chat -------------------------------------------------------------------


def test_an_unrestricted_local_model_answers_an_authorised_case_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    serve(monkeypatch, REAL, [])
    for stream in (False, True):
        assert journey.ask(stream=stream)["answered_by"] == "model"
    assert journey.baseline.calls == 2


def test_a_restricted_local_model_answers_only_verified_synthetic_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    _restrict(journey)
    serve(monkeypatch, LIVE_GARDEN)
    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "model", reply
        assert reply["notice"].startswith(LOCAL_NOTICES.dev_answered)
    assert journey.baseline.calls == 2
    serve(monkeypatch, REAL, [])
    for stream in (False, True):
        assert journey.ask(stream=stream)["answered_by"] == "case_data"
    name = GARDEN[1][0]["display_name"]
    serve(monkeypatch, LIVE_GARDEN, digests_for(GARDEN[1], **{name: _tampered(_fixture(name))}))
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    serve(monkeypatch, LIVE_GARDEN)
    assert journey.ask("Is Tan Ah Kow, NRIC S1234567D, a director?")["answered_by"] == "case_data"
    assert journey.baseline.calls == 2


def test_without_d095_a_restricted_local_model_keeps_the_d094_fixture_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    _restrict(journey)
    # D-142 R4: the external field table no longer carries the backend's free text (the live
    # Garden timeline's "policy catalogue v1" event was the only word outside the D-094
    # vocabulary), so the synthetic Garden case's live prompt is inside the text boundary.
    serve(monkeypatch, LIVE_GARDEN)
    assert journey.ask(stream=True)["answered_by"] == "model"
    assert journey.baseline.calls == 1
    # A case that is not the synthetic fixture is still refused by the D-094 case boundary.
    serve(monkeypatch, REAL, [])
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    assert journey.baseline.calls == 1


def test_the_wrapper_itself_refuses_unchecked_messages_and_never_warms(tmp_path: Path) -> None:
    baseline = Baseline()
    model = SyntheticOnlyModel(baseline, config(tmp_path))
    _, _, messages = _messages(REAL)
    with pytest.raises(LlmUnavailableError):
        model.complete(messages)

    async def drain() -> None:
        async for _ in model.stream(messages):
            pass

    with pytest.raises(LlmUnavailableError):
        anyio.run(drain)
    model.warm(messages)
    assert baseline.calls == 0 and model.name == baseline.name


def test_external_models_stay_restricted_whatever_the_local_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    journey.activate_remote()
    sent = len(journey.openrouter.chats)
    view = journey.client.get(POLICY).json()
    assert view["active_class"] == "openrouter" and view["active_restricted"]
    assert not view["classes"][3]["restricted"]  # the local setting is unrestricted
    serve(monkeypatch, REAL, [])
    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "case_data"
        assert reply["notice"].startswith(REMOTE_ELIGIBILITY_NOTICE)
    assert len(journey.openrouter.chats) == sent and journey.baseline.calls == 0


def test_an_unauthorised_user_cannot_read_the_case_and_nothing_is_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    serve(monkeypatch, LIVE_GARDEN)
    journey.backend.revoked.add("rm-session")
    journey.client.cookies.set("clm_session", "rm-session")
    reply = journey.client.post(f"/assistant/cases/{CASE_ID}/chat", json={"message": QUESTION})
    assert reply.status_code == 401
    other = journey.client.post(
        "/assistant/cases/00000000-0000-0000-0000-000000000000/chat",
        json={"message": QUESTION},
        headers={"Origin": ORIGIN},
    )
    assert other.status_code in (401, 404)
    assert journey.baseline.calls == 0 and journey.openrouter.chats == []


# --- local classification: only a literal loopback endpoint is local --------------------------


def test_an_it_configured_remote_endpoint_is_restricted_and_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095, llm_base_url="http://10.0.0.5:8080/v1")
    view = journey.client.get(POLICY).json()
    assert view["active_class"] == "it_configured" and view["active_restricted"]
    assert not view["classes"][3]["restricted"]  # the local setting does not unlock it
    serve(monkeypatch, REAL, [])
    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "case_data"
        assert reply["notice"].startswith(IT_NOTICES.eligibility)
        assert "Reason: SYNTHETIC_CASE_NOT_APPROVED." in reply["notice"]
    assert journey.baseline.calls == 0
    serve(monkeypatch, LIVE_GARDEN)
    reply = journey.ask(stream=True)
    assert reply["answered_by"] == "model" and reply["notice"].startswith(IT_NOTICES.dev_answered)


# --- QG L1 to L5 ----------------------------------------------------------------------------------


def test_a_restricted_local_refusal_has_its_own_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    _restrict(journey)
    serve(monkeypatch, REAL, [])
    for stream in (False, True):
        notice = journey.ask(stream=stream)["notice"]
        assert notice == f"{LOCAL_NOTICES.eligibility} Reason: SYNTHETIC_CASE_NOT_APPROVED."
        assert not notice.startswith("The AI model is not available")


def test_data_access_changes_have_their_own_rate_limit_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095)
    for revision in range(20):
        body = {"expected_revision": revision, "restrict_local": revision % 2 == 0}
        if revision % 2:
            body["confirm_widen"] = True
        assert _put(journey, **body).status_code == 200
    limited = _put(journey, expected_revision=20, restrict_local=True)
    assert limited.status_code == 429
    detail = limited.json()["detail"]
    assert detail["code"] == "DATA_ACCESS_RATE_LIMITED"
    assert detail["message"] == MESSAGES["DATA_ACCESS_RATE_LIMITED"]
    assert "spending" not in detail["message"]
    # The spending controls keep their own count.
    budget = journey.client.put(
        f"{API}/budget/controls",
        json={"expected_revision": 0, "daily_cap_micro_usd": 500_000, "max_calls": 10},
    )
    assert budget.status_code != 429


def test_a_policy_change_is_never_stored_without_its_audit_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ModelAdminStore(tmp_path / "admin.sqlite3")

    def broken(*args: Any, **kwargs: Any) -> None:
        raise sqlite3.OperationalError("audit write failed")

    monkeypatch.setattr(ModelAdminStore, "_insert_event", staticmethod(broken))
    with pytest.raises(sqlite3.OperationalError):
        store.set_data_access_policy(0, True, "hr-admin")
    monkeypatch.undo()
    assert store.data_access_policy().revision == 0
    assert store.set_data_access_policy(0, True, "hr-admin", role="HR") == 1
    store.set_data_access_policy(1, False, "hr-admin", role="HR")
    events = [e for e in store.events(10) if e["action"] == ACTION]
    assert [(e["code"], e["revision"], e["outcome"]) for e in reversed(events)] == [
        ("LOCAL_DEFAULT_ALL_CASES_TO_LOCAL_SYNTHETIC_ONLY", 1, "applied"),
        ("LOCAL_SYNTHETIC_ONLY_TO_LOCAL_ALL_CASES", 2, "applied"),
    ]


def test_concurrent_changes_from_one_view_apply_only_once(tmp_path: Path) -> None:
    store = ModelAdminStore(tmp_path / "admin.sqlite3")
    barrier = threading.Barrier(4)
    outcomes: list[str] = []

    def change(flag: bool) -> None:
        barrier.wait()
        try:
            store.set_data_access_policy(0, flag, "hr-admin")
            outcomes.append("applied")
        except RevisionConflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=change, args=(i % 2 == 0,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["applied", "conflict", "conflict", "conflict"]
    assert store.data_access_policy().revision == 1
    assert len([e for e in store.events(10) if e["action"] == ACTION]) == 1


def test_claude_active_is_unaffected_by_a_restricted_local_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch, **D095)
    journey.activate_claude()
    _restrict(journey)
    view = journey.client.get(POLICY).json()
    assert view["active_class"] == "anthropic" and view["active_restricted"]
    assert not isinstance(journey.selector.current().model, SyntheticOnlyModel)
    serve(monkeypatch, LIVE_GARDEN)
    reply = journey.ask(stream=True)
    assert reply["answered_by"] == "model" and reply["notice"].startswith(
        CLAUDE_NOTICES.dev_answered
    )
    serve(monkeypatch, REAL, [])
    assert journey.ask(stream=True)["notice"].startswith(CLAUDE_NOTICES.eligibility)
    assert journey.baseline.calls == 0 and journey.openrouter.chats == []


def test_the_brief_never_warms_a_restricted_local_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, **D095, llm_warm_up=True)
    warmed: list[int] = []
    monkeypatch.setattr(journey.baseline, "warm", lambda messages: warmed.append(len(messages)))
    serve(monkeypatch, REAL, [])

    def brief() -> None:
        journey.client.cookies.set("clm_session", "rm-session")
        try:
            assert journey.client.get(f"/assistant/cases/{CASE_ID}/brief").status_code == 200
        finally:
            journey.client.cookies.set("clm_session", "hr-session")

    brief()
    assert len(warmed) == 1  # the control: an unrestricted local model is warmed as before
    _restrict(journey)
    serve(monkeypatch, LIVE_GARDEN)  # different facts, so no cached warm-up hides a call
    brief()
    assert len(warmed) == 1 and journey.baseline.calls == 0


def test_without_model_management_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No profiles file: the selector has no state database (D-093 fixed model).
    baseline = Baseline()
    backend = Backend()
    monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: baseline)
    app = create_app(
        config(tmp_path, **D095),
        clm_transport=httpx.MockTransport(lambda request: backend.handler(request)),
    )
    assert not app.state.model_selector.managed
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "hr-session")
    view = client.get(POLICY).json()
    assert view["status"] == "not_managed" and not view["active_restricted"]
    refused = client.put(POLICY, json={"expected_revision": 0, "restrict_local": True})
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "MODEL_MANAGEMENT_OFF"
    serve(monkeypatch, REAL, [])
    client.cookies.set("clm_session", "rm-session")
    reply = client.post(f"/assistant/cases/{CASE_ID}/chat", json={"message": QUESTION})
    assert reply.json()["answered_by"] == "model" and baseline.calls == 1


def test_the_a1_and_policy_modules_are_part_of_the_qualification_basis() -> None:
    # Any change to them makes every earlier qualification out of date (never kept current).
    for name in ("synthetic_eligibility.py", "anthropic_runtime.py", "main.py", "data_access.py"):
        assert name in BASIS_FILES


def test_without_model_management_a_non_loopback_model_is_still_restricted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Re-QG M1: no profiles file, a model IT configured on a non-loopback address.
    baseline = Baseline()
    backend = Backend()
    monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: baseline)
    app = create_app(
        config(tmp_path, **D095, llm_base_url="http://10.0.0.5:8080/v1"),
        clm_transport=httpx.MockTransport(lambda request: backend.handler(request)),
    )
    assert not app.state.model_selector.managed
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "hr-session")
    view = client.get(POLICY).json()
    assert view["status"] == "not_managed" and view["active_class"] == "it_configured"
    assert view["active_restricted"]
    assert view["classes"][2] == {
        "provider_class": "it_configured",
        "restricted": True,
        "locked": True,
    }
    client.cookies.set("clm_session", "rm-session")
    serve(monkeypatch, REAL, [])
    for path in ("chat", "chat/stream"):
        reply = client.post(f"/assistant/cases/{CASE_ID}/{path}", json={"message": QUESTION})
        assert reply.status_code == 200
        text = reply.text  # one JSON reply, or the stream's lines ending with "done"
        assert '"answered_by":"case_data"' in text.replace(" ", "")
        assert IT_NOTICES.eligibility in text
    assert baseline.calls == 0


def test_claude_catalogue_scope_follows_the_shared_mode(tmp_path: Path) -> None:
    # Re-QG L1: the page names D-095 scope for Claude without any OpenRouter configuration.
    from ai_assistant.model_catalog import load_catalogue

    settings = claude_config(tmp_path, **D095, **NO_OPENROUTER)
    entries = [e for e in load_catalogue(settings).entries if e.deployment == "anthropic"]
    assert entries and all(dict(e.details)["scope"] == "VERIFIED_SYNTHETIC_CASES" for e in entries)
