"""D-142 (proposed): hosted external inference on any authorised synthetic or Mock POC case,
through the privacy boundary, with each provider's data policy (synthetic_only stays the default
and the rollback).

The case is deliberately outside the D-095 lists: a Mock ACRA company that is not one of the
approved synthetic companies, and a viewer who is no seeded user. R2 (owner direction): an
upload whose bytes are not a tracked synthetic fixture has no authoritative provenance, so it and
everything derived from it are withheld from the external prompt while the case's independently
authorised POC facts are still answered. Mock backend, mock Claude and mock OpenRouter; invented
values only; no key, no network, no paid call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_assistant import config as assistant_config
from ai_assistant.main import PRIVACY_ATTRIBUTION
from ai_assistant.privacy_boundary import ALIAS, PSEUDONYMISED, SYNTHETIC_ONLY
from assistant_hosting import eligibility, profile
from tests import test_hosting
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_case_policy import WAITING, WAITING_ID, AnyCaseClm
from tests.test_hosted_claude import (  # noqa: F401
    CLAUDE_ENV,
    Hosted,
    HostedClm,
    done,
    hosted_replies,
)
from tests.test_hosted_claude_paths import general, support
from tests.test_hosting import hosted_settings, no_files

VIEWER = "Kowalczyk Nakamura"  # no seeded user, no vocabulary word
ANTHROPIC = eligibility.DATA_POLICY_VARIABLES["anthropic"]


# A Mock ACRA company that is on no D-095 list (invented name and UEN).
OUTSIDE_NAME, OUTSIDE_UEN = "KESTREL FREIGHT", "202699123K"
OUTSIDE = json.loads(
    json.dumps(WAITING).replace("GARDEN BUSINESS", OUTSIDE_NAME).replace("11111999A", OUTSIDE_UEN)
)


class PrivateClm(HostedClm, AnyCaseClm):
    """The waiting case, renamed to a Mock company outside the D-095 lists, with no upload."""

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        person = test_hosting.SESSIONS.get(token)
        if (
            person is not None
            and person["profile"]["team_id"] == "team-a"
            and request.url.path == f"/api/clm/zero-touch/cases/{WAITING_ID}"
        ):
            self.requests.append(request)
            return httpx.Response(200, json=OUTSIDE)
        return super().handler(request)


class UnverifiedUploadClm(PrivateClm):
    unverified = True  # one upload that is not a tracked synthetic fixture


def case_secrets() -> list[str]:
    case = OUTSIDE["case"]
    entity = case.get("entity") or {}
    initial = case.get("initial_identity") or {}
    found = [VIEWER, "kowalczyk", "nakamura", "scanned-upload"]
    for value in (
        entity.get("legal_name"),
        initial.get("legal_name"),
        entity.get("registration_number"),
        case.get("requested_uen"),
    ):
        if isinstance(value, str) and value:
            found.append(value)
    return found


def leaked(text: str, values: list[str]) -> list[str]:
    folded = text.casefold()
    return [value for value in values if value.casefold() in folded]


def build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: str | None,
    *,
    decision: bool,
    clm: HostedClm | None = None,
) -> Hosted:
    if decision:
        monkeypatch.setattr(assistant_config, "HOSTED_PRIVACY_DECISION", "D-142")
        # Test-only adoption of the separate broad policy uses the canonical rollback.
        monkeypatch.setattr(assistant_config, "CASE_REASONING_DECISION", None)
    if policy is not None:
        monkeypatch.setitem(CLAUDE_ENV, ANTHROPIC, policy)
    rm = test_hosting.actor("kowalczyk-nakamura", "RM", "team-a", "CASE_ACCESS")
    rm["profile"]["display_name"] = VIEWER
    monkeypatch.setitem(test_hosting.SESSIONS, "rm-a", rm)
    hosted = Hosted(tmp_path, monkeypatch, clm or PrivateClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    return hosted


@pytest.fixture
def private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> Hosted:
    return build(tmp_path, monkeypatch, PSEUDONYMISED, decision=True)


@pytest.fixture
def restrictive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> Hosted:
    return build(tmp_path, monkeypatch, None, decision=True)


def sent_since(hosted: Hosted, before: int) -> str:
    return json.dumps(hosted.claude.messages[before:])


# --- configuration --------------------------------------------------------------------------


def test_an_unset_policy_is_synthetic_only() -> None:
    policy = eligibility.CasePolicy.from_env({})
    assert policy.data_policy("anthropic") == SYNTHETIC_ONLY
    assert policy.data_policy("openrouter") == SYNTHETIC_ONLY


def test_the_pseudonymised_policy_needs_the_recorded_decision(tmp_path: Path) -> None:
    assert assistant_config.HOSTED_PRIVACY_DECISION is None  # shipped off
    env = {ANTHROPIC: PSEUDONYMISED}
    found = profile.refusals(hosted_settings(tmp_path), env, env_files=no_files())
    assert eligibility.PRIVACY_DECISION_REQUIRED in found


@pytest.mark.parametrize("value", ["open", "PSEUDONYMISED", "none", "synthetic"])
def test_an_unknown_policy_stops_the_service(tmp_path: Path, value: str) -> None:
    found = profile.refusals(hosted_settings(tmp_path), {ANTHROPIC: value}, env_files=no_files())
    assert eligibility.DATA_POLICY_INVALID in found


def test_with_the_decision_each_provider_has_its_own_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assistant_config, "HOSTED_PRIVACY_DECISION", "D-142")
    policy = eligibility.CasePolicy.from_env({ANTHROPIC: PSEUDONYMISED})
    assert policy.data_policy("anthropic") == PSEUDONYMISED
    assert policy.data_policy("openrouter") == SYNTHETIC_ONLY


# --- the case chat: any authorised case, nothing identifying sent ----------------------------


def test_synthetic_only_still_refuses_a_case_that_is_not_verified_synthetic(
    restrictive: Hosted,
) -> None:
    hosted = restrictive
    posts = hosted.claude.posts
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "verified synthetic" in (answer["notice"] or "")
    assert hosted.claude.posts == posts


def test_the_outside_company_is_on_no_synthetic_list() -> None:
    from ai_assistant import synthetic_eligibility

    approved = synthetic_eligibility.manifest()
    assert all(uen != OUTSIDE_UEN and name != OUTSIDE_NAME for uen, name in approved.companies)
    assert VIEWER not in approved.viewers


def test_pseudonymised_withholds_an_upload_with_no_authoritative_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> None:
    # R2: an unfamiliar upload is uncertain provenance, never assumed safe: it is withheld (its
    # name and anything read from it never reach the provider) and the rest is answered.
    hosted = build(tmp_path, monkeypatch, PSEUDONYMISED, decision=True, clm=UnverifiedUploadClm())
    before, posts = len(hosted.claude.messages), hosted.claude.posts
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "model", answer
    assert hosted.claude.posts == posts + 1
    payload = sent_since(hosted, before)
    assert "scanned-upload" not in payload.casefold()
    assert leaked(payload, case_secrets()) == []


def test_pseudonymised_answers_any_authorised_case_without_its_identities(
    private: Hosted,
) -> None:
    hosted = private
    before, posts = len(hosted.claude.messages), hosted.claude.posts
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "model", answer
    assert hosted.claude.posts == posts + 1
    assert PRIVACY_ATTRIBUTION in (answer["notice"] or "")
    payload = sent_since(hosted, before)
    assert leaked(payload, case_secrets()) == []
    assert "[COMPANY-A]" in payload or "[PERSON-" in payload or "[ID-" in payload
    # The answer the RM reads holds real values and no placeholder.
    assert ALIAS.search(answer["answer"]) is None


def test_pseudonymised_sends_no_personal_information_typed_into_the_question(
    private: Hosted,
) -> None:
    hosted = private
    before = len(hosted.claude.messages)
    status, events = hosted.ask(
        "Which documents are still missing for this case, and what should I do next? "
        "Priyanka Ramasamy (S1234567D, p.ramasamy@example.com) asked me to check.",
        case_id=WAITING_ID,
    )
    assert status == 200
    payload = sent_since(hosted, before)
    for value in ("Priyanka", "Ramasamy", "S1234567D", "p.ramasamy@example.com"):
        assert value.casefold() not in payload.casefold()
    assert ALIAS.search(done(events)["answer"]) is None


def test_rbac_and_the_safe_404_are_unchanged(private: Hosted) -> None:
    hosted = private
    posts = hosted.claude.posts
    status, events = hosted.ask(
        "Is this case ready to be sent to GoldTier?", token="rm-b", case_id=WAITING_ID
    )
    assert status == 404
    assert hosted.claude.posts == posts


# --- every other path: general chat and Support chat --------------------------------------------


def test_general_chat_sends_no_personal_information(private: Hosted) -> None:
    hosted = private
    before = len(hosted.claude.messages)
    reply, _ = general(
        hosted,
        "What documents does onboarding usually need for a company? My colleague "
        "Priyanka Ramasamy, 91234567, asked.",
    )
    assert reply.status_code == 200, reply.text
    payload = sent_since(hosted, before)
    for value in ("Priyanka", "Ramasamy", "91234567", VIEWER):
        assert value.casefold() not in payload.casefold()


def test_support_chat_sends_no_personal_information(private: Hosted) -> None:
    hosted = private
    before = len(hosted.claude.messages)
    reply = support(
        hosted,
        "How should an address mismatch be reviewed? Priyanka Ramasamy raised it.",
    )
    assert reply.status_code == 200, reply.text
    payload = sent_since(hosted, before)
    assert leaked(payload, ["Priyanka", "Ramasamy", "sam-support"]) == []
    assert ALIAS.search(reply.json()["answer"]) is None


# --- GPT-OSS through OpenRouter: the same boundary inside its own model ----------------------


@pytest.fixture
def private_gptoss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scripted: list[str],  # noqa: F811
) -> Any:
    from tests import test_hosted_gptoss

    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_DECISION", "D-134-TEST-ONLY")
    monkeypatch.setattr(
        test_hosted_gptoss.provider, "system_local_source", test_hosted_gptoss.on_internal_network
    )
    monkeypatch.setattr(assistant_config, "HOSTED_PRIVACY_DECISION", "D-142")
    monkeypatch.setattr(assistant_config, "CASE_REASONING_DECISION", None)
    env = {
        **test_hosted_gptoss.GPTOSS_ENV,
        eligibility.DATA_POLICY_VARIABLES["openrouter"]: PSEUDONYMISED,
    }
    rm = test_hosting.actor("kowalczyk-nakamura", "RM", "team-a", "CASE_ACCESS")
    rm["profile"]["display_name"] = VIEWER
    monkeypatch.setitem(test_hosting.SESSIONS, "rm-a", rm)
    site = test_hosted_gptoss.Site(tmp_path, monkeypatch, PrivateClm(), env)  # outside a list
    site.go_live()
    return site


def test_gpt_oss_answers_any_authorised_case_without_its_identities(private_gptoss: Any) -> None:
    site = private_gptoss
    before = site.chats()
    status, events = site.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "model", answer
    assert site.chats() == before + 1
    assert PRIVACY_ATTRIBUTION in (answer["notice"] or "")
    payload = json.dumps(site.openrouter.chats[before:])
    assert leaked(payload, case_secrets()) == []
    assert ALIAS.search(answer["answer"]) is None
    assert site.claude.requests == []
