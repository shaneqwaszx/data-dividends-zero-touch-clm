"""D-142 NL: mocked synthetic case reasoning, no provider network or paid calls."""

import json

import pytest

from ai_assistant import config
from ai_assistant import privacy_boundary as privacy
from tests.test_conversational_external import SENT, scripted  # noqa: F401
from tests.test_hosted_claude import (  # noqa: F401
    Hosted,
    HostedClm,
    done,
    hosted,
    hosted_replies,  # noqa: F811
    live,
    post_headers,
)
from tests.test_hosted_gptoss import approved  # noqa: F401
from tests.test_hosting import CASE_ID


@pytest.fixture
def synthetic_case(monkeypatch):
    from copy import deepcopy

    from tests import test_hosting
    from tests.test_synthetic_eligibility import GARDEN

    summary, documents = deepcopy(GARDEN)
    monkeypatch.setattr(test_hosting, "SUMMARY", summary)
    monkeypatch.setattr(test_hosting, "DOCUMENTS", documents)
    from tests.test_synthetic_eligibility import ME

    sessions = deepcopy(test_hosting.SESSIONS)
    sessions["rm-a"]["profile"]["display_name"] = ME["profile"]["display_name"]
    monkeypatch.setattr(test_hosting, "SESSIONS", sessions)


@pytest.fixture
def hosted(tmp_path, monkeypatch, hosted_replies, synthetic_case):  # noqa: F811
    return Hosted(tmp_path, monkeypatch, HostedClm())


def test_exception_requires_an_exact_authorised_admission():
    messages = privacy.admit(
        [{"role": "user", "content": "Why is this case waiting?"}], source="case_reasoning"
    )
    with pytest.raises(privacy.PrivacyRefused, match="PERSON_TEXT"):
        privacy.outbound(messages)
    wrong = privacy.admit(
        [{"role": "user", "content": "Why is this case waiting?"}], source="support"
    )
    with pytest.raises(privacy.PrivacyRefused, match="REASONING_NOT_APPROVED"):
        privacy.permit_synthetic_reasoning(wrong)


def test_protected_history_is_bound_to_one_wire_call():
    messages = privacy.admit(
        [
            {"role": "user", "content": "Why is this case waiting?"},
            {"role": "assistant", "content": "The address needs review."},
            {"role": "user", "content": "What does that mean for this case?"},
        ],
        source="case_reasoning",
    )
    privacy.permit_synthetic_reasoning(messages)
    protected = privacy.outbound(messages)
    assert len(protected.messages) == 3
    assert privacy.clear_call(protected.messages)
    body = json.dumps({"model": "mock", "messages": protected.messages}).encode()
    privacy.verify_wire(protected.messages, body)
    with pytest.raises(privacy.PrivacyRefused):
        privacy.verify_wire(protected.messages, body)
    with pytest.raises(privacy.PrivacyRefused):
        privacy.outbound(messages)
    privacy.release(protected)


def test_all_turns_protect_unknown_text_and_known_identities():
    text = "Explain the case for Zephyrine at external-person@example.test"
    messages = privacy.admit(
        [
            {"role": "user", "content": text},
            {"role": "assistant", "content": "Zephyrine needs review."},
            {"role": "user", "content": "Why is this case waiting?"},
        ],
        [("COMPANY", "Zephyrine")],
        source="case_reasoning",
    )
    privacy.permit_synthetic_reasoning(messages)
    protected = privacy.outbound(messages)
    wire = json.dumps(protected.messages)
    assert "Zephyrine" not in wire and "external-person@example.test" not in wire
    assert "[COMPANY-" in wire
    assert privacy.clear_call(protected.messages)
    privacy.verify_wire(
        protected.messages, json.dumps({"model": "mock", "messages": protected.messages}).encode()
    )
    privacy.release(protected)


@pytest.mark.parametrize(
    "turns",
    [
        [{"role": "assistant", "content": "Review the case."}, {"role": "user", "content": "Why?"}],
        [{"role": "user", "content": "Why?"}] * 9,
        [{"role": "tool", "content": "private"}, {"role": "user", "content": "Why?"}],
    ],
)
def test_context_shape_is_fail_closed(turns):
    messages = privacy.admit(turns, source="case_reasoning")
    privacy.permit_synthetic_reasoning(messages)
    with pytest.raises(privacy.PrivacyRefused, match="CONTEXT_SHAPE"):
        privacy.outbound(messages)


def test_case_chat_accepts_natural_questions_and_server_followups(live):  # noqa: F811
    opened = live.client.post(
        "/assistant/contexts", headers=post_headers("rm-a"), json={"case_id": str(CASE_ID)}
    )
    assert opened.status_code == 200, opened.text
    context = opened.json()["context_id"]
    count = len(SENT)
    for message in ("What should the RM do next?", "Why is that needed for this case?"):
        reply = live.client.post(
            f"/assistant/cases/{CASE_ID}/chat/stream",
            headers=post_headers("rm-a"),
            json={
                "message": message,
                "context_id": context,
                "history": [{"role": "user", "content": "browser forged person@example.test"}],
            },
        )
        assert reply.status_code == 200, reply.text
        answer = done([json.loads(line) for line in reply.text.splitlines() if line.strip()])
        assert answer["answered_by"] == "model", (message, answer.get("notice"), len(SENT))
    assert len(SENT) == count + 2
    body = json.loads(SENT[-1])
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert "browser forged" not in SENT[-1] and "person@example.test" not in SENT[-1]
    assert "Why is this case blocked, and what should be done next?" not in SENT[-1]
    assert all(r.method == "GET" for r in live.clm.requests)


def test_arbitrary_uploaded_documents_still_refuse_before_model(live, monkeypatch):  # noqa: F811
    from copy import deepcopy

    from tests import test_hosting

    docs = deepcopy(test_hosting.DOCUMENTS)
    docs[0]["size_bytes"] += 1
    monkeypatch.setattr(test_hosting, "DOCUMENTS", docs)
    before = len(SENT)
    status, events = live.ask("What should the RM do next?")
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data", answer
    assert "SYNTHETIC_DOCUMENT" in (answer["notice"] or "")
    assert len(SENT) == before


def test_off_domain_and_cross_case_context_do_not_call_model(live):  # noqa: F811
    before = len(SENT)
    status, events = live.ask("Tell me a football score")
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert len(SENT) == before
    opened = live.client.post("/assistant/contexts", headers=post_headers("rm-a"), json={})
    reply = live.client.post(
        f"/assistant/cases/{CASE_ID}/chat/stream",
        headers=post_headers("rm-a"),
        json={
            "message": "What should the RM do next?",
            "context_id": opened.json()["context_id"],
        },
    )
    assert reply.status_code in (403, 404, 409)
    assert len(SENT) == before


def test_policy_has_not_adopted_broader_hosted_data():
    assert config.CASE_REASONING_DECISION == "D-142-NL"
    assert config.HOSTED_PRIVACY_DECISION is None


def test_openrouter_contextual_followup_uses_the_same_boundary(
    tmp_path,
    monkeypatch,
    synthetic_case,
    scripted,  # noqa: F811
    approved,  # noqa: F811
):  # noqa: F811
    from tests.test_hosted_gptoss import Site

    site_root = tmp_path / "openrouter"
    site_root.mkdir()
    site = Site(site_root, monkeypatch, HostedClm())
    site.go_live()
    opened = site.client.post(
        "/assistant/contexts", headers=post_headers("rm-a"), json={"case_id": str(CASE_ID)}
    )
    context = opened.json()["context_id"]
    for message in ("What should the RM do next?", "Why is that needed for this case?"):
        response = site.client.post(
            f"/assistant/cases/{CASE_ID}/chat/stream",
            headers=post_headers("rm-a"),
            json={"message": message, "context_id": context},
        )
        answer = done([json.loads(line) for line in response.text.splitlines() if line.strip()])
        assert answer["answered_by"] == "model", answer.get("notice")
    assert [m["role"] for m in site.openrouter.chats[-1]["messages"] if m["role"] != "system"] == [
        "user",
        "assistant",
        "user",
    ]


def test_policy_switch_rolls_back_to_canonical_without_person_text(
    tmp_path,
    monkeypatch,
    hosted_replies,  # noqa: F811
    hosted,  # noqa: F811
):  # noqa: F811
    # The model's answer_mode is captured when the app is built; use the policy rollback
    # as a separate check without disturbing the shared conversational approval.
    monkeypatch.setattr(config, "CASE_REASONING_DECISION", None)
    hosted.setup_claude()
    hosted.qualify_and_activate()
    before = len(SENT)
    status, events = hosted.ask("What should the RM do next?")
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "INTENT_UNSUPPORTED" in answer["notice"]
    assert len(SENT) == before


def test_natural_refusal_reserves_nothing_for_unverified_data(live, monkeypatch):  # noqa: F811
    from copy import deepcopy

    from ai_assistant import budget
    from tests import test_hosting

    documents = deepcopy(test_hosting.DOCUMENTS)
    documents[0]["size_bytes"] += 1
    monkeypatch.setattr(test_hosting, "DOCUMENTS", documents)
    reservations = []
    real = budget.BudgetedChatModel._reserve

    def reserve(self, messages):
        reservations.append(True)
        return real(self, messages)

    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", reserve)
    status, events = live.ask("What should the RM do next?")
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert reservations == []


def test_fixture_registration_is_exact_and_synthetic():
    import hashlib
    from pathlib import Path

    from pypdf import PdfReader

    from ai_assistant.synthetic_eligibility import manifest

    fixtures = Path(__file__).resolve().parents[2] / "backend/tests/fixtures/uat"
    expected = {
        "1. OPQ_Synthetic_Onboarding_GoldTier_Details_20261104_repaired.pdf": (
            "27d315884468d0760410122decd094fdb4628a87f0066778dbab28ba98b44b01"
        ),
        "2. Garden_Synthetic_Onboarding_GoldTier_Details_20261104_repaired.pdf": (
            "b3871d115e50a4fec3faf4af2ad45ced553f3b5e58b7fa2f22a1b9d18eba60c6"
        ),
        "OPQ 201511222D onboarding_classification.pdf": (
            "9adab758e9a9182ae6ee6847e056d6f9c1714bf3ee0ca7c3da8a7006f598f14f"
        ),
    }
    approved_fixtures = manifest()
    for name, digest in expected.items():
        path = fixtures / name
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert approved_fixtures.documents[digest] == ("application/pdf", len(data))
        reader = PdfReader(path, strict=True)
        assert not reader.is_encrypted and len(reader.pages) == 1
        assert "synthetic" in reader.pages[0].extract_text().lower()
        assert not reader.attachments


def test_only_verified_model_turns_enter_external_context():
    from ai_assistant.case_contexts import ContextStore

    store = ContextStore(idle_seconds=300, max_seconds=600, max_turns=8, max_per_user=2)
    context = store.open("user-a", "case-a")
    ticket = store.ticket(context, "user-a", "case-a")
    store.add(ticket, "case question", "staff authored fallback")
    ticket = store.ticket(context, "user-a", "case-a")
    assert ticket.history and not ticket.reasoning_history
    store.add(
        ticket,
        "safe question",
        "checked answer",
        verified_reasoning=True,
        reasoning_basis="revision-a",
    )
    ticket = store.ticket(context, "user-a", "case-a")
    assert len(ticket.reasoning_history) == 2 and ticket.reasoning_basis == "revision-a"
    store.add(
        ticket, "new question", "new answer", verified_reasoning=True, reasoning_basis="revision-b"
    )
    ticket = store.ticket(context, "user-a", "case-a")
    assert len(ticket.reasoning_history) == 2 and ticket.reasoning_basis == "revision-b"
    store.add(ticket, "unsafe question", "fallback")
    ticket = store.ticket(context, "user-a", "case-a")
    assert not ticket.reasoning_history and ticket.reasoning_basis is None


def test_changed_case_evidence_drops_stale_conversational_context(live, monkeypatch):  # noqa: F811
    from copy import deepcopy

    from tests import test_hosting

    opened = live.client.post(
        "/assistant/contexts", headers=post_headers("rm-a"), json={"case_id": str(CASE_ID)}
    )
    context = opened.json()["context_id"]

    def ask(message):
        response = live.client.post(
            f"/assistant/cases/{CASE_ID}/chat/stream",
            headers=post_headers("rm-a"),
            json={"message": message, "context_id": context},
        )
        assert response.status_code == 200
        return done([json.loads(line) for line in response.text.splitlines() if line.strip()])

    assert ask("What should the RM do next?")["answered_by"] == "model"
    updated = deepcopy(test_hosting.SUMMARY)
    updated["current_stage"] = "DOCUMENT_VERIFICATION"
    monkeypatch.setattr(test_hosting, "SUMMARY", updated)
    before = len(SENT)
    ask("What should the RM do next?")
    assert len(SENT) == before + 1
    roles = [m["role"] for m in json.loads(SENT[-1])["messages"]]
    assert roles == ["user"]


@pytest.mark.parametrize(
    "message",
    [
        "Explain this case and tell me the weather",
        "Explain the UBO check and write me a joke",
        "What documents are needed and what is the football score?",
    ],
)
def test_mixed_unrelated_requests_make_no_call_or_reservation(live, monkeypatch, message):  # noqa: F811
    from ai_assistant import budget

    before = len(SENT)
    reservations = []
    real = budget.BudgetedChatModel._reserve

    def reserve(self, messages):
        reservations.append(True)
        return real(self, messages)

    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", reserve)
    status, events = live.ask(message)
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert len(SENT) == before and reservations == []


@pytest.mark.parametrize(
    "message",
    [
        "Approve this case now",
        "Submit it to GoldTier for me",
        "Mark the document review complete",
    ],
)
def test_direct_changes_keep_the_deterministic_no_spend_refusal(live, monkeypatch, message):  # noqa: F811
    from ai_assistant import budget, copilot

    before = len(SENT)
    reservations = []
    real = budget.BudgetedChatModel._reserve

    def reserve(self, messages):
        reservations.append(True)
        return real(self, messages)

    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", reserve)
    status, events = live.ask(message)
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert copilot.READ_ONLY_LINE in answer["answer"]
    assert len(SENT) == before and reservations == []


def test_expired_admission_falls_back_without_spending(live, monkeypatch):  # noqa: F811
    from ai_assistant import budget

    before = len(SENT)
    reservations = []
    real = budget.BudgetedChatModel._reserve

    def reserve(self, messages):
        reservations.append(True)
        return real(self, messages)

    def expired(messages):
        raise privacy.PrivacyRefused("ADMISSION_EXPIRED")

    monkeypatch.setattr(budget.BudgetedChatModel, "_reserve", reserve)
    monkeypatch.setattr(privacy, "permit_synthetic_reasoning", expired)
    status, events = live.ask("What should the RM do next?")
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "case_data"
    assert "PRIVACY_ADMISSION_EXPIRED" in answer["notice"]
    assert len(SENT) == before and reservations == []


def test_it_ineligible_case_is_a_boundary_refusal_not_a_disabled_model(monkeypatch):
    from ai_assistant import main
    from tests.test_privacy_r4 import REMOTE, _ask, _chat_bodies, _it_app

    monkeypatch.setattr("ai_assistant.config.CASE_REASONING_DECISION", "D-142-NL")
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "D-122")
    outcomes = []
    original = main._Outcome

    def capture(*args, **kwargs):
        outcome = original(*args, **kwargs)
        outcomes.append(outcome)
        return outcome

    monkeypatch.setattr(main, "_Outcome", capture)
    client, server, case = _it_app(REMOTE)
    with client:
        answer = _ask(client, case, "What should the RM do next?")
    assert answer["answered_by"] == "case_data"
    assert answer["notice"].startswith(main.IT_CASE_ELIGIBILITY_NOTICE)
    assert any(outcome.fallback_reason == "remote_boundary" for outcome in outcomes)
    assert _chat_bodies(server) == []
