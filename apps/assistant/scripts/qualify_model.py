"""Run one recorded model qualification (D-093). Started by the AI Assistant service for an
HR administrator; not meant to be run by hand.

    python scripts/qualify_model.py --qualification-id <32 hex> --db <state db> --profiles <file>

Synthetic scenarios only, against the local loopback model the qualification names. Every
other setting comes from the service's environment, as for the service itself.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.config import AiAssistantSettings  # noqa: E402
from assistant_eval.qualification import run_job  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-id", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--profiles", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.qualification_id):
        return 2
    settings = AiAssistantSettings(model_profiles_file=args.profiles, model_admin_db_path=args.db)
    run_job(args.qualification_id, settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
