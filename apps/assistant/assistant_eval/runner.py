"""Run scenarios through the real service, offline.

For each scenario the runner serves its synthetic case from a fake CLM backend
(``httpx.MockTransport``), builds the knowledge the scenario names in a temporary folder
(official guidance from the repository, plus the illustrative seed), and asks each question
on ``/chat/stream`` exactly as the chat panel does. Both clocks are fixed to the same
instant, so a frozen evaluation is a function of code and fixtures only: the knowledge
store's (approval dates in the prompt) and retrieval's "now" (recency in the scores,
``create_app(retrieval_clock=)``). Embeddings are off (no local model is assumed), so
retrieval runs in its documented keyword-and-context mode; the snapshot records that.

The measured app uses the code-default settings: environment variables and ``.env`` files
are ignored, so a developer's own configuration cannot change what is measured. (Importing
``ai_assistant.main`` still builds that module's own app from the environment, as it
always has; the harness never uses that app.)
"""

import json
import shutil
import tempfile
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol

import httpx
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.embeddings import EmbeddingUnavailableError
from ai_assistant.knowledge.ingest import ingest_guidance, ingest_synthetic_resolutions
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.knowledge.vector_index import VectorIndex
from ai_assistant.llm import ChatModel, ModelAnswer, Piece
from ai_assistant.main import create_app
from ai_assistant.telemetry import MemorySink, prompt_version

from .models import Capture, TurnAware
from .scenarios import Scenario, ScenarioSet
from .snapshot import (
    Line,
    SnapshotSet,
    TurnSnapshot,
    offered_lines,
    prompt_fingerprint,
    turn_snapshot,
)
from .variants import CaseInputs, case_inputs

STORE_CLOCK = "2026-10-26T00:00:00+00:00"
EVAL_NOW = datetime.fromisoformat(STORE_CLOCK)
EMBEDDER = "none (embeddings off: keyword and case-context retrieval)"
ORIGIN = "http://127.0.0.1:5173"
SESSION = "eval-session"


class NoEmbedder:
    """Embeddings are not available: retrieval uses keywords and case context only."""

    name = "none"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailableError("embeddings are off in offline evaluation")

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingUnavailableError("embeddings are off in offline evaluation")


def settings() -> AiAssistantSettings:
    """The code defaults, without reading environment variables or ``.env``."""

    return AiAssistantSettings.model_construct(llm_enabled=False, knowledge_enabled=True)


class Workspace:
    """A temporary folder holding one knowledge base per knowledge profile (built once)."""

    def __init__(self) -> None:
        self._dir = Path(tempfile.mkdtemp(prefix="assistant-eval-"))
        self._bases: dict[str, KnowledgeBase] = {}

    def knowledge(self, profile: str) -> KnowledgeBase | None:
        if profile == "none":
            return None
        if profile not in self._bases:
            folder = self._dir / profile.replace("+", "-")
            kb = KnowledgeBase(
                store=KnowledgeStore(folder / "knowledge.sqlite3", clock=lambda: STORE_CLOCK),
                index=VectorIndex(folder / "chroma"),
                embedder=NoEmbedder(),
            )
            ingest_guidance(kb)
            if profile == "guidance+seed":
                ingest_synthetic_resolutions(kb)
            self._bases[profile] = kb
        return self._bases[profile]

    def close(self) -> None:
        self._bases.clear()
        # ChromaDB may keep its files open on Windows; the folder is temporary either way.
        shutil.rmtree(self._dir, ignore_errors=True)

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()


def _backend(case: CaseInputs) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET" or request.headers.get("cookie") != f"clm_session={SESSION}":
            return httpx.Response(401, json={"detail": "auth"})
        path = request.url.path
        if path == "/api/auth/me":
            return httpx.Response(200, json=case.actor)
        if path == f"/api/clm/zero-touch/cases/{case.case_id}":
            return httpx.Response(200, json=case.summary)
        if path == f"/api/onboarding/cases/{case.case_id}/documents":
            return httpx.Response(200, json=case.documents)
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


@dataclass(frozen=True)
class TurnResult:
    key: str
    rep: int
    answered_by: str
    fallback_reason: str
    # Ids of the allowed lines the answer showed (model answers only), in order.
    shown: tuple[str, ...]
    # Lines shown that are not allowed lines of this question (must stay 0).
    unmapped: int
    # Entries (by id) whose tag the answer cited.
    cited_entries: tuple[str, ...]
    offered: tuple[str, ...]
    prompt_fingerprint: str
    # The question offered different lines or a different prompt than its frozen snapshot.
    drift: bool
    metrics: dict[str, Any]
    answer_text: str = field(repr=False, default="")


@dataclass
class RunResult:
    model: str
    reps: int
    manifest: dict[str, str]
    turns: list[TurnResult]


def _shown(
    answer: str, offered: dict[str, str], added: frozenset[int] = frozenset()
) -> tuple[tuple[str, ...], int]:
    by_text = {text: line_id for line_id, text in offered.items()}
    shown: list[str] = []
    unmapped = 0
    for index, line in enumerate(answer.splitlines()):
        line = line.strip()
        if not line:
            continue
        if line not in by_text:
            # Counted wherever it is: the service's added_lines claim is not trusted here.
            unmapped += 1
        elif index not in added:
            # Required lines the service added (D-090) are not the model's selection.
            shown.append(by_text[line])
    return tuple(shown), unmapped


class _Reply(Protocol):
    """The parts of a test-client response used here (Starlette's client has its own httpx)."""

    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...


def _done(response: _Reply) -> dict[str, Any]:
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    done = [event for event in events if event.get("type") == "done"]
    if response.status_code != 200 or len(done) != 1:
        raise RuntimeError(f"unexpected reply from the service (HTTP {response.status_code})")
    return dict(done[0])


def run(
    scenario_set: ScenarioSet,
    make_model: Callable[[Capture], ChatModel],
    *,
    reps: int = 1,
    snapshots: SnapshotSet | None = None,
    workspace: Workspace | None = None,
    only: set[str] | None = None,
    turns: frozenset[str] | None = None,
) -> RunResult:
    """Ask every question of every scenario (``only``: a subset of scenario ids; ``turns``:
    only these turn keys, from scenarios without a conversation history)."""

    if reps < 1:
        raise ValueError("reps must be at least 1")
    if turns is not None:
        known = set(scenario_set.turn_keys())
        if not turns or not turns <= known:
            raise ValueError("unknown turn keys: " + ", ".join(sorted(turns - known)))
        for scenario in scenario_set.scenarios:
            keys = {scenario.turn_key(i) for i in range(len(scenario.questions))}
            if scenario.conversation and keys & turns and not keys <= turns:
                raise ValueError(f"{scenario.id} is a conversation: select all its turns")
    owned = workspace is None
    space = workspace or Workspace()
    results: list[TurnResult] = []
    model_name = ""
    try:
        for scenario in scenario_set.scenarios:
            if only is not None and scenario.id not in only:
                continue
            if turns is not None and not any(
                scenario.turn_key(i) in turns for i in range(len(scenario.questions))
            ):
                continue
            capture = Capture()
            model = make_model(capture)
            model_name = model.name
            sink = MemorySink()
            case = case_inputs(scenario.base, scenario.variants)
            app = create_app(
                settings(),
                clm_transport=_backend(case),
                chat_model=model,
                knowledge=space.knowledge(scenario.knowledge),
                metrics=sink,
                on_prepared=capture,
                retrieval_clock=lambda: EVAL_NOW,
            )
            with TestClient(app, headers={"Origin": ORIGIN}) as client:
                client.cookies.set("clm_session", SESSION)
                chat = f"/assistant/cases/{case.case_id}/chat/stream"
                for rep in range(reps):
                    results.extend(
                        _scenario(
                            client, chat, scenario, model, capture, sink, rep, snapshots, turns
                        )
                    )
    finally:
        if owned:
            space.close()
    return RunResult(
        model=model_name,
        reps=reps,
        manifest=manifest(scenario_set),
        turns=results,
    )


def _scenario(
    client: TestClient,
    chat: str,
    scenario: Scenario,
    model: ChatModel,
    capture: Capture,
    sink: MemorySink,
    rep: int,
    snapshots: SnapshotSet | None,
    turns: frozenset[str] | None = None,
) -> list[TurnResult]:
    history: list[dict[str, str]] = [turn.model_dump() for turn in scenario.forged_history]
    results: list[TurnResult] = []
    for index, question in enumerate(scenario.questions):
        key = scenario.turn_key(index)
        if turns is not None and key not in turns:
            continue
        if isinstance(model, TurnAware):
            model.begin(key, rep)
        capture.latest = None
        before = len(sink.records)
        response = client.post(chat, json={"message": question, "history": history})
        done = _done(response)
        prep = capture.latest
        if prep is None or len(sink.records) != before + 1:
            raise RuntimeError("the service did not prepare and record this question")
        offered = {item.id: text for _, item, text in offered_lines(prep)}
        answer = str(done.get("answer") or "")
        added = frozenset(done.get("added_lines") or [])
        shown, unmapped = (
            _shown(answer, offered, added) if done["answered_by"] == "model" else ((), 0)
        )
        tags = {item.tag: item.hit.entry.entry_id for item in prep.tagged}
        cited = tuple(
            tags[source["tag"]]
            for source in done.get("sources") or []
            if source.get("cited") and source.get("tag") in tags
        )
        fingerprint = prompt_fingerprint(prep.messages)
        frozen = snapshots.turns.get(key) if snapshots else None
        drift = frozen is not None and (
            frozen.prompt_fingerprint != fingerprint or frozen.offered_ids() != list(offered)
        )
        record = sink.records[-1]
        results.append(
            TurnResult(
                key=key,
                rep=rep,
                answered_by=str(done["answered_by"]),
                fallback_reason=record.fallback_reason,
                shown=shown,
                unmapped=unmapped,
                cited_entries=cited,
                offered=tuple(offered),
                prompt_fingerprint=fingerprint,
                drift=drift,
                metrics=record.to_dict(),
                answer_text=answer,
            )
        )
        if scenario.conversation:
            history += [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
    return results


def manifest(scenario_set: ScenarioSet) -> dict[str, str]:
    return {
        "prompt_version": prompt_version(),
        "embedder": EMBEDDER,
        "store_clock": STORE_CLOCK,
        "retrieval_clock": STORE_CLOCK,
        "settings": "code defaults (environment and .env ignored)",
        "route": "/chat/stream",
        "scenarios": str(len(scenario_set.scenarios)),
        "turns": str(len(scenario_set.turn_keys())),
    }


# --- snapshots -------------------------------------------------------------------------------


class SnapshotModel:
    """Records what each question offered, and selects nothing (the answer falls back)."""

    name = "snapshot"

    def __init__(self, capture: Capture) -> None:
        self._capture = capture
        self._key = ""
        self.turns: dict[str, TurnSnapshot] = {}
        self.lines: dict[str, Line] = {}

    def begin(self, key: str, rep: int) -> None:
        self._key = key

    def _record(self, messages: list[dict[str, str]]) -> None:
        prep = self._capture.latest
        if prep is None:
            raise RuntimeError("no prepared question")
        snapshot, offered = turn_snapshot(self._key, messages[-1]["content"], prep)
        self.turns[self._key] = snapshot
        for line in offered:
            self.lines.setdefault(line.id, line)

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._record(messages)
        return ModelAnswer("")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self._record(messages)
        yield Piece(cut_short=False)

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def build_snapshots(
    scenario_set: ScenarioSet, *, workspace: Workspace | None = None
) -> SnapshotSet:
    """Freeze what every question offers the model (each answer falls back to case data)."""

    models: list[SnapshotModel] = []

    def make(capture: Capture) -> ChatModel:
        models.append(SnapshotModel(capture))
        return models[-1]

    run(scenario_set, make, reps=1, workspace=workspace)
    captured: dict[str, TurnSnapshot] = {}
    lines: dict[str, Line] = {}
    for model in models:
        captured.update(model.turns)
        for line_id, line in model.lines.items():
            lines.setdefault(line_id, line)
    return SnapshotSet(
        note=(
            "Synthetic. What each evaluation question offers the model, built by "
            "scripts/evaluate_answers.py snapshot. Not a model result."
        ),
        built_with=manifest(scenario_set),
        lines=dict(sorted(lines.items())),
        turns=dict(sorted(captured.items())),
    )
