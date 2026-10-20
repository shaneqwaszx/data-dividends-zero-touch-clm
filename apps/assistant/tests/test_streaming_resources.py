"""Bounded synthetic streams only; finite producers and outer watchdogs."""

import asyncio
import inspect
import json
import time
from collections.abc import AsyncIterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import httpx
import pytest

from ai_assistant.guardrails import StreamingGuard
from ai_assistant.llm import LlmUnavailableError, OpenAICompatibleChatModel, Piece


def event(text: str = "", finish: str | None = None) -> bytes:
    return (
        "data: "
        + json.dumps(
            {"choices": [{"delta": {"content": text}, "finish_reason": finish}]}, ensure_ascii=False
        )
        + "\n\n"
    ).encode()


def provider(
    transport: Any = None, *, url: str = "http://synthetic.invalid/v1", timeout: float = 1
) -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url=url,
        model="synthetic",
        credential="test",
        timeout_seconds=timeout,
        temperature=0,
        transport=transport,
    )


def collect(
    model: OpenAICompatibleChatModel, messages: list[dict[str, str]] | None = None
) -> list[Piece]:
    # Keeps the same reproducer executable against the original sync baseline.
    stream = model.stream(messages or [])
    if not inspect.isasyncgen(stream):
        return list(stream)

    async def read() -> list[Piece]:
        async with asyncio.timeout(3):
            return [piece async for piece in stream]

    return asyncio.run(read())


class Bytes(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False
        self.reads = 0

    def __iter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            await asyncio.sleep(0)
            yield chunk

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.close()


@pytest.mark.parametrize(
    "body",
    [event("x" * 65537, "stop"), (b": " + b"x" * 65500 + b"\n\n") * 20 + b"data: [DONE]\n\n"],
    ids=["frame", "cumulative"],
)
def test_frame_and_cumulative_limits(body: bytes) -> None:
    source = Bytes(
        [body[i : i + 1024] for i in range(0, len(body), 1024)] + [b"unread trailing bytes"]
    )
    model = provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source)))
    with pytest.raises(LlmUnavailableError, match="limit"):
        collect(model)
    assert source.closed
    assert source.reads < len(source.chunks)


def test_guard_bounds_unterminated_model_text() -> None:
    guard = StreamingGuard({})
    with pytest.raises(LlmUnavailableError, match="limit"):
        for _ in range(1025):
            guard.feed("x" * 64)
    assert len(guard._raw) <= 65536


@contextmanager
def loopback(mode: str):
    starts: list[float] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            starts.append(time.monotonic())
            self.rfile.read(int(self.headers["Content-Length"]))
            if mode == "headers-stall":
                time.sleep(0.65)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                if mode == "read-stall":
                    time.sleep(0.65)
                if mode in ("oversized", "many-frames"):
                    body = (
                        event("x" * 70000, "stop")
                        if mode == "oversized"
                        else event() * 16000 + b"data: [DONE]\n\n"
                    )
                    for offset in range(0, len(body), 1024):
                        part = body[offset : offset + 1024]
                        self.wfile.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
                        self.wfile.flush()
                    self.wfile.write(b"0\r\n\r\n")
                    return
                if mode == "chunk-header-trickle":
                    self.wfile.write(b"1;")
                    for _ in range(65):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.01)
                    self.wfile.write(b"\r\nx\r\n0\r\n\r\n")
                    return
                end = time.monotonic() + 0.65  # producer's own watchdog
                while time.monotonic() < end:
                    chunk = b"x" if mode == "no-newline" else b": heartbeat\n\n"
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                    self.wfile.flush()
                    time.sleep(0.01)
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", starts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


@pytest.mark.parametrize(
    "mode", ["no-newline", "heartbeat", "read-stall", "headers-stall", "chunk-header-trickle"]
)
def test_loopback_total_deadline(mode: str) -> None:
    with loopback(mode) as (url, starts):
        with pytest.raises(LlmUnavailableError):
            collect(provider(url=url, timeout=0.12))
        elapsed = time.monotonic() - starts[0]
        print(f"loopback {mode}: elapsed={elapsed:.3f}s; deadline=0.120s")
        assert elapsed < 0.45, f"total-deadline bypass: {elapsed:.3f}s"


@pytest.mark.parametrize(
    "terminal", [b"data: [DONE]\r\n\r\n", event(finish="stop"), event(finish="length")]
)
def test_split_utf8_and_fragmented_terminators(terminal: bytes) -> None:
    body = event("café 🌍") + terminal
    source = Bytes([bytes([b]) for b in body])
    result = collect(provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source))))
    assert result == [Piece("café 🌍"), Piece(cut_short=b"length" in terminal)]
    assert source.closed


@pytest.mark.parametrize(
    "body",
    [
        event() * 16000 + b"data: [DONE]\n\n",
        b"data: " + b"x" * 33000 + b"\ndata: " + b"x" * 33000 + b"\n\n",
    ],
    ids=["many-small-json-frames", "multiline-frame"],
)
def test_independent_raw_budgets(body: bytes) -> None:
    source = Bytes([body[i : i + 512] for i in range(0, len(body), 512)] + [b"unread"])
    with pytest.raises(LlmUnavailableError, match="limit"):
        collect(provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source))))
    assert source.closed and source.reads < len(source.chunks)


@pytest.mark.parametrize(
    "body",
    [
        b"data: \xff\n\n",
        b"data: \xe2\x82",
        b"data: [DONE]",
        b"data: [DONE]\n",
        b"data: {bad}\n\n",
        b'data: {"choices":[{"delta":{"content":"\\ud800"}}]}\n\n',
    ],
    ids=[
        "invalid-utf8",
        "incomplete-utf8",
        "unterminated-done",
        "incomplete-frame",
        "malformed-json",
        "unpaired-surrogate",
    ],
)
def test_malformed_or_incomplete_frames_are_owned(body: bytes) -> None:
    source = Bytes([body])
    with pytest.raises(LlmUnavailableError):
        collect(provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source))))
    assert source.closed


def test_multiline_sse_data_and_cr_framing() -> None:
    body = b': comment\rdata: {"choices":\rdata: [{"delta":{"content":"ok"},\r'
    body += b'data: "finish_reason":"stop"}]}\r\r'
    source = Bytes([bytes([b]) for b in body])
    assert collect(provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source)))) == [
        Piece("ok"),
        Piece(),
    ]
    assert source.closed


@pytest.mark.parametrize("prefix", ["", 'The current case offers "Keep registry value".\n'])
def test_limit_preserves_guarded_partial_or_deterministic_fallback(prefix: str) -> None:
    from tests.test_ai_assistant import CASE_ID, FakeBackend, _client

    source = Bytes([event(prefix)] + [event("x" * 1000)] * 70 + [event(finish="stop")])
    model = provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source)))
    response = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": "Why?"}
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    last = events[-1]
    assert last["type"] == "done" and source.closed
    if prefix:
        assert events[0] == {"type": "text", "text": prefix.strip()}
        assert last["answer"] == prefix.strip() and "cut short" in last["notice"]
    else:
        assert last["answered_by"] == "case_data" and "Keep registry value" in last["answer"]
    assert source.reads < len(source.chunks)


def test_guard_partial_excludes_the_unchecked_tail() -> None:
    # The grounding checker re-checks the finished text (bounded by MAX_MODEL_TEXT_BYTES);
    # on failure only text that was already checked and shown is kept.
    guard = StreamingGuard({})
    sentence = "The case page shows the current evidence."
    for _ in range(100):
        guard.feed(sentence + " ")
    assert guard.feed("Unfinished and unchecked") is None
    assert guard.partial().text == " ".join([sentence] * 100)
    assert "Unfinished" not in guard.partial().text


def test_pending_read_cancellation_closes_source_without_completion() -> None:
    async def run() -> None:
        closed = asyncio.Event()
        reading = asyncio.Event()

        class Stalled(httpx.AsyncByteStream):
            async def __aiter__(self) -> AsyncIterator[bytes]:
                yield event("first")
                reading.set()
                await asyncio.sleep(10)

            async def aclose(self) -> None:
                closed.set()

        source = Stalled()
        model = provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source)))
        pieces = model.stream([])
        assert await anext(pieces) == Piece("first")
        pending = asyncio.create_task(anext(pieces))
        await asyncio.wait_for(reading.wait(), 1)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert closed.is_set()
        with pytest.raises(StopAsyncIteration):
            await anext(pieces)
        await pieces.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["oversized", "many-frames"])
def test_real_chunked_http_enforces_budgets(mode: str) -> None:
    with loopback(mode) as (url, _), pytest.raises(LlmUnavailableError, match="limit"):
        collect(provider(url=url))


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br"])
def test_compressed_sse_is_rejected_before_read(encoding: str) -> None:
    source = Bytes([b"never decode or retain me"])
    with pytest.raises(LlmUnavailableError, match="encoding"):
        collect(
            provider(
                httpx.MockTransport(
                    lambda _: httpx.Response(
                        200, stream=source, headers={"Content-Encoding": encoding}
                    )
                )
            )
        )
    assert source.closed and source.reads == 0


def test_initial_bom_and_multi_byte_text_budget() -> None:
    source = Bytes([b"\xef\xbb\xbf" + event("café", "stop")])
    assert collect(provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source)))) == [
        Piece("café"),
        Piece(),
    ]
    guard = StreamingGuard({})
    with pytest.raises(LlmUnavailableError, match="limit"):
        guard.feed("🌍" * 16385)
    assert guard._raw == ""


def test_asgi_disconnect_closes_pending_model_read() -> None:
    from ai_assistant.config import AiAssistantSettings
    from ai_assistant.main import create_app
    from tests.test_ai_assistant import CASE_ID, FakeBackend

    async def run() -> None:
        waiting = asyncio.Event()
        closed = asyncio.Event()
        sent: list[dict[str, Any]] = []

        class Waiting(httpx.AsyncByteStream):
            async def __aiter__(self) -> AsyncIterator[bytes]:
                waiting.set()
                await asyncio.sleep(5)
                yield event("never")

            async def aclose(self) -> None:
                closed.set()

        source = Waiting()
        app = create_app(
            AiAssistantSettings(_env_file=None, llm_enabled=False),
            clm_transport=httpx.MockTransport(FakeBackend().handler),
            chat_model=provider(httpx.MockTransport(lambda _: httpx.Response(200, stream=source))),
        )
        request_sent = False

        async def receive() -> dict[str, Any]:
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": b'{"message":"Why?"}', "more_body": False}
            await waiting.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 1),
            "root_path": "",
            "query_string": b"",
            "path": f"/assistant/cases/{CASE_ID}/chat/stream",
            "headers": [
                (b"content-type", b"application/json"),
                (b"cookie", b"clm_session=valid-session"),
                (b"origin", b"http://127.0.0.1:5173"),
            ],
        }
        async with asyncio.timeout(2):
            await app(scope, receive, send)
        assert closed.is_set()
        assert not any(b'"type": "done"' in message.get("body", b"") for message in sent)

    asyncio.run(run())
