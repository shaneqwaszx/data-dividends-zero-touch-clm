"""Build the knowledge base from settings."""

from pathlib import Path

from ..config import AiAssistantSettings
from .embeddings import OllamaEmbedder
from .service import KnowledgeBase
from .store import KnowledgeStore
from .vector_index import VectorIndex

ASSISTANT_DIR = Path(__file__).resolve().parents[2]


def data_dir(settings: AiAssistantSettings) -> Path:
    path = Path(settings.knowledge_data_dir)
    return path if path.is_absolute() else ASSISTANT_DIR / path


def build_knowledge_base(settings: AiAssistantSettings) -> KnowledgeBase:
    directory = data_dir(settings)
    return KnowledgeBase(
        store=KnowledgeStore(directory / "knowledge.sqlite3"),
        index=VectorIndex(directory / "chroma"),
        embedder=OllamaEmbedder(
            base_url=settings.embed_base_url,
            model=settings.embed_model,
            timeout_seconds=settings.embed_timeout_seconds,
        ),
    )
