"""B0 cutover: prove the code is D-108 and every store resolves to an existing file in the root.

Run from apps/assistant with the launcher's environment (reads .env like the service; prints
paths only, never a value from .env). No network, no store is opened. Exit 1 on any mismatch.
"""

import os
import sys
from pathlib import Path

from ai_assistant import anthropic_runtime, remote_test
from ai_assistant.config import AiAssistantSettings
from ai_assistant.model_factory import ledger_path

if "data_dir" not in AiAssistantSettings.model_fields:
    print("FAIL: loaded code predates D-108 (no data_dir); AI_ASSISTANT_DATA_DIR would be ignored")
    sys.exit(1)

root = Path(os.environ["CLM_EXPECTED_ROOT"]).resolve(strict=True)
s = AiAssistantSettings()
expected = {
    "data_dir": (s.data_dir, root),
    "model_admin_db_path": (s.model_admin_db_path, root / "models" / "model_admin.sqlite3"),
    "anthropic_ledger (runtime/CLI)": (
        anthropic_runtime.ledger_file(s),
        root / "budget" / "anthropic_fyp_ledger.sqlite3",
    ),
    "budget_ledger (runtime/CLI)": (ledger_path(s), root / "budget" / "ledger.sqlite3"),
    "budget_ledger (D-094 remote test)": (
        remote_test.ledger_file(s),
        root / "budget" / "ledger.sqlite3",
    ),
    "model_profiles_file": (s.model_profiles_file, root / "models" / "profiles.json"),
    "knowledge_data_dir": (s.knowledge_data_dir, root / "knowledge"),
}
bad = 0
for name, (actual, want) in expected.items():
    actual_p = Path(actual).resolve()
    ok = actual_p == want and actual_p.exists()
    bad += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name}: {actual_p}")
print("code:", Path(sys.modules["ai_assistant"].__file__).parent)
sys.exit(1 if bad else 0)
