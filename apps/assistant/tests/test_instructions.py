"""The bot's rules and glossary are loaded from markdown files the team can edit."""

from pathlib import Path

import pytest

from ai_assistant import instructions
from ai_assistant.instructions import InstructionFileError, case_page_terms, system_prompt
from ai_assistant.prompts import build_messages


def test_rules_are_loaded_from_markdown_without_editor_notes() -> None:
    prompt = system_prompt()
    assert prompt.startswith("You are the AI Assistant")
    assert "<!--" not in prompt and "HOW THE AI ASSISTANT BEHAVES" not in prompt
    for number in range(1, 19):
        assert f"\n{number}. " in prompt, f"rule {number} must start on its own line"


def test_rules_are_the_first_message_sent_to_the_model() -> None:
    facts = {"company": {}, "blockers": []}
    messages = build_messages(facts, [], "Why is this case blocked?")
    assert messages[0] == {"role": "system", "content": system_prompt()}
    assert messages[-1] == {"role": "user", "content": "Why is this case blocked?"}


def test_case_page_terms_are_read_from_markdown() -> None:
    terms = case_page_terms()
    assert terms["canonical"].startswith("the official value from the registry (ACRA)")
    assert "not a probability" in terms["evidence score"]
    assert all(term == term.lower() for term in terms)


def test_a_badly_formatted_term_line_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "case_page_terms.md").write_text("- canonical without bold\n", encoding="utf-8")
    monkeypatch.setattr(instructions, "INSTRUCTIONS_DIR", tmp_path)
    case_page_terms.cache_clear()
    try:
        with pytest.raises(InstructionFileError):
            case_page_terms()
    finally:
        case_page_terms.cache_clear()


def test_a_missing_rules_file_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instructions, "INSTRUCTIONS_DIR", tmp_path)
    system_prompt.cache_clear()
    try:
        with pytest.raises(InstructionFileError):
            system_prompt()
    finally:
        system_prompt.cache_clear()
