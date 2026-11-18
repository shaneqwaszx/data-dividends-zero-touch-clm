"""D-142 R1: the mandatory mocked acceptance groups (X1-X9, Y1-Y10, Z1-Z7) for the remediated
privacy boundary. Each test names its group; the crosswalk is
outputs/assistant-privacy-20261116/r1/D142_R1_ACCEPTANCE_CROSSWALK.md.

Mock backend, mock Claude, mock OpenRouter and in-memory models only; invented values; no key,
no network, no paid call.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import pytest

from ai_assistant import anthropic_chat, data_access, synthetic_eligibility
from ai_assistant import privacy_boundary as pb
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import validate_answer
from ai_assistant.guide import FIELD_LABEL
from ai_assistant.llm import ModelAnswer, Piece
from ai_assistant.model_qualification import PROBE, probe_target
from ai_assistant.prompts import build_messages
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_case_policy import WAITING_ID
from tests.test_hosted_claude import (
    Hosted,
    done,
    hosted_replies,  # noqa: F401 (fixture)
    post_headers,
)
from tests.test_hosted_claude_paths import general, support
from tests.test_hosted_privacy import (
    OUTSIDE,
    OUTSIDE_NAME,
    OUTSIDE_UEN,
    VIEWER,
    case_secrets,
    leaked,
    private,  # noqa: F401 (fixture)
    private_gptoss,  # noqa: F401 (fixture)
    sent_since,
)

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "tests" / "fixtures"
LABELS = frozenset(FIELD_LABEL.values())


def garden_snapshot(summary: dict[str, Any] | None = None) -> CaseSnapshot:
    data = summary or json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
    actor = json.loads((FIXTURES / "me_client_onboarder.json").read_text())
    return CaseSnapshot(data, [], actor)


def protect_one(text: str, known: list[tuple[str, str]] | None = None) -> str:
    protected = pb.outbound(
        pb.admit([{"role": "user", "content": text}], known or [], person_written=False)
    )
    return protected.messages[0]["content"]


def refusal(text: str, known: list[tuple[str, str]] | None = None) -> str | None:
    try:
        protect_one(text, known)
    except pb.PrivacyRefused as refused:
        return refused.code
    return None


class Recording:
    """An in-memory external model: records what it would send, writes fixed replies."""

    name = "it-model"

    def __init__(self, reply: str = "[PERSON-A] asked.\n") -> None:
        self.sent: list[list[dict[str, str]]] = []
        self.reply = reply

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.sent.append(list(messages))
        return ModelAnswer(text=self.reply)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[Piece]:
        self.sent.append(list(messages))
        yield Piece(text=self.reply)
        yield Piece(text="", finish_reason="stop")


# --- X: the privacy boundary ------------------------------------------------------------------


def test_x1_every_external_model_class_runs_the_boundary_on_every_role() -> None:
    # X1: system, user and assistant text are all transformed (a name in each role).
    messages = [
        {"role": "system", "content": "Context for the case of Priyanka Ramasamy."},
        {"role": "user", "content": "Is Priyanka Ramasamy a director?"},
        {"role": "assistant", "content": "Priyanka Ramasamy was mentioned earlier."},
    ]
    protected = pb.outbound(
        pb.admit(messages, [("PERSON", "Priyanka Ramasamy")], person_written=False)
    )
    assert leaked(json.dumps(list(protected.messages)), ["Priyanka", "Ramasamy"]) == []
    assert all("[PERSON-A]" in item["content"] for item in protected.messages)
    # The three external model classes all take the boundary (structural, plus the hosted
    # tests below for Claude and GPT-OSS and the IT model here).
    import inspect

    from ai_assistant import anthropic_runtime, remote_test

    for cls in (remote_test.RemoteTestModel, anthropic_runtime.ClaudeTestModel):
        assert "privacy_boundary.outbound(messages)" in inspect.getsource(cls._ready)
    inner = Recording()
    pb.BoundedModel(inner).complete(
        pb.admit(messages, [("PERSON", "Priyanka Ramasamy")], person_written=False)
    )
    assert leaked(json.dumps(inner.sent), ["Priyanka", "Ramasamy"]) == []


def test_x2_the_field_table_drops_unexpected_fields() -> None:
    facts = build_case_facts(garden_snapshot())
    facts["company"]["registration_date"] = "2019-04-01"
    facts["company"]["unexpected_secret"] = "SHOULD-NOT-LEAVE"
    facts["case_id"] = "ffffffff-0000-0000-0000-000000000001"
    facts["documents"] = [
        {
            "name": "passport-of-priyanka.pdf",
            "detected_type": "PASSPORT",
            "state": "UPLOADED",
            "storage_key": "s3://secret/bucket",
            "fields": [
                {"field": "Unreviewed label", "value_read_from_document": "K98765432"},
            ],
        }
    ]
    minimised = pb.minimise_facts(facts, known_labels=LABELS)
    text = json.dumps(minimised)
    for value in ("2019-04-01", "SHOULD-NOT-LEAVE", "passport-of-priyanka", "s3://", "K98765432"):
        assert value not in text
    assert minimised["case_id"] is None
    assert set(minimised["company"]) <= set(pb.COMPANY_FIELDS)


@pytest.mark.parametrize(
    "text",
    [
        "Is \\u0050riyanka a director?",  # literal unicode escape
        "Is \\x50riyanka a director?",
        "Is &#80;riyanka a director?",  # HTML numeric entity
        "Is %50%72iyanka a director?",  # percent-encoded
    ],
)
def test_x3_a_transformation_failure_sends_nothing(text: str) -> None:
    inner = Recording()
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.BoundedModel(inner).complete(
            pb.admit([{"role": "user", "content": text}], person_written=False)
        )
    assert refused.value.code == "ENCODED_INPUT"
    assert inner.sent == []


def test_x3_hosted_a_refused_prompt_reserves_and_sends_nothing(private: Hosted) -> None:  # noqa: F811
    hosted = private
    posts, before = hosted.claude.posts, len(hosted.claude.messages)
    status, events = hosted.ask(
        "What is blocking this case? Ask \\u0050riyanka.", case_id=WAITING_ID
    )
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert hosted.claude.posts == posts and len(hosted.claude.messages) == before


def test_x4_altered_unticketed_or_replayed_payloads_cannot_pass() -> None:
    messages = pb.admit(
        [{"role": "user", "content": "Is the review finished?"}], person_written=False
    )
    messages[0]["content"] = "Is Priyanka Ramasamy a director?"  # altered after admission
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(messages)
    assert refused.value.code == "ADMISSION_MISMATCH"
    # A provider call whose protected messages change after the boundary has no clearance.
    protected = pb.outbound(
        pb.admit([{"role": "user", "content": "Is the review finished?"}], person_written=False)
    )
    altered = pb.ProtectedMessages(
        [{"role": "user", "content": "Priyanka Ramasamy"}], protected.call_id or ""
    )
    assert pb.clear_call(altered) is False
    assert pb.clear_call(protected.messages) is True
    assert pb.clear_call(protected.messages) is False  # single use
    # The wire: an extra unprotected text in the exact body is refused, and once only. R3: an
    # extra user turn is history (WIRE_HISTORY); a replaced turn is caught by its own rules.
    body = json.dumps(
        {"model": "m", "messages": [*protected.messages, {"role": "user", "content": "Priyanka"}]}
    ).encode()
    with pytest.raises(pb.PrivacyRefused) as wire:
        pb.verify_wire(protected.messages, body)
    assert wire.value.code == "WIRE_HISTORY"
    with pytest.raises(pb.PrivacyRefused) as again:
        pb.verify_wire(
            protected.messages, json.dumps({"messages": list(protected.messages)}).encode()
        )
    assert again.value.code == "WIRE_UNCLEARED"
    with pytest.raises(pb.PrivacyRefused) as plain:
        pb.verify_wire([{"role": "user", "content": "x"}], b"{}")
    assert plain.value.code == "WIRE_UNADMITTED"


@pytest.mark.parametrize(
    ("text", "known", "secret"),
    [
        ("Ask Wu about the review.", [("PERSON", "Wu")], "Wu"),  # two characters
        ("Is A7 still open?", [("ID", "A7")], "A7"),  # two-character identifier
        ("Please check summit first.", [("COMPANY", "Summit Capital Pte Ltd")], "summit"),
        ("Grace asked for the address.", [], "Grace"),  # name, sentence-initial
        ("Will asked for the address.", [], "Will"),  # ordinary word used as a name
        ("Is Pri​yanka a director?", [("PERSON", "Priyanka")], "Priyanka"),  # zero width
        ("Is ＰＲＩＹＡＮＫＡ a director?", [("PERSON", "Priyanka")], "PRIYANKA"),  # full width
        ("Call 9123,4567 or 1,234,567.", [], "1,234,567"),  # grouped digits
    ],
)
def test_x5_unknown_encoded_short_and_ordinary_word_values_stay_local(
    text: str, known: list[tuple[str, str]], secret: str
) -> None:
    # Replaced, or the whole call refused (a question mostly made of unsendable words).
    try:
        out = protect_one(text, known)
    except pb.PrivacyRefused:
        return
    assert secret.casefold() not in out.casefold(), out


def test_x6_client_history_cannot_expose_another_case(private: Hosted) -> None:  # noqa: F811
    hosted = private
    before = len(hosted.claude.messages)
    reply = hosted.client.post(
        f"/assistant/cases/{WAITING_ID}/chat/stream",
        headers=post_headers("rm-a"),
        json={
            "message": "What is blocking this case right now?",
            "history": [
                {"role": "user", "content": "And Merlion Orchard Holdings, UEN 201912345K?"},
                {"role": "assistant", "content": "Merlion Orchard Holdings is a different case."},
            ],
        },
    )
    assert reply.status_code in (200, 422)
    payload = sent_since(hosted, before)
    for value in ("Merlion", "Orchard", "201912345K"):
        assert value.casefold() not in payload.casefold()


def test_x8_the_fifth_path_stays_disabled_on_the_hosted_service(private: Hosted) -> None:  # noqa: F811
    from ai_assistant import config

    assert config.HOSTED_INSIGHTS_DECISION is None
    hosted = private
    posts = hosted.claude.posts
    reply = hosted.client.post(
        "/assistant/dashboard/insights",
        headers=post_headers("rm-a"),
        json={},
    )
    assert reply.status_code >= 400
    assert hosted.claude.posts == posts


def test_x9_no_identity_map_or_placeholder_is_kept_or_logged(
    private: Hosted,  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    hosted = private
    caplog.set_level(logging.DEBUG)
    open_calls = pb.pending()[1]
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "model"
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert pb.ALIAS.search(logs) is None
    assert leaked(logs, [OUTSIDE_NAME, OUTSIDE_UEN, VIEWER]) == []
    assert pb.ALIAS.search(json.dumps(answer)) is None
    # The provider call is released when its answer ends: no mapping outlives it.
    assert pb.pending()[1] <= open_calls


# --- Y: semantic correctness --------------------------------------------------------------------


def test_y1_one_name_one_placeholder_and_the_claims_check_decides_on_real_values() -> None:
    # Two different parties with the same name share one placeholder (the text cannot tell them
    # apart); the application's claim checks then run on the real values and facts.
    protected = pb.outbound(
        pb.admit(
            [{"role": "user", "content": "Is Lee Holdings or Lee a shareholder?"}],
            [("COMPANY", "Lee Holdings"), ("PERSON", "Lee")],
            person_written=False,
        )
    )
    text = protected.messages[0]["content"]
    assert "Lee" not in text
    assert text.count("[COMPANY-A]") == 1 and "[PERSON-" in text


def test_y2_alias_shaped_real_values_are_neutralised() -> None:
    protected = pb.outbound(
        pb.admit(
            [{"role": "user", "content": "Is [COMPANY-A] the same as [PERSON-B]?"}],
            [("PERSON", "Priyanka Ramasamy")],
            person_written=False,
        )
    )
    text = protected.messages[0]["content"]
    assert "[COMPANY-A]" not in text and "[PERSON-B]" not in text
    # A reply echoing the neutralised form is dropped, not restored.
    assert protected.restore_text("(COMPANY A) owns it.\nThe review is open.\n") == (
        "The review is open.\n"
    )


def test_y4_ownership_values_thresholds_and_parties_are_exact() -> None:
    text = (
        "Priyanka Ramasamy holds 1.123456% directly, 25.5% in total and 1.1234% through "
        "Kestrel Freight; the threshold is 25%."
    )
    out = protect_one(text, [("PERSON", "Priyanka Ramasamy"), ("COMPANY", "Kestrel Freight")])
    for value in ("1.123456%", "25.5%", "1.1234%", "25%"):
        assert value in out, out
    assert "Priyanka" not in out and "Kestrel" not in out
    protected = pb.outbound(
        pb.admit(
            [{"role": "user", "content": text}],
            [("PERSON", "Priyanka Ramasamy"), ("COMPANY", "Kestrel Freight")],
            person_written=False,
        )
    )
    restored = protected.restore_text(protected.messages[0]["content"])
    assert restored == text


def test_y5_case_and_workflow_status_codes_pass_unchanged() -> None:
    for code in ("WAITING_FOR_DOCUMENTS", "READY_FOR_APPROVAL", "COMPLETE", "BLOCKED"):
        out = protect_one(f"The case status is {code}.")
        assert code in out, out


def test_y6_an_invented_source_is_still_removed_after_restoration() -> None:
    facts = build_case_facts(garden_snapshot())
    protected = pb.outbound(pb.admit([{"role": "user", "content": "Why?"}], person_written=False))
    reply = protected.restore_text("The case is ready for approval [G9].\n")
    validation = validate_answer(reply, facts, knowledge_lines=[])
    assert "[G9]" not in validation.text


def test_y7_a_placeholder_split_at_every_position_is_restored() -> None:
    known = [("PERSON", "Priyanka Ramasamy")]
    line = "[PERSON-A] asked about the review.\n"

    async def run(split: int) -> str:
        protected = pb.outbound(
            pb.admit(
                [{"role": "user", "content": "Did Priyanka Ramasamy ask?"}],
                known,
                person_written=False,
            )
        )

        async def source() -> AsyncIterator[Piece]:
            yield Piece(text=line[:split])
            yield Piece(text=line[split:])
            yield Piece(text="", finish_reason="stop")

        return "".join([piece.text async for piece in protected.restore_stream(source())])

    for split in range(1, len(line)):
        assert anyio.run(run, split) == "Priyanka Ramasamy asked about the review.\n", split


@pytest.mark.parametrize(
    "line",
    [
        "ID-Z is the identifier.",
        "[[PERSON-A]] asked.",
        "[PERSON-A]] asked.",
        "[PERSON-Q] asked.",  # never issued
        "PERSON A asked.",
        "[TEXT-ZZ] asked.",
    ],
)
def test_y8_unknown_unissued_and_malformed_placeholders_drop_the_line(line: str) -> None:
    protected = pb.outbound(
        pb.admit(
            [{"role": "user", "content": "Did Priyanka Ramasamy ask?"}],
            [("PERSON", "Priyanka Ramasamy")],
            person_written=False,
        )
    )
    assert protected.restore_text(line + "\nThe review is open.\n") == "The review is open.\n"


def test_y8_an_allocated_but_unsent_placeholder_is_never_restored() -> None:
    # [PERSON-B] exists in the shield (a component) but this call never sent it.
    protected = pb.outbound(
        pb.admit(
            [{"role": "user", "content": "Did Priyanka Ramasamy ask?"}],
            [("PERSON", "Priyanka Ramasamy"), ("PERSON", "Kowalczyk Nakamura")],
            person_written=False,
        )
    )
    unsent = [alias for alias in protected.shield.originals if alias not in protected.emitted]
    assert unsent
    for alias in unsent:
        assert protected.restore_text(f"{alias} asked.\n") == ""


def test_y9_an_interrupted_stream_never_restores_a_partial_line_late() -> None:
    known = [("PERSON", "Priyanka Ramasamy")]

    async def run() -> list[str]:
        protected = pb.outbound(
            pb.admit(
                [{"role": "user", "content": "Did Priyanka Ramasamy ask?"}],
                known,
                person_written=False,
            )
        )

        async def source() -> AsyncIterator[Piece]:
            yield Piece(text="The review is open.\n[PERS")
            yield Piece(text="ON-A] asked")
            await anyio.sleep(10)
            yield Piece(text=".\n")

        out: list[str] = []
        stream = protected.restore_stream(source())
        out.append((await stream.__anext__()).text)
        await stream.aclose()  # the RM switched case
        return out

    assert anyio.run(run) == ["The review is open.\n"]


def test_y10_a_loopback_model_is_unchanged() -> None:
    from ai_assistant.llm import OpenAICompatibleChatModel

    assert (
        data_access.model_class(Recording(), "http://127.0.0.1:8080/v1") == data_access.LOCAL_CLASS
    )
    adapter = OpenAICompatibleChatModel.__new__(OpenAICompatibleChatModel)
    adapter._url = "http://127.0.0.1:8080/v1/chat/completions"  # type: ignore[attr-defined]
    assert probe_target(adapter) is adapter


# --- Z: authorisation and qualification ---------------------------------------------------------


def test_z1_rbac_and_the_safe_404_come_first(private: Hosted) -> None:  # noqa: F811
    hosted = private
    posts = hosted.claude.posts
    status, _ = hosted.ask(
        "Is this case ready to be sent to GoldTier?", token="rm-b", case_id=WAITING_ID
    )
    assert status == 404 and hosted.claude.posts == posts
    reply = hosted.client.post(
        f"/assistant/cases/{WAITING_ID}/chat/stream", json={"message": "Why?"}
    )
    assert reply.status_code in (401, 403)


def test_z2_concurrent_identical_messages_have_independent_maps() -> None:
    same = [
        {
            "role": "user",
            "content": "Did Priyanka Ramasamy and Kowalczyk ask about the review of the documents?",
        }
    ]
    # R3: both names are known in each request (an unknown one would fall back), but to each
    # request differently, so the two identity maps differ.
    known_one = [("PERSON", "Priyanka Ramasamy"), ("PERSON", "Kowalczyk")]
    known_two = [("COMPANY", "Priyanka Ramasamy"), ("PERSON", "Kowalczyk")]
    first = pb.admit(same, known_one, person_written=False)
    second = pb.admit(same, known_two, person_written=False)
    assert first.admission_id != second.admission_id
    one, two = pb.outbound(first), pb.outbound(second)
    assert one.call_id != two.call_id
    assert one.shield.originals != two.shield.originals
    assert one.restore_text("[PERSON-A] asked.\n") == "Priyanka Ramasamy asked.\n"
    assert two.restore_text("[PERSON-A] asked.\n") == "Kowalczyk asked.\n"

    async def concurrently() -> list[str]:
        results: list[str] = []

        async def ask(known: list[tuple[str, str]]) -> None:
            inner = Recording()
            model = pb.BoundedModel(inner)
            messages = pb.admit(same, known, person_written=False)
            async for piece in model.stream(messages):
                if piece.text:
                    results.append(piece.text)

        async with anyio.create_task_group() as group:
            group.start_soon(ask, known_one)
            group.start_soon(ask, known_two)
        return sorted(results)

    assert anyio.run(concurrently) == ["Kowalczyk asked.\n", "Priyanka Ramasamy asked.\n"]


def test_z2_expired_evicted_and_consumed_admissions_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inner = Recording()
    model = pb.BoundedModel(inner)
    messages = pb.admit(
        [{"role": "user", "content": "Is the review finished?"}], person_written=False
    )
    model.complete(messages)
    with pytest.raises(pb.PrivacyRefused):
        model.complete(messages)  # consumed: a retry needs a new admission
    clock = [0.0]
    monkeypatch.setattr(pb, "_clock", lambda: clock[0])
    old = pb.admit([{"role": "user", "content": "Is the review finished?"}], person_written=False)
    clock[0] = pb.ADMISSION_SECONDS + 1
    with pytest.raises(pb.PrivacyRefused):
        model.complete(old)
    monkeypatch.setattr(pb, "_MAX_ADMISSIONS", 2)
    evicted = pb.admit(
        [{"role": "user", "content": "Is the review finished?"}], person_written=False
    )
    pb.admit([{"role": "user", "content": "Is the review finished?"}], person_written=False)
    pb.admit([{"role": "user", "content": "Is the review finished?"}], person_written=False)
    with pytest.raises(pb.PrivacyRefused):
        model.complete(evicted)
    assert len(inner.sent) == 1


def _with(summary: dict[str, Any], **changes: Any) -> dict[str, Any]:
    data = json.loads(json.dumps(summary))
    entity = data["case"]["entity"]
    for key, value in changes.items():
        if key == "environment":
            entity["source"]["environment"] = value
        elif key == "source_system":
            entity["source"]["source_system"] = value
        elif key == "no_source":
            entity.pop("source", None)
        elif key == "requested_uen":
            data["case"]["requested_uen"] = value
    return data


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, None),  # an authorised Mock POC case outside the D-095 lists
        ({"environment": "SANDBOX"}, "POC_SPONSOR_DATA"),
        ({"source_system": "UNKNOWN_REGISTRY"}, "POC_PROVENANCE_UNKNOWN"),
        ({"no_source": True}, "POC_PROVENANCE_UNKNOWN"),
        ({"requested_uen": "199999999Z"}, "POC_PROVENANCE_UNKNOWN"),
    ],
)
def test_z3_the_trusted_poc_admission(changes: dict[str, Any], expected: str | None) -> None:
    snapshot = garden_snapshot(_with(OUTSIDE, **changes))
    facts = build_case_facts(snapshot)
    assert synthetic_eligibility.poc_check(snapshot, facts, [], digests=[]) == expected


def test_z3_a_sandbox_goldtier_target_is_sponsor_data() -> None:
    snapshot = garden_snapshot(OUTSIDE)
    facts = build_case_facts(snapshot)
    facts["goldtier"] = {"goldtier_id": "143887"}
    assert synthetic_eligibility.poc_check(snapshot, facts, [], digests=[]) == "POC_SPONSOR_DATA"


def test_z3_an_unreadable_document_list_is_uncertain() -> None:
    snapshot = CaseSnapshot(OUTSIDE, [], garden_snapshot().actor, documents_loaded=False)
    facts = build_case_facts(snapshot)
    assert synthetic_eligibility.poc_check(snapshot, facts, [], digests=[]) == (
        "POC_DOCUMENTS_UNAVAILABLE"
    )


def test_z4_claude_under_pseudonymised_keeps_its_contract(private: Hosted) -> None:  # noqa: F811
    hosted = private
    before = len(hosted.claude.messages)
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    assert status == 200 and done(events)["answered_by"] == "model"
    assert leaked(sent_since(hosted, before), case_secrets()) == []


def test_z4_gptoss_under_pseudonymised_keeps_its_contract(private_gptoss: Any) -> None:  # noqa: F811
    site = private_gptoss
    chats = site.chats()
    status, events = site.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    assert status == 200 and done(events)["answered_by"] == "model"
    assert leaked(json.dumps(site.openrouter.chats[chats:]), case_secrets()) == []


def test_z5_the_exact_http_body_is_checked_and_a_corrupted_one_is_never_sent(
    private: Hosted,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The adapter builds a body that differs from the protected messages (a defect or an
    # attack after the boundary): the wire check on the exact bytes refuses it before sending.
    hosted = private
    monkeypatch.setattr(
        anthropic_chat.AnthropicChatModel,
        "payload",
        _corrupting(anthropic_chat.AnthropicChatModel.payload),
    )
    posts = hosted.claude.posts
    status, events = hosted.ask("Is this case ready to be sent to GoldTier?", case_id=WAITING_ID)
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert hosted.claude.posts == posts  # the corrupted body never left


def _corrupting(payload: Any) -> Any:
    def wrapped(self: Any, messages: list[dict[str, str]]) -> dict[str, Any]:
        body = payload(self, messages)
        body["messages"][-1]["content"] = f"{body['messages'][-1]['content']} Priyanka Ramasamy"
        return dict(body)

    return wrapped


def test_z5_every_hosted_body_has_the_protected_text_only(private: Hosted) -> None:  # noqa: F811
    hosted = private
    before = len(hosted.claude.messages)
    status, _ = hosted.ask(
        "Which documents are missing? Priyanka Ramasamy (S1234567D) asked.", case_id=WAITING_ID
    )
    assert status == 200
    for body in hosted.claude.messages[before:]:
        text = json.dumps(body)
        assert leaked(text, [*case_secrets(), "Priyanka", "S1234567D"]) == []
        assert set(body) >= {"model", "messages"}


def test_z6_qualification_uses_the_deployed_policy_and_the_real_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_assistant import config
    from ai_assistant.model_qualification import WatchedModel
    from ai_assistant.remote_test import RemoteTestModel
    from assistant_eval.hosted_paths import _FixtureGate
    from assistant_hosting import eligibility

    monkeypatch.setattr(config, "HOSTED_PRIVACY_DECISION", "D-142")
    gate = _FixtureGate("case", {eligibility.DATA_POLICY_VARIABLES["openrouter"]: pb.PSEUDONYMISED})
    assert gate.data_policy("openrouter") == pb.PSEUDONYMISED
    assert gate.data_policy("anthropic") == pb.SYNTHETIC_ONLY
    assert _FixtureGate("case", {}).data_policy("openrouter") == pb.SYNTHETIC_ONLY
    remote = RemoteTestModel.__new__(RemoteTestModel)
    watched = WatchedModel.__new__(WatchedModel)
    watched.inner = remote
    wrapped = pb.BoundedModel(watched)
    assert data_access.model_class(wrapped, "http://127.0.0.1:1/v1") == "openrouter"


def test_z7_probes_are_fixed_content_and_non_loopback_ones_take_the_boundary() -> None:
    text = json.dumps(PROBE)
    assert "case" in text and pb.ALIAS.search(text) is None
    from ai_assistant.llm import OpenAICompatibleChatModel

    adapter = OpenAICompatibleChatModel.__new__(OpenAICompatibleChatModel)
    adapter._url = "https://it-models.example.com/v1/chat/completions"  # type: ignore[attr-defined]
    assert isinstance(probe_target(adapter), pb.BoundedModel)
    # The fixed probe passes the boundary as written (nothing case-derived to remove).
    protected = pb.outbound(pb.admit(PROBE, source="probe", person_written=False))
    assert protected.messages[1]["content"] == PROBE[1]["content"]


def test_general_and_support_paths_admit_their_own_messages(private: Hosted) -> None:  # noqa: F811
    hosted = private
    before = len(hosted.claude.messages)
    reply, _ = general(hosted, "What documents does onboarding usually need? Will asked.")
    assert reply.status_code == 200
    reply = support(hosted, "How should an address mismatch be reviewed? Grace asked.")
    assert reply.status_code == 200
    payload = sent_since(hosted, before)
    assert "Grace" not in payload and "Will asked" not in payload


def test_build_messages_carry_a_single_use_admission() -> None:
    facts = build_case_facts(garden_snapshot())
    built = build_messages(pb.minimise_facts(facts, known_labels=LABELS), [], "Why?")
    admitted = pb.admit(built, pb.identities_from_facts(facts), person_written=False)
    assert pb.preview(admitted) is None  # preview does not consume
    pb.outbound(admitted)
    assert pb.preview(admitted) == "PRIVACY_ADMISSION_UNAVAILABLE"
    assert pb.preview(list(admitted)) == "PRIVACY_ADMISSION_MISSING"  # a copy has none


def test_admissions_and_cancelled_calls_do_not_accumulate() -> None:
    # R1 resource check: 600 calls (half cancelled mid-stream) leave no open provider call, and
    # the registries never exceed their caps.
    calls_before = pb.pending()[1]

    async def many() -> None:
        for number in range(600):
            model = pb.BoundedModel(Recording(reply="[PERSON-A] asked.\nmore text\n"))
            messages = pb.admit(
                [{"role": "user", "content": "Did Priyanka Ramasamy ask about the review?"}],
                [("PERSON", "Priyanka Ramasamy")],
                person_written=False,
            )
            stream = model.stream(messages)
            if number % 2:
                await stream.__anext__()
                await stream.aclose()  # cancelled by the consumer
            else:
                async for _ in stream:
                    pass

    anyio.run(many)
    admissions, calls = pb.pending()
    assert calls <= calls_before
    assert admissions <= pb._MAX_ADMISSIONS and calls <= pb._MAX_CALLS
