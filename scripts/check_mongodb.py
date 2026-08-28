"""Run a safe MongoDB connectivity check using the repository .env file."""

from __future__ import annotations

import sys
from pathlib import Path

from pymongo.errors import PyMongoError

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.mongo import count_users

if __name__ == "__main__":
    try:
        user_count = count_users()
    except (ValueError, PyMongoError) as error:
        print(f"MongoDB check failed: {error.__class__.__name__}")
        raise SystemExit(1) from error

    print(f"MongoDB connection successful. FYP.users contains {user_count} document(s).")