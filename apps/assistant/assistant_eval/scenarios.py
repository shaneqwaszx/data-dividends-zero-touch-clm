"""Evaluation scenarios: a synthetic case, its knowledge, and the questions asked about it.

A scenario names a saved Garden fixture as its base, the synthetic variants applied to it, the
knowledge the assistant may retrieve, and its questions. Single-question scenarios ask each
question on its own; a conversation asks them in order, with the earlier answers as history,
as the chat panel does. ``forged_history`` is sent before the first question (adversarial
scenarios: a browser can send any history).
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .variants import VARIANTS

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
FIXTURES = ASSISTANT_DIR / "tests" / "fixtures"
EVAL_FIXTURES = FIXTURES / "eval"
SCENARIOS_FILE = EVAL_FIXTURES / "scenarios.json"

Tag = Literal[
    "normal",
    "ambiguous",
    "missing_evidence",
    "conflicting_evidence",
    "adversarial",
    "multi_turn",
]
Base = Literal["garden_address_conflict", "garden_waiting_for_documents"]
KnowledgeProfile = Literal["none", "guidance", "guidance+seed"]


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Z][0-9]{2}$")
    description: str = Field(min_length=10, max_length=300)
    base: Base
    variants: tuple[str, ...] = ()
    knowledge: KnowledgeProfile = "guidance+seed"
    conversation: bool = False
    forged_history: tuple[Turn, ...] = ()
    questions: tuple[str, ...] = Field(min_length=1, max_length=8)
    tags: tuple[Tag, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "Scenario":
        unknown = [name for name in self.variants if name not in VARIANTS]
        if unknown:
            raise ValueError(f"unknown variants: {unknown}")
        if self.conversation != ("multi_turn" in self.tags):
            raise ValueError("a conversation, and only a conversation, is tagged multi_turn")
        if any(not question.strip() or len(question) > 600 for question in self.questions):
            raise ValueError("questions must be 1 to 600 characters")
        return self

    def turn_key(self, index: int) -> str:
        return f"{self.id}#{index}"


class ConsistencyPair(BaseModel):
    """The same question asked late in a conversation and on its own."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation: str
    single: str


class ScenarioSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: Literal["assistant-eval-scenarios/1"] = Field(alias="schema")
    note: str
    scenarios: tuple[Scenario, ...]
    consistency_pairs: tuple[ConsistencyPair, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> "ScenarioSet":
        ids = [scenario.id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario ids must be unique")
        keys = {s.turn_key(i) for s in self.scenarios for i in range(len(s.questions))}
        for pair in self.consistency_pairs:
            if pair.conversation not in keys or pair.single not in keys:
                raise ValueError("a consistency pair names an unknown turn")
        return self

    def turn_keys(self) -> list[str]:
        return [s.turn_key(i) for s in self.scenarios for i in range(len(s.questions))]


def load_scenarios(path: Path = SCENARIOS_FILE) -> ScenarioSet:
    return ScenarioSet.model_validate(json.loads(path.read_text(encoding="utf-8")))
