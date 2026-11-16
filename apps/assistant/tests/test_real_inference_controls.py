"""Real-inference controls (owner directive 2026-11-15): the D-129 transmission gate on the
hosted service, the standing US$3.00 Singapore-day GPT-OSS ceiling on every deployment, and the
read-only reach of the model. Synthetic values only; no provider, no key and no network."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ai_assistant import anthropic_runtime, budget, remote_test
from ai_assistant import config as assistant_config
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID as ANTHROPIC_LEDGER_PROFILE_ID
from ai_assistant.budget import GPT_OSS_DAILY_CEILING_MICRO_USD as CEILING
from ai_assistant.budget import LedgerError, daily_ceiling, register_daily_ceiling
from ai_assistant.model_admin_store import SpendingControls, apply_controls
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from assistant_hosting import profile, provider
from tests import conftest
from tests.test_hosted_claude import CEILING as CLAUDE_CEILING
from tests.test_hosted_claude import CLAUDE_ENV
from tests.test_hosted_gptoss import (
    BOTH_ENV,
    GPTOSS_ENV,
    OR_SETTINGS,
    on_internal_network,
    resolve,
)
from tests.test_hosting import ELIGIBLE, ORIGIN, hosted_settings, no_files

ASSISTANT_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def unaccepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The code as it ships: D-129 not accepted (the suite otherwise runs as if it were)."""

    monkeypatch.setattr(assistant_config, "HOSTED_TRANSMISSION_DECISION", None)


@pytest.fixture
def openrouter_decided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_DECISION", "D-134-TEST-ONLY")
    monkeypatch.setattr(provider, "system_local_source", on_internal_network)


# --- D-129: nothing leaves the hosted service before the owner's acceptance is in the code ---


def test_the_code_ships_with_d129_recorded_and_openrouter_still_refused() -> None:
    # D-129 ACCEPTED 2026-11-15 for Anthropic only; OpenRouter is still refused (D-134, A1).
    assert conftest.SHIPPED_TRANSMISSION_DECISION == "D-129"
    tree = ast.parse((ASSISTANT_DIR / "ai_assistant" / "config.py").read_text("utf-8"))
    shipped = {
        node.target.id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    # The suite runs as if the OpenRouter decisions were taken (conftest); the code ships with
    # both still refused.
    # D-134 and D-129A accepted (owner): the OpenRouter decisions ship recorded.
    assert shipped["HOSTED_OPENROUTER_DECISION"] == "D-134"
    assert shipped["HOSTED_OPENROUTER_TRANSMISSION_DECISION"] == "D-129A"
    values = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "HOSTED_TRANSMISSION_DECISION"
    ]
    assert len(values) == 1
    assert isinstance(values[0], ast.Constant) and values[0].value == "D-129"


@pytest.mark.parametrize(
    "env", [CLAUDE_ENV, GPTOSS_ENV, BOTH_ENV], ids=["claude", "gptoss", "both"]
)
def test_no_provider_mode_starts_without_the_d129_acceptance(
    tmp_path: Path, unaccepted: None, openrouter_decided: None, env: dict[str, str]
) -> None:
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    found = profile.refusals(settings, env, env_files=no_files(), resolve=resolve)
    assert "TRANSMISSION_DECISION_REQUIRED" in found


def test_with_the_acceptance_the_gate_adds_nothing(
    tmp_path: Path, openrouter_decided: None
) -> None:
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    for env in (CLAUDE_ENV, GPTOSS_ENV, BOTH_ENV):
        found = profile.refusals(settings, env, env_files=no_files(), resolve=resolve)
        assert "TRANSMISSION_DECISION_REQUIRED" not in found


def test_the_model_free_service_is_not_affected_by_the_gate(
    tmp_path: Path, unaccepted: None
) -> None:
    settings = hosted_settings(tmp_path)
    assert profile.refusals(settings, ELIGIBLE, env_files=no_files(), resolve=resolve) == []
    assert provider.config_codes(settings, ELIGIBLE, resolve=resolve) == []


def test_neither_runtime_registers_a_hosted_deployment_without_the_acceptance(
    unaccepted: None, openrouter_decided: None
) -> None:
    with pytest.raises(ValueError):
        anthropic_runtime.register_hosted_deployment(ORIGIN, CLAUDE_CEILING)
    with pytest.raises(ValueError):
        remote_test.register_hosted_deployment(ORIGIN, CEILING)
    assert anthropic_runtime.hosted_deployment() is None
    assert remote_test.hosted_deployment() is None
    # So no hosted chat path is open to Claude.
    assert anthropic_runtime.hosted_paths() == frozenset()


def test_install_refuses_without_the_acceptance(
    tmp_path: Path, unaccepted: None, openrouter_decided: None
) -> None:
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    with pytest.raises(ValueError):
        provider.install(settings, CLAUDE_ENV)
    assert anthropic_runtime.hosted_deployment() is None


# --- the standing US$3.00 Singapore-day GPT-OSS ceiling ---------------------------------------


def test_the_gpt_oss_ceiling_stands_with_nothing_registered() -> None:
    assert CEILING == 3_000_000
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == CEILING
    assert daily_ceiling(ANTHROPIC_LEDGER_PROFILE_ID) is None


def test_a_registration_may_only_lower_the_standing_ceiling() -> None:
    with pytest.raises(LedgerError):
        register_daily_ceiling(CEILING + 1)
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == CEILING
    register_daily_ceiling(1_250_000)
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == 1_250_000


def test_the_standing_ceiling_is_not_process_state() -> None:
    # Clearing every registration (as a fresh process has) leaves it in force.
    budget._daily_ceilings.clear()
    assert daily_ceiling(OPENROUTER_PROFILE_ID) == CEILING


def test_a_development_machine_never_applies_an_hr_value_above_the_ceiling(
    tmp_path: Path,
) -> None:
    local = hosted_settings(
        tmp_path,
        clm_backend_url="http://127.0.0.1:8000",
        allowed_origins=["http://127.0.0.1:5173"],
    )
    assert remote_test.hosted_deployment() is None
    stored = SpendingControls(1, 9_000_000, 20, None, None)
    assert apply_controls(local, stored).budget_daily_cap_micro_usd == CEILING
    lower = SpendingControls(2, 400_000, 20, None, None)
    assert apply_controls(local, lower).budget_daily_cap_micro_usd == 400_000


# --- the model cannot change a case or move money --------------------------------------------


def _http_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text("utf-8"))
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "post", "put", "patch", "delete", "request", "stream"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "client"
        ):
            found.append(node.func.attr)
    return found


def test_the_clm_backend_client_only_reads() -> None:
    calls = _http_calls(ASSISTANT_DIR / "ai_assistant" / "clm_client.py")
    assert calls and set(calls) == {"get"}


@pytest.mark.parametrize(
    "module", ["openrouter.py", "anthropic_chat.py", "provider_payload.py", "llm.py"]
)
def test_no_model_request_offers_tools_or_functions(module: str) -> None:
    text = (ASSISTANT_DIR / "ai_assistant" / module).read_text("utf-8")
    tree = ast.parse(text)
    keys = {
        key.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    assert not keys & {"tools", "tool_choice", "functions", "function_call", "plugins"}


# --- review P2-1: a qualification sends the payload the chat sends --------------------------


class _Inner:
    name = "stub"

    def __init__(self) -> None:
        self.bound = False

    @property
    def provider_bound(self) -> bool:
        return self.bound


def test_the_qualification_wrapper_reads_provider_bound_from_the_model_it_wraps() -> None:
    from ai_assistant.model_qualification import WatchedModel
    from ai_assistant.provider_payload import provider_bound

    inner = _Inner()
    for synthetic in (False, True):
        watched = WatchedModel(inner, lambda _turns: None, synthetic=synthetic)  # type: ignore[arg-type]
        inner.bound = False
        assert provider_bound(watched) is False
        # Live, not copied at wrap time: registering the hosted deployment later still applies.
        inner.bound = True
        assert provider_bound(watched) is True


def test_a_registered_hosted_gptoss_model_stays_provider_bound_when_wrapped(
    openrouter_decided: None,
) -> None:
    from ai_assistant.model_qualification import WatchedModel
    from ai_assistant.provider_payload import identities, provider_bound

    remote_test.register_hosted_deployment(ORIGIN, CEILING)
    try:
        model = object.__new__(remote_test.RemoteTestModel)
        watched = WatchedModel(model, lambda _turns: None, synthetic=True)
        assert provider_bound(watched) is True
        names = identities({"user_id": "ethan-tan", "display_name": "Ethan Tan"})
        assert set(names) == {"ethan-tan", "Ethan Tan"}
    finally:
        remote_test._hosted = None  # noqa: SLF001


# D-139: these tests treat the fixture case as verified synthetic (the seam in conftest);
# test_hosted_case_policy.py runs the real provenance check.
pytestmark = pytest.mark.usefixtures("hosted_case_eligible")
