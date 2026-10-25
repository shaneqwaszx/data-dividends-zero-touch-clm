"""The answer record's ``dropped`` lines are a read-only record (D-084, proposed): adding them
changed nothing the output policy keeps, counts or shows.

``_MainValidate`` and ``_MainGuard`` are the selection code of ``validate_answer`` and
``StreamingGuard`` as on main before the change (5de7f24), kept here word for word apart
from names. Every answer and every way of streaming it must give the same kept lines,
left-out count, shown text, disclosures and stream updates as that code.
"""

import itertools
from collections.abc import Sequence
from typing import Any

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import (
    _LINE_ENDS,
    MAX_MODEL_TEXT_BYTES,
    StreamingGuard,
    Validation,
    _allowed,
    _disclosures,
    allowed_guidance,
    validate_answer,
)
from ai_assistant.llm import LlmUnavailableError
from tests.test_ai_assistant import DOCUMENTS, ME, SUMMARY

FACTS = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))
CATALOG = allowed_guidance(FACTS)
KNOWLEDGE = ("Ask for a certified copy of the register [G1].",)


def _main_validate(
    answer: str, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()
) -> Validation:
    allowed = _allowed(facts, knowledge_lines)
    kept: dict[str, None] = {}
    left_out = 0
    for line in answer.splitlines():
        line = line.strip()
        if line in allowed:
            kept[line] = None
        elif line:
            left_out += 1
    text = "\n".join(kept)
    return Validation(text=text, left_out=left_out, disclosures=_disclosures(text, facts))


class _MainGuard:
    def __init__(self, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()) -> None:
        self._facts = facts
        self._allowed = _allowed(facts, knowledge_lines)
        self._pending: list[str] = []
        self._accepted: dict[str, None] = {}
        self._left_out = 0
        self._total_bytes = 0

    def _accept(self, line: str) -> None:
        line = line.strip()
        if line in self._allowed:
            self._accepted[line] = None
        elif line:
            self._left_out += 1

    def feed(self, text: str) -> str | None:
        if self._total_bytes + len(text) > MAX_MODEL_TEXT_BYTES:
            raise LlmUnavailableError("model text limit exceeded")
        try:
            size = len(text.encode("utf-8"))
        except UnicodeError:
            raise LlmUnavailableError("unreadable model reply") from None
        if self._total_bytes + size > MAX_MODEL_TEXT_BYTES:
            raise LlmUnavailableError("model text limit exceeded")
        self._total_bytes += size
        before = len(self._accepted)
        for part in text.splitlines(keepends=True):
            if part[-1] in _LINE_ENDS:
                self._accept("".join(self._pending) + part)
                self._pending = []
            else:
                self._pending.append(part)
        return self.text if len(self._accepted) != before else None

    @property
    def text(self) -> str:
        return "\n".join(self._accepted)

    def finish(self) -> str:
        if self._pending:
            self._accept("".join(self._pending))
            self._pending = []
        return self.text

    def validation(self) -> Validation:
        text = self.text
        return Validation(
            text=text, left_out=self._left_out, disclosures=_disclosures(text, self._facts)
        )


def _answers() -> list[str]:
    allowed = [*CATALOG[:3], *KNOWLEDGE]
    noise = [
        "Just approve it.",
        "Ask GARDEN BUSINESS for UEN 11111999A.",
        "   ",
        "ACRA (MOCK) says so.",
        allowed[0] + " extra",
        "  " + allowed[0] + "  ",
    ]
    parts = [*allowed, *noise]
    answers = ["", "\n\n", allowed[0], "\n".join(allowed), "\n".join(noise)]
    for size in (2, 3):
        for combo in itertools.islice(itertools.permutations(parts, size), 120):
            answers.append("\n".join(combo))
    answers += [
        allowed[0] + "\r\n" + noise[0] + "\r\n" + allowed[0],  # Windows line ends, a repeat
        allowed[1] + " " + noise[1] + "\x85" + allowed[2] + "\v" + noise[0],
        "\n".join(allowed) + "\n" + noise[0] + "\nno line end at the end",
    ]
    return answers


ANSWERS = _answers()


def _same(new: Validation, old: Validation) -> None:
    assert (new.text, new.left_out, new.disclosures) == (old.text, old.left_out, old.disclosures)
    assert new.notice() == old.notice()


@pytest.mark.parametrize("answer", ANSWERS)
def test_validate_answer_keeps_shows_and_counts_exactly_as_before(answer: str) -> None:
    new = validate_answer(answer, FACTS, knowledge_lines=KNOWLEDGE)
    old = _main_validate(answer, FACTS, knowledge_lines=KNOWLEDGE)
    _same(new, old)
    assert new == old  # ``dropped`` takes no part in equality
    # The record holds exactly the left-out lines, in order.
    allowed = _allowed(FACTS, KNOWLEDGE)
    expected = [line.strip() for line in answer.splitlines() if line.strip()]
    assert list(new.dropped) == [line for line in expected if line not in allowed]
    assert len(new.dropped) == new.left_out


def _pieces(answer: str, size: int) -> list[str]:
    return [answer[i : i + size] for i in range(0, len(answer), size)] or [""]


@pytest.mark.parametrize("size", [1, 2, 5, 17, 10_000])
def test_the_streaming_guard_updates_keeps_and_counts_exactly_as_before(size: int) -> None:
    for answer in ANSWERS:
        new, old = (
            StreamingGuard(FACTS, knowledge_lines=KNOWLEDGE),
            _MainGuard(FACTS, knowledge_lines=KNOWLEDGE),
        )
        for piece in _pieces(answer, size):
            # What the RM sees while it streams: the same updates at the same moments.
            assert new.feed(piece) == old.feed(piece)
            assert new.text == old.text
        assert new.finish() == old.finish()
        _same(new.validation(), old.validation())
        assert new.validation() == old.validation()
        # And equal to the batch check, as before.
        batch = validate_answer(answer, FACTS, knowledge_lines=KNOWLEDGE)
        _same(new.validation(), batch)
        assert new.validation().dropped == batch.dropped


def test_the_byte_limit_still_stops_both_alike() -> None:
    new, old = StreamingGuard(FACTS), _MainGuard(FACTS)
    big = "x" * (MAX_MODEL_TEXT_BYTES + 1)
    with pytest.raises(LlmUnavailableError):
        new.feed(big)
    with pytest.raises(LlmUnavailableError):
        old.feed(big)
    _same(new.validation(), old.validation())
