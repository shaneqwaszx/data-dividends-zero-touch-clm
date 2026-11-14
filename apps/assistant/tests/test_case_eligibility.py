"""RD-1 (R2.1): the hosted assistant serves only the owner-approved synthetic cases.

The real create_app behind harden(), as in test_hosting. The CLM backend is a mock transport
that enforces team access, so the order (backend first, then the gate) is checked through the
assistant. A bounded POC rule: an exact list of case references plus a creation cutoff.
"""

import copy
import hashlib
import json
import logging
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.main import create_app
from assistant_hosting import eligibility
from assistant_hosting.eligibility import (
    CUTOFF_VARIABLE,
    INVALID,
    REFS_VARIABLE,
    REQUIRED,
    CaseGate,
    EligibilityConfigError,
    case_ref,
)
from assistant_hosting.harden import harden
from assistant_hosting.profile import refusals
from tests.test_hosting import (
    COMPOSE,
    DOCUMENTS,
    ORIGIN,
    SUMMARY,
    actor,
    hosted_settings,
    knowledge,
    no_files,
)

CUTOFF = "2026-11-12T05:07:25Z"
CUTOFF_AT = datetime(2026, 11, 12, 5, 7, 25, tzinfo=UTC)
APPROVED_REFS = ("0ff73a514d12", "125743b9c5e0", "fa1aab4d6f68")
REFUSED = {
    "code": "ASSISTANT_CASE_NOT_ELIGIBLE",
    "message": "The assistant is not available for this case.",
}
QUESTION = "What is blocking this case?"

APPROVED = UUID(SUMMARY["case"]["case_id"])  # the fixture: Mock ACRA, created 2026-10-05
UNLISTED = uuid4()  # a newly created case: everything else is right, it is just not listed
AT_CUTOFF = uuid4()
AFTER_CUTOFF = uuid4()
NAIVE_TIME = uuid4()
NO_TIME = uuid4()
MARKETPLACE = uuid4()
MARKETPLACE_MODE = uuid4()
SANDBOX = uuid4()
NOT_ACRA = uuid4()
NO_ENTITY = uuid4()
MISMATCH = uuid4()
NOT_A_CASE = uuid4()


def summary_for(case_id: UUID, **case: Any) -> dict[str, Any]:
    body = copy.deepcopy(SUMMARY)
    body["case"]["case_id"] = str(case_id)
    body["case"].update(case)
    return body


def with_source(case_id: UUID, **source: Any) -> dict[str, Any]:
    body = summary_for(case_id)
    body["case"]["entity"]["source"].update(source)
    return body


def with_marker(case_id: UUID, marker: str) -> dict[str, Any]:
    body = summary_for(case_id)
    body["case"]["source_case_id"] = f"seed-{marker}-1"
    return body


CASES: dict[UUID, Any] = {
    APPROVED: SUMMARY,
    UNLISTED: summary_for(UNLISTED),
    AT_CUTOFF: summary_for(AT_CUTOFF, created_at=CUTOFF),
    AFTER_CUTOFF: summary_for(AFTER_CUTOFF, created_at="2026-11-13T00:00:00Z"),
    NAIVE_TIME: summary_for(NAIVE_TIME, created_at="2026-10-05T04:02:37"),
    NO_TIME: summary_for(NO_TIME, created_at=None),
    MARKETPLACE: with_marker(MARKETPLACE, "ACRA_API_MARKETPLACE_MOCK_V1"),
    MARKETPLACE_MODE: with_marker(MARKETPLACE_MODE, "api_marketplace_mock"),
    SANDBOX: with_source(SANDBOX, environment="SANDBOX"),
    NOT_ACRA: with_source(NOT_ACRA, source_system="GOLDTIER"),
    NO_ENTITY: summary_for(NO_ENTITY, entity=None),
    MISMATCH: summary_for(uuid4()),  # the backend answers with another case's id
    NOT_A_CASE: {"case": "not an object"},
}
# Every case but the unlisted one is on the list, so each refusal below has its own cause.
LISTED = frozenset(case_ref(case) for case in CASES if case != UNLISTED)
ENV = {REFS_VARIABLE: ",".join(sorted(LISTED)), CUTOFF_VARIABLE: CUTOFF}
INELIGIBLE = [case for case in CASES if case != APPROVED]

SUPPORT_CAPABILITIES = ("POLICY_VIEW", "KNOWLEDGE_REVIEW", "KNOWLEDGE_CASE_READ")
SESSIONS = {
    "rm-a": actor("maya-lim", "RELATIONSHIP_MANAGER", "team-a", "CASE_ACCESS"),
    "director-a": actor("ethan-tan", "DIRECTOR", "team-a", "CASE_ACCESS", "KNOWLEDGE_REVIEW"),
    "support": {
        "profile": {
            "user_id": "support-user",
            "display_name": "support-user",
            "role": "SUPPORT",
            "team_id": None,
            "capabilities": list(SUPPORT_CAPABILITIES),
        }
    },
    "rm-b": actor("ryan-lee", "RELATIONSHIP_MANAGER", "team-b", "CASE_ACCESS"),
    "hr": actor("hr-admin", "HR", "team-hr", "MODEL_CONFIG_MANAGE"),
}
READERS = ("rm-a", "director-a", "support")


class Clm:
    """The backend: no session is 401; team B and HR get a safe 404 for every case."""

    def __init__(self) -> None:
        self.case_reads: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET", "the assistant must stay read-only toward the backend"
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        person = SESSIONS.get(token)
        if person is None:
            return httpx.Response(401, json={"detail": "no session"})
        if path == "/api/auth/me":
            return httpx.Response(200, json=person)
        if path == "/api/policies":
            return httpx.Response(200, json={"rules": []})
        profile = person["profile"]
        if profile["role"] != "SUPPORT" and profile["team_id"] != "team-a":
            return httpx.Response(404, json={"detail": "not found"})
        for case_id, body in CASES.items():
            if path == f"/api/clm/zero-touch/cases/{case_id}":
                self.case_reads.append(str(case_id))
                return httpx.Response(200, json=body)
            if path == f"/api/onboarding/cases/{case_id}/documents":
                return httpx.Response(200, json=DOCUMENTS)
        return httpx.Response(404, json={"detail": "not found"})


def build(root: Path, clm: Clm, *, gated: bool = True) -> TestClient:
    settings = hosted_settings(root)
    assert refusals(settings, ENV, env_files=no_files()) == []
    kb = knowledge(settings)
    ingest_guidance(kb)
    transport = httpx.MockTransport(clm.handler)
    app = create_app(settings, clm_transport=transport, knowledge=kb)
    if gated:
        harden(app, settings, environ=ENV, transport=transport)
    return TestClient(
        app, base_url="http://clm-assistant-proxy:8100", raise_server_exceptions=False
    )


@pytest.fixture
def clm() -> Clm:
    return Clm()


@pytest.fixture
def client(tmp_path: Path, clm: Clm) -> Iterator[TestClient]:
    with build(tmp_path, clm) as test_client:
        yield test_client


def headers(token: str) -> dict[str, str]:
    return {"cookie": f"clm_session={token}", "origin": ORIGIN}


def rows(root: Path) -> dict[str, int]:
    """Every row of every SQLite store under the data root, by store and table."""

    found: dict[str, int] = {}
    for path in sorted(root.rglob("*.sqlite3")):
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            tables = [
                row[0] for row in db.execute("select name from sqlite_master where type='table'")
            ]
            for table in tables:
                found[f"{path.relative_to(root)}:{table}"] = db.execute(
                    f'select count(*) from "{table}"'  # noqa: S608 - names from sqlite_master
                ).fetchone()[0]
    return found


def contexts(client: TestClient) -> int:
    return len(client.app.state.contexts._contexts)  # type: ignore[attr-defined]


def case_requests(case_id: UUID) -> list[tuple[str, str, dict[str, Any] | None]]:
    base = f"/assistant/cases/{case_id}"
    return [
        ("GET", base + "/brief", None),
        ("POST", base + "/chat", {"message": QUESTION}),
        ("POST", base + "/chat/stream", {"message": QUESTION}),
        ("POST", "/assistant/contexts", {"case_id": str(case_id)}),
        ("POST", base + "/feedback", {"helpful": True}),
    ]


def send(client: TestClient, token: str, method: str, path: str, body: Any) -> httpx.Response:
    if method == "GET":
        return client.get(path, headers=headers(token))
    return client.post(path, json=body, headers=headers(token))


# --- the gate on a backend summary -------------------------------------------------------------


def gate() -> CaseGate:
    return CaseGate.from_env(ENV)


@pytest.mark.parametrize(
    ("case_id", "reason"),
    [
        (UNLISTED, "CASE_NOT_LISTED"),
        (AT_CUTOFF, "CREATED_AFTER_CUTOFF"),
        (AFTER_CUTOFF, "CREATED_AFTER_CUTOFF"),
        (NAIVE_TIME, "CREATED_AT_UNCERTAIN"),
        (NO_TIME, "CREATED_AT_UNCERTAIN"),
        (MARKETPLACE, "MARKETPLACE_MARKER"),
        (MARKETPLACE_MODE, "MARKETPLACE_MARKER"),
        (SANDBOX, "SOURCE_NOT_MOCK_ACRA"),
        (NOT_ACRA, "SOURCE_NOT_MOCK_ACRA"),
        (NO_ENTITY, "SOURCE_NOT_MOCK_ACRA"),
        (MISMATCH, "CASE_ID_MISMATCH"),
        (NOT_A_CASE, "SUMMARY_MALFORMED"),
    ],
)
def test_each_rule_refuses_on_its_own(case_id: UUID, reason: str) -> None:
    assert gate()(case_id, CASES[case_id]) == reason


def test_the_approved_mock_case_is_admitted() -> None:
    assert gate()(APPROVED, SUMMARY) is None


def test_the_binding_and_its_policy_are_not_provenance() -> None:
    # The fixture has no registry binding (a real Mock case can have none), and a binding with
    # either policy id neither admits an unlisted case nor refuses a listed one.
    assert SUMMARY["case"].get("registry_evidence_binding") is None
    for policy in ("MOCK_ACRA_FIXED_90D", "MOCK_ACRA_APPROVED_POLICY"):
        binding = {"freshness_policy_id": policy, "disposition": "MISS_FETCHED"}
        assert gate()(APPROVED, summary_for(APPROVED, registry_evidence_binding=binding)) is None
        unlisted = summary_for(UNLISTED, registry_evidence_binding=binding)
        assert gate()(UNLISTED, unlisted) == "CASE_NOT_LISTED"


def test_the_absence_of_a_marketplace_token_admits_nothing() -> None:
    assert "MARKETPLACE" not in json.dumps(CASES[UNLISTED]).upper()
    assert gate()(UNLISTED, CASES[UNLISTED]) == "CASE_NOT_LISTED"


@pytest.mark.parametrize(
    ("created_at", "admitted"),
    [
        ("2026-11-12T05:07:24.999999Z", True),
        ("2026-11-12T05:07:25Z", False),
        ("2026-11-12T05:07:25.000001Z", False),
        ("2026-11-12T13:07:24+08:00", True),  # 05:07:24 UTC
        ("2026-11-12T13:07:25+08:00", False),  # exactly the cutoff
        ("2026-11-12T05:07:24+00:00", True),
        ("2026-11-12T05:07:24", False),  # no zone: uncertain
        ("not a time", False),
        ("", False),
    ],
)
def test_the_cutoff_is_strict_and_needs_a_zone(created_at: str, admitted: bool) -> None:
    body = summary_for(APPROVED, created_at=created_at)
    assert (gate()(APPROVED, body) is None) is admitted


@pytest.mark.parametrize("summary", [None, [], "text", {}, {"case": None}, {"case": {}}])
def test_a_malformed_summary_refuses(summary: Any) -> None:
    assert gate()(APPROVED, summary) is not None


def test_the_reference_is_the_sha256_prefix_of_the_server_case_id() -> None:
    assert case_ref(APPROVED) == hashlib.sha256(str(APPROVED).encode()).hexdigest()[:12]
    assert len(case_ref(uuid4())) == 12


def test_a_refusal_is_logged_with_the_reference_and_reason_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    checker = gate()
    with caplog.at_level(logging.WARNING, logger="assistant_hosting.eligibility"):
        checker(UNLISTED, CASES[UNLISTED])
    legal_name = SUMMARY["case"]["entity"]["legal_name"]
    assert case_ref(UNLISTED) in caplog.text and "CASE_NOT_LISTED" in caplog.text
    assert legal_name not in caplog.text and str(UNLISTED) not in caplog.text
    assert checker.refusals() == {"CASE_NOT_LISTED": 1}


# --- configuration -----------------------------------------------------------------------------


def test_the_approved_r21_values_parse() -> None:
    approved = CaseGate.from_env({REFS_VARIABLE: ",".join(APPROVED_REFS), CUTOFF_VARIABLE: CUTOFF})
    assert approved.refs == frozenset(APPROVED_REFS)
    assert approved.created_before == CUTOFF_AT


@pytest.mark.parametrize(
    ("environ", "code"),
    [
        ({}, REQUIRED),
        ({REFS_VARIABLE: ",".join(APPROVED_REFS)}, REQUIRED),
        ({CUTOFF_VARIABLE: CUTOFF}, REQUIRED),
        ({REFS_VARIABLE: "  ", CUTOFF_VARIABLE: CUTOFF}, REQUIRED),
        ({REFS_VARIABLE: ",".join(APPROVED_REFS), CUTOFF_VARIABLE: " "}, REQUIRED),
        ({REFS_VARIABLE: "0FF73A514D12", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d1", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12a", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12,", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12,0ff73a514d12", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "Maya's case", CUTOFF_VARIABLE: CUTOFF}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12", CUTOFF_VARIABLE: "2026-11-12T05:07:25"}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12", CUTOFF_VARIABLE: "2026-11-12T13:07:25+08:00"}, INVALID),
        ({REFS_VARIABLE: "0ff73a514d12", CUTOFF_VARIABLE: "tomorrow"}, INVALID),
    ],
)
def test_missing_or_malformed_settings_stop_the_service(
    tmp_path: Path, environ: dict[str, str], code: str
) -> None:
    with pytest.raises(EligibilityConfigError) as raised:
        CaseGate.from_env(environ)
    assert raised.value.code == code
    assert refusals(hosted_settings(tmp_path), environ, env_files=no_files()) == [code]
    assert eligibility.config_codes(environ) == [code]


def test_a_refusal_code_never_contains_the_value(tmp_path: Path) -> None:
    found = refusals(
        hosted_settings(tmp_path),
        {REFS_VARIABLE: "secret-looking-value", CUTOFF_VARIABLE: CUTOFF},
        env_files=no_files(),
    )
    assert found == [INVALID] and "secret-looking-value" not in " ".join(found)


def test_harden_refuses_to_install_without_a_valid_list(tmp_path: Path, clm: Clm) -> None:
    settings = hosted_settings(tmp_path)
    kb = knowledge(settings)
    transport = httpx.MockTransport(clm.handler)
    app = create_app(settings, clm_transport=transport, knowledge=kb)
    with pytest.raises(EligibilityConfigError):
        harden(app, settings, environ={}, transport=transport)


def test_harden_installs_the_gate(client: TestClient) -> None:
    installed = client.app.state.case_gate  # type: ignore[attr-defined]
    assert isinstance(installed, CaseGate) and installed.refs == LISTED


def test_the_overlay_requires_both_values_with_no_fallback() -> None:
    text = COMPOSE.read_text("utf-8")
    assert (
        'ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS: "${ASSISTANT_ELIGIBLE_CASE_REFS:?' in text
        and 'ASSISTANT_HOSTING_ELIGIBLE_CREATED_BEFORE: "${ASSISTANT_ELIGIBLE_CREATED_BEFORE:?'
        in text
    )
    assert "ASSISTANT_ELIGIBLE_CASE_REFS:-" not in text
    assert "ASSISTANT_ELIGIBLE_CREATED_BEFORE:-" not in text


# --- through the routes ------------------------------------------------------------------------


@pytest.mark.parametrize("token", READERS)
def test_the_approved_case_answers_for_every_role_that_can_read_it(
    client: TestClient, token: str
) -> None:
    brief = client.get(f"/assistant/cases/{APPROVED}/brief", headers=headers(token))
    assert brief.status_code == 200, brief.text
    chat = client.post(
        f"/assistant/cases/{APPROVED}/chat", json={"message": QUESTION}, headers=headers(token)
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["answered_by"] == "case_data"
    opened = client.post(
        "/assistant/contexts", json={"case_id": str(APPROVED)}, headers=headers(token)
    )
    assert opened.status_code == 200, opened.text


@pytest.mark.parametrize("token", READERS)
@pytest.mark.parametrize("case_id", INELIGIBLE)
def test_every_case_route_refuses_an_ineligible_case_and_writes_nothing(
    client: TestClient, tmp_path: Path, token: str, case_id: UUID
) -> None:
    before, open_before = rows(tmp_path), contexts(client)
    for method, path, body in case_requests(case_id):
        response = send(client, token, method, path, body)
        assert response.status_code == 403, (path, response.text)
        assert response.json() == {"detail": REFUSED}, path
    assert rows(tmp_path) == before
    assert contexts(client) == open_before


@pytest.mark.parametrize("token", ["rm-b", "hr"])
@pytest.mark.parametrize("case_id", [APPROVED, UNLISTED])
def test_another_team_still_gets_the_backends_safe_404(
    client: TestClient, clm: Clm, token: str, case_id: UUID
) -> None:
    for method, path, body in case_requests(case_id):
        response = send(client, token, method, path, body)
        assert response.status_code == 404, (path, response.text)
        assert "ASSISTANT_CASE_NOT_ELIGIBLE" not in response.text
    assert clm.case_reads == []
    assert client.app.state.case_gate.refusals() == {}  # type: ignore[attr-defined]


def test_no_session_is_still_a_401(client: TestClient) -> None:
    for method, path, body in case_requests(UNLISTED):
        response = send(client, "nobody", method, path, body)
        assert response.status_code == 401, path


def test_a_case_unknown_to_the_backend_is_still_a_404(client: TestClient) -> None:
    response = client.get(f"/assistant/cases/{uuid4()}/brief", headers=headers("rm-a"))
    assert response.status_code == 404
    assert "ASSISTANT_CASE_NOT_ELIGIBLE" not in response.text


def test_a_case_created_after_the_service_started_is_refused(
    client: TestClient, tmp_path: Path
) -> None:
    created = uuid4()
    CASES[created] = summary_for(created, created_at=datetime.now(UTC).isoformat())
    try:
        before = rows(tmp_path)
        response = client.get(f"/assistant/cases/{created}/brief", headers=headers("rm-a"))
        assert response.status_code == 403 and response.json() == {"detail": REFUSED}
        assert rows(tmp_path) == before
    finally:
        del CASES[created]


def test_records_of_a_case_taken_off_the_list_are_closed_too(
    client: TestClient, tmp_path: Path
) -> None:
    # Answers and a rated conversation exist for the approved case; then the list changes (a
    # restart with new settings). Every route that loads that case now refuses, with no write.
    first = client.post(
        f"/assistant/cases/{APPROVED}/chat", json={"message": QUESTION}, headers=headers("rm-a")
    ).json()
    conversation, answer = first["conversation_id"], first["answer_id"]
    client.post(
        f"/assistant/cases/{APPROVED}/chat",
        json={"message": QUESTION, "conversation_id": conversation},
        headers=headers("rm-a"),
    )
    ended = client.post(
        f"/assistant/conversations/{conversation}/end",
        json={"resolved": False, "satisfaction": "neutral", "comment": "Improve it."},
        headers=headers("rm-a"),
    )
    assert ended.status_code == 200, ended.text
    client.app.state.case_gate = CaseGate(LISTED - {case_ref(APPROVED)}, CUTOFF_AT)  # type: ignore[attr-defined]

    before = rows(tmp_path)
    refused = [
        ("support", "POST", f"/assistant/knowledge/conversations/{conversation}/try",
         {"kind": "guidance", "title": "Proof list", "body": "Ask the client for the lease."}),
        ("rm-a", "GET", f"/assistant/conversations/{conversation}", None),
        ("rm-a", "GET", f"/assistant/answers/{answer}", None),
        ("rm-a", "POST", f"/assistant/cases/{APPROVED}/feedback",
         {"helpful": False, "note": "Wrong.", "answer_id": answer}),
    ]  # fmt: skip
    for token, method, path, body in refused:
        response = send(client, token, method, path, body)
        assert response.status_code == 403, (path, response.text)
        assert response.json() == {"detail": REFUSED}, path
    assert rows(tmp_path) == before


def test_chat_without_a_case_is_unaffected(tmp_path: Path, clm: Clm) -> None:
    calls = [
        ("rm-a", "/assistant/contexts", {}),
        ("rm-a", "/assistant/general/chat/stream", {"message": "Hello"}),
        ("support", "/assistant/support/chat", {"message": "What is the UBO threshold?"}),
    ]
    results = []
    for gated in (True, False):
        root = tmp_path / ("gated" if gated else "ungated")
        root.mkdir()
        with build(root, clm, gated=gated) as test_client:
            results.append(
                [
                    test_client.post(path, json=body, headers=headers(token)).status_code
                    for token, path, body in calls
                ]
            )
    assert results[0] == results[1]
    assert clm.case_reads == []


def test_without_a_gate_every_readable_case_is_served_as_before(tmp_path: Path, clm: Clm) -> None:
    with build(tmp_path, clm, gated=False) as ungated:
        assert not hasattr(ungated.app.state, "case_gate")
        for case_id in (APPROVED, UNLISTED, AFTER_CUTOFF, MARKETPLACE):
            response = ungated.get(f"/assistant/cases/{case_id}/brief", headers=headers("rm-a"))
            assert response.status_code == 200, response.text
