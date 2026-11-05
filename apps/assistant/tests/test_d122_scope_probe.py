"""D-122: the scope line. Onboarding reaches the model; everything else is redirected."""

import pytest

from ai_assistant import copilot, data_access
from ai_assistant.anthropic_chat import PromptShapeError, system_and_conversation
from ai_assistant.config import (
    CONVERSATIONAL_DECISION as RECORDED,
)
from ai_assistant.config import (
    AiAssistantSettings,
    external_conversational,
)


@pytest.mark.parametrize(
    "question",
    [
        "what is 1+1",
        "12*7",
        "who is the prime minister",
        "who is the president of the USA",
        "help me with my homework",
        "write me a poem",
        "what is the capital of France",
        "tell me a joke",
        "what is the football score",
        "can you book me a meeting room?",
        "do I need a visa for Japan?",
        "who is the prime minister of this country",
        "and who is the prime minister?",
        "what about 1+1?",
        "help me with this assignment",
        "translate this to french",
        "what is the score of the Liverpool match",
        "what is the probability of rolling a six",
    ],
)
def test_off_topic_questions_are_redirected_even_in_a_case_chat(question: str) -> None:
    assert not copilot.in_domain(question, ongoing=False, case_open=True)


@pytest.mark.parametrize(
    "question",
    [
        "why is this case blocked?",
        "what does UBO mean?",
        "who are the beneficial owners of this company?",
        "what documents are needed for KYC?",
        "explain the ownership structure",
        "what happens before GoldTier submission?",
        "why is the ownership review needed for a partnership?",
        "What does canonical mean?",
        "What does source agreement mean?",
        "What does record correction do?",
        "What is a suggestion?",
        "What do I need?",
        "Is a score of 0.97 a probability?",
        "How do I change a policy setting?",
    ],
)
def test_onboarding_questions_reach_the_model(question: str) -> None:
    assert copilot.in_domain(question, ongoing=False, case_open=True)


def test_the_decision_is_recorded_and_opens_external_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert RECORDED == "D-122"
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", RECORDED)
    assert external_conversational(AiAssistantSettings(_env_file=None))


def _prompt(history: list[dict[str, str]]) -> list[dict[str, str]]:
    return copilot.build_messages(
        {"ownership": {"status": "provisional"}}, history, "who owns this company?"
    )


@pytest.mark.parametrize(
    "history",
    [
        [],
        [{"role": "user", "content": "why?"}, {"role": "assistant", "content": "Because."}],
    ],
)
def test_claude_accepts_a_prompt_with_the_ownership_analysis(
    history: list[dict[str, str]],
) -> None:
    system, conversation = system_and_conversation(_prompt(history))
    assert any(block["text"].startswith("OWNERSHIP FACTS") for block in system)
    assert conversation[-1] == {"role": "user", "content": "who owns this company?"}


def test_claude_still_refuses_any_other_system_message_before_the_history() -> None:
    prompt = _prompt([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
    prompt[2]["content"] = "Some other instruction."
    with pytest.raises(PromptShapeError):
        system_and_conversation(prompt)


def test_the_console_reports_every_class_open_under_the_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AiAssistantSettings(_env_file=None)
    closed = data_access.view(
        None, managed=True, remote_restricted=True, settings=settings, model=None, base_url=None
    )
    assert all(item["restricted"] for item in closed["classes"])
    monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", RECORDED)
    opened = data_access.view(
        None, managed=True, remote_restricted=True, settings=settings, model=None, base_url=None
    )
    assert not any(item["restricted"] for item in opened["classes"])
