from __future__ import annotations

import http.client
import io
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Event, Thread

import pytest
from scripts.seed_phase13_demo import HttpSeedApi


@contextmanager
def dummy_response(
    wire: bytes, *, hold_open: bool = False
) -> Iterator[tuple[HttpSeedApi, Event, list[int]]]:
    """Owned dummy HTTP peer; no application, credential, case or target state."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(10)
    release = Event()
    peer_closed = Event()
    request_counts: list[int] = []
    failures: list[BaseException] = []

    def serve() -> None:
        try:
            with listener.accept()[0] as connection:
                connection.settimeout(10)
                request = bytearray()
                while b"\r\n\r\n" not in request:
                    piece = connection.recv(1024)
                    if not piece:
                        raise AssertionError("Dummy request ended before headers")
                    request.extend(piece)
                    if len(request) > 8192:
                        raise AssertionError("Dummy request exceeded header bound")
                request_counts.append(1)
                connection.sendall(wire)
                if hold_open and not release.wait(15):
                    raise AssertionError("Dummy peer hold exceeded client timeout")
            peer_closed.set()
        except BaseException as error:
            failures.append(error)

    worker = Thread(target=serve, daemon=True)
    worker.start()
    try:
        yield (
            HttpSeedApi(f"http://127.0.0.1:{listener.getsockname()[1]}"),
            peer_closed,
            request_counts,
        )
    finally:
        release.set()
        worker.join(timeout=10)
        listener.close()
        assert not worker.is_alive()
        assert not failures


class WireSocket:
    def __init__(self, wire: bytes) -> None:
        self.wire = wire

    def makefile(self, mode: str) -> io.BytesIO:
        assert mode == "rb"
        return io.BytesIO(self.wire)


@contextmanager
def parsed_response(wire: bytes) -> Iterator[tuple[HttpSeedApi, list[int]]]:
    """Real HTTPResponse parsing with deterministic EOF, supplementary to HTTP tests."""
    counts: list[int] = []
    response = http.client.HTTPResponse(WireSocket(wire))
    response.begin()

    class SingleResponseOpener:
        def open(self, request: object, *, timeout: int) -> http.client.HTTPResponse:
            assert timeout == 15
            counts.append(1)
            assert counts == [1]
            return response

    api = HttpSeedApi("http://127.0.0.1:1")
    api._opener = SingleResponseOpener()
    try:
        yield api, counts
    finally:
        response.close()


def content_length_response(body: bytes, declared: int | None = None) -> bytes:
    size = len(body) if declared is None else declared
    return f"HTTP/1.1 200 OK\r\nContent-Length: {size}\r\nConnection: close\r\n\r\n".encode() + body


def request(api: HttpSeedApi, method: str = "GET") -> object:
    return api._request(
        method,
        "/dummy-completion",
        data=None,
        headers={"Accept": "application/json"},
        authenticated=False,
    )


def test_early_eof_rejects_valid_json_when_declared_bytes_are_missing() -> None:
    body = b'{"ok":true}' + b" " * (65786 - len(b'{"ok":true}'))
    with parsed_response(content_length_response(body[:-506], declared=len(body))) as (api, counts):
        with pytest.raises(RuntimeError, match="incomplete response"):
            request(api)
        assert counts == [1]


def test_early_eof_rejects_missing_body_instead_of_returning_empty_success() -> None:
    with parsed_response(content_length_response(b"", declared=506)) as (api, counts):
        with pytest.raises(RuntimeError, match="incomplete response"):
            request(api)
        assert counts == [1]


def test_complete_declared_body_returns_without_waiting_for_peer_eof() -> None:
    body = b'{"ok":true}' + b" " * (65786 - len(b'{"ok":true}'))
    with dummy_response(content_length_response(body), hold_open=True) as (api, closed, counts):
        assert request(api) == {"ok": True}
        assert not closed.is_set()
        assert counts == [1]


def test_complete_zero_length_response_retains_empty_result() -> None:
    with parsed_response(content_length_response(b"")) as (api, _):
        assert request(api) == {}


def test_eof_delimited_response_retains_supported_json_behavior() -> None:
    wire = b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"ok":true}'
    with parsed_response(wire) as (api, _):
        assert request(api) == {"ok": True}


def test_complete_chunked_response_retains_supported_json_behavior() -> None:
    body = b'{"ok":true}'
    wire = (
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        + f"{len(body):x}\r\n".encode()
        + body
        + b"\r\n0\r\n\r\n"
    )
    with parsed_response(wire) as (api, _):
        assert request(api) == {"ok": True}


def test_incomplete_chunked_response_is_not_accepted() -> None:
    wire = (
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        b'20\r\n{"ok":true}'
    )
    with parsed_response(wire) as (api, counts):
        with pytest.raises(http.client.IncompleteRead):
            request(api)
        assert counts == [1]


@pytest.mark.parametrize("missing", [0, 1])
def test_existing_response_size_limit_takes_precedence(missing: int) -> None:
    body = b'{"ok":true}' + b" " * (1048577 - len(b'{"ok":true}'))
    with (
        parsed_response(content_length_response(body, declared=len(body) + missing)) as (api, _),
        pytest.raises(RuntimeError, match="exceeded the safe local limit"),
    ):
        request(api)


def test_ambiguous_dummy_mutation_delivery_rejects_without_retry() -> None:
    body = b'{"committed":true}'
    with parsed_response(content_length_response(body, declared=len(body) + 506)) as (api, counts):
        with pytest.raises(RuntimeError, match="incomplete response"):
            request(api, "POST")
        assert counts == [1]
