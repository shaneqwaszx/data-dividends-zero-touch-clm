"""Load the AI assistant's plain-English instruction files (ai_assistant/instructions/*.md).

The AI model cannot open files. This module reads them and the harness puts their text into
the model's context, so the bot's behaviour can be changed by editing markdown, not code.
Editor notes inside <!-- ... --> are removed before anything reaches the model.
"""

import re
from functools import cache
from pathlib import Path

INSTRUCTIONS_DIR = Path(__file__).parent / "instructions"

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_TERM_LINE = re.compile(r"^\s*-\s+\*\*(?P<term>[^*]+)\*\*\s*:\s*(?P<meaning>.+?)\s*$")


class InstructionFileError(RuntimeError):
    """An instruction file is missing or not in the expected format."""


def _read(name: str) -> str:
    path = INSTRUCTIONS_DIR / name
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InstructionFileError(f"cannot read instruction file {name}") from exc
    text = _COMMENT.sub("", raw).strip()
    if not text:
        raise InstructionFileError(f"instruction file {name} is empty")
    return text


@cache
def system_prompt() -> str:
    """Who the AI assistant is and the rules it must follow (persona_and_rules.md)."""

    return _read("persona_and_rules.md")


@cache
def case_page_terms() -> dict[str, str]:
    """Plain-English meanings of case page labels (case_page_terms.md)."""

    terms: dict[str, str] = {}
    for line in _read("case_page_terms.md").splitlines():
        if not line.strip():
            continue
        match = _TERM_LINE.match(line)
        if match is None:
            raise InstructionFileError(f"case_page_terms.md: cannot read line {line.strip()!r}")
        terms[match["term"].strip().lower()] = match["meaning"]
    if not terms:
        raise InstructionFileError("case_page_terms.md has no terms")
    return terms
