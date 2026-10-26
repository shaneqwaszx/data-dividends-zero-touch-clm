"""Content-free metrics for each explicit question (telemetry.py, off by default).

A record holds counts, sizes, timings, codes and opaque references only. The sentinel test
plants recognisable text in every place case, user or model content can come from and
checks that none of it reaches a record.
"""

import copy
import json
import logging
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import telemetry
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.ingest import ingest_guidance, ingest_synthetic_resolutions
from ai_assistant.knowledge.models import Entry, EntryKind
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.llm import LlmUnavailableError, Piece
from ai_assistant.main import create_app
from ai_assistant.telemetry import (
    PARTS,
    TIMINGS,
    AnswerMetrics,
    LogSink,
    MemorySink,
    MetricsRecorder,
    MetricsValidationError,
    NullSink,
    RetrievalMetrics,
    RetrievedEntry,
    describe_messages,
    entry_ref,
    prompt_version,
    sink_for,
)
from tests.test_ai_assistant import (
    CASE_ID,
    DOCUMENTS,
    ME,
    ORIGIN,
    SUMMARY,
    FakeBackend,
    FakeModel,
    _session,
)
from tests.test_knowledge_store import _kb

CHAT = f"/assistant/cases/{CASE_ID}/chat"
STREAM = f"/assistant/cases/{CASE_ID}/chat/stream"
ALLOWED = 'The current case offers "Keep registry value".'
SETTINGS = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]


def _app(
    model: Any,
    *,
    metrics: telemetry.MetricsSink | None = None,
    kb: KnowledgeBase | None = None,
    backend: Any = None,
    settings: AiAssistantSettings = SETTINGS,
) -> TestClient:
    handler = (backend or FakeBackend()).handler
    app = create_app(
        settings,
        clm_transport=httpx.MockTransport(handler),
        chat_model=model,
        knowledge=kb,
        metrics=metrics,
    )
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "valid-session")
    return client


def _only(sink: MemorySink) -> AnswerMetrics:
    assert len(sink.records) == 1
    return sink.records[0]


class PartialModel(FakeModel):
    """Streams one allowed line, then fails."""

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self.calls.append(messages)
        yield Piece(ALLOWED + "\n")
        raise LlmUnavailableError("dropped")


# --- off by default ------------------------------------------------------------------------


def test_telemetry_is_off_by_default_and_builds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    assert AiAssistantSettings(_env_file=None).telemetry == "off"  # type: ignore[call-arg]
    assert isinstance(sink_for("off"), NullSink)
    built: list[object] = []
    monkeypatch.setattr("ai_assistant.main.AnswerMetrics", lambda **kw: built.append(kw))
    client = _app(FakeModel(answer=ALLOWED))
    client.post(CHAT, json={"message": "Why is this case blocked?"})
    client.post(STREAM, json={"message": "Why is this case blocked?"})
    client.post(CHAT, json={"message": "hi"})
    assert built == []


def test_the_log_setting_selects_the_log_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    chosen: list[str] = []

    def fake_sink_for(mode: str) -> telemetry.MetricsSink:
        chosen.append(mode)
        return MemorySink()

    monkeypatch.setattr("ai_assistant.main.sink_for", fake_sink_for)
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False, telemetry="log")  # type: ignore[call-arg]
    _app(None, settings=settings)
    assert chosen == ["log"]
    assert isinstance(sink_for("log"), LogSink)


# --- one record per question ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("route", "model", "reason", "answered_by", "kept", "left_out"),
    [
        ("chat", FakeModel(answer=ALLOWED), "none", "model", 1, 0),
        ("stream", FakeModel(answer=ALLOWED), "none", "model", 1, 0),
        ("chat", FakeModel(fail=True), "model_unavailable", "case_data", 0, 0),
        ("stream", FakeModel(fail=True), "model_unavailable", "case_data", 0, 0),
        ("chat", None, "model_disabled", "case_data", 0, 0),
        ("stream", None, "model_disabled", "case_data", 0, 0),
        ("chat", FakeModel(answer="Free prose."), "policy_no_allowed_line", "case_data", 0, 1),
        ("stream", FakeModel(answer="Free prose."), "policy_no_allowed_line", "case_data", 0, 1),
        ("stream", PartialModel(), "stream_partial", "model", 1, 0),
    ],
)
def test_each_answer_has_one_record_with_what_happened(
    route: str, model: Any, reason: str, answered_by: str, kept: int, left_out: int
) -> None:
    sink = MemorySink()
    client = _app(model, metrics=sink)
    path = CHAT if route == "chat" else STREAM
    response = client.post(path, json={"message": "What should I do next?"})
    assert response.status_code == 200
    record = _only(sink)
    assert (record.route, record.fallback_reason, record.answered_by) == (
        route,
        reason,
        answered_by,
    )
    assert (record.kept_lines, record.left_out_lines) == (kept, left_out)
    assert record.cancelled is False
    assert record.model == (None if model is None else "fake-model")
    assert record.timings_ms["total"] is not None
    if reason == "stream_partial":
        assert record.cut_short is True


def test_small_talk_is_recorded_without_a_prompt_or_model() -> None:
    sink = MemorySink()
    model = FakeModel(answer=ALLOWED)
    client = _app(model, metrics=sink)
    client.post(CHAT, json={"message": "hi"})
    client.post(STREAM, json={"message": "thanks"})
    assert [r.fallback_reason for r in sink.records] == ["small_talk", "small_talk"]
    assert all(r.model is None and r.message_count == 0 for r in sink.records)
    assert all(sum(r.part_chars.values()) == 0 for r in sink.records)
    assert model.calls == []


class SlowModel(FakeModel):
    """Streams one allowed line, then waits until the request is cancelled."""

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self.calls.append(messages)
        yield Piece(ALLOWED + "\n")
        await anyio.sleep(30)
        yield Piece(cut_short=False)


def test_a_client_that_disconnects_mid_stream_is_recorded_as_cancelled() -> None:
    sink = MemorySink()
    app = create_app(
        SETTINGS,
        clm_transport=httpx.MockTransport(FakeBackend().handler),
        chat_model=SlowModel(),
        metrics=sink,
    )
    payload = json.dumps({"message": "What should I do next?"}).encode()
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": STREAM,
        "raw_path": STREAM.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "headers": [
            (b"host", b"testserver"),
            (b"origin", ORIGIN.encode()),
            (b"cookie", b"clm_session=valid-session"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
        ],
    }

    async def run() -> list[dict[str, Any]]:
        sent: list[dict[str, Any]] = []
        first_line = anyio.Event()
        requested = False

        async def receive() -> dict[str, Any]:
            nonlocal requested
            if not requested:
                requested = True
                return {"type": "http.request", "body": payload, "more_body": False}
            await first_line.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)
            if message["type"] == "http.response.body" and message.get("body"):
                first_line.set()

        with anyio.fail_after(10):
            await app(scope, receive, send)
        return sent

    sent = anyio.run(run)
    bodies = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert b'"type": "text"' in bodies and b'"type": "done"' not in bodies
    record = _only(sink)
    assert record.cancelled is True
    assert record.route == "stream"


def test_an_answer_cut_short_by_the_length_limit_is_recorded() -> None:
    sink = MemorySink()
    _app(FakeModel(answer=ALLOWED, cut_short=True), metrics=sink).post(
        STREAM, json={"message": "What should I do next?"}
    )
    assert _only(sink).cut_short is True


def test_prompt_sizes_match_what_the_model_was_sent() -> None:
    sink = MemorySink()
    model = FakeModel(answer=ALLOWED)
    history = [
        {"role": "user", "content": "What is blocking us?"},
        {"role": "assistant", "content": ALLOWED},
    ]
    _app(model, metrics=sink).post(
        STREAM, json={"message": "What does evidence score mean?", "history": history}
    )
    record = _only(sink)
    sent = model.calls[0]
    assert record.message_count == len(sent)
    assert sum(record.part_chars.values()) == sum(len(m["content"]) for m in sent)
    assert record.part_chars["rules"] > 0 and record.part_chars["facts"] > 0
    assert record.part_chars["terms"] > 0  # the question names a page term
    assert record.part_chars["question"] == len("What does evidence score mean?")
    assert record.history_turns == 2
    assert record.prompt_version == prompt_version()
    assert record.allowed_catalog_lines > 0
    assert record.retrieval is None  # no knowledge base in this app
    first, total = record.timings_ms["first_displayed_line"], record.timings_ms["total"]
    assert first is not None and total is not None and first <= total


def test_retrieved_knowledge_is_recorded_by_opaque_reference(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    ingest_guidance(kb)
    ingest_synthetic_resolutions(kb)
    sink = MemorySink()
    _app(FakeModel(answer=ALLOWED), metrics=sink, kb=kb).post(
        CHAT, json={"message": "Can I use the document address?"}
    )
    record = _only(sink)
    assert record.retrieval is not None
    assert record.retrieval.entries
    refs = {entry_ref(entry.entry_id) for entry in kb.store.entries()}
    for entry in record.retrieval.entries:
        assert entry.ref in refs
        assert entry.kind in {"guidance", "resolution"}
    assert record.allowed_knowledge_lines > 0
    assert record.timings_ms["retrieval"] is not None


# --- privacy -------------------------------------------------------------------------------

SENTINELS = (
    "zqxcompanyzqx",
    "zqxuenzqx",
    "zqxstreetzqx",
    "zqxdocvaluezqx",
    "zqxviewerzqx",
    "zqxquestionzqx",
    "zqxhistoryzqx",
    "zqxreplyzqx",
    "zqxtitlezqx",
    "zqxbodyzqx",
    "zqxrefzqx",
    "zqxeventzqx",
)


class SentinelBackend:
    """The recorded case, with sentinel text in company, address, document and viewer
    fields and the timeline."""

    def __init__(self) -> None:
        self.summary = copy.deepcopy(SUMMARY)
        entity = self.summary["case"]["entity"]
        entity["legal_name"] = "ZQXCOMPANYZQX PTE LTD"
        entity["registration_number"] = "ZQXUENZQX"
        entity["registered_address"]["address_line_1"] = "1 ZQXSTREETZQX ROAD"
        for event in self.summary.get("timeline") or []:
            event["message"] = "zqxeventzqx happened"
        self.documents = copy.deepcopy(DOCUMENTS)
        for document in self.documents:
            for field in document.get("fields") or []:
                field["normalized_value"] = "ZQXDOCVALUEZQX"
                field["original_extracted_value"] = "ZQXDOCVALUEZQX"
        self.me = copy.deepcopy(ME)
        self.me["profile"]["display_name"] = "Zqxviewerzqx Person"

    def handler(self, request: httpx.Request) -> httpx.Response:
        if _session(request) != "valid-session":
            return httpx.Response(401, json={"detail": "auth"})
        path = request.url.path
        if path == "/api/auth/me":
            return httpx.Response(200, json=self.me)
        if path == f"/api/clm/zero-touch/cases/{CASE_ID}":
            return httpx.Response(200, json=self.summary)
        if path == f"/api/onboarding/cases/{CASE_ID}/documents":
            return httpx.Response(200, json=self.documents)
        return httpx.Response(404, json={"detail": "not found"})


def _sentinel_kb(tmp_path: Path) -> KnowledgeBase:
    kb = _kb(tmp_path)
    proposed = kb.propose(
        Entry(
            entry_id="resolution.zqxrefzqx",
            kind=EntryKind.RESOLUTION,
            title="Zqxtitlezqx resolution",
            body="Zqxbodyzqx was checked against the registry.",
            blocker_codes=("DOCUMENT_SOURCE_CONFLICT",),
            fields=("registered_address",),
            author="maya-lim",
        )
    )
    kb.decide(proposed.entry_id, proposed.version, reviewer="director-dan", approve=True)
    return kb


def _all_records_text(records: list[AnswerMetrics], lines: list[str]) -> str:
    return "\n".join([*(r.to_json() for r in records), *lines]).lower()


def test_no_case_user_or_model_content_reaches_a_record(tmp_path: Path) -> None:
    sink = MemorySink()
    logged: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logged.append(record.getMessage())

    logger = logging.getLogger("tests.telemetry.sentinel")
    logger.handlers = [ListHandler()]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    class BothSinks:
        def __init__(self) -> None:
            self.log = LogSink(logger)

        def record(self, metrics: AnswerMetrics) -> None:
            sink.record(metrics)
            self.log.record(metrics)

    reply = f"zqxreplyzqx says approve\n{ALLOWED}\nZqxbodyzqx was checked [P1]"
    client = _app(
        FakeModel(answer=reply),
        metrics=BothSinks(),
        kb=_sentinel_kb(tmp_path),
        backend=SentinelBackend(),
    )
    history = [
        {"role": "user", "content": "zqxhistoryzqx earlier question"},
        {"role": "assistant", "content": "zqxhistoryzqx earlier answer"},
    ]
    for path in (CHAT, STREAM):
        response = client.post(
            path,
            json={"message": "zqxquestionzqx can I use the address?", "history": history},
        )
        assert response.status_code == 200
    client.post(CHAT, json={"message": "hi zqxquestionzqx"})

    assert len(sink.records) == 3 and len(logged) == 3
    text = _all_records_text(sink.records, logged)
    for sentinel in SENTINELS:
        assert sentinel not in text
    for content in (
        "keep registry value",
        "registered address",
        CASE_ID.lower(),
        "maya-lim",
        "director-dan",
        "team_a",
        "resolution.",
        "guidance.",
    ):
        assert content not in text
    # The records still say what happened.
    model_record = sink.records[0]
    assert model_record.retrieval is not None
    assert entry_ref("resolution.zqxrefzqx") in {e.ref for e in model_record.retrieval.entries}


# --- the answer never changes --------------------------------------------------------------


def _responses(metrics: telemetry.MetricsSink | None) -> list[bytes]:
    client = _app(FakeModel(answer=f"{ALLOWED}\nNot allowed."), metrics=metrics)
    out = []
    for path in (CHAT, STREAM):
        for message in ("What should I do next?", "hi"):
            out.append(client.post(path, json={"message": message}).content)
    return out


def test_answers_are_byte_identical_with_and_without_metrics() -> None:
    assert _responses(None) == _responses(MemorySink())


def test_a_failing_sink_never_changes_the_answer() -> None:
    class Broken:
        def record(self, metrics: AnswerMetrics) -> None:
            raise RuntimeError("sink down")

    assert _responses(Broken()) == _responses(None)


def test_the_model_is_sent_the_same_messages_with_metrics_on() -> None:
    plain, measured = FakeModel(answer=ALLOWED), FakeModel(answer=ALLOWED)
    _app(plain).post(STREAM, json={"message": "What should I do next?"})
    _app(measured, metrics=MemorySink()).post(STREAM, json={"message": "What should I do next?"})
    assert plain.calls == measured.calls


def test_a_record_that_cannot_be_built_is_dropped_and_counted() -> None:
    sink = MemorySink()
    recorder = MetricsRecorder(sink)

    def bad() -> AnswerMetrics:
        raise MetricsValidationError("model is not a content-free identifier")

    recorder.record(bad)
    assert sink.records == [] and recorder.dropped == 1
    off = MetricsRecorder(NullSink())
    off.record(bad)
    assert off.dropped == 0  # nothing is built when telemetry is off


def test_a_log_sink_writes_one_json_line_per_answer() -> None:
    lines: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(record.getMessage())

    logger = logging.getLogger("tests.telemetry.log")
    logger.handlers = [ListHandler()]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    client = _app(FakeModel(answer=ALLOWED), metrics=LogSink(logger))
    client.post(CHAT, json={"message": "What should I do next?"})
    client.post(STREAM, json={"message": "What should I do next?"})
    assert len(lines) == 2
    for line in lines:
        data = json.loads(line)
        # Version 2 (Phase A2, D-091 proposed) added content-free usage and budget fields.
        assert data["metrics_version"] == 2
        assert set(data) == set(AnswerMetrics.__dataclass_fields__)


def test_the_default_log_sink_writes_to_standard_error_only() -> None:
    logger = logging.getLogger(telemetry.LOGGER_NAME)
    saved = (list(logger.handlers), logger.level, logger.propagate)
    try:
        logger.handlers = []
        LogSink()
        assert len(logger.handlers) == 1
        assert logger.propagate is False
        assert logger.level == logging.INFO
    finally:
        logger.handlers, logger.level, logger.propagate = saved[0], saved[1], saved[2]


# --- field validation ----------------------------------------------------------------------


def _metrics(**changes: Any) -> AnswerMetrics:
    fields: dict[str, Any] = {
        "request_id": "0" * 32,
        "route": "chat",
        "answered_by": "model",
        "fallback_reason": "none",
        "model": "ministral-3:8b",
        "prompt_version": "a" * 16,
        "part_chars": dict.fromkeys(PARTS, 1),
        "message_count": 3,
        "history_turns": 0,
        "retrieval": None,
        "allowed_catalog_lines": 1,
        "allowed_knowledge_lines": 0,
        "kept_lines": 1,
        "left_out_lines": 0,
        "cited_sources": 0,
        "cut_short": False,
        "cancelled": False,
        "timings_ms": dict.fromkeys(TIMINGS, None),
    }
    fields.update(changes)
    return AnswerMetrics(**fields)


def test_a_valid_record_round_trips_to_json() -> None:
    record = _metrics(model="openai/gpt-oss-120b")
    assert json.loads(record.to_json())["model"] == "openai/gpt-oss-120b"


@pytest.mark.parametrize(
    "changes",
    [
        {"request_id": "ZQXSECRETZQX"},
        {"route": "zqxsecretzqx"},
        {"answered_by": "zqxsecretzqx"},
        {"fallback_reason": "zqxsecretzqx"},
        {"model": "ZQXSECRETZQX PTE LTD"},
        {"model": "zqxsecretzqx\nnext line"},
        {"prompt_version": "zqxsecretzqx"},
        {"part_chars": {"zqxsecretzqx": 1}},
        {"part_chars": {**dict.fromkeys(PARTS, 1), "rules": -1}},
        {"part_chars": {**dict.fromkeys(PARTS, 1), "rules": True}},
        {"message_count": "zqxsecretzqx"},
        {"kept_lines": 1.5},
        {"cut_short": 1},
        {"timings_ms": {"zqxsecretzqx": 1}},
        {"retrieval": "zqxsecretzqx"},
    ],
)
def test_a_value_that_is_not_content_free_is_refused_without_quoting_it(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(MetricsValidationError) as refused:
        _metrics(**changes)
    assert "zqxsecretzqx" not in str(refused.value).lower()


_ENTRY: dict[str, Any] = {
    "kind": "guidance",
    "ref": "a" * 16,
    "version": 1,
    "score": 0.5,
    "fallback": False,
}


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "zqxsecretzqx"},
        {"ref": "guidance.zqxsecretzqx"},
        {"version": -1},
        {"score": float("nan")},
        {"score": 1},
        {"fallback": "no"},
    ],
)
def test_retrieval_identifiers_must_be_content_free(changes: dict[str, Any]) -> None:
    with pytest.raises(MetricsValidationError) as refused:
        RetrievedEntry(**{**_ENTRY, **changes})
    assert "zqxsecretzqx" not in str(refused.value).lower()


def test_retrieval_codes_are_checked() -> None:
    with pytest.raises(MetricsValidationError):
        RetrievalMetrics(confidence="zqxsecretzqx", degraded=False)
    with pytest.raises(MetricsValidationError):
        RetrievalMetrics(confidence="high", degraded=False, entries=("zqxsecretzqx",))  # type: ignore[arg-type]


def test_entry_references_are_opaque_and_stable() -> None:
    ref = entry_ref("guidance.address-mismatch")
    assert ref == entry_ref("guidance.address-mismatch")
    assert ref != entry_ref("guidance.ubo-threshold")
    assert len(ref) == 16 and "address" not in ref


# --- prompt description --------------------------------------------------------------------


def test_messages_are_described_by_part() -> None:
    messages = [
        {"role": "system", "content": "rules"},
        {"role": "system", "content": "CASE FACTS {}"},
        {"role": "user", "content": "KNOWLEDGE typed by a user"},
        {"role": "assistant", "content": "answer"},
        {"role": "system", "content": "KNOWLEDGE (approved)"},
        {"role": "system", "content": "CASE PAGE TERMS {}"},
        {"role": "system", "content": "something new"},
        {"role": "user", "content": "question?"},
    ]
    parts, history = describe_messages(messages)
    assert parts == {
        "rules": 5,
        "facts": 13,
        "history": len("KNOWLEDGE typed by a user") + len("answer"),
        "knowledge": len("KNOWLEDGE (approved)"),
        "terms": 18,
        "question": 9,
        "other": len("something new"),
    }
    assert history == 2


def test_the_prompt_version_changes_with_the_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    current = prompt_version()
    assert len(current) == 16
    prompt_version.cache_clear()
    monkeypatch.setattr(telemetry.prompts, "SYSTEM_PROMPT", "different rules")
    try:
        assert prompt_version() != current
    finally:
        prompt_version.cache_clear()


@pytest.fixture(autouse=True)
def _restore_prompt_version() -> Iterator[None]:
    yield
    prompt_version.cache_clear()


def test_records_never_hold_a_model_answer_object() -> None:
    # Guard against a future field that would carry text: every leaf is a number, a bool,
    # None, or a string from a closed vocabulary or identifier pattern.
    record = _metrics(
        retrieval=RetrievalMetrics(
            confidence="high",
            degraded=True,
            entries=(RetrievedEntry("guidance", "b" * 16, 2, 0.4, False),),
        )
    )

    def leaves(value: Any) -> Iterator[Any]:
        if isinstance(value, dict):
            for item in value.values():
                yield from leaves(item)
        elif isinstance(value, list | tuple):
            for item in value:
                yield from leaves(item)
        else:
            yield value

    for leaf in leaves(record.to_dict()):
        assert leaf is None or isinstance(leaf, int | float | bool | str)
        if isinstance(leaf, str):
            assert len(leaf) <= 100 and "\n" not in leaf and " " not in leaf
