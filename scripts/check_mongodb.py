"""Run a connectivity-only MongoDB ping from explicit process environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pymongo.errors import PyMongoError

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings
from app.mongo import ping_mongodb


def main() -> int:
    """Run the diagnostic without exposing the configured URI or server details."""

    uri = os.environ.get("MONGO_URI")
    if not uri:
        print("MongoDB check failed: MONGO_URI_UNAVAILABLE")
        return 1
    try:
        settings = Settings(_env_file=None, mongo_uri=uri)
        ping_mongodb(settings)
    except (ValueError, PyMongoError) as error:
        print(f"MongoDB check failed: {error.__class__.__name__}")
        return 1

    print("MongoDB connectivity check successful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
