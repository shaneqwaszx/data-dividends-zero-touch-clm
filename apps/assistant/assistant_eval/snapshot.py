"""What one question offered the model, frozen with stable line ids.

Every allowed line gets an id that does not depend on retrieval order:

- catalog line: ``C-`` + hash of its text;
- knowledge line: ``K-`` + hash of its entry id, version and sentence (not its tag, which
  depends on ranking: the same sentence is ``[G1]`` in one answer and ``[G2]`` in another).

Gold labels name these ids, so they survive retrieval changes. A snapshot turn keeps the
offered line ids (and tags), the retrieval result, part sizes and a fingerprint of the
prompt without its conversation history. History is left out of the fingerprint because a
conversation's history is the model's own earlier answers, which differ from run to run;
the allowed lines never depend on it.
"""

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_assistant.guardrails import allowed_guidance
from ai_assistant.main import Prepared
from ai_assistant.telemetry import describe_messages

SCHEMA = "assistant-eval-snapshots/1"
_KNOWLEDGE_LINE = re.compile(r"^(?P<sentence>.*) \[(?P<tag>[GP]\d+)\]$")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def catalog_line_id(text: str) -> str:
    return "C-" + _digest(text)


def knowledge_line_id(entry_id: str, version: int, sentence: str) -> str:
    return "K-" + _digest(f"{entry_id}@v{version}\n{sentence}")


class Line(BaseModel):
    """One allowed line, as text the labeller reads (a knowledge line without its tag)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    source: Literal["catalog", "knowledge"]
    text: str
    entry_id: str | None = None
    version: int | None = None


class Offered(BaseModel):
    """A line offered on one turn, with the tag it carried there (knowledge only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    tag: str | None = None


class RetrievedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tag: str
    entry_id: str
    version: int
    kind: Literal["guidance", "resolution"]
    score: float
    fallback: bool


class TurnSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    question: str
    prompt_fingerprint: str
    part_chars: dict[str, int]
    offered: tuple[Offered, ...]
    retrieval_confidence: Literal["high", "low", "none"] | None
    retrieval_degraded: bool | None
    retrieved: tuple[RetrievedEntry, ...] = ()

    def offered_ids(self) -> list[str]:
        return [item.id for item in self.offered]


class SnapshotSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_: Literal["assistant-eval-snapshots/1"] = Field(
        default="assistant-eval-snapshots/1", alias="schema"
    )
    note: str
    built_with: dict[str, str]
    lines: dict[str, Line]
    turns: dict[str, TurnSnapshot]

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        """Deterministic JSON with one line per allowed line and one per question, so a
        change shows up as a few changed lines in a diff."""

        data = self.model_dump(mode="json", by_alias=True)

        def one(value: object) -> str:
            return json.dumps(value, sort_keys=True, ensure_ascii=False)

        def block(name: str) -> str:
            rows = ",\n".join(
                f"  {one(key)}: {one(item)}" for key, item in sorted(data[name].items())
            )
            return f' "{name}": {{\n{rows}\n }}'

        head = [f' "{name}": {one(data[name])}' for name in ("schema", "note", "built_with")]
        return "{\n" + ",\n".join([*head, block("lines"), block("turns")]) + "\n}\n"


# --- reading one prepared question -----------------------------------------------------------


def offered_lines(prep: Prepared) -> list[tuple[Line, Offered, str]]:
    """Every allowed line of this question: (line, offered, the exact text a model must
    copy), catalog lines first, then knowledge lines in the order the model was shown them."""

    out: list[tuple[Line, Offered, str]] = []
    for text in allowed_guidance(prep.facts):
        line_id = catalog_line_id(text)
        out.append((Line(id=line_id, source="catalog", text=text), Offered(id=line_id), text))
    entries = {item.tag: item.hit.entry for item in prep.tagged}
    for text in prep.shown.lines:
        match = _KNOWLEDGE_LINE.match(text)
        if match is None or match["tag"] not in entries:
            raise ValueError("a knowledge line without a known tag")
        entry = entries[match["tag"]]
        sentence = match["sentence"]
        line_id = knowledge_line_id(entry.entry_id, entry.version, sentence)
        line = Line(
            id=line_id,
            source="knowledge",
            text=sentence,
            entry_id=entry.entry_id,
            version=entry.version,
        )
        out.append((line, Offered(id=line_id, tag=match["tag"]), text))
    return out


def _is_history(index: int, message: Mapping[str, str], last: int) -> bool:
    return message.get("role") in ("user", "assistant") and index != last


def prompt_fingerprint(messages: Sequence[Mapping[str, str]]) -> str:
    """The prompt without its conversation history, hashed."""

    last = len(messages) - 1
    kept = [dict(m) for i, m in enumerate(messages) if not _is_history(i, m, last)]
    return hashlib.sha256(
        json.dumps(kept, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


def part_chars(messages: Sequence[Mapping[str, str]]) -> dict[str, int]:
    parts, _ = describe_messages(messages)
    return parts


def retrieved_entries(prep: Prepared) -> tuple[RetrievedEntry, ...]:
    return tuple(
        RetrievedEntry(
            tag=item.tag,
            entry_id=item.hit.entry.entry_id,
            version=item.hit.entry.version,
            kind="guidance" if item.hit.entry.kind.value == "guidance" else "resolution",
            score=float(item.hit.score),
            fallback=item.hit.fallback,
        )
        for item in prep.tagged
    )


def turn_snapshot(key: str, question: str, prep: Prepared) -> tuple[TurnSnapshot, list[Line]]:
    offered = offered_lines(prep)
    snapshot = TurnSnapshot(
        key=key,
        question=question,
        prompt_fingerprint=prompt_fingerprint(prep.messages),
        part_chars=part_chars(prep.messages),
        offered=tuple(item for _, item, _ in offered),
        retrieval_confidence=prep.knowledge.confidence if prep.knowledge else None,
        retrieval_degraded=prep.knowledge.degraded if prep.knowledge else None,
        retrieved=retrieved_entries(prep),
    )
    return snapshot, [line for line, _, _ in offered]
