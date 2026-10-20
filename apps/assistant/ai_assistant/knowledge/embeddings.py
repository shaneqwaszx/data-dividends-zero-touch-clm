"""Turn text into vectors with a local embedding model (Ollama, ``nomic-embed-text``).

Nothing leaves the machine. ``nomic-embed-text`` expects a task prefix, so documents and
questions are embedded slightly differently; both sides must use the same model.
"""

from typing import Any, Protocol

import httpx


class EmbeddingUnavailableError(Exception):
    """The embedding model could not be reached or returned something unusable."""


class Embedder(Protocol):
    @property
    def name(self) -> str: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    """Ollama's own embedding API (``POST /api/embed``)."""

    DOCUMENT_PREFIX = "search_document: "
    QUERY_PREFIX = "search_query: "

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/api/embed"
        self._model = model
        self._timeout = timeout_seconds
        self._transport = transport

    @property
    def name(self) -> str:
        return self._model

    def _embed(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {"model": self._model, "input": texts}
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(self._url, json=payload)
        except httpx.HTTPError:
            raise EmbeddingUnavailableError("embedding model unreachable") from None
        if response.status_code != 200:
            raise EmbeddingUnavailableError(f"embedding model returned {response.status_code}")
        try:
            vectors = response.json()["embeddings"]
        except (ValueError, KeyError, TypeError):
            raise EmbeddingUnavailableError("unreadable embedding reply") from None
        if (
            not isinstance(vectors, list)
            or len(vectors) != len(texts)
            or not all(isinstance(v, list) and v for v in vectors)
        ):
            raise EmbeddingUnavailableError("embedding reply has the wrong shape")
        return [[float(x) for x in vector] for vector in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed([self.DOCUMENT_PREFIX + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self.QUERY_PREFIX + text])[0]
