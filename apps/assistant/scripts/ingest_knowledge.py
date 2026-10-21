"""Load official guidance (and optionally synthetic past resolutions) into the knowledge base.

Needs Ollama running with the embedding model:  ollama pull nomic-embed-text

    cd apps/assistant
    ../../.venv/bin/python scripts/ingest_knowledge.py                 # guidance only
    ../../.venv/bin/python scripts/ingest_knowledge.py --with-synthetic-resolutions
    ../../.venv/bin/python scripts/ingest_knowledge.py --rebuild       # re-embed everything

Safe to run again: unchanged guidance is skipped, changed files become new versions, and
removed files are retired. If the embedding model is not running, entries are still saved and
indexed on the next run.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.knowledge.factory import build_knowledge_base, data_dir  # noqa: E402
from ai_assistant.knowledge.ingest import (  # noqa: E402
    ingest_guidance,
    ingest_synthetic_resolutions,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--with-synthetic-resolutions", action="store_true")
    parser.add_argument("--rebuild", action="store_true", help="re-embed every current entry")
    args = parser.parse_args()

    settings = AiAssistantSettings()
    kb = build_knowledge_base(settings)
    print(f"Knowledge data: {data_dir(settings)}")
    report = ingest_guidance(kb)
    print(
        f"Guidance: {len(report.added)} added, {len(report.updated)} updated, "
        f"{len(report.unchanged)} unchanged, {len(report.retired)} retired"
    )
    if args.with_synthetic_resolutions:
        seeded = ingest_synthetic_resolutions(kb)
        print(
            f"Synthetic resolutions: {len(seeded.added)} added, "
            f"{len(seeded.updated)} updated, {len(seeded.unchanged)} unchanged"
        )
    sync = kb.rebuild() if args.rebuild else kb.reconcile()
    print(f"Index: {sync.indexed} indexed, {sync.removed} removed, {sync.failed} waiting")
    if sync.failed:
        print("Some entries are waiting: is Ollama running with nomic-embed-text? Run again.")
    for name, count in sorted(kb.status().items()):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
