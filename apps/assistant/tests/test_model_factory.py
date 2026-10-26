"""Model registry, composition locks and network containment (Phase A2, D-091 proposed).

T3-03 lock and validation refusals, T3-20 the key is read last, S1 endpoint identity and S2
test-only transport containment. Every refusal is checked for a fixed message that never
holds a setting value or the sentinel key.
"""

import socket
from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_assistant.budget import BudgetedChatModel
from ai_assistant.config import AiAssistantSettings
from ai_assistant.main import create_app
from ai_assistant.model_factory import build_chat_model, resolve_remote_credential
from ai_assistant.model_profiles import (
    APPROVED_PROFILES,
    DEEPINFRA_BF16,
    LOCAL_PROFILE_ID,
    OPENROUTER_PROFILE,
    OPENROUTER_PROFILE_ID,
    ApprovedEndpoint,
    ProfileConfigError,
)
from ai_assistant.openrouter import OpenRouterChatModel, require_offline_transport
from tests.conftest import SuiteRemoteConnectionBlocked
from tests.remote_fixtures import (
    ENDPOINT,
    ENVIRON,
    SENTINEL_KEY,
    TEST_PROFILE,
    TEST_REGISTRY,
    new_ledger,
    remote_settings,
)
from tests.test_ai_assistant import FakeBackend

LEDGER: dict[str, Path] = {}


@pytest.fixture(autouse=True)
def _ledger(tmp_path: Path) -> Iterator[Path]:
    """A fresh synthetic ledger for every test, so lock L4 holds unless a test removes it."""

    LEDGER["path"] = new_ledger(tmp_path / "ledger.sqlite3")
    yield LEDGER["path"]
    LEDGER.clear()


def _mock() -> httpx.MockTransport:
    return httpx.MockTransport(lambda _: httpx.Response(500))


def _refused(code: str, settings: AiAssistantSettings, **kwargs: Any) -> ProfileConfigError:
    arguments: dict[str, Any] = {
        "transport": _mock(),
        "environ": ENVIRON,
        "registry": TEST_REGISTRY,
        "budget_ledger": LEDGER["path"],
    }
    arguments.update(kwargs)
    with pytest.raises(ProfileConfigError) as raised:
        build_chat_model(settings, **arguments)
    error = raised.value
    assert error.code == code
    assert SENTINEL_KEY not in str(error) and SENTINEL_KEY not in repr(error)
    return error


def _build(**kwargs: Any) -> Any:
    arguments: dict[str, Any] = {
        "transport": _mock(),
        "environ": ENVIRON,
        "registry": TEST_REGISTRY,
        "budget_ledger": LEDGER["path"],
    }
    arguments.update(kwargs)
    return build_chat_model(remote_settings(), **arguments)


def _build_with(settings: AiAssistantSettings) -> Any:
    return build_chat_model(
        settings,
        transport=_mock(),
        environ=ENVIRON,
        registry=TEST_REGISTRY,
        budget_ledger=LEDGER["path"],
    )


def test_the_remote_profile_composes_only_when_every_lock_holds() -> None:
    model = _build()

    assert isinstance(model, BudgetedChatModel)
    assert isinstance(model._inner, OpenRouterChatModel)
    assert model.endpoint_slug == ENDPOINT.slug and model._inner.max_tokens == 2000
    assert model.profile_id == OPENROUTER_PROFILE_ID
    assert SENTINEL_KEY not in repr(model)


# --- the production registry ---------------------------------------------------------------


def test_the_production_registry_approves_exactly_the_phase_b_endpoint() -> None:
    profile = APPROVED_PROFILES[OPENROUTER_PROFILE_ID]

    assert profile is OPENROUTER_PROFILE
    assert profile.dormant and profile.requires_budget and profile.boundary == "external"
    # Phase B (D-092, proposed): one reviewed endpoint record; tests/test_phase_b_live.py.
    assert profile.endpoints == (DEEPINFRA_BF16,)
    assert set(APPROVED_PROFILES) == {LOCAL_PROFILE_ID, OPENROUTER_PROFILE_ID}
    with pytest.raises(TypeError):
        APPROVED_PROFILES["extra"] = TEST_PROFILE  # type: ignore[index]


# --- each lock on its own (T3-03) ----------------------------------------------------------


def test_lock_1_the_remote_profile_is_dormant_without_a_mock_transport() -> None:
    _refused("PROFILE_DORMANT", remote_settings(), transport=None)


def test_lock_2_an_unapproved_endpoint_is_refused_by_the_production_registry() -> None:
    _refused("ENDPOINT_NOT_APPROVED", remote_settings(), registry=APPROVED_PROFILES)


def test_lock_3_the_decision_interlock_must_name_the_decision() -> None:
    for value in ("", "D-090", "d-091", "D-091 ", "yes"):
        error = _refused("DECISION_INTERLOCK", remote_settings(remote_inference_decision=value))
        assert value.strip() == "" or value not in str(error)


def test_lock_4_a_missing_or_unhealthy_ledger_is_refused(tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "ledger.sqlite3"
    _refused("LEDGER_UNAVAILABLE", remote_settings(), budget_ledger=missing)
    assert not missing.exists() and not missing.parent.exists()

    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"not a database" * 100)
    _refused("LEDGER_UNAVAILABLE", remote_settings(), budget_ledger=garbage)


def test_the_default_ledger_path_is_package_relative_and_git_ignored() -> None:
    from ai_assistant.model_factory import ASSISTANT_DIR, ledger_path

    path = ledger_path(remote_settings())
    assert path == ASSISTANT_DIR / "data" / "budget" / "ledger.sqlite3"
    assert not path.exists()


def test_the_service_refuses_to_start_with_the_remote_profile() -> None:
    with pytest.raises(ProfileConfigError) as raised:
        create_app(remote_settings(), clm_transport=httpx.MockTransport(FakeBackend().handler))

    assert raised.value.code == "PROFILE_DORMANT"


# --- S1: one exactly identified endpoint -------------------------------------------------------


def test_a_base_provider_slug_does_not_select_an_endpoint() -> None:
    """``fictional-provider`` would match every endpoint of that provider on OpenRouter."""

    _refused("ENDPOINT_NOT_APPROVED", remote_settings(openrouter_endpoint="fictional-provider"))


def test_an_endpoint_not_shown_to_be_unique_is_refused() -> None:
    endpoint = replace(ENDPOINT, slug_unique_for_model=False)
    registry = {
        **TEST_REGISTRY,
        OPENROUTER_PROFILE_ID: replace(TEST_PROFILE, endpoints=(endpoint,)),
    }

    _refused("ENDPOINT_NOT_UNIQUE", remote_settings(), registry=registry)


@pytest.mark.parametrize(
    "slug", ["", "Fictional/fp8", "a b", "x/y/z/w/v", "/fp8", "provider//fp8", "p/" + "v" * 49]
)
def test_an_endpoint_setting_that_is_not_one_slug_is_refused(slug: str) -> None:
    error = _refused("ENDPOINT_SLUG_INVALID", remote_settings(openrouter_endpoint=slug))
    assert not slug.strip() or slug not in str(error)


# --- other validation -----------------------------------------------------------------------


@pytest.mark.parametrize("effort", ["", "none", "minimal", "xhigh", "LOW"])
def test_a_reasoning_effort_the_model_does_not_accept_is_refused(effort: str) -> None:
    _refused("REASONING_EFFORT_INVALID", remote_settings(llm_reasoning_effort=effort))


def test_reasoning_needs_an_allowance_and_the_total_is_bounded() -> None:
    _refused("REASONING_ALLOWANCE_INVALID", remote_settings(llm_reasoning_allowance_tokens=0))
    _refused("MAX_TOKENS_TOO_LARGE", remote_settings(llm_reasoning_allowance_tokens=3500))
    small = replace(ENDPOINT, max_completion_tokens=1000)
    registry = {**TEST_REGISTRY, OPENROUTER_PROFILE_ID: replace(TEST_PROFILE, endpoints=(small,))}
    _refused("MAX_TOKENS_TOO_LARGE", remote_settings(), registry=registry)


def test_the_remote_url_and_model_cannot_be_overridden() -> None:
    _refused("BASE_URL_OVERRIDE", remote_settings(llm_base_url="https://openrouter.ai/api/v1"))
    _refused("MODEL_OVERRIDE", remote_settings(llm_model="openai/gpt-oss-120b:free"))


def test_an_unknown_profile_is_refused() -> None:
    _refused("PROFILE_UNKNOWN", remote_settings(llm_profile="openrouter"))


def test_validation_also_holds_for_settings_built_without_validators() -> None:
    settings = AiAssistantSettings.model_construct(
        llm_profile=OPENROUTER_PROFILE_ID,
        remote_inference_decision="D-091",
        openrouter_endpoint=ENDPOINT.slug,
        llm_reasoning_effort="low",
        llm_reasoning_allowance_tokens=-5,
    )

    _refused("SETTING_OUT_OF_BOUNDS", settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"budget_max_in_flight": 50},
        {"budget_max_in_flight": 0},
        {"remote_max_prompt_bytes": 10**9},
        {"llm_temperature": float("nan")},
        {"llm_temperature": 1.5},
        {"llm_timeout_seconds": 0.0},
        {"llm_timeout_seconds": float("inf")},
        {"llm_max_answer_tokens": 1.5},
        {"budget_settle_lag_seconds": -1},
        {"llm_reasoning_allowance_tokens": True},
    ],
)
def test_numeric_bounds_are_rechecked_for_settings_built_without_validators(
    changes: dict[str, Any],
) -> None:
    """QG F-4: the factory re-checks every bounded number the remote profile uses."""

    values: dict[str, Any] = {
        "llm_profile": OPENROUTER_PROFILE_ID,
        "remote_inference_decision": "D-091",
        "openrouter_endpoint": ENDPOINT.slug,
        "llm_reasoning_effort": "low",
        "llm_reasoning_allowance_tokens": 1400,
        **changes,
    }
    error = _refused("SETTING_OUT_OF_BOUNDS", AiAssistantSettings.model_construct(**values))
    assert all(str(value) not in str(error) for value in changes.values() if value not in (0, 1))


def test_valid_settings_built_without_validators_still_compose() -> None:
    settings = AiAssistantSettings.model_construct(
        llm_profile=OPENROUTER_PROFILE_ID,
        remote_inference_decision="D-091",
        openrouter_endpoint=ENDPOINT.slug,
        llm_reasoning_effort="low",
        llm_reasoning_allowance_tokens=1400,
    )

    assert isinstance(_build_with(settings), BudgetedChatModel)


# --- the credential (T3-20) -----------------------------------------------------------------


class Watched(dict[str, str]):
    """Records every read of the environment mapping."""

    def __init__(self, values: dict[str, str]) -> None:
        super().__init__(values)
        self.reads: list[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        self.reads.append(key)
        return super().get(key, default)

    def __getitem__(self, key: str) -> str:
        self.reads.append(key)
        return super().__getitem__(key)


def test_the_key_is_read_only_after_every_other_check_passes() -> None:
    environ = Watched(ENVIRON)
    base: dict[str, Any] = {
        "transport": _mock(),
        "registry": TEST_REGISTRY,
        "budget_ledger": LEDGER["path"],
    }
    for settings, kwargs in [
        (remote_settings(remote_inference_decision=""), {}),
        (remote_settings(llm_reasoning_effort="none"), {}),
        (remote_settings(), {"transport": None}),
        (remote_settings(), {"registry": APPROVED_PROFILES}),
        (remote_settings(), {"budget_ledger": LEDGER["path"].with_name("absent.sqlite3")}),
    ]:
        with pytest.raises(ProfileConfigError):
            build_chat_model(settings, **{**base, **kwargs}, environ=environ)
    assert environ.reads == []

    build_chat_model(remote_settings(), **base, environ=environ)
    assert environ.reads == ["OPENROUTER_API_KEY"]


@pytest.mark.parametrize(
    "value", [None, "", " ", "has space", "tab\tkey", "x" * 257, "café", "line\nbreak"]
)
def test_a_missing_or_malformed_key_is_refused_without_quoting_it(value: str | None) -> None:
    environ = {} if value is None else {"OPENROUTER_API_KEY": value}

    error = _refused("CREDENTIAL_MISSING", remote_settings(), environ=environ)
    assert value is None or value.strip() == "" or value not in str(error)


def test_the_key_is_only_shape_checked_and_held_as_a_secret() -> None:
    secret = resolve_remote_credential(ENVIRON)

    assert secret.get_secret_value() == SENTINEL_KEY
    assert SENTINEL_KEY not in repr(secret) and SENTINEL_KEY not in str(secret)


# --- S2: test-only transport containment ------------------------------------------------------


class SubclassedMock(httpx.MockTransport):
    """A subclass could forward to a real network; only the exact mock type is accepted."""


class Wrapper(httpx.BaseTransport):
    def __init__(self) -> None:
        self.inner = httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self.inner.handle_request(request)


@pytest.mark.parametrize(
    "transport",
    [
        httpx.HTTPTransport(),
        httpx.AsyncHTTPTransport(),
        SubclassedMock(lambda _: httpx.Response(200)),
        Wrapper(),
        object(),
    ],
    ids=["http", "async-http", "mock-subclass", "wrapper", "object"],
)
def test_a_live_capable_transport_cannot_open_a_network_path(
    transport: object, no_remote_connections: list[str]
) -> None:
    before = list(no_remote_connections)

    _refused("TRANSPORT_NOT_ALLOWED", remote_settings(), transport=transport)
    with pytest.raises(ProfileConfigError) as raised:
        OpenRouterChatModel(
            endpoint=ENDPOINT,
            credential=resolve_remote_credential(ENVIRON),
            timeout_seconds=5.0,
            temperature=0.2,
            answer_tokens=600,
            reasoning_effort="low",
            reasoning_allowance_tokens=1400,
            max_prompt_bytes=32768,
            transport=transport,
        )
    assert raised.value.code == "TRANSPORT_NOT_ALLOWED"
    with pytest.raises(ProfileConfigError):
        require_offline_transport(transport)
    assert no_remote_connections == before


def test_the_suite_guard_blocks_remote_connections(no_remote_connections: list[str]) -> None:
    """192.0.2.1 is reserved for documentation and ``.invalid`` never resolves, so nothing
    could be reached even if the guard failed."""

    before = len(no_remote_connections)
    try:
        with pytest.raises(SuiteRemoteConnectionBlocked):
            socket.create_connection(("192.0.2.1", 443), timeout=5)
        with pytest.raises(SuiteRemoteConnectionBlocked):
            socket.getaddrinfo("example.invalid", 443)
        with pytest.raises(SuiteRemoteConnectionBlocked):
            httpx.get("https://example.invalid/api/v1/models", timeout=5)
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(SuiteRemoteConnectionBlocked):
                raw.connect(("192.0.2.1", 443))
        finally:
            raw.close()
        assert no_remote_connections[before:] == [
            "getaddrinfo",  # create_connection resolves the name first
            "getaddrinfo",
            "getaddrinfo",
            "connect",
        ]
    finally:
        del no_remote_connections[before:]


# --- endpoint records ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"slug": "Bad Slug"}, "ENDPOINT_SLUG_INVALID"),
        ({"prompt_price_per_m": Decimal("-0.01")}, "RESERVATION_INPUT_MISSING"),
        ({"completion_price_per_m": Decimal("NaN")}, "RESERVATION_INPUT_MISSING"),
        ({"request_price": Decimal("0.0000001")}, "RESERVATION_INPUT_MISSING"),
        ({"cache_write_price_per_m": Decimal("Infinity")}, "RESERVATION_INPUT_MISSING"),
        ({"max_completion_tokens": 0}, "RESERVATION_INPUT_MISSING"),
        ({"quantization": "fp3"}, "ENDPOINT_SLUG_INVALID"),
    ],
)
def test_an_endpoint_record_with_a_missing_or_invalid_input_is_refused(
    changes: dict[str, Any], code: str
) -> None:
    values: dict[str, Any] = {
        "slug": "fictional-provider/fp8",
        "prompt_price_per_m": Decimal("0.15"),
        "completion_price_per_m": Decimal("0.60"),
        "request_price": Decimal("0"),
        "max_completion_tokens": 117964,
        "max_tokens_includes_reasoning": False,
        "slug_unique_for_model": True,
        "evidence_date": date(2026, 10, 26),
    }
    values.update(changes)
    with pytest.raises(ProfileConfigError) as raised:
        ApprovedEndpoint(**values)
    assert raised.value.code == code


def test_price_terms_take_the_highest_listed_price() -> None:
    endpoint = replace(
        ENDPOINT,
        cache_write_price_per_m=Decimal("0.1875"),
        internal_reasoning_price_per_m=Decimal("0.75"),
    )

    assert endpoint.input_price_per_m == Decimal("0.1875")
    assert endpoint.output_price_per_m == Decimal("0.75")
    assert ENDPOINT.input_price_per_m == Decimal("0.15")
    assert ENDPOINT.output_price_per_m == Decimal("0.60")
