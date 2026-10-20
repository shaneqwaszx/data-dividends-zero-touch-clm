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
"""

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.knowledge.embeddings import OllamaEmbedder  # noqa: E402
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


def build(directory: Path, settings: AiAssistantSettings, *, resolutions: bool) -> KnowledgeBase:
    kb = KnowledgeBase(
        store=KnowledgeStore(directory / "knowledge.sqlite3"),
        index=VectorIndex(directory / "chroma"),
        embedder=OllamaEmbedder(
            base_url=settings.embed_base_url,
            model=settings.embed_model,
            timeout_seconds=settings.embed_timeout_seconds,
        ),
    )
    ingest_guidance(kb)
    if resolutions:
        ingest_synthetic_resolutions(kb)
    waiting = len(kb.store.index_tasks())
    if waiting:
        raise SystemExit(f"{waiting} entries could not be embedded: is Ollama running?")
    return kb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args()
    settings = AiAssistantSettings()
    items = load_labelled(LABELLED)
    print(f"{len(items)} labelled questions, embedding model {settings.embed_model}\n")
    for label, with_resolutions in (("guidance only", False), ("with past cases", True)):
        with tempfile.TemporaryDirectory() as tmp:
            kb = build(Path(tmp), settings, resolutions=with_resolutions)
            result = evaluate(Retriever(kb, settings_from(settings)), items)
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
