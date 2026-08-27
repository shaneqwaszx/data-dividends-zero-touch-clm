"""Small MongoDB connection boundary used by local checks and future services."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Any

from app.config import Settings, get_settings

MONGO_SERVER_SELECTION_TIMEOUT_MS = 5_000


def create_mongo_client(settings: Settings | None = None) -> MongoClient[dict[str, Any]]:
    """Create a MongoDB client from the configured URI without exposing it."""

    active_settings = settings or get_settings()
    if active_settings.mongo_uri is None:
        raise ValueError("MONGO_URI is not configured")

    return MongoClient(
        active_settings.mongo_uri.get_secret_value(),
        serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS,
    )


def ping_mongodb(settings: Settings | None = None) -> None:
    """Verify that MongoDB accepts a connection, then close the client."""

    client = create_mongo_client(settings)
    try:
        client.admin.command("ping")
    except PyMongoError:
        raise
    finally:
        client.close()


def count_users(settings: Settings | None = None) -> int:
    """Count documents in the FYP database's users collection."""

    client = create_mongo_client(settings)
    try:
        client.admin.command("ping")
        return client["FYP"]["users"].count_documents({})
    finally:
        client.close()


if __name__ == "__main__":
    try:
        ping_mongodb()
    except ValueError as error:
        print(f"MongoDB check failed: {error}")
        raise SystemExit(1) from error
    except PyMongoError as error:
        print(f"MongoDB check failed: {error.__class__.__name__}")
        raise SystemExit(1) from error

    print("MongoDB connection successful.")