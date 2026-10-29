"""D-099 Option B (proposed): the gated Claude Sonnet 5.5 runtime, offline.

A mock Anthropic API (the free model read and streamed messages), the separate Anthropic ledger,
a mock OpenRouter beside it and the fake CLM backend serving the synthetic Garden fixture.
Nothing reaches a network or spends; the suite guard (conftest.py) refuses any non-local
connection. The key is a sentinel searched for in every output.
"""

import json
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from pydantic import SecretStr, ValidationError

from ai_assistant import anthropic_runtime, budget, key_sources, remote_test
from ai_assistant.anthropic_chat import AnthropicChatModel
from ai_assistant.anthropic_profiles import BALANCED, FAST, LEDGER_PROFILE_ID, PROFILE_IDS
from ai_assistant.anthropic_runtime import (
    CHAT_RECONCILE_SECONDS,
    NOTICES,
    PAID_RECONCILE_SECONDS,
    ClaudeTestModel,
    readiness,
    resolve_key,
)
from ai_assistant.budget import BudgetedChatModel, BudgetLedger, BudgetRefusedError, Reservation
from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import LlmUnavailableError, ModelCallError, Piece
from ai_assistant.model_admin import UNAVAILABLE_ID, ModelSelector
from ai_assistant.model_admin_store import ModelAdminStore
from ai_assistant.model_catalog import load_catalogue
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID, ProfileConfigError
from ai_assistant.model_qualification import BASIS_FILES
from ai_assistant.remote_checks import Preflight
from assistant_eval.qualification import CLAUDE_G8_RULE
from tests.remote_fixtures import Chunks
from tests.test_budget_cli import CLI as budget_ledger
from tests.test_claude_console import _reply
from tests.test_model_management import API, profile, wait_for, write_profiles
from tests.test_remote_test import ALLOWED, Journey, config, new_ledger
from tests.test_remote_test import SENTINEL as OPENROUTER_SENTINEL

WORKSPACE = "wrkspc_TestWorkspace01"
# Built at run time so the secret scanner never sees a key-shaped literal.
KEY = "sk-" + "ant-" + "api03-" + "RuntimeSentinel" * 3
ATTESTS = "dedicated_workspace,workspace_limit_set,inference_key_only,key_revoked_at_fyp_end"
SYSTEM = [{"role": "system", "content": "RULES"}, {"role": "system", "content": "CASE FACTS"}]
MESSAGES = [*SYSTEM, {"role": "user", "content": "Is this case ready for review?"}]
MODEL_PATH = "/v1/models/claude-sonnet-5-5"
VAR = anthropic_runtime.CREDENTIAL_VARIABLE


@pytest.fixture(autouse=True)
def _forget_the_last_preflight() -> Iterator[None]:
    anthropic_runtime._last.clear()
    yield
    anthropic_runtime._last.clear()


def claude_config(tmp_path: Path, **extra: Any) -> AiAssistantSettings:
    values: dict[str, Any] = {
        "anthropic_decision": "D-099",
        "anthropic_owner_attests": ATTESTS,
        "anthropic_workspace_id": WORKSPACE,
        "anthropic_workspace_limit_micro_usd": 5_000_000,
        "anthropic_ledger_path": str(tmp_path / "budget" / "anthropic.sqlite3"),
        **extra,
    }
    return config(tmp_path, **values)


def claude_ledger(
    settings: AiAssistantSettings, *, cap: int = 5_000_000, reconcile: bool = True
) -> BudgetLedger:
    path = Path(settings.anthropic_ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger = BudgetLedger.initialise(
        path,
        cap_micro_usd=cap,
        opening_usage_micro_usd=0,
        key_alias="key-01",
        profile_id=LEDGER_PROFILE_ID,
    )
    if reconcile:
        ledger.reconcile(0, settle_lag_seconds=0)
    return ledger


def reconciled_ago(settings: AiAssistantSettings, seconds: float) -> None:
    # Moves the last reconciliation back in time (the ledger has no clock seam here).
    with sqlite3.connect(settings.anthropic_ledger_path) as connection:
        connection.execute(
            "UPDATE ledger_meta SET last_reconciled_at = ?",
            (int((time.time() - seconds) * 1000),),
        )


def _lines(body: dict[str, Any]) -> str:
    # Allowed lines from the prompt itself (the topic lines, else the first allowed line).
    texts = [block["text"] for block in body.get("system", [])]
    for text in texts:
        if text.startswith("QUESTION TOPIC:"):
            return "\n".join(text.splitlines()[1:]) + "\n"
    for text in texts:
        if text.startswith("CASE FACTS\n"):
            facts = json.loads(text.split("\n", 1)[1])
            return str(facts["allowed_guidance"][0]) + "\n"
    return ALLOWED + "\n"


class Claude:
    # A mock Anthropic API: ``GET /v1/models/{model}`` and streamed ``POST /v1/messages``.
    def __init__(self) -> None:
        self.workspace: str | None = WORKSPACE
        self.listed_model = "claude-sonnet-5-5"
        self.reply_model = "claude-sonnet-5-5"
        self.models_status = 200
        self.status = 200
        self.error: dict[str, Any] = {}
        self.finished = True
        self.requests: list[httpx.Request] = []
        self.messages: list[dict[str, Any]] = []

    def headers(self, kind: str) -> dict[str, str]:
        headers = {"content-type": kind}
        if self.workspace is not None:
            headers["anthropic-workspace-id"] = self.workspace
        return headers

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET":
            assert request.url.path == MODEL_PATH
            return httpx.Response(
                self.models_status,
                json={"id": self.listed_model, "type": "model"},
                headers=self.headers("application/json"),
            )
        body = json.loads(request.content)
        self.messages.append(body)
        if self.status != 200:
            return httpx.Response(
                self.status,
                stream=Chunks([json.dumps({"type": "error", **self.error}).encode()]),
                headers=self.headers("application/json"),
            )
        # Token counts inside the byte-based bounds the reservation uses.
        usage = {"input_tokens": max(1, len(request.content) // 10), "output_tokens": 1}
        reply = _reply(
            _lines(body),
            model=self.reply_model,
            start_usage=usage,
            end_usage={"output_tokens": 50},
            finished=self.finished,
        )
        return httpx.Response(
            200, stream=Chunks([reply]), headers=self.headers("text/event-stream")
        )

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)

    @property
    def posts(self) -> int:
        return sum(1 for request in self.requests if request.method == "POST")


def _model(
    settings: AiAssistantSettings, claude: Claude, profile_id: str = BALANCED.profile_id
) -> ClaudeTestModel:
    return ClaudeTestModel(
        settings,
        profile_id,
        environ={VAR: KEY},
        transport=claude.transport(),
    )


def _ask(
    model: Any, messages: list[dict[str, str]] = MESSAGES
) -> tuple[list[Piece], ModelCallError | None]:
    pieces: list[Piece] = []

    async def gather() -> ModelCallError | None:
        try:
            async for piece in model.stream(messages):
                pieces.append(piece)
        except ModelCallError as error:
            return error
        return None

    return pieces, anyio.run(gather)


def _ledger(settings: AiAssistantSettings) -> BudgetLedger:
    return BudgetLedger.open(Path(settings.anthropic_ledger_path))


# --- readiness: every Option B condition, no key or network -----------------------------------


def test_a_ready_configuration_lists_both_as_selectable_with_the_gpt_oss_scope(
    tmp_path: Path,
) -> None:
    settings = claude_config(tmp_path)
    assert readiness(settings) is None
    catalogue = load_catalogue(settings)
    for profile_id in PROFILE_IDS:
        entry = catalogue.get(profile_id)
        assert entry is not None and entry.status == "selectable" and entry.reason is None
        assert dict(entry.details)["scope"] == "APPROVED_SYNTHETIC_CASE"
    # GPT-OSS is unchanged by the Claude settings.
    plain = config(tmp_path)
    assert remote_test.readiness(settings) == remote_test.readiness(plain)
    assert remote_test.remote_fingerprint(settings) == remote_test.remote_fingerprint(plain)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"anthropic_decision": ""}, "ANTHROPIC_NOT_AUTHORISED"),
        ({"anthropic_decision": "D-098"}, "ANTHROPIC_NOT_AUTHORISED"),
        ({"llm_enabled": False}, "MODEL_DISABLED_BY_ENVIRONMENT"),
        ({"local_api_test_decision": ""}, "DECISION_INTERLOCK"),
        ({"remote_inference_decision": ""}, "DECISION_INTERLOCK"),
        ({"remote_live_decision": ""}, "DECISION_INTERLOCK"),
        ({"clm_backend_url": "https://clm.example.com"}, "NOT_DEVELOPMENT_ENVIRONMENT"),
        ({"allowed_origins": ["https://clm.example.com"]}, "NOT_DEVELOPMENT_ENVIRONMENT"),
        ({"anthropic_owner_attests": ""}, "ANTHROPIC_ATTESTATION_MISSING"),
        (
            {"anthropic_owner_attests": ATTESTS.replace(",key_revoked_at_fyp_end", "")},
            "ANTHROPIC_ATTESTATION_MISSING",
        ),
        ({"anthropic_owner_attests": ATTESTS + ",admin_key"}, "ANTHROPIC_ATTESTATION_MISSING"),
        ({"anthropic_workspace_id": ""}, "WORKSPACE_NOT_ATTESTED"),
        ({"anthropic_workspace_id": "default"}, "WORKSPACE_NOT_ATTESTED"),
        ({"anthropic_workspace_limit_micro_usd": 0}, "WORKSPACE_LIMIT_NOT_ATTESTED"),
        ({"anthropic_daily_cap_micro_usd": 0}, "ANTHROPIC_SETTINGS_INVALID"),
        ({"remote_max_prompt_bytes": 65_536}, "ANTHROPIC_SETTINGS_INVALID"),
    ],
)
def test_every_condition_is_required(tmp_path: Path, changes: dict[str, Any], code: str) -> None:
    settings = claude_config(tmp_path, **changes)
    assert readiness(settings) == code
    entry = load_catalogue(settings).get(BALANCED.profile_id)
    assert entry is not None and entry.status != "selectable"


@pytest.mark.parametrize(
    "name",
    ["anthropic_workspace_limit_micro_usd", "anthropic_daily_cap_micro_usd", "anthropic_max_calls"],
)
def test_the_policy_ceilings_cannot_be_raised(tmp_path: Path, name: str) -> None:
    above = {
        "anthropic_workspace_limit_micro_usd": 5_000_001,
        "anthropic_daily_cap_micro_usd": 1_000_001,
        "anthropic_max_calls": 21,
    }[name]
    with pytest.raises(ValidationError):
        claude_config(tmp_path, **{name: above})
    # Settings built without validation are re-checked.
    unchecked = claude_config(tmp_path).model_copy(update={name: above})
    assert readiness(unchecked) in {"WORKSPACE_LIMIT_NOT_ATTESTED", "ANTHROPIC_SETTINGS_INVALID"}


# --- the key ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (KEY, None),
        ("sk-" + "ant-" + "usr-" + "UserKeySentinel" * 3, None),
        ("sk-" + "ant-" + "admin01-" + "AdminKeySentinel" * 3, "CREDENTIAL_ADMIN_REFUSED"),
        ("sk-" + "ant-" + "oat01-" + "OauthTokenSentinel" * 3, "CREDENTIAL_INVALID"),
        ("sk-" + "ant-" + "sid01-" + "SessionSentinel" * 3, "CREDENTIAL_INVALID"),
        ("sk-or-v1-" + "a" * 64, "CREDENTIAL_INVALID"),
    ],
)
def test_only_an_inference_key_is_accepted(value: str, code: str | None) -> None:
    key, status, refusal = resolve_key({VAR: value})
    assert refusal == code
    assert (key is not None) == (code is None)
    assert status.source == "environment" and value not in json.dumps(status.view())


def test_the_key_comes_from_the_environment_then_the_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(VAR + "=" + KEY + "\n", encoding="utf-8")
    key, status, _ = resolve_key({}, env_file=env_file)
    assert key is not None and status.source == "env_file"
    # A malformed environment value decides: nothing falls through to the file.
    key, status, refusal = resolve_key({VAR: "not-a-key"}, env_file=env_file)
    assert key is None and status.source == "environment" and refusal == "CREDENTIAL_INVALID"
    assert resolve_key({})[2] == "CREDENTIAL_MISSING"
    # The OpenRouter key never serves Claude.
    openrouter = key_sources.CREDENTIAL_VARIABLE
    assert resolve_key({openrouter: KEY})[2] == "CREDENTIAL_MISSING"


# --- one ledger per provider ------------------------------------------------------------------


def test_one_providers_calls_are_never_admitted_by_the_others_ledger(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    anthropic = claude_ledger(settings)
    openrouter = BudgetLedger.open(new_ledger(settings))
    reservation = Reservation(10, 10, 1_000)
    for ledger, other in ((anthropic, OPENROUTER_PROFILE_ID), (openrouter, LEDGER_PROFILE_ID)):
        with pytest.raises(BudgetRefusedError) as refused:
            ledger.reserve(
                reservation,
                endpoint_slug="x/y",
                max_in_flight=1,
                lease_seconds=60,
                profile_id=other,
            )
        assert refused.value.budget is not None
        assert refused.value.budget.outcome == "refused_ledger"
        assert ledger.status().open_calls == 0 and ledger.last_call_id() == 0
    # The Claude adapter behind the unchanged guard, pointed at the OpenRouter ledger.
    claude = Claude()
    guarded = BudgetedChatModel(
        AnthropicChatModel(
            configuration=BALANCED,
            credential=SecretStr(KEY),
            max_prompt_bytes=30_000,
            transport=claude.transport(),
        ),
        openrouter,
        max_in_flight=1,
        lease_seconds=60,
    )
    _, error = _ask(guarded)
    assert error is not None and error.error_class == "budget_refused"
    assert claude.requests == [] and openrouter.last_call_id() == 0


def test_an_existing_openrouter_ledger_keeps_working(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A ledger created before D-099 has the narrower profile CHECK baked in.
    old = budget.SCHEMA.replace(f", '{LEDGER_PROFILE_ID}'", "")
    assert old != budget.SCHEMA
    monkeypatch.setattr(budget, "SCHEMA", old)
    path = new_ledger(config(tmp_path))
    monkeypatch.undo()
    ledger = BudgetLedger.open(path)
    ledger.verify()
    reservation_id = ledger.reserve(
        Reservation(10, 10, 1_000),
        endpoint_slug="deepinfra/bf16",
        max_in_flight=1,
        lease_seconds=60,
        profile_id=OPENROUTER_PROFILE_ID,
    )
    assert ledger.settle(reservation_id, usage=None, error_class="timeout").outcome == "unsettled"


def test_the_claude_model_refuses_the_openrouter_ledger(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    path = Path(settings.anthropic_ledger_path)
    path.parent.mkdir(parents=True)
    BudgetLedger.initialise(path, cap_micro_usd=1, opening_usage_micro_usd=0, key_alias="key-01")
    with pytest.raises(ProfileConfigError) as error:
        _model(settings, Claude())
    assert error.value.code == "LEDGER_UNAVAILABLE"


# --- the free preflight -----------------------------------------------------------------------


def _preflight(settings: AiAssistantSettings, claude: Claude, **kwargs: Any) -> Preflight:
    return anthropic_runtime.preflight(
        settings,
        environ={VAR: KEY},
        transport=claude.transport(),
        **kwargs,
    )


def _failed(report: Preflight) -> list[str]:
    return [check.name for check in report.checks if not check.ok]


def test_a_passing_preflight_reads_only_the_model_and_names_the_workspace(
    tmp_path: Path,
) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    report = _preflight(settings, claude)
    assert report.passed, report.lines()
    names = [check.name for check in report.checks]
    assert {
        "anthropic.inference_key",
        "ledger.profile",
        "ledger.cap_within_ceiling",
        "ledger.reconciled_recently",
        "ledger.daily_room_for_one_call",
        "anthropic.workspace_matches",
        "anthropic.model_available",
    } <= set(names)
    (request,) = claude.requests
    assert request.method == "GET" and str(request.url) == f"https://api.anthropic.com{MODEL_PATH}"
    assert request.headers["x-api-key"] == KEY
    assert request.headers["anthropic-version"] == "2026-10-21"
    assert KEY not in "\n".join(report.lines())


@pytest.mark.parametrize(
    ("setup", "check"),
    [
        (lambda c: setattr(c, "workspace", "wrkspc_SomeOtherSpace"), "anthropic.workspace_matches"),
        (lambda c: setattr(c, "workspace", None), "anthropic.workspace_matches"),
        (lambda c: setattr(c, "listed_model", "claude-opus-5-5"), "anthropic.model_available"),
        (lambda c: setattr(c, "models_status", 401), "anthropic.models_reachable"),
    ],
)
def test_a_provider_mismatch_fails_the_preflight(tmp_path: Path, setup: Any, check: str) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    setup(claude)
    assert _failed(_preflight(settings, claude)) == [check]


def test_missing_billing_evidence_fails_before_anything_is_sent(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    claude = Claude()
    assert _failed(_preflight(settings, claude)) == ["ledger.healthy"]  # no ledger
    claude_ledger(settings, reconcile=False)
    assert _failed(_preflight(settings, claude)) == ["ledger.reconciled_recently"]
    assert claude.requests == []


def test_reconciliation_must_be_within_7_days_for_chat_and_24_hours_for_paid_runs(
    tmp_path: Path,
) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    reconciled_ago(settings, 2 * 86_400)
    assert _preflight(settings, claude, within_seconds=CHAT_RECONCILE_SECONDS).passed
    paid = _preflight(settings, claude, within_seconds=PAID_RECONCILE_SECONDS)
    assert _failed(paid) == ["ledger.reconciled_recently"]
    reconciled_ago(settings, 8 * 86_400)
    assert _failed(_preflight(settings, claude)) == ["ledger.reconciled_recently"]


@pytest.mark.parametrize(
    ("cap", "limit"), [(6_000_000, 5_000_000), (3_000_000, 2_000_000), (0, 5_000_000)]
)
def test_the_ledger_cap_stays_within_the_lifetime_ceiling_and_the_workspace_limit(
    tmp_path: Path, cap: int, limit: int
) -> None:
    settings = claude_config(tmp_path, anthropic_workspace_limit_micro_usd=limit)
    claude_ledger(settings, cap=cap)
    failed = _failed(_preflight(settings, Claude()))
    assert "ledger.cap_within_ceiling" in failed


def test_an_open_breaker_or_a_missing_key_fails_the_preflight(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    ledger = claude_ledger(settings)
    claude = Claude()
    report = anthropic_runtime.preflight(settings, environ={}, transport=claude.transport())
    assert _failed(report) == ["anthropic.inference_key"]
    ledger.open_breaker("provider_error")
    assert "ledger.breaker_closed_no_open_calls" in _failed(_preflight(settings, claude))
    assert claude.requests == []


# --- every call ----------------------------------------------------------------------------


def test_a_call_is_settled_from_usage_and_verified_in_band(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    model = _model(settings, claude)
    assert model.requires_synthetic_boundary and model.notices is NOTICES
    pieces, error = _ask(model)
    assert error is None and ALLOWED in "".join(p.text for p in pieces)
    assert [r.method for r in claude.requests] == ["GET", "POST"]
    (call,) = _ledger(settings).closed_calls_after(0)
    assert call.state == "settled" and call.verification == "verified"
    assert call.charged_micro_usd < call.reserved_micro_usd
    # The preflight is reused for the next call; the call is again verified.
    assert _ask(model)[1] is None
    assert [r.method for r in claude.requests] == ["GET", "POST", "POST"]
    assert model.calls_used() == 2
    assert [c.verification for c in model.calls_since_start()] == ["verified", "verified"]


@pytest.mark.parametrize(
    ("setup", "breaker"),
    [
        (lambda c: setattr(c, "reply_model", "claude-opus-5-5"), "routing_anomaly"),
        (lambda c: setattr(c, "workspace", "wrkspc_SomeOtherSpace"), "routing_anomaly"),
        (lambda c: setattr(c, "finished", False), "reconcile_drift"),
    ],
)
def test_an_unverifiable_call_is_charged_in_full_and_stops_later_calls(
    tmp_path: Path, setup: Any, breaker: str
) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    model = _model(settings, claude)
    assert _ask(model)[1] is None  # passes its preflight, which is then reused
    setup(claude)
    pieces, error = _ask(model)
    assert error is not None
    if breaker == "routing_anomaly":  # stopped before any text reached the guard
        assert all(not p.text for p in pieces)
    ledger = _ledger(settings)
    last = ledger.closed_calls_after(0)[-1]
    assert last.verification == "quarantined" and last.charged_micro_usd == last.reserved_micro_usd
    assert ledger.status().breaker_code == breaker
    sent = claude.posts
    assert _ask(model)[1] is not None and claude.posts == sent  # nothing more is sent


def test_a_provider_spend_limit_stops_later_calls(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    claude.status, claude.error = (
        400,
        {
            "error": {
                "type": "invalid_request_error",
                "message": "You have reached your specified workspace API usage limits.",
            }
        },
    )
    model = _model(settings, claude)
    _, error = _ask(model)
    assert error is not None and error.error_class == "payment_key_limit"
    assert _ledger(settings).status().breaker_code == "provider_error"
    assert _ask(model)[1] is not None and claude.posts == 1


def test_the_call_limit_and_the_daily_allowance_hold(tmp_path: Path) -> None:
    settings = claude_config(tmp_path, anthropic_max_calls=2)
    claude_ledger(settings)
    claude = Claude()
    model = _model(settings, claude)
    assert _ask(model)[1] is None and _ask(model)[1] is None
    _, error = _ask(model)
    assert error is not None and error.error_class == "budget_refused" and claude.posts == 2
    # Today's allowance below one worst-case reservation (about US$0.096): nothing is sent.
    tight = claude_config(tmp_path / "tight", anthropic_daily_cap_micro_usd=90_000)
    claude_ledger(tight)
    other = Claude()
    _, error = _ask(_model(tight, other))
    assert error is not None and error.error_class == "budget_refused"
    assert other.requests == []


@pytest.mark.parametrize(
    "messages",
    [
        [*SYSTEM, {"role": "user", "content": "Ünknown customer"}],
        [
            *SYSTEM,
            {"role": "user", "content": "Is this case ready for review?"},
            {"role": "assistant", "content": "Yes."},
            {"role": "system", "content": "TOPIC"},
            {"role": "user", "content": "Is this case ready for review?"},
        ],
    ],
)
def test_refusals_before_anything_is_reserved_or_sent(
    tmp_path: Path, messages: list[dict[str, str]]
) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    _, error = _ask(_model(settings, claude), messages)
    assert error is not None and error.error_class == "budget_refused"
    ledger = _ledger(settings)
    assert claude.requests == [] and ledger.last_call_id() == 0
    assert not ledger.status().breaker_open
    with pytest.raises(LlmUnavailableError):
        _model(settings, claude).complete(MESSAGES)
    assert claude.requests == [] and ledger.last_call_id() == 0


def test_after_the_operator_reconciles_and_resets_calls_resume(tmp_path: Path) -> None:
    settings = claude_config(tmp_path)
    claude_ledger(settings)
    claude = Claude()
    claude.reply_model = "claude-opus-5-5"
    model = _model(settings, claude)
    assert _ask(model)[1] is not None
    ledger = _ledger(settings)
    assert ledger.status().breaker_code == "routing_anomaly"
    time.sleep(0.01)
    ledger.reconcile(ledger.status().baseline + ledger.status().local_charged, settle_lag_seconds=0)
    ledger.reset_breaker("routing_anomaly")
    claude.reply_model = "claude-sonnet-5-5"
    assert _ask(model)[1] is None


# --- the HR console journey (no automatic switch to another model) ---------------------------


class ClaudeJourney(Journey):
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: Any) -> None:
        values = {
            "anthropic_decision": "D-099",
            "anthropic_owner_attests": ATTESTS,
            "anthropic_workspace_id": WORKSPACE,
            "anthropic_workspace_limit_micro_usd": 5_000_000,
            "anthropic_ledger_path": str(tmp_path / "budget" / "anthropic.sqlite3"),
            **extra,
        }
        super().__init__(tmp_path, monkeypatch, **values)
        claude_ledger(self.settings)
        self.claude = Claude()
        openrouter = self.openrouter

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "api.anthropic.com":
                return self.claude.handler(request)
            return openrouter.handler(request)

        self.selector.transport = httpx.MockTransport(handler)
        self.selector.environ = {
            key_sources.CREDENTIAL_VARIABLE: OPENROUTER_SENTINEL,
            VAR: KEY,
        }

    def activate_claude(self, profile_id: str = BALANCED.profile_id) -> dict[str, Any]:
        test = self.client.post(f"{API}/{profile_id}/connection-test")
        assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
        started = self.start_qualification(profile_id)
        assert started.status_code == 202, started.text
        result = wait_for(self.client, started.json()["qualification_id"])
        assert result["status"] == "passed", result
        revision = self.client.get(API).json()["revision"]
        applied = self.client.post(
            f"{API}/{profile_id}/activate",
            json={"expected_revision": revision, "acknowledge_quality_unscored": True},
        )
        assert applied.status_code == 200, applied.text
        return result


def test_hr_qualifies_and_activates_claude_and_the_rm_chat_uses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    item = next(
        p for p in journey.client.get(API).json()["profiles"] if p["profile_id"] == FAST.profile_id
    )
    assert item["status"] == "selectable" and item["activation_blockers"] == ["NOT_QUALIFIED"]
    result = journey.activate_claude(FAST.profile_id)
    gates = {gate["gate"]: gate for gate in result["gates"]}
    assert gates["G-8"]["rule"] == CLAUDE_G8_RULE
    assert gates["G-8"]["passed"] and gates["G-8"]["value"] == "2/2"
    assert journey.claude.posts == 2 and journey.openrouter.chats == []
    assert {body["output_config"]["effort"] for body in journey.claude.messages} == {"low"}
    assert journey.client.get(API).json()["active"]["profile_id"] == FAST.profile_id

    reply = journey.ask(stream=True)
    assert reply["answered_by"] == "model" and reply["model"] == "claude-sonnet-5-5"
    assert reply["notice"].startswith(NOTICES.answered)
    # Streaming only: the plain route gets the case-data answer and sends nothing.
    assert journey.ask()["answered_by"] == "case_data"
    assert journey.claude.posts == 3 and journey.openrouter.chats == []
    assert journey.baseline.calls == 0
    calls = _ledger(journey.settings).closed_calls_after(0)
    assert [c.verification for c in calls] == ["verified"] * 3
    texts = [journey.client.get(API).text, journey.client.get(f"{API}/audit").text]
    assert all(KEY not in text for text in texts)


def test_a_failing_claude_never_switches_to_gpt_oss_or_the_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()
    journey.claude.reply_model = "claude-opus-5-5"
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    sent = journey.claude.posts
    journey.claude.reply_model = "claude-sonnet-5-5"
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    assert journey.claude.posts == sent
    assert journey.openrouter.chats == [] and journey.baseline.calls == 0
    assert journey.client.get(API).json()["active"]["profile_id"] == BALANCED.profile_id


def test_paid_runs_and_activation_need_a_reconciliation_within_24_hours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    profile_id = BALANCED.profile_id
    reconciled_ago(journey.settings, 2 * 86_400)
    test = journey.client.post(f"{API}/{profile_id}/connection-test")
    assert test.json()["outcome"] == "passed"  # 7 days for a connection test
    refused = journey.start_qualification(profile_id)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "QUALIFICATION_BILLING_UNRECONCILED"
    reconciled_ago(journey.settings, 0)
    started = journey.start_qualification(profile_id)
    assert wait_for(journey.client, started.json()["qualification_id"])["status"] == "passed"
    reconciled_ago(journey.settings, 2 * 86_400)
    revision = journey.client.get(API).json()["revision"]
    applied = journey.client.post(
        f"{API}/{profile_id}/activate",
        json={"expected_revision": revision, "acknowledge_quality_unscored": True},
    )
    assert applied.status_code == 409 and applied.json()["detail"]["code"] == "CONNECTION_FAILED"


def test_a_stored_claude_activation_reverts_to_ai_unavailable_when_no_longer_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()
    store = ModelAdminStore(Path(journey.settings.model_admin_db_path))
    restarted = ModelSelector(
        journey.settings.model_copy(update={"anthropic_workspace_id": ""}),
        None,
        store,
        environ=journey.selector.environ,
        transport=journey.selector.transport,
    )
    active = restarted.current()
    assert active.profile_id == UNAVAILABLE_ID and active.model is None
    assert "STARTUP_REVERTED" in [event["action"] for event in store.events(20)]


def test_hr_spending_controls_never_apply_to_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = ClaudeJourney(tmp_path, monkeypatch)
    journey.activate_claude()
    revision = journey.client.get(f"{API}/budget").json()["controls"]["revision"]
    saved = journey.client.put(
        f"{API}/budget/controls",
        json={"expected_revision": revision, "daily_cap_micro_usd": 500_000, "max_calls": 50},
    )
    assert saved.status_code == 200, saved.text
    model = journey.selector.current().model
    assert isinstance(model, ClaudeTestModel)
    assert model._settings.anthropic_daily_cap_micro_usd == 1_000_000
    assert model._settings.anthropic_max_calls == 20


# --- operator commands and the qualification basis -------------------------------------------


def test_the_anthropic_ledger_commands_keep_the_ceiling_and_the_24_hour_rule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = str(tmp_path / "anthropic.sqlite3")
    base = ["--ledger", path, "--anthropic"]
    init = ["init", "--opening-provider-usage", "0", "--key-alias", "key-01"]
    assert budget_ledger.main([*base, *init, "--cap", "5.01"]) == 2
    assert budget_ledger.main([*base, *init, "--cap", "2.00"]) == 0
    ledger = BudgetLedger.open(Path(path))
    assert ledger.status().profile_id == LEDGER_PROFILE_ID
    raise_to = ["set-cap", "--usd", "3.00", "--raise", "--confirm-new-cap", "3.00"]
    assert budget_ledger.main(["--ledger", path, *raise_to]) == 2  # never reconciled
    assert budget_ledger.main([*base, "reconcile", "--provider-usage", "0"]) == 0
    assert budget_ledger.main(["--ledger", path, *raise_to]) == 0
    above = ["set-cap", "--usd", "5.50", "--raise", "--confirm-new-cap", "5.50"]
    assert budget_ledger.main(["--ledger", path, *above]) == 2
    assert ledger.status().cap == 3_000_000
    assert budget_ledger.main(["--ledger", path, "set-cap", "--usd", "1.00"]) == 0  # lowering
    assert budget_ledger.main(["--ledger", path, "status"]) == 0
    assert "profile: anthropic_claude_sonnet_5_5" in capsys.readouterr().out


def test_the_claude_modules_are_part_of_the_qualification_basis(tmp_path: Path) -> None:
    assert {"anthropic_chat.py", "anthropic_profiles.py", "anthropic_runtime.py"} <= set(
        BASIS_FILES
    )
    settings = config(tmp_path, write_profiles(tmp_path / "profiles.json", profile()))
    assert load_catalogue(settings).get(BALANCED.profile_id) is not None
