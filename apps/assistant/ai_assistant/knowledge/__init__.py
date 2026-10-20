"""Reviewed knowledge for the AI Assistant: official guidance and approved past resolutions.

The assistant "learns" by retrieving reviewed entries, never by retraining the model:

- ``models``       what an entry is (kind, version, status, permissions)
- ``store``        SQLite: every version of every entry, reviews, keyword index
- ``embeddings``   turns text into vectors with a local Ollama model
- ``vector_index`` ChromaDB: vectors of the approved, current entries only
- ``service``      keeps SQLite and ChromaDB in step (approve, replace, retire, re-index)
- ``ingest``       loads official guidance from markdown files
"""
