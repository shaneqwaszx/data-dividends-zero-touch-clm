"""Print the bounded synthetic evaluation for the advisory intelligence bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.intelligence_evaluation import (
    evaluate_synthetic_intelligence_bundle,
)


def main() -> int:
    result = evaluate_synthetic_intelligence_bundle()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_expected_outcomes_observed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
