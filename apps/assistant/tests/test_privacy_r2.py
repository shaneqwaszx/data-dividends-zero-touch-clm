"""D-142 R2: the four delta findings on R1 (D-1 to D-4) and the owner's upload direction.

    D-1  a model IT configured on an endpoint that is not literal loopback is qualified, counted
         and capacity-measured through the same privacy boundary it runs behind once activated
    D-2  the final transport check passes only a live, cleared, unsent call for exactly its
         messages, once
    D-3  short and ordinary words of known names are protected where they are name-like
    D-4  entities that share a name are told apart by their authoritative ids, never merged
    OD-3 (owner decision): unclassifiable person references in what a person writes send
         nothing; the deterministic case-data answer follows
    U    an unverified upload is withheld with what was derived from it; Mock provenance
         (the ACRA Mock and the Marketplace Mock) is recognised; sponsor and uncertain data stay
         out

Mock transports and in-memory models only; invented values; no key, no network, no paid call.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_assistant import copilot, synthetic_eligibility
from ai_assistant import privacy_boundary as pb
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.llm import ModelAnswer, OpenAICompatibleChatModel
from ai_assistant.model_admin_store import ModelAdminStore
from ai_assistant.model_qualification import probe_target, verify_capacity
from assistant_eval.qualification import QualificationJob
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_case_policy import WAITING_ID
from tests.test_hosted_claude import Hosted, done, hosted_replies  # noqa: F401 (fixture)
from tests.test_hosted_privacy import OUTSIDE, private, sent_since  # noqa: F401 (fixture)
from tests.test_model_management import ModelServer

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "tests" / "fixtures"
REMOTE = "https://it-models.synthetic.invalid/v1"


def actor() -> dict[str, Any]:
    return json.loads((FIXTURES / "me_client_onboarder.json").read_text())


def adapter(server: ModelServer, base_url: str = REMOTE) -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url=base_url,
        model=server.model_id,
        credential="x",
        timeout_seconds=5,
        temperature=0.2,
        transport=httpx.MockTransport(server.handler),
    )


def bodies(server: ModelServer) -> list[str]:
    return [
        request.content.decode("utf-8")
        for request in server.requests
        if request.url.path.endswith("/chat/completions")
    ]


CASE = [("COMPANY", "KESTREL FREIGHT"), ("ID", "202699123K"), ("PERSON", "Do Van An")]


def case_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "Do not invent facts. CASE FACTS: KESTREL FREIGHT (202699123K); "
            "director Do Van An.",
        },
        {"role": "user", "content": "Did do sign for KESTREL FREIGHT?"},
    ]


# --- D-2: final transport verification ------------------------------------------------------


def _body(messages: list[dict[str, str]]) -> bytes:
    return json.dumps({"model": "m", "messages": list(messages)}).encode("utf-8")


def test_d2_the_wire_refuses_a_call_its_caller_never_cleared() -> None:
    protected = pb.outbound(pb.admit(case_messages(), CASE, person_written=False))
    try:
        with pytest.raises(pb.PrivacyRefused) as refused:
            pb.verify_wire(protected.messages, _body(protected.messages))
        assert refused.value.code == "WIRE_UNCLEARED"
    finally:
        pb.release(protected)


def test_d2_a_cleared_call_passes_exactly_once() -> None:
    protected = pb.outbound(pb.admit(case_messages(), CASE, person_written=False))
    try:
        assert pb.clear_call(protected.messages)
        pb.verify_wire(protected.messages, _body(protected.messages))
        with pytest.raises(pb.PrivacyRefused) as again:
            pb.verify_wire(protected.messages, _body(protected.messages))
        assert again.value.code == "WIRE_UNCLEARED"
        assert not pb.clear_call(protected.messages)  # nor can it be cleared again
    finally:
        pb.release(protected)


def test_d2_the_wire_is_bound_to_the_exact_messages_of_its_call() -> None:
    protected = pb.outbound(pb.admit(case_messages(), CASE, person_written=False))
    other = pb.outbound(
        pb.admit([{"role": "user", "content": "What is blocking it?"}], person_written=False)
    )
    try:
        assert pb.clear_call(protected.messages)
        # Another call's id on these messages, or these messages altered under their own id.
        swapped = pb.ProtectedMessages(list(protected.messages), other.call_id or "")
        with pytest.raises(pb.PrivacyRefused) as wrong_call:
            pb.verify_wire(swapped, _body(protected.messages))
        assert wrong_call.value.code == "WIRE_UNCLEARED"
        altered = pb.ProtectedMessages(
            [*protected.messages[:1], {"role": "user", "content": "Something else?"}],
            protected.call_id or "",
        )
        with pytest.raises(pb.PrivacyRefused) as changed:
            pb.verify_wire(altered, _body(altered))
        assert changed.value.code == "WIRE_UNCLEARED"
    finally:
        pb.release(protected)
        pb.release(other)


def test_d2_an_expired_or_released_call_never_reaches_the_wire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protected = pb.outbound(pb.admit(case_messages(), CASE, person_written=False))
    assert pb.clear_call(protected.messages)
    now = time.monotonic()
    monkeypatch.setattr(pb, "_clock", lambda: now + pb.ADMISSION_SECONDS + 1)
    with pytest.raises(pb.PrivacyRefused):
        pb.verify_wire(protected.messages, _body(protected.messages))
    monkeypatch.undo()
    pb.release(protected)
    with pytest.raises(pb.PrivacyRefused):
        pb.verify_wire(protected.messages, _body(protected.messages))


def test_d2_a_bounded_it_adapter_sends_nothing_outside_a_cleared_call() -> None:
    server = ModelServer()
    raw = adapter(server)
    pb.BoundedModel(raw)  # binds the adapter's transport check
    for call in (raw.complete, raw.prompt_tokens):
        with pytest.raises(pb.PrivacyRefused) as refused:
            call(case_messages())
        assert refused.value.code == "WIRE_UNADMITTED"
    assert bodies(server) == []


def test_d2_the_clearance_precedes_any_reservation_on_every_bounded_call() -> None:
    order: list[str] = []
    real_clear = pb.clear_call

    def clear(messages: list[dict[str, str]]) -> bool:
        order.append("clear")
        return real_clear(messages)

    class Inner:
        name = "it"

        def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
            order.append("send")
            return ModelAnswer("ok")

    original = pb.clear_call
    pb.clear_call = clear  # type: ignore[assignment]
    try:
        pb.BoundedModel(Inner()).complete(pb.admit(case_messages(), CASE, person_written=False))
    finally:
        pb.clear_call = original  # type: ignore[assignment]
    assert order == ["clear", "send"]


# --- D-1: qualification, token counting and capacity through the boundary --------------------


def test_d1_token_counting_of_a_non_loopback_model_takes_the_boundary() -> None:
    server = ModelServer()
    model = probe_target(adapter(server))
    assert isinstance(model, pb.BoundedModel)
    tokens, sent = model.measure(pb.admit(case_messages(), CASE, person_written=False))
    assert tokens is not None and tokens > 0
    (body,) = bodies(server)
    assert "KESTREL" not in body and "202699123K" not in body and "Do Van" not in body
    assert json.loads(body)["messages"] == list(sent)  # the bound is taken on what was sent
    # An unadmitted count is refused; nothing else is sent.
    with pytest.raises(pb.PrivacyRefused):
        model.prompt_tokens(case_messages())
    assert len(bodies(server)) == 1


def test_d1_the_wrapper_exposes_no_request_internals() -> None:
    model = pb.BoundedModel(adapter(ModelServer()))
    for name in ("_payload", "_client", "_headers", "_sse_frames", "_credential", "_transport"):
        with pytest.raises(AttributeError):
            getattr(model, name)


def test_d1_capacity_is_measured_on_the_protected_payload() -> None:
    server = ModelServer()
    model = probe_target(adapter(server), retain_largest=True)
    assert isinstance(model, pb.BoundedModel)
    model.complete(pb.admit(case_messages(), CASE, person_written=False))
    sent_turn = json.loads(bodies(server)[0])["messages"]
    result = verify_capacity(
        model, declared_tokens=8192, max_answer_tokens=600, largest_prompt=None
    )
    assert result["status"] == "verified", result
    capacity = bodies(server)[1:]
    assert len(capacity) >= 4
    for body in capacity:
        assert "KESTREL" not in body and "202699123K" not in body
    # The largest-prompt check re-sent exactly the protected turn after a unique header.
    remeasured = [json.loads(body)["messages"] for body in capacity]
    assert any(messages[1:] == sent_turn for messages in remeasured)
    headers = {messages[0]["content"] for messages in remeasured}
    assert len(headers) == len(remeasured)  # every header stays unique when protected
    model.forget()
    assert model.measure_largest([{"role": "system", "content": "x"}]) is None


def test_d1_a_loopback_model_is_qualified_as_before() -> None:
    server = ModelServer()
    local = adapter(server, "http://127.0.0.1:1234/v1")
    assert probe_target(local, retain_largest=True) is local
    result = verify_capacity(
        local,
        declared_tokens=8192,
        max_answer_tokens=600,
        largest_prompt=[{"role": "user", "content": "rules " * 50}],
    )
    assert result["status"] == "verified"


def test_d1_an_it_qualification_of_a_non_loopback_model_sends_only_protected_payloads(
    tmp_path: Path,
) -> None:
    server = ModelServer()
    store = ModelAdminStore(tmp_path / "jobs.sqlite3")
    qualification_id = store.begin_qualification("p", "f", "b", "biz-ops", 84)
    job = QualificationJob(
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
    )
    job.run()
    item = store.qualification(qualification_id)
    assert item is not None and item["status"] in ("passed", "failed"), item
    sent = bodies(server)
    assert len(sent) > 10
    for body in sent:
        folded = body.casefold()
        assert "garden business" not in folded and "11111999a" not in folded
    assert any("[COMPANY-" in body for body in sent)
    summary = item["summary"] or {}
    capacity = summary.get("capacity") or {}
    assert capacity.get("status") == "verified", capacity
    # The prompt bound is the protected payload's, and the identity map was not kept.
    assert summary["metrics"]["largest_prompt_bound"] > 0
    assert pb.pending()[1] == 0


# --- D-3: short and ordinary words of known names --------------------------------------------


def protect_messages(
    messages: list[dict[str, str]], known: list[pb.Identity]
) -> list[dict[str, str]]:
    protected = pb.outbound(pb.admit(messages, known, person_written=False))
    pb.release(protected)
    return list(protected.messages)


def test_d3_short_and_ordinary_name_words_are_protected_in_free_text() -> None:
    known: list[pb.Identity] = [
        ("PERSON", "Do Van An"),
        ("PERSON", "Ng Kai Wen"),
        ("PERSON", "Will Ong"),
    ]
    text = "did do sign? did Do sign? is ng here? and NG? will will reply? An answer?"
    (sent,) = protect_messages([{"role": "user", "content": text}], known)
    words = {word.casefold() for word in pb._PART.findall(pb.ALIAS.sub(" ", sent["content"]))}
    assert not words & {"do", "an", "ng", "will", "ong", "kai", "wen"}


def test_d3_the_services_own_text_keeps_its_wording_and_loses_name_uses() -> None:
    known: list[pb.Identity] = [("PERSON", "Do Van An"), ("PERSON", "Ng Kai Wen")]
    # R3: only wording registered as trusted at construction keeps this treatment.
    system = pb.trusted_text(
        "Do not invent facts. Ask the director, Mr Ng, before you do anything."
    )
    (sent,) = protect_messages([{"role": "system", "content": system}], known)
    content = sent["content"]
    assert content.startswith("Do not invent facts.")  # a sentence opener of the service
    assert "Ng" not in content and "[PERSON-" in content  # a name use is replaced
    assert "before you do anything" in content  # an ordinary lower-case word stays


def test_d3_the_scrubs_own_phrase_is_never_taken_for_a_name() -> None:
    # R3 (QG P2, trusted origin): the phrase has no exemption any more. A known person named
    # "Support User" loses the word wherever a person wrote it; the question still goes.
    known: list[pb.Identity] = [("PERSON", "Support User")]
    (sent,) = protect_messages(
        [{"role": "user", "content": "What can the user change? Ask user support."}], known
    )
    assert "user" not in sent["content"].casefold() and "[PERSON-" in sent["content"]


def test_d3_a_name_word_that_is_a_service_term_keeps_the_services_wording() -> None:
    # A person whose name holds one of the service's own terms ("Support"): the service's
    # system text keeps its wording; a question naming the person still loses the word.
    vocab = pb.vocabulary()
    assert "Support" in vocab.terms
    known: list[pb.Identity] = [("PERSON", "Grace Support")]
    system = pb.trusted_text("You answer questions from a Support reviewer.")
    sent = protect_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": "did support sign? did Support sign?"},
        ],
        known,
    )
    assert sent[0]["content"] == system
    assert "support" not in sent[1]["content"].casefold()


def test_d3_particles_and_honorifics_alone_identify_nobody() -> None:
    vocab = pb.vocabulary()
    assert pb._ambiguous_parts("PERSON", "Ahmad bin Ismail", vocab) == []
    assert pb._ambiguous_parts("PERSON", "Mr Do Van An", vocab) == ["Do", "An"]
    (sent,) = protect_messages(
        [{"role": "user", "content": "is ahmad the shareholder?"}], [("PERSON", "Ahmad bin Ismail")]
    )
    assert "ahmad" not in sent["content"].casefold()


def test_d3_the_residual_check_and_the_wire_catch_a_missed_name_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    known: list[pb.Identity] = [("PERSON", "Do Van An")]
    monkeypatch.setattr(pb.Shield, "protect_text", lambda self, text, role="user": text)
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.protect([{"role": "user", "content": "did do sign"}], known, person_written=False)
    assert refused.value.code == "KNOWN_VALUE"
    monkeypatch.undo()
    protected = pb.outbound(
        pb.admit([{"role": "user", "content": "did do sign"}], known, person_written=False)
    )
    try:
        assert pb.clear_call(protected.messages)
        corrupted = json.dumps({"messages": [{"role": "user", "content": "did do sign"}]}).encode(
            "utf-8"
        )
        with pytest.raises(pb.PrivacyRefused) as wire:
            pb.verify_wire(protected.messages, corrupted)
        # R4 (R3-3): a body that is not the cleared projection is refused first.
        assert wire.value.code == "WIRE_PROJECTION"
    finally:
        pb.release(protected)


def test_d3_the_wire_reads_each_text_under_its_own_role() -> None:
    known: list[pb.Identity] = [("PERSON", "Do Van An")]
    messages = [
        {"role": "system", "content": "Do not invent facts."},
        {"role": "user", "content": "What is blocking it?"},
    ]
    for shape in ("openai", "anthropic"):
        protected = pb.outbound(pb.admit(messages, known, person_written=False))
        try:
            assert pb.clear_call(protected.messages)
            system, user = protected.messages
            body = (
                {"messages": [dict(system), dict(user)]}
                if shape == "openai"
                else {
                    "system": [{"type": "text", "text": system["content"]}],
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "text": user["content"]}]}
                    ],
                }
            )
            pb.verify_wire(protected.messages, json.dumps(body).encode("utf-8"))
        finally:
            pb.release(protected)


# --- D-4: entities that share a name ---------------------------------------------------------


def _candidate(party_id: str, name: str, percent: str) -> dict[str, Any]:
    return {
        "party": {"party_id": party_id, "display_name": name},
        "direct_ownership_percent": percent,
        "indirect_ownership_percent": "0",
        "aggregated_ownership_percent": percent,
        "classification": "UBO",
        "threshold_result": "MEETS",
        "paths": [
            {
                "is_direct": True,
                "edges": [
                    {
                        "parent_party_id": party_id,
                        "parent_display_name": name,
                        "child_party_id": "company-1",
                        "child_display_name": "KESTREL FREIGHT",
                        "ownership_percent": percent,
                    }
                ],
                "effective_ownership_percent": percent,
            }
        ],
    }


def shared_ownership() -> dict[str, Any]:
    return copilot.ownership_facts(
        {
            "state": "COMPLETE",
            "provider_environment": "MOCK",
            "threshold_percent": "25",
            "threshold_comparator": "GREATER_THAN_OR_EQUAL",
            "candidates": [
                _candidate("party-1", "TAN WEI MING", "40"),
                _candidate("party-2", "TAN WEI MING", "60"),
            ],
        }
    )


def test_d4_the_ownership_facts_keep_distinct_parties_apart() -> None:
    ownership = shared_ownership()
    assert [person["party_ref"] for person in ownership["people"]] == ["party-1", "party-2"]
    # Two holdings with the same text but distinct parties are both kept (never merged).
    assert len(ownership["relationships"]) == 2
    stripped = pb.strip_entity_refs({"ownership": ownership})
    text = json.dumps(stripped)
    assert "party-1" not in text and "party-2" not in text and "_ref" not in text


def test_d4_distinct_entities_with_one_name_get_distinct_placeholders() -> None:
    facts = {"ownership": shared_ownership()}
    known = pb.identities_from_facts(facts)
    external = pb.qualify_entities(facts)
    rendered = json.dumps(external)
    assert "TAN WEI MING entity-1" in rendered and "TAN WEI MING entity-2" in rendered
    assert "party-" not in rendered
    messages = [
        {"role": "system", "content": "CASE FACTS: " + rendered},
        {"role": "user", "content": "Does TAN WEI MING hold more than 50%?"},
    ]
    protected = pb.outbound(pb.admit(messages, known, person_written=False))
    pb.release(protected)
    system, user = protected.messages
    assert "TAN WEI MING" not in system["content"] and "entity-" not in system["content"]
    data = json.loads(system["content"][system["content"].index("{") :])
    people = [person["name"] for person in data["ownership"]["people"]]
    assert len(set(people)) == 2 and all(pb.ALIAS.fullmatch(name) for name in people)
    # The unqualified name in the question cannot be bound to one entity: a third placeholder.
    (asked,) = pb.ALIAS.findall(user["content"])
    assert f"[{asked[0]}-{asked[1]}]" not in people
    # Each placeholder restores to the name as the case writes it.
    for name in people:
        assert protected.restore_line(f"{name} holds it.") == "TAN WEI MING holds it."


def test_d4_one_entity_under_one_id_stays_one_placeholder() -> None:
    ownership = copilot.ownership_facts(
        {
            "candidates": [
                _candidate("party-1", "TAN WEI MING", "40"),
                _candidate("party-9", "LIM AH KOW", "60"),
            ]
        }
    )
    facts = {"ownership": ownership}
    assert pb.shared_names(facts) == {}
    assert "entity-" not in json.dumps(pb.qualify_entities(facts))


def test_d4_a_shared_name_without_a_reference_is_not_merged_into_one_entity() -> None:
    ownership = shared_ownership()
    ownership.pop("relationship_refs")
    external = pb.qualify_entities({"ownership": ownership})["ownership"]
    assert external["relationships"] == []  # left out, never attributed to one entity


def test_d4_a_local_model_never_receives_the_party_ids() -> None:
    facts = {"ownership": shared_ownership()}
    assert "party-1" not in json.dumps(pb.strip_entity_refs(facts))


# --- U: unverified uploads, Mock provenance ---------------------------------------------------


def _approved_fixture() -> tuple[str, tuple[str, int]]:
    approved = synthetic_eligibility.manifest()
    digest, (media, size) = sorted(approved.documents.items())[0]
    return digest, (media, size)


def _upload_snapshot() -> tuple[CaseSnapshot, list[dict[str, Any]]]:
    digest, (media, size) = _approved_fixture()
    verified = {
        "document_id": "doc-verified",
        "document_version": 1,
        "display_name": "fixture.pdf",
        "media_type": media,
        "size_bytes": size,
        "fields": [],
    }
    unverified = {
        "document_id": "doc-upload",
        "document_version": 1,
        "display_name": "private-scan.pdf",
        "media_type": "application/pdf",
        "size_bytes": 2048,
        "fields": [{"field_key": "legal_name", "original_extracted_value": "ZEPHYRINE ORCHID"}],
    }
    summary = json.loads(json.dumps(OUTSIDE))
    summary["reconciliation"] = {**(summary.get("reconciliation") or {})}
    summary["reconciliation"]["discrepancies"] = [
        {
            "field_name": "legal_name",
            "status": "CONFLICT",
            "observations": [
                {"source_kind": "REGISTRY", "normalized_value": "KESTREL FREIGHT"},
                {
                    "source_kind": "DOCUMENT_IDP",
                    "document_id": "doc-upload",
                    "document_display_name": "private-scan.pdf",
                    "normalized_value": "ZEPHYRINE ORCHID",
                },
            ],
        }
    ]
    summary["active_exceptions"] = [
        {"evidence": [{"field_key": "legal_name", "document_value": "ZEPHYRINE ORCHID"}]}
    ]
    digests = [
        {"document_id": "doc-verified", "document_version": 1, "content_sha256": digest},
        {"document_id": "doc-upload", "document_version": 1, "content_sha256": "ab" * 32},
    ]
    return CaseSnapshot(summary, [verified, unverified], actor()), digests


def test_u_an_unverified_upload_and_what_was_derived_from_it_are_withheld() -> None:
    snapshot, digests = _upload_snapshot()
    view = synthetic_eligibility.poc_view(snapshot, digests)
    assert view.withheld == 1
    assert [d["document_id"] for d in view.snapshot.documents] == ["doc-verified"]
    text = json.dumps(view.snapshot.summary)
    assert "ZEPHYRINE" not in text and "private-scan" not in text
    assert "KESTREL FREIGHT" in text  # the registry's own facts stay
    assert "zephyrine orchid" in view.withheld_values
    # The view's documents are all verified, so the POC admission passes on it.
    facts = build_case_facts(view.snapshot)
    assert synthetic_eligibility.poc_check(view.snapshot, facts, [], digests=view.digests) is None
    assert "ZEPHYRINE" not in json.dumps(facts)


def test_u_an_unreadable_digest_list_withholds_every_upload() -> None:
    snapshot, _ = _upload_snapshot()
    view = synthetic_eligibility.poc_view(snapshot, None)
    assert view.withheld == 2 and view.snapshot.documents == []


def test_u_the_backstop_refuses_a_prompt_still_holding_a_withheld_value() -> None:
    snapshot, digests = _upload_snapshot()
    view = synthetic_eligibility.poc_view(snapshot, digests)
    facts = build_case_facts(view.snapshot)
    clean = [{"role": "user", "content": "What is blocking KESTREL FREIGHT?"}]
    assert not synthetic_eligibility.withheld_present(view, clean, facts)
    leaky = [{"role": "user", "content": "Is Zephyrine Orchid the real name?"}]
    assert synthetic_eligibility.withheld_present(view, leaky, facts)


def _acquisition(summary: dict[str, Any], provenance: dict[str, Any] | None) -> dict[str, Any]:
    data = json.loads(json.dumps(summary))
    party: dict[str, Any] = {"party_id": "p", "name": "LIM AH KOW"}
    if provenance is not None:
        party["provenance"] = provenance
    data["case"].setdefault("registry_acquisition", {})["ownership_parties"] = [party]
    return data


@pytest.mark.parametrize(
    ("provenance", "expected"),
    [
        # The ACRA Mock and the Marketplace Mock both record ACRA in MOCK mode.
        ({"provider": "ACRA", "environment": "MOCK", "operation": "SHAREHOLDERS"}, None),
        (
            {
                "provider": "ACRA",
                "environment": "MOCK",
                "operation": "SHAREHOLDERS",
                "evidence_reference": "MARKETPLACE_SHAREHOLDERS_V2",
            },
            None,
        ),
        ({"provider": "ACRA", "environment": "SANDBOX"}, "POC_SPONSOR_DATA"),
        ({"provider": "OTHER", "environment": "MOCK"}, "POC_PROVENANCE_UNKNOWN"),
        (None, "POC_PROVENANCE_UNKNOWN"),
    ],
)
def test_u_registry_records_need_mock_provenance(
    provenance: dict[str, Any] | None, expected: str | None
) -> None:
    snapshot = CaseSnapshot(_acquisition(OUTSIDE, provenance), [], actor())
    facts = build_case_facts(snapshot)
    assert synthetic_eligibility.poc_check(snapshot, facts, [], digests=[]) == expected


def test_u_hosted_a_prompt_still_holding_a_withheld_value_is_refused_before_any_call(
    private: Hosted,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_assistant import main

    real = main.poc_view

    def holding(snapshot: CaseSnapshot, digests: Any) -> Any:
        view = real(snapshot, digests)
        return synthetic_eligibility.PocView(
            view.snapshot, view.digests, 1, frozenset({"zephyrine orchid"})
        )

    monkeypatch.setattr(main, "poc_view", holding)
    hosted = private
    posts = hosted.claude.posts
    status, events = hosted.ask("Is Zephyrine Orchid on this case?", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    # R4 (R3-1): no supported intent, so nothing is reserved or sent before the backstop runs.
    assert "INTENT_UNSUPPORTED" in (answer["notice"] or "")
    assert hosted.claude.posts == posts  # nothing reserved or sent
    # A supported prefix followed by a separate question also falls back.
    status, events = hosted.ask(
        "Is this case ready to be sent to GoldTier? Is Zephyrine Orchid on it?",
        case_id=WAITING_ID,
    )
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "INTENT_UNSUPPORTED" in (answer["notice"] or "")
    assert hosted.claude.posts == posts


# --- OD-3: unclassifiable person references fall back ----------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "ask will about it",
        "please ask rose and mark about the share transfer",
        "ask director and will",
        "will said yes",
        "is will's form in?",
        "documents from will",
        # R3: positively classified, not position-based: these leaked through R2's rules.
        "will the case pass?",
        "email will about it",
        "did rose approve the form?",
        "the will was signed by them",
        "Kowalczyk asked about it",
        "ask Kowalczyk about it",
    ],
)
def test_od3_an_unclassifiable_person_reference_sends_nothing(text: str) -> None:
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit([{"role": "user", "content": text}]))
    # R4 (R3-1): no person-written text is admitted at all (R3 classified it word by word).
    assert refused.value.code == "PERSON_TEXT"


@pytest.mark.parametrize(
    "text",
    [
        "ask the director about the blocker",
        "tell me what is missing",
        "contact support",
        "contact details for the company?",
        "hi, what is blocking this case?",
        "thanks for the update",
        "Who are the directors?",
        "What is blocking this case right now, and what should I do next?",
    ],
)
def test_od3_r4_ordinary_questions_are_never_sent_as_typed(text: str) -> None:
    # R4 (R3-1): R3 sent these as typed once every word classified. Now none is admitted; the
    # chat sends the recognised intent's canonical question instead (controlled_intents).
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit([{"role": "user", "content": text}]))
    assert refused.value.code == "PERSON_TEXT"


def test_od3_r4_a_known_party_in_what_was_typed_is_not_sent_either() -> None:
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(
            pb.admit([{"role": "user", "content": "ask will about it"}], [("PERSON", "Will Ong")])
        )
    assert refused.value.code == "PERSON_TEXT"


def test_od3_history_is_never_forwarded_and_the_services_text_is_not_a_question() -> None:
    # R3 (OD-3): chat history is dropped from every external prompt, whatever it holds.
    protected = pb.outbound(
        pb.admit(
            [
                {"role": "user", "content": "ask will about it"},
                {"role": "assistant", "content": "Noted."},
                {"role": "user", "content": "What is blocking this case?"},
            ],
            person_written=False,
        )
    )
    pb.release(protected)
    assert [m["role"] for m in protected.messages] == ["user"]
    assert protected.messages[0]["content"] == "What is blocking this case?"
    protected = pb.outbound(
        pb.admit(
            [
                {"role": "system", "content": "Ask the reviewer before you change it."},
                {"role": "user", "content": "What is blocking this case?"},
            ],
            person_written=False,
        )
    )
    pb.release(protected)


def test_od3_hosted_the_deterministic_answer_follows_and_nothing_is_sent(
    private: Hosted,  # noqa: F811
) -> None:
    hosted = private
    posts = hosted.claude.posts
    status, events = hosted.ask("ask will about the share transfer", case_id=WAITING_ID)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "INTENT_UNSUPPORTED" in (answer["notice"] or "")  # R4 (R3-1)
    assert hosted.claude.posts == posts
