"""D-142 (proposed): the privacy boundary on every external model call, offline.

Adversarial inputs (unknown names, identifiers, contact details, placeholder forgeries) in the
question, chat history, retrieved knowledge and unstructured case text. Synthetic fixtures and
invented values only; no model, key or network.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import pytest

from ai_assistant import privacy_boundary as pb
from ai_assistant import synthetic_eligibility
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import allowed_guidance, validate_answer
from ai_assistant.guide import FIELD_LABEL
from ai_assistant.llm import ModelAnswer, ModelUsage, Piece
from ai_assistant.prompts import build_messages, facts_for_model

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "tests" / "fixtures"
LABELS = frozenset(FIELD_LABEL.values())

# Invented personal information that no vocabulary or fixture knows.
UNKNOWN = {
    "name": "Priyanka Ramasamy",
    "lower_name": "zhang weiqiang",
    "caps_company": "ACME WIDGETS",
    "nric": "S1234567D",
    "email": "p.ramasamy@example.com",
    "phone": "+65 9123 4567",
    "postcode": "738099",
    "url": "https://intranet.example.com/p/77",
    "passport": "K98765432",
    "birth": "14/02/1987",
}


def garden_facts() -> dict[str, Any]:
    summary = json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
    documents = json.loads((FIXTURES / "garden_documents.json").read_text())
    actor = json.loads((FIXTURES / "me_client_onboarder.json").read_text())
    if isinstance(documents, dict):
        documents = documents.get("documents", [])
    return build_case_facts(CaseSnapshot(summary, documents, actor))


def outbound_text(protected: pb.Protected) -> str:
    return "\n".join(message["content"] for message in protected.messages)


def leaked(text: str, values: list[str]) -> list[str]:
    folded = text.casefold()
    return [value for value in values if value.casefold() in folded]


# D-142 R4 (R3-1): the only user turn an external model receives is a canonical question.
CANONICAL_QUESTION = "Why is this case blocked, and what should be done next?"


def protected_case(
    question: str = CANONICAL_QUESTION,
    history: list[dict[str, str]] | None = None,
    knowledge: str | None = None,
    facts: dict[str, Any] | None = None,
    *,
    person_written: bool = False,
) -> tuple[pb.Protected, dict[str, Any]]:
    """The protected external prompt for this case. R4: by default its user turn is service
    text (the canonical question); ``person_written`` builds one with what a person wrote,
    which the boundary refuses."""

    facts = facts or garden_facts()
    messages = build_messages(
        pb.minimise_facts(facts, known_labels=LABELS), history or [], question, knowledge=knowledge
    )
    protected = pb.protect(messages, pb.identities_from_facts(facts), person_written=person_written)
    return protected, facts


# --- the vocabulary -----------------------------------------------------------------------


def test_the_privacy_vocabulary_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_privacy_vocabulary.py", "--check"],
        cwd=HERE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_vocabulary_holds_no_known_person_name() -> None:
    vocab = pb.vocabulary()
    boundary = json.loads((HERE / "ai_assistant" / "synthetic_boundary.json").read_text("utf-8"))
    for viewer in boundary["viewers"]:
        if viewer in ("POC HR Administrator", "Support User"):
            continue
        for word in re.findall(r"[^\W\d_]+", viewer):
            assert word.casefold() not in vocab.words, word
    for word in ("grace", "priyanka", "ramasamy", "zhang", "weiqiang", "tan", "lim", "wong"):
        assert word not in vocab.words
    # A fixture company's distinctive word is never a term, so GARDEN in capitals is replaced.
    assert "GARDEN" not in vocab.terms and "Garden" not in vocab.terms


def test_the_name_detection_lists_never_widen_the_generated_vocabularies() -> None:
    # The boundary's name, particle and honorific lists are not service wording, so neither
    # generator scans privacy_boundary.py (D-142: the vocabulary excludes person-name words).
    script = (HERE / "scripts" / "build_synthetic_boundary.py").read_text("utf-8")
    skipped = next(
        node.value
        for node in ast.walk(ast.parse(script))
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SKIPPED_MODULES" for t in node.targets)
    )
    assert isinstance(skipped, ast.Call)
    assert "privacy_boundary.py" in ast.literal_eval(skipped.args[0])
    boundary = json.loads((HERE / "ai_assistant" / "synthetic_boundary.json").read_text("utf-8"))
    vocab = pb.vocabulary()
    # Words whose only source was those lists (C10 E-6 review).
    for word in ("rose", "frank", "victor", "binte", "madam"):
        assert word not in boundary["code_vocabulary"], word
        assert word not in vocab.words, word


def test_fixture_people_and_matcher_words_never_widen_the_privacy_vocabulary() -> None:
    # C10 I-3: the mock connectors' made-up people and the copilot's matcher-only word lists
    # are not service wording (D-142: the vocabulary excludes person-name words).
    def assigned(path: Path, name: str) -> Any:
        return next(
            node.value
            for node in ast.walk(ast.parse(path.read_text("utf-8")))
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
        )

    scripts = HERE / "scripts"
    mocks = {"mock_acra.py", "mock_ownership.py"}
    for script in ("build_privacy_vocabulary.py", "build_synthetic_boundary.py"):
        skipped = assigned(scripts / script, "SKIPPED_MODULES")
        assert {"privacy_boundary.py", *mocks} <= ast.literal_eval(skipped.args[0]), script
    table = assigned(scripts / "build_privacy_vocabulary.py", "SKIPPED_CONSTANTS")
    assert isinstance(table, ast.Dict)
    skipped_constants = {
        ast.literal_eval(key): ast.literal_eval(value.args[0])
        for key, value in zip(table.keys, table.values, strict=True)
    }
    assert skipped_constants == {"copilot.py": {"_OFF_TOPIC", "_CONTEXTUAL_WORDS"}}
    # The skipped constants still exist, so a rename cannot silently re-admit their words.
    for name in ("_OFF_TOPIC", "_CONTEXTUAL_WORDS"):
        assigned(HERE / "ai_assistant" / "copilot.py", name)
    boundary = json.loads((HERE / "ai_assistant" / "synthetic_boundary.json").read_text("utf-8"))
    vocab = pb.vocabulary()
    terms = {term.casefold() for term in vocab.terms}
    fixture_people = ("avery", "blair", "casey", "devon", "beatrice", "choon", "huat")
    for word in (*fixture_people, "cook", "rain", "red"):
        assert word not in vocab.words, word
        assert word not in terms, word
    for word in ("avery", "blair", "casey", "devon", "goh"):
        assert word not in boundary["code_vocabulary"], word
    # A synthetic company's distinctive word is never a term (OPQ in capitals is replaced).
    assert "opq" not in terms


# --- known identities become typed placeholders --------------------------------------------


def test_every_case_identity_is_replaced_with_a_typed_placeholder() -> None:
    protected, facts = protected_case()
    text = outbound_text(protected)
    company = facts["company"]
    secrets = [company["legal_name"], company["uen"], facts["viewer"]["name"]]
    secrets += [document["name"] for document in facts["documents"]]
    secrets += [value for kind, value in pb.identities_from_facts(facts) if kind == "ADDRESS"]
    assert leaked(text, secrets) == []
    assert "[COMPANY-A]" in text
    assert any(alias.startswith("[ID-") for alias in protected.shield.originals)
    # The viewer is reduced to the role, as OD-G8 requires for every external model.
    assert "Maya Lim" not in text


def test_the_field_table_omits_the_registration_date_and_unknown_document_fields() -> None:
    facts = garden_facts()
    facts["company"]["registration_date"] = "2018-03-10"
    facts["documents"][0]["fields"].append(
        {"field": "internal scanner note", "value_read_from_document": "kept by ops"}
    )
    minimised = pb.minimise_facts(facts, known_labels=LABELS)
    assert "registration_date" not in minimised["company"]
    assert all(
        field["field"] in LABELS
        for document in minimised["documents"]
        for field in document["fields"]
    )
    assert all(document["name"].startswith("document ") for document in minimised["documents"])
    view = json.dumps(facts_for_model(minimised))
    assert "2018" not in view and "kept by ops" not in view


# --- unknown personal information, wherever it appears ---------------------------------------


def test_unknown_personal_information_in_the_question_never_leaves() -> None:
    question = (
        f"Is {UNKNOWN['name']} from {UNKNOWN['caps_company']} PTE LTD a director? Ask "
        f"{UNKNOWN['lower_name']}: NRIC {UNKNOWN['nric']}, passport {UNKNOWN['passport']}, "
        f"born {UNKNOWN['birth']}, mail {UNKNOWN['email']}, call {UNKNOWN['phone']}, "
        f"postcode {UNKNOWN['postcode']}, see {UNKNOWN['url']}"
    )
    words = [*UNKNOWN.values(), "Priyanka", "Ramasamy", "zhang", "weiqiang", "ACME", "WIDGETS"]
    # D-142 R4 (R3-1): nothing a person wrote is ever admitted, however it reads.
    with pytest.raises(pb.PrivacyRefused) as refused:
        protected_case(question, person_written=True)
    assert refused.value.code == "PERSON_TEXT"
    padded = (
        "Please explain what is still blocking this case right now, which documents are still "
        "missing for the review, what I should do next and which section of the case page I "
        "should open first, and also whether the ownership evidence is complete. " + question
    )
    with pytest.raises(pb.PrivacyRefused) as refused:
        protected_case(padded, person_written=True)
    assert refused.value.code == "PERSON_TEXT"
    # Service-built text holding the same values is still protected value by value.
    protected, _ = protected_case(question)
    assert leaked(outbound_text(protected), words) == []


def test_unknown_names_in_the_chat_history_never_leave() -> None:
    history = [
        {"role": "user", "content": f"Earlier I spoke with {UNKNOWN['name']}."},
        {"role": "assistant", "content": f"Noted: {UNKNOWN['lower_name']} called about it."},
    ]
    protected, _ = protected_case(history=history)
    assert leaked(outbound_text(protected), ["Priyanka", "Ramasamy", "zhang", "weiqiang"]) == []


def test_unknown_names_in_retrieved_knowledge_never_leave() -> None:
    knowledge = (
        "KNOWLEDGE (approved entries):\n[G1] Ask Priyanka Ramasamy in compliance, extension "
        "4567, before you choose a value."
    )
    protected, _ = protected_case(knowledge=knowledge)
    text = outbound_text(protected)
    assert leaked(text, ["Priyanka", "Ramasamy", "4567"]) == []
    assert "[G1]" in text  # the knowledge tag the model must copy is kept


def test_unknown_names_in_unstructured_case_text_never_leave() -> None:
    facts = garden_facts()
    facts["timeline"] = [
        *facts.get("timeline", []),
        {"when": "now", "what": "Call from Priyanka Ramasamy (S1234567D) about the address."},
    ]
    facts["system_problem"] = {"code": "X", "message": "Escalated by zhang weiqiang 91234567"}
    protected, _ = protected_case(facts=facts)
    words = ["Priyanka", "Ramasamy", "S1234567D", "zhang", "weiqiang", "91234567"]
    assert leaked(outbound_text(protected), words) == []


def test_a_question_mostly_made_of_unsendable_words_falls_back() -> None:
    facts = garden_facts()
    messages = build_messages(
        pb.minimise_facts(facts, known_labels=LABELS),
        [],
        "Priyanka Ramasamy zhang weiqiang Kowalczyk Nakamura Oyelaran?",
    )
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.protect(messages, pb.identities_from_facts(facts))
    # D-142 R4: a person-written question is never admitted (it superseded the R3 query).
    assert refused.value.code == "PERSON_TEXT"


def test_ordinary_service_wording_is_kept() -> None:
    protected, _ = protected_case()
    question = protected.messages[-1]["content"]
    assert question == CANONICAL_QUESTION
    system = protected.messages[0]["content"]
    assert "GoldTier" in system and "[TEXT-" not in system


# --- validation is independent of the replacement -------------------------------------------


def test_validation_refuses_a_known_value_the_replacement_missed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pb.Shield, "protect_text", lambda self, text, role="user": text)
    facts = garden_facts()
    messages = build_messages(facts, [], CANONICAL_QUESTION)
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.protect(messages, pb.identities_from_facts(facts), person_written=False)
    assert refused.value.code in ("KNOWN_VALUE", "PATTERN", "RESIDUAL")


@pytest.mark.parametrize("value", [UNKNOWN["email"], UNKNOWN["nric"], "91234567", "Priyanka"])
def test_validation_refuses_an_identifier_the_replacement_missed(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setattr(pb.Shield, "protect_text", lambda self, text, role="user": text)
    with pytest.raises(pb.PrivacyRefused):
        pb.protect([{"role": "user", "content": f"Please check {value} today"}])


def test_a_placeholder_the_call_did_not_issue_is_refused_on_the_way_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = pb.Shield.protect_text
    monkeypatch.setattr(
        pb.Shield,
        "protect_text",
        lambda self, text, role="user": original(self, text) + " [PERSON-Z]",
    )
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.protect([{"role": "user", "content": CANONICAL_QUESTION}], person_written=False)
    assert refused.value.code == "ALIAS"


# --- the reply: every placeholder checked before anything is restored ------------------------


def test_a_forged_placeholder_in_the_question_is_neutralised() -> None:
    # R4: a person's question never leaves at all (forged placeholders included); service text
    # that holds one still has it neutralised.
    with pytest.raises(pb.PrivacyRefused) as refused:
        protected_case("Who is [COMPANY-A] and [PERSON-A]?", person_written=True)
    assert refused.value.code == "PERSON_TEXT"
    protected, _ = protected_case("Who is [COMPANY-A] and [PERSON-A]?")
    question = protected.messages[-1]["content"]
    assert "[COMPANY-A]" not in question and "[PERSON-A]" not in question


def test_issued_placeholders_are_restored_to_the_real_values() -> None:
    protected, facts = protected_case()
    reply = "[COMPANY-A] is waiting for a document decision.\n"
    assert protected.restore_text(reply) == (
        f"{facts['company']['legal_name']} is waiting for a document decision.\n"
    )


@pytest.mark.parametrize(
    "line",
    [
        "[PERSON-Q] owns the company.",  # never issued
        "[Person A] owns the company.",  # malformed
        "PERSON A owns the company.",  # bare
        "[COMPANY-A] is owned by [TEXT-ZZ].",  # one good, one unknown: the whole line goes
        "[company-a] is blocked.",
    ],
)
def test_a_line_with_an_unissued_or_malformed_placeholder_is_dropped(line: str) -> None:
    protected, _ = protected_case()
    kept = protected.restore_text(line + "\nThe document review is not finished.\n")
    assert kept == "The document review is not finished.\n"
    assert protected.dropped_lines == 1


def test_a_restored_allowed_line_passes_the_unchanged_answer_checks() -> None:
    protected, facts = protected_case()
    minimised = pb.minimise_facts(facts, known_labels=LABELS)
    real = allowed_guidance(minimised)
    sent = json.loads(protected.messages[1]["content"].split("\n", 1)[1])["allowed_guidance"]
    assert sent
    restored = [protected.restore_text(line) for line in sent]
    assert all(line in real for line in restored), set(restored) - set(real)
    reply = "\n".join(sent[:3])
    validation = validate_answer(protected.restore_text(reply), facts)
    assert validation.text


def test_streamed_placeholders_split_across_pieces_are_restored() -> None:
    protected, facts = protected_case()

    async def source() -> AsyncIterator[Piece]:
        for text in ("[COMP", "ANY-A] is wai", "ting.\nThe review", " is open."):
            yield Piece(text=text)
        yield Piece(text="", usage=ModelUsage(prompt_tokens=1, completion_tokens=1))

    async def collect() -> list[Piece]:
        return [piece async for piece in protected.restore_stream(source())]

    pieces = anyio.run(collect)
    assert "".join(piece.text for piece in pieces) == (
        f"{facts['company']['legal_name']} is waiting.\nThe review is open."
    )
    assert pieces[-1].usage is not None


def test_a_whole_answer_is_restored_line_by_line() -> None:
    protected, facts = protected_case()
    answer = protected.restore_answer(ModelAnswer(text="[COMPANY-A] waits.\n[PERSON-ZZ] owns."))
    assert answer.text == f"{facts['company']['legal_name']} waits.\n"


# --- ownership: the application's figures, explained, never recalculated ---------------------


def test_ownership_figures_are_kept_and_parties_are_replaced() -> None:
    facts = garden_facts()
    facts["ownership"] = {
        "available": True,
        "people": [
            {
                "name": "Priyanka Ramasamy",
                "direct_percent": "12.5",
                "indirect_percent": "18.75",
                "aggregated_percent": "31.25",
                "threshold_result": "MET",
                "paths": [
                    {
                        "links": [
                            {
                                "holder": "Priyanka Ramasamy",
                                "held": "Kowalczyk Holdings Pte. Ltd.",
                                "ownership_percent": "25",
                            },
                            {
                                "holder": "Kowalczyk Holdings Pte. Ltd.",
                                "held": facts["company"]["legal_name"],
                                "ownership_percent": "75",
                            },
                        ],
                        "effective_percent": "18.75",
                    }
                ],
            }
        ],
    }
    messages = [{"role": "system", "content": "OWNERSHIP:\n" + json.dumps(facts["ownership"])}]
    protected = pb.protect(messages, pb.identities_from_facts(facts))
    text = outbound_text(protected)
    assert leaked(text, ["Priyanka", "Ramasamy", "Kowalczyk"]) == []
    for figure in ("12.5", "18.75", "31.25", "25", "75", "MET"):
        assert figure in text
    assert "[PERSON-A]" in text and "[COMPANY-" in text


# --- the wire point: the single-use ticket follows the protected messages --------------------


def test_outbound_uses_the_admitted_identities_once_and_leaves_the_ticket_alone() -> None:
    facts = garden_facts()
    built = build_messages(pb.minimise_facts(facts, known_labels=LABELS), [], CANONICAL_QUESTION)
    messages = pb.admit(built, pb.identities_from_facts(facts), person_written=False)
    synthetic_eligibility.approve(messages)
    protected = pb.outbound(messages)
    assert "[COMPANY-A]" in outbound_text(protected)  # the admitted identities were used
    # The model's own admission consumes the ticket for the messages as built (not here).
    assert synthetic_eligibility.admitted(messages)
    assert not synthetic_eligibility.admitted(protected.messages)
    # R1 P1-2: the admission is used once. A second call is refused; it never continues with
    # an empty identity map.
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(messages)
    assert refused.value.code == "ADMISSION_UNAVAILABLE"


def test_messages_without_an_admission_are_refused() -> None:
    # R1 P1-2: no admission, no call (R0 sent them with an empty identity map).
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound([{"role": "user", "content": "Is Priyanka Ramasamy a director?"}])
    assert refused.value.code == "ADMISSION_MISSING"
    # D-142 R4: admitted, a person-written question is still refused, whatever it says.
    with pytest.raises(pb.PrivacyRefused) as refused:
        pb.outbound(pb.admit([{"role": "user", "content": "Is Priyanka Ramasamy a director?"}]))
    assert refused.value.code == "PERSON_TEXT"


# --- every external model sends only protected messages --------------------------------------


class Recording:
    """A model on an IT-configured endpoint: records what it would send."""

    name = "it-model"

    def __init__(self) -> None:
        self.sent: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.sent.append(messages)
        return ModelAnswer(text="[PERSON-A] asked.\nThe document review is not finished.\n")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[Piece]:
        self.sent.append(messages)
        yield Piece(text="[PERSON-A] asked.\n")
        yield Piece(text="", finish_reason="stop")

    def warm(self, messages: list[dict[str, str]]) -> None:
        raise AssertionError("a warm-up would send case text")


def test_an_it_configured_model_sends_only_protected_messages() -> None:
    inner = Recording()
    model = pb.BoundedModel(inner)
    # R4: a person-written turn is refused before anything is sent.
    asked = [{"role": "user", "content": "Did Priyanka Ramasamy upload the profile?"}]
    with pytest.raises(pb.PrivacyRefused):
        model.complete(pb.admit(asked, [("PERSON", "Priyanka Ramasamy")]))
    assert inner.sent == []
    built = [
        {"role": "system", "content": "Priyanka Ramasamy uploaded the profile."},
        {"role": "user", "content": "Who are the company's directors in the registry record?"},
    ]
    messages = pb.admit(built, [("PERSON", "Priyanka Ramasamy")], person_written=False)
    answer = model.complete(messages)
    assert "Priyanka" not in json.dumps(inner.sent)
    assert answer.text.startswith("Priyanka Ramasamy asked.")
    model.warm(messages)  # never forwarded

    async def streamed() -> str:
        again = pb.admit(built, [("PERSON", "Priyanka Ramasamy")], person_written=False)
        return "".join([piece.text async for piece in model.stream(again)])

    assert anyio.run(streamed) == "Priyanka Ramasamy asked.\n"
    assert "Priyanka" not in json.dumps(inner.sent)


def test_the_built_in_external_models_call_the_boundary_after_admission() -> None:
    # Structural guard: each external model's own _ready runs the boundary, and complete and
    # stream send what _ready returned (no path to the provider skips it).
    import inspect

    from ai_assistant import anthropic_runtime, remote_test

    for cls in (remote_test.RemoteTestModel, anthropic_runtime.ClaudeTestModel):
        ready = inspect.getsource(cls._ready)
        assert "privacy_boundary.outbound(messages)" in ready
        assert ready.index("check_messages(messages)") < ready.index("privacy_boundary.outbound")
        for method in ("stream", *(("complete",) if cls is remote_test.RemoteTestModel else ())):
            source = inspect.getsource(getattr(cls, method))
            assert "inner, protected = " in source and "protected.messages" in source
            assert "restore_" in source


def test_dashboard_insights_go_through_the_model_and_so_the_boundary() -> None:
    # D-128 I7 calls model.complete on the active model; on the hosted service the route is
    # refused outright (D-139 R5). Either way no insights text reaches a provider unprotected.
    import inspect

    from ai_assistant import dashboard_insights

    source = inspect.getsource(dashboard_insights)
    assert "model.complete(messages)" in source
    assert ".post(" not in source and "httpx" not in source
