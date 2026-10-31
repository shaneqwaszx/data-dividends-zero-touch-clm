"""Measure knowledge retrieval with the real local embedding model, before and after past
resolutions are added.

Needs Ollama running with:  ollama pull nomic-embed-text

    cd apps/assistant
    ../../.venv/bin/python scripts/evaluate_retrieval.py
    ../../.venv/bin/python scripts/evaluate_retrieval.py --show-misses

It builds two throw-away knowledge bases (your real one is not touched): official guidance
only, then guidance plus the synthetic past resolutions, and scores both on the labelled
questions in tests/fixtures/knowledge_eval.json:

  recall@3              share of expected entries found in the top 3
  correct "nothing"     off-topic questions that retrieved nothing confident

Use the results to tune the AI_ASSISTANT_RETRIEVAL_* settings; do not assume them.

B2: --degraded measures the mode the service falls back to when the embedding model is
not running (keywords and case context only; no Ollama needed). --role and --team score
what another role may see (knowledge visibility). Settings come from the environment only,
never .env.
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.knowledge.embeddings import (  # noqa: E402
    EmbeddingUnavailableError,
    OllamaEmbedder,
)
from ai_assistant.knowledge.evaluation import evaluate, load_labelled  # noqa: E402
from ai_assistant.knowledge.ingest import (  # noqa: E402
    ingest_guidance,
    ingest_synthetic_resolutions,
)
from ai_assistant.knowledge.retrieval import Retriever, settings_from  # noqa: E402
from ai_assistant.knowledge.service import KnowledgeBase  # noqa: E402
from ai_assistant.knowledge.store import KnowledgeStore  # noqa: E402
from ai_assistant.knowledge.vector_index import VectorIndex  # noqa: E402

LABELLED = HERE / "tests" / "fixtures" / "knowledge_eval.json"


class NoEmbeddings:
    """The embedding model is down: the retriever's degraded mode (keywords and context)."""

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingUnavailableError("degraded measurement")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailableError("degraded measurement")


def build(
    directory: Path, settings: AiAssistantSettings, *, resolutions: bool, degraded: bool = False
) -> KnowledgeBase:
    embedder: Any = (
        NoEmbeddings()
        if degraded
        else OllamaEmbedder(
            base_url=settings.embed_base_url,
            model=settings.embed_model,
            timeout_seconds=settings.embed_timeout_seconds,
        )
    )
    kb = KnowledgeBase(
        store=KnowledgeStore(directory / "knowledge.sqlite3"),
        index=VectorIndex(directory / "chroma"),
        embedder=embedder,
    )
    ingest_guidance(kb)
    if resolutions:
        ingest_synthetic_resolutions(kb)
    waiting = len(kb.store.index_tasks())
    if waiting and not degraded:
        raise SystemExit(f"{waiting} entries could not be embedded: is Ollama running?")
    return kb


def measure(
    settings: AiAssistantSettings,
    *,
    resolutions: bool,
    degraded: bool,
    role: str,
    team: str | None,
    directory: Path,
) -> Any:
    kb = build(directory, settings, resolutions=resolutions, degraded=degraded)
    return evaluate(
        Retriever(kb, settings_from(settings)), load_labelled(LABELLED), role=role, team=team
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--show-misses", action="store_true")
    parser.add_argument("--degraded", action="store_true", help="no embedding model")
    parser.add_argument("--role", default="RELATIONSHIP_MANAGER")
    parser.add_argument("--team", default="TEAM_A")
    args = parser.parse_args()
    settings = AiAssistantSettings(_env_file=None)
    items = load_labelled(LABELLED)
    model = "none (degraded)" if args.degraded else settings.embed_model
    print(f"{len(items)} labelled questions, role {args.role}, embedding model {model}\n")
    for label, with_resolutions in (("guidance only", False), ("with past cases", True)):
        # Chroma may keep its file open on Windows: cleanup errors are ignored.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            result = measure(
                settings,
                resolutions=with_resolutions,
                degraded=args.degraded,
                role=args.role,
                team=args.team or None,
                directory=Path(tmp),
            )
            print(
                f"{label:16} recall@3 {result.recall_at_k:.2f}   "
                f'correct "nothing" {result.correct_nothing_rate:.2f}'
            )
            if args.show_misses:
                for miss in result.misses:
                    print(f"   miss: {miss['question']}")
                    print(f"         expected {miss['expected']}, got {miss['got']}")
    print(
        "\nQuestions that expect a past case can only be found once past cases exist, "
        "so recall rises after they are added."
    )


if __name__ == "__main__":
    main()
