"""D-142 R3: regression tests reproducing every finding of the independent R2 quality gate
(outputs/assistant-privacy-20261116/r2/D142_R2_INDEPENDENT_QG.md) and the owner's R3 decisions.

    F1 (P1)  short and numeric upload-derived values are withheld; derived ownership withheld
    F2 (P1)  OD-3: a controlled, positively classified query; no history forwarded
    F3 (P2)  Claude: the privacy clearance precedes any budget reservation
    F4 (P2)  an activated non-loopback IT model gets the field table and entity rules
    F5 (P2)  provenance across every registry record family; authoritative absence
    F6 (P2)  trusted text origin is established at construction, not by the system role
    F7 (P2)  documents are bound by id and version, never by file name; end-to-end ownership
             withholding
    F8 (P3)  the case-data-free metadata request is the documented, constrained exception
    F9 (P3)  same-name registry officers stay distinct; unresolved identity is omitted

For every refused request: zero provider sends and zero budget reservations. Mock transports,
mock providers and in-memory models only; invented values; no key, no network, no paid call.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_assistant import budget, copilot, synthetic_eligibility
from ai_assistant import privacy_boundary as pb
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import officer_record_lines
from ai_assistant.llm import OpenAICompatibleChatModel
from ai_assistant.model_admin_store import ModelAdminStore
from assistant_eval.qualification import QualificationJob
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_case_policy import UNVERIFIED_DOCUMENT, WAITING_ID
from tests.test_hosted_claude import (  # noqa: F401 (fixture)
    Hosted,
    done,
    hosted_replies,
    post_headers,
)
from tests.test_hosted_privacy import (
    OUTSIDE,
    PrivateClm,
    UnverifiedUploadClm,
    build,
    case_secrets,
    leaked,
    private,  # noqa: F401 (fixture)
    sent_since,
)
from tests.test_model_management import ModelServer
from tests.test_privacy_r2 import _candidate, _upload_snapshot, actor

REMOTE = "https://it-models.synthetic.invalid/v1"


def bodies(server: ModelServer) -> list[str]:
    return [
        request.content.decode("utf-8")
        for request in server.requests
        if request.url.path.endswith("/chat/completions")
    ]


def adapter(server: ModelServer, base_url: str = REMOTE) -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url=base_url,
        model=server.model_id,
        credential="x",
        timeout_seconds=5,
        temperature=0.2,
        transport=httpx.MockTransport(server.handler),
    )


@pytest.fixture
def reservations(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every budget reservation any guarded external model makes (Claude and GPT-OSS)."""

    made: list[str] = []
    real = budget.BudgetedChatModel._reserve

    def spy(self: Any, messages: list[dict[str, str]]) -> Any:
        made.append("reserve")
        return real(self, messages)

    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", spy)
    return made


# --- F1: short and numeric upload-derived values ------------------------------------------------


def _short_value_snapshot() -> tuple[CaseSnapshot, list[dict[str, Any]]]:
    snapshot, digests = _upload_snapshot()
    unverified = snapshot.documents[1]
    unverified["fields"] = [
        *unverified["fields"],
        {"field_key": "ownership_percentage", "original_extracted_value": "37"},
        {"field_key": "unit", "original_extracted_value": "Q7"},
    ]
    return snapshot, digests


def test_f1_short_and_numeric_withheld_values_are_tracked() -> None:
    snapshot, digests = _short_value_snapshot()
    view = synthetic_eligibility.poc_view(snapshot, digests)
    assert view.withheld == 1
    from decimal import Decimal

    assert Decimal("37") in view.withheld_numbers
    assert "q7" in view.withheld_values
    facts = build_case_facts(view.snapshot)
    for text in ("Is the shareholding 37%?", "is it 37.0 percent", "unit Q7?"):
        assert synthetic_eligibility.withheld_present(
            view, [{"role": "user", "content": text}], facts
        )
    # R4 (R3-2): a number some fact merely happens to hold is not independent corroboration;
    # a Mock registry record holding it is (source lineage, not textual equality).
    facts_with = {**facts, "threshold_percent": 37}
    assert synthetic_eligibility.withheld_present(
        view, [{"role": "user", "content": "Is the threshold 37%?"}], facts_with
    )
    lineage = json.loads(json.dumps(view.snapshot.summary))
    lineage["case"].setdefault("registry_acquisition", {})["ownership_parties"] = [
        {"party_id": "p", "name": "LIM AH KOW", "ownership_percentage": "37", "provenance": {}}
    ]
    registry_view = synthetic_eligibility.PocView(
        CaseSnapshot(lineage, view.snapshot.documents, actor()),
        view.digests,
        view.withheld,
        view.withheld_values,
        view.withheld_documents,
        view.withheld_numbers,
    )
    assert not synthetic_eligibility.withheld_present(
        registry_view, [{"role": "user", "content": "Is the threshold 37%?"}], facts
    )


def test_f1_hosted_a_question_repeating_a_withheld_number_sends_and_reserves_nothing(
    private: Hosted,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    reservations: list[str],
) -> None:
    from decimal import Decimal

    from ai_assistant import main

    real = main.poc_view

    def holding(snapshot: CaseSnapshot, digests: Any) -> Any:
        view = real(snapshot, digests)
        return synthetic_eligibility.PocView(
            view.snapshot, view.digests, 1, frozenset(), frozenset(), frozenset({Decimal("37")})
        )

    monkeypatch.setattr(main, "poc_view", holding)
    hosted = private
    posts, reserved = hosted.claude.posts, len(reservations)
    status, events = hosted.ask("Is the shareholding 37 percent?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    # R4 (R3-1): what the person wrote never leaves; an unsupported question is refused first.
    assert "INTENT_UNSUPPORTED" in (answer["notice"] or "")
    assert hosted.claude.posts == posts and len(reservations) == reserved


# --- F2: the controlled query ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "email will about it",
        "per will, is it done?",
        "did rose ever approve it?",
        "the will was signed by them",
        "our contact, will, asked",
        "Kowalczyk wants an update",
        "ask about it, said mark",
        "page me when it is ready",
    ],
)
def test_f2_unclassified_person_text_sends_nothing(text: str) -> None:
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit([{"role": "user", "content": text}]))
    assert refused.value.code == "PERSON_TEXT"  # R4 (R3-1): no person text is admitted


@pytest.mark.parametrize(
    "text",
    [
        "What is blocking this case right now?",
        "Who are the directors?",
        "Approve this case.",
        "What should a Relationship Manager review next?",
        "Ask the client for a recent utility bill that shows the registered address.",
    ],
)
def test_f2_r4_questions_r3_classified_are_never_sent_as_typed(text: str) -> None:
    # R4 (R3-1): R3 sent these once every word classified (Codex R3-1: "bill" kept a person's
    # meaning). None is admitted now; the chat sends a recognised intent's canonical question.
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit([{"role": "user", "content": text}]))
    assert refused.value.code == "PERSON_TEXT"


def test_f2_client_history_is_never_forwarded_on_the_hosted_service(
    private: Hosted,  # noqa: F811
) -> None:
    hosted = private
    before = len(hosted.claude.messages)
    reply = hosted.client.post(
        f"/assistant/cases/{WAITING_ID}/chat/stream",
        headers=post_headers("rm-a"),
        json={
            "message": "Is this case ready to be sent to GoldTier?",
            "history": [
                {"role": "user", "content": "ask will about it"},
                {"role": "assistant", "content": "Kowalczyk Nakamura said Zephyrine signed."},
            ],
        },
    )
    assert reply.status_code == 200
    payload = sent_since(hosted, before)
    assert "Zephyrine" not in payload and "will about" not in payload
    assert hosted.claude.messages[before:], "the supported question was sent"
    for body in hosted.claude.messages[before:]:
        assert [m["role"] for m in body["messages"]] == ["user"]


def test_f2_the_wire_refuses_history_and_repeats_the_controlled_query() -> None:
    protected = pb.outbound(
        pb.admit([{"role": "user", "content": "What is blocking it?"}], person_written=False)
    )
    try:
        assert pb.clear_call(protected.messages)
        history = {
            "messages": [
                {"role": "user", "content": "What is blocking it?"},
                {"role": "assistant", "content": "Noted."},
            ]
        }
        with pytest.raises(pb.PrivacyRefused) as wire:
            pb.verify_wire(protected.messages, json.dumps(history).encode("utf-8"))
        assert wire.value.code == "WIRE_HISTORY"
    finally:
        pb.release(protected)
    protected = pb.outbound(
        pb.admit([{"role": "user", "content": "What is blocking it?"}], person_written=False)
    )
    try:
        assert pb.clear_call(protected.messages)
        swapped = {"messages": [{"role": "user", "content": "ask will about it"}]}
        with pytest.raises(pb.PrivacyRefused) as wire:
            pb.verify_wire(protected.messages, json.dumps(swapped).encode("utf-8"))
        # R4 (R3-3): a substituted turn no longer matches the cleared projection.
        assert wire.value.code == "WIRE_PROJECTION"
    finally:
        pb.release(protected)


def test_f2_try_content_takes_the_controlled_query() -> None:
    messages = [
        {"role": "system", "content": "RULE: ask will about the address."},
        {"role": "user", "content": "What is blocking it?"},
    ]
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit(messages, controlled=("ask will about the address.",)))
    assert refused.value.code == "PERSON_TEXT"  # R4 (R3-1): Try never goes external at all


# --- F3: Claude clearance before reservation ------------------------------------------------------


def test_f3_claude_clears_before_it_reserves(
    private: Hosted,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    reservations: list[str],
) -> None:
    order: list[str] = []
    real_clear = pb.clear_call

    def clear(messages: list[dict[str, str]]) -> bool:
        order.append("clear")
        return real_clear(messages)

    real_reserve = budget.BudgetedChatModel._reserve

    def reserve(self: Any, messages: list[dict[str, str]]) -> Any:
        order.append("reserve")
        return real_reserve(self, messages)

    monkeypatch.setattr(pb, "clear_call", clear)
    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", reserve)
    status, events = private.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    assert status == 200 and done(events)["answered_by"] == "model"
    assert order[:2] == ["clear", "reserve"]


def test_f3_an_uncleared_claude_call_reserves_and_sends_nothing(
    private: Hosted,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    reservations: list[str],
) -> None:
    hosted = private
    monkeypatch.setattr(pb, "clear_call", lambda messages: False)
    posts, reserved = hosted.claude.posts, len(reservations)
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert hosted.claude.posts == posts and len(reservations) == reserved


# --- F4: activated IT models get the field table and entity rules -------------------------------


def test_f4_an_it_qualification_and_runtime_send_the_minimised_facts(tmp_path: Path) -> None:
    server = ModelServer()
    store = ModelAdminStore(tmp_path / "jobs.sqlite3")
    qualification_id = store.begin_qualification("p", "f", "b", "biz-ops", 84)
    QualificationJob(
        store=store,
        qualification_id=qualification_id,
        profile_id="p",
        model=adapter(server),
        model_id=server.model_id,
        declared_tokens=8192,
        max_answer_tokens=600,
        basis="b",
        started_by="biz-ops",
        deadline=time.monotonic() + 600,
    ).run()
    sent = bodies(server)
    assert len(sent) > 10
    snapshots = json.loads(
        (Path(__file__).parent / "fixtures" / "eval" / "snapshots.json").read_text()
    )
    dates = {
        str(
            ((case.get("summary") or {}).get("case") or {})
            .get("entity", {})
            .get("registration_date")
        )
        for case in snapshots.get("snapshots", [])
        if isinstance(case, dict)
    } - {"None"}
    for body in sent:
        assert "registration_date" not in body  # the field table's Q1 omission
        for date in dates:
            assert date not in body


def test_f4_the_service_classifies_an_it_model_by_its_endpoint() -> None:
    from ai_assistant import data_access

    remote = pb.BoundedModel(adapter(ModelServer()))
    local = adapter(ModelServer(), "http://127.0.0.1:1234/v1")
    assert data_access.model_class(remote, REMOTE) == data_access.IT_CLASS
    assert data_access.model_class(local, "http://127.0.0.1:1234/v1") == data_access.LOCAL_CLASS


# --- F5: provenance across every registry record family ---------------------------------------


def _with_family(family: str, record: dict[str, Any]) -> dict[str, Any]:
    data = json.loads(json.dumps(OUTSIDE))
    data["case"].setdefault("registry_acquisition", {})[family] = [record]
    return data


MOCK = {"provider": "ACRA", "environment": "MOCK", "operation": "RELATIONSHIPS"}


@pytest.mark.parametrize(
    ("family", "record", "expected"),
    [
        ("relationships", {"relationship_id": "r", "provenance": MOCK}, None),
        (
            "relationships",
            {"relationship_id": "r", "provenance": {**MOCK, "environment": "SANDBOX"}},
            "POC_SPONSOR_DATA",
        ),
        (
            "relationships",
            {"relationship_id": "r", "provenance": {**MOCK, "provider": "UNKNOWN"}},
            "POC_PROVENANCE_UNKNOWN",
        ),
        ("relationships", {"relationship_id": "r"}, "POC_PROVENANCE_UNKNOWN"),
        (
            "operation_results",
            {"operation": "OFFICERS", "status": "COMPLETE", "record_count": 1, "provenance": MOCK},
            None,
        ),
        (
            "operation_results",
            {
                "operation": "OFFICERS",
                "status": "COMPLETE",
                "record_count": 1,
                "provenance": {**MOCK, "environment": "SANDBOX"},
            },
            "POC_SPONSOR_DATA",
        ),
        # Authoritative absence: nothing was acquired, so there is no provenance to show.
        (
            "operation_results",
            {
                "operation": "OFFICERS",
                "status": "NOT_ATTEMPTED",
                "record_count": 0,
                "provenance": None,
            },
            None,
        ),
        (
            "operation_results",
            {"operation": "OFFICERS", "status": "FAILED", "record_count": 0, "provenance": None},
            None,
        ),
        # A claim without provenance is unknown, even an empty one.
        (
            "operation_results",
            {"operation": "OFFICERS", "status": "EMPTY", "record_count": 0, "provenance": None},
            "POC_PROVENANCE_UNKNOWN",
        ),
        (
            "operation_results",
            {"operation": "OFFICERS", "status": "COMPLETE", "record_count": 2, "provenance": None},
            "POC_PROVENANCE_UNKNOWN",
        ),
        (
            "operation_results",
            {"operation": "OFFICERS", "status": "FAILED", "record_count": 1, "provenance": None},
            "POC_PROVENANCE_UNKNOWN",
        ),
    ],
)
def test_f5_every_record_family_needs_mock_provenance(
    family: str, record: dict[str, Any], expected: str | None
) -> None:
    snapshot = CaseSnapshot(_with_family(family, record), [], actor())
    facts = build_case_facts(snapshot)
    assert synthetic_eligibility.poc_check(snapshot, facts, [], digests=[]) == expected


# --- F6: trusted origin is established at construction ----------------------------------------


def test_f6_a_system_role_alone_is_not_trusted() -> None:
    known: list[pb.Identity] = [("PERSON", "Grace Support"), ("PERSON", "Support User")]
    wording = "You answer questions from a Support reviewer. Do not ask the user."
    dynamic = [
        {"role": "system", "content": wording},
        {"role": "user", "content": "What is blocking it?"},
    ]
    protected = pb.outbound(pb.admit(dynamic, known, person_written=False))
    pb.release(protected)
    text = protected.messages[0]["content"]
    assert "Support" not in text and "user" not in text  # dynamic system text: strict
    pb.trusted_text(wording)
    protected = pb.outbound(pb.admit(dynamic, known, person_written=False))
    pb.release(protected)
    assert protected.messages[0]["content"] == wording  # registered wording: kept


def test_f6_the_wire_applies_the_strict_rules_to_untrusted_system_text() -> None:
    known: list[pb.Identity] = [("PERSON", "Grace Support")]
    messages = [
        {"role": "system", "content": "CASE FACTS: nothing."},
        {"role": "user", "content": "What is blocking it?"},
    ]
    protected = pb.outbound(pb.admit(messages, known, person_written=False))
    try:
        assert pb.clear_call(protected.messages)
        body = {
            "system": [{"type": "text", "text": "Ask a Support reviewer."}],
            "messages": [{"role": "user", "content": "What is blocking it?"}],
        }
        with pytest.raises(pb.PrivacyRefused) as wire:
            pb.verify_wire(protected.messages, json.dumps(body).encode("utf-8"))
        # R4 (R3-3): the body is not the cleared projection (the strict scan follows it).
        assert wire.value.code == "WIRE_PROJECTION"
    finally:
        pb.release(protected)


def test_f6_the_services_own_instructions_are_registered_at_construction() -> None:
    from ai_assistant import dashboard_insights, prompts, support_chat
    from ai_assistant.model_qualification import PROBE

    for text in (
        prompts.SYSTEM_PROMPT,
        copilot.RULES,
        copilot.NO_CASE_MESSAGE,
        support_chat.RULES,
        dashboard_insights.INSTRUCTIONS,
        PROBE[0]["content"],
    ):
        assert pb.is_trusted_text(text)
    assert not pb.is_trusted_text("CASE FACTS (current, from the onboarding app):\n{}")


# --- F7: same file names; end-to-end ownership withholding --------------------------------------


def test_f7_documents_are_bound_by_id_and_version_not_by_file_name() -> None:
    snapshot, digests = _upload_snapshot()
    snapshot.documents[1]["display_name"] = snapshot.documents[0]["display_name"]
    summary = snapshot.summary
    summary["reconciliation"]["discrepancies"][0]["observations"].append(
        {
            "source_kind": "DOCUMENT_IDP",
            "document_id": "doc-verified",
            "document_version": 1,
            "document_display_name": snapshot.documents[0]["display_name"],
            "normalized_value": "KESTREL FREIGHT",
        }
    )
    view = synthetic_eligibility.poc_view(snapshot, digests)
    assert [d["document_id"] for d in view.snapshot.documents] == ["doc-verified"]
    observations = view.snapshot.summary["reconciliation"]["discrepancies"][0]["observations"]
    assert {o.get("document_id") for o in observations} == {None, "doc-verified"}
    facts = build_case_facts(view.snapshot)
    assert synthetic_eligibility.poc_check(view.snapshot, facts, [], digests=view.digests) is None
    assert ("doc-upload", 1, "ab" * 32) in view.withheld_documents


def test_f7_an_observation_naming_no_document_id_is_uncertain() -> None:
    snapshot, digests = _upload_snapshot()
    snapshot.summary["reconciliation"]["discrepancies"][0]["observations"].append(
        {"source_kind": "DOCUMENT_IDP", "document_display_name": "fixture.pdf"}
    )
    view = synthetic_eligibility.poc_view(snapshot, digests)
    facts = build_case_facts(view.snapshot)
    assert synthetic_eligibility.poc_check(view.snapshot, facts, [], digests=view.digests) == (
        "POC_DOCUMENT_PROVENANCE_UNKNOWN"
    )


OWNERSHIP = {
    "state": "COMPLETE",
    "provider_environment": "MOCK",
    "threshold_percent": "25",
    "threshold_comparator": "GREATER_THAN_OR_EQUAL",
    "candidates": [_candidate("party-1", "QUILLON VARGAS", "60")],
}


class _Owned:
    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/api/onboarding/cases/{WAITING_ID}/ownership":
            self.requests.append(request)  # type: ignore[attr-defined]
            return httpx.Response(200, json=OWNERSHIP)
        return super().handler(request)  # type: ignore[misc]


class OwnedUploadClm(_Owned, UnverifiedUploadClm):
    pass


class OwnedClm(_Owned, PrivateClm):
    pass


def _conversational(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clm: Any) -> Hosted:
    from ai_assistant.privacy_boundary import PSEUDONYMISED

    hosted = build(tmp_path, monkeypatch, PSEUDONYMISED, decision=True, clm=clm)
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "TEST-OWNER-APPROVAL")
    hosted.settings.answer_mode = "copilot"
    return hosted


def test_f7_end_to_end_the_ownership_analysis_is_withheld_with_an_unverified_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> None:
    hosted = _conversational(tmp_path, monkeypatch, OwnedUploadClm())
    before = len(hosted.claude.messages)
    status, _ = hosted.ask("Who are the ultimate beneficial owners?", case_id=WAITING_ID)
    assert status == 200
    payload = sent_since(hosted, before)
    assert payload  # the case is still answered, from its independently authorised facts
    assert "QUILLON" not in payload and "direct_percent" not in payload
    assert "scanned-upload" not in payload.casefold()
    assert "not shared while an uploaded document is withheld" in payload


def test_f7_end_to_end_without_an_upload_the_ownership_analysis_is_sent_pseudonymised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
) -> None:
    hosted = _conversational(tmp_path, monkeypatch, OwnedClm())
    before = len(hosted.claude.messages)
    status, _ = hosted.ask("Who are the ultimate beneficial owners?", case_id=WAITING_ID)
    assert status == 200
    payload = sent_since(hosted, before)
    assert payload and "direct_percent" in payload and "QUILLON" not in payload
    assert "party-1" not in payload and "company-1" not in payload


# --- F8: the metadata request ---------------------------------------------------------------------


def test_f8_the_wrapper_offers_its_own_methods_only() -> None:
    server = ModelServer()
    model = pb.BoundedModel(adapter(server))
    for name in ("bind_wire_check", "_payload", "_client", "_credential", "prompt_bytes"):
        with pytest.raises(AttributeError):
            getattr(model, name)
    assert model._url.startswith(REMOTE)
    assert model.listed_models() == [server.model_id]
    gets = [r for r in server.requests if r.method == "GET"]
    assert len(gets) == 1 and gets[0].url.path.endswith("/models") and gets[0].content == b""
    assert bodies(server) == []


# --- F9: same-name registry officers ------------------------------------------------------------


def _officers(*records: dict[str, Any]) -> dict[str, Any]:
    return {"registry_officer_records": list(records)}


def test_f9_two_officers_of_one_name_get_distinct_placeholders() -> None:
    facts = _officers(
        {"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-1"},
        {"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-2"},
    )
    external = pb.qualify_entities(facts)
    names = [r["name"] for r in external["registry_officer_records"]]
    assert names == ["TAN WEI MING entity-1", "TAN WEI MING entity-2"]
    assert "o-1" not in json.dumps(external) and "officer_ref" not in json.dumps(external)
    known = pb.identities_from_facts(facts)
    protected = pb.outbound(
        pb.admit(
            [
                {"role": "system", "content": json.dumps(external)},
                {"role": "user", "content": "Who are the directors?"},
            ],
            known,
            person_written=False,
        )
    )
    pb.release(protected)
    aliases = pb.ALIAS.findall(protected.messages[0]["content"])
    assert len({f"[{kind}-{letters}]" for kind, letters in aliases}) == 2
    for kind, letters in aliases:
        assert protected.restore_line(f"[{kind}-{letters}] is a director.") == (
            "TAN WEI MING is a director."
        )


@pytest.mark.parametrize(
    "facts",
    [
        # Two officers of one name, one without its id: identity not established.
        _officers(
            {"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-1"},
            {"name": "TAN WEI MING", "role": "SECRETARY", "officer_ref": None},
        ),
        # An officer whose name is also an ownership party's: no verified link joins them.
        {
            **_officers({"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-1"}),
            "ownership": copilot.ownership_facts(
                {"candidates": [_candidate("p-1", "TAN WEI MING", "60")]}
            ),
        },
    ],
)
def test_f9_officers_of_unresolved_identity_are_omitted_not_merged(facts: dict[str, Any]) -> None:
    external = pb.qualify_entities(facts)
    assert all(r["name"] != "TAN WEI MING" for r in external.get("registry_officer_records") or [])
    assert "TAN WEI MING" not in json.dumps(external.get("registry_officer_records"))


def test_f9_officer_lines_are_built_from_the_qualified_records() -> None:
    snapshot = CaseSnapshot(json.loads(json.dumps(OUTSIDE)), [], actor())
    facts = build_case_facts(snapshot)
    facts["registry_officer_records"] = [
        {"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-1"},
        {"name": "TAN WEI MING", "role": "DIRECTOR", "officer_ref": "o-2"},
    ]
    local = officer_record_lines(pb.strip_entity_refs(facts))
    external = officer_record_lines(pb.qualify_entities(facts))
    assert len(local) <= 1  # the local view: one rendered line (as before)
    assert len(external) in (0, 2)  # the external view: one line per officer, or none


# --- no structural id or raw value in answers, records, logs or telemetry -----------------------


def test_no_structural_id_or_raw_value_in_answers_logs_or_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: Any,  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    hosted = _conversational(tmp_path, monkeypatch, OwnedClm())
    before = len(hosted.claude.messages)
    status, events = hosted.ask("Who are the ultimate beneficial owners?", case_id=WAITING_ID)
    assert status == 200
    answer = done(events)
    logs = "\n".join(record.getMessage() for record in caplog.records)
    payload = sent_since(hosted, before)
    for text in (logs, json.dumps(answer), payload):
        assert "party-1" not in text and "company-1" not in text and "o-1" not in text
    assert leaked(logs, case_secrets()) == []
    assert pb.ALIAS.search(json.dumps(answer)) is None
    # Every file the hosted service wrote (answer records, conversations, ledgers, stores).
    written = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert written
    for path in written:
        data = path.read_bytes()
        assert b"party-1" not in data and b"company-1" not in data, path.name
        assert pb.ALIAS.search(data.decode("utf-8", "ignore")) is None, path.name
    assert UNVERIFIED_DOCUMENT["display_name"] not in payload
