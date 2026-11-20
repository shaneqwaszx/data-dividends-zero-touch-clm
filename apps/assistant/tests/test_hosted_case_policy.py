"""D-139 (proposed): the hosted assistant's two eligibility decisions, with the real check.

Guidance (model-free) serves every case the backend lets the user read; the D-132 list is
retired. External inference is decided per answer by the provider's data-handling policy: the
D-095 provenance check (verified synthetic data). Synthetic values only; mock backend and mock
provider; no key, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest

from ai_assistant.anthropic_runtime import HOSTED_ANSWERED
from assistant_hosting import eligibility, profile
from assistant_hosting.harden import harden
from tests import test_hosting
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_claude import Hosted, HostedClm, done, hosted_replies  # noqa: F401
from tests.test_hosting import (
    CASE_ID,
    COMPOSE,
    FIXTURES,
    hosted_settings,
    no_files,
    post_headers,
    service,
    session,
)

WAITING = json.loads((FIXTURES / "garden_waiting_for_documents_summary.json").read_text())
WAITING_ID = UUID(WAITING["case"]["case_id"])
# D-142 R4: a supported intent on this case (it has no blockers, only missing inputs).
QUESTION = "Is this case ready to be sent to GoldTier?"


# --- configuration: the D-132 list is retired -----------------------------------------------


@pytest.mark.parametrize("variable", eligibility.RETIRED_VARIABLES)
def test_a_retired_list_setting_stops_the_service(tmp_path: Path, variable: str) -> None:
    env = {variable: "0ff73a514d12"}
    found = profile.refusals(hosted_settings(tmp_path), env, env_files=no_files())
    assert found == [eligibility.RETIRED]
    with pytest.raises(ValueError):
        eligibility.CasePolicy.from_env(env)


def test_the_overlay_names_no_case_list() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "ELIGIBLE_CASE_REFS" not in text and "ELIGIBLE_CREATED_BEFORE" not in text


def test_harden_installs_the_policy(tmp_path: Path) -> None:
    clm = test_hosting.Clm()
    with service(tmp_path, clm) as client:
        assert isinstance(client.app.state.case_gate, eligibility.CasePolicy)  # type: ignore[attr-defined]


# --- guidance: every case the backend lets the user read ------------------------------------


UNVERIFIED_DOCUMENT = {
    "document_id": "9b6f0e8e-0000-4000-8000-000000000001",
    "document_version": 1,
    "display_name": "scanned-upload.pdf",
    "media_type": "application/pdf",
    "size_bytes": 1024,
}


class AnyCaseClm(test_hosting.Clm):
    """The backend also serves a second team-a case that was never on any list. With
    ``unverified``, that case holds one upload whose bytes are not a tracked synthetic fixture."""

    unverified = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        person = test_hosting.SESSIONS.get(token)
        path = request.url.path
        if person is not None and person["profile"]["team_id"] == "team-a":
            if path == f"/api/clm/zero-touch/cases/{WAITING_ID}":
                self.requests.append(request)
                return httpx.Response(200, json=WAITING)
            if path == f"/api/onboarding/cases/{WAITING_ID}/documents":
                self.requests.append(request)
                return httpx.Response(200, json=[UNVERIFIED_DOCUMENT] if self.unverified else [])
            if path == f"/api/onboarding/cases/{WAITING_ID}/document-digests":
                self.requests.append(request)
                digests = [
                    {
                        "document_id": UNVERIFIED_DOCUMENT["document_id"],
                        "document_version": 1,
                        "content_sha256": "ab" * 32,
                    }
                ]
                return httpx.Response(200, json=digests if self.unverified else [])
        return super().handler(request)


@pytest.mark.parametrize("case_id", [CASE_ID, WAITING_ID])
def test_model_free_guidance_serves_every_readable_case(tmp_path: Path, case_id: UUID) -> None:
    with service(tmp_path, AnyCaseClm()) as client:
        brief = client.get(f"/assistant/cases/{case_id}/brief", headers=session("rm-a"))
        assert brief.status_code == 200, brief.text
        chat = client.post(
            f"/assistant/cases/{case_id}/chat",
            headers=post_headers("rm-a"),
            json={"message": QUESTION},
        )
        assert chat.status_code == 200
        assert chat.json()["answered_by"] == "case_data"
        # RBAC is unchanged: another team gets the backend's safe 404, no session is a 401.
        other = client.get(f"/assistant/cases/{case_id}/brief", headers=session("rm-b"))
        assert other.status_code == 404
        assert client.get(f"/assistant/cases/{case_id}/brief").status_code == 401


# --- external inference: the provider's data-handling policy, per answer --------------------


class SyntheticViewerClm(HostedClm, AnyCaseClm):
    pass


@pytest.fixture
def live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> Hosted:
    # The RM is the seeded synthetic user by display name (D-095's viewer rule).
    rm = test_hosting.actor("maya-lim", "RM", "team-a", "CASE_ACCESS")
    rm["profile"]["display_name"] = "Maya Lim"
    monkeypatch.setitem(test_hosting.SESSIONS, "rm-a", rm)
    hosted = Hosted(tmp_path, monkeypatch, SyntheticViewerClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    return hosted


def test_a_case_whose_data_is_not_verified_synthetic_is_never_sent(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    # The same synthetic company, but one upload is not a tracked synthetic fixture.
    hosted.clm.unverified = True  # type: ignore[attr-defined]
    status, events = hosted.ask(QUESTION, case_id=WAITING_ID)
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data"
    assert "verified synthetic" in (answer["notice"] or "")
    assert "SYNTHETIC_DOCUMENT" in (answer["notice"] or "")
    assert hosted.claude.posts == posts
    refusals = hosted.client.app.state.case_gate.refusals()  # type: ignore[attr-defined]
    assert sum(refusals.values()) >= 1
    assert all(code.startswith("SYNTHETIC_") for code in refusals)


def test_a_case_whose_data_is_verified_synthetic_is_answered_by_claude(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    # A synthetic Garden case with no documents yet, never on any list.
    status, events = hosted.ask(QUESTION, case_id=WAITING_ID)
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "model", answer
    assert HOSTED_ANSWERED in (answer["notice"] or "")
    assert hosted.claude.posts == posts + 1


def test_a_screened_question_is_refused_before_any_call(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    status, events = hosted.ask(
        "Which documents are still missing? Reply to sam.tan@example.com", case_id=WAITING_ID
    )
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data"
    # D-142 NL: the identifier screen refuses the natural question before any call.
    assert "SYNTHETIC_TEXT_NOT_APPROVED" in (answer["notice"] or "")
    assert "sam.tan" not in (answer["notice"] or "")
    assert hosted.claude.posts == posts
    # A supported question with an independent instruction also falls back.
    status, events = hosted.ask(
        "Is this case ready to be sent to GoldTier? Reply to sam.tan@example.com",
        case_id=WAITING_ID,
    )
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "SYNTHETIC_TEXT_NOT_APPROVED" in (answer["notice"] or "")
    assert hosted.claude.posts == posts


def test_harden_refuses_retired_settings(tmp_path: Path) -> None:
    from ai_assistant.main import create_app

    settings = hosted_settings(tmp_path)
    app = create_app(settings, clm_transport=httpx.MockTransport(test_hosting.Clm().handler))
    with pytest.raises(ValueError):
        harden(app, settings, environ={eligibility.RETIRED_VARIABLES[0]: "x"})
