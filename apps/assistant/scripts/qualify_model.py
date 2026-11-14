"""Run one recorded model qualification (D-093). Started by the AI Assistant service for an
HR administrator; not meant to be run by hand.

    python scripts/qualify_model.py --qualification-id <32 hex> --db <state db> --profiles <file>

Synthetic scenarios only, against the local loopback model the qualification names. Every
other setting comes from the service's environment, as for the service itself. D-106: an HR
administrator's session keys arrive as one JSON object on standard input, never on the command
line or in the environment; the service ends the run if that HR session ends.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from pydantic import SecretStr  # noqa: E402

from ai_assistant import anthropic_runtime, key_sources  # noqa: E402
from ai_assistant.config import AiAssistantSettings  # noqa: E402
from assistant_eval.qualification import run_job  # noqa: E402

MAX_HANDOFF_BYTES = 4096
HANDOFF = {
    "openrouter": ("HR_STORE", key_sources.HR_KEY),
    "anthropic": ("ANTHROPIC_STORE", anthropic_runtime.HR_KEY),
}


def take_handoff(raw: bytes) -> bool:
    """Hold the handed-over HR keys in this process's memory (as the service holds them)."""

    if len(raw) > MAX_HANDOFF_BYTES:
        return False
    try:
        keys = json.loads(raw or b"{}")
    except ValueError:
        return False
    if not isinstance(keys, dict) or not set(keys) <= set(HANDOFF):
        return False
    for provider, key in keys.items():
        store, shape = HANDOFF[provider]
        if not isinstance(key, str) or not shape.fullmatch(key):
            return False
        getattr(key_sources, store).set(SecretStr(key), "qualification", session=None)
    return True


def hosted_ready() -> bool:
    """R2.2: in the hosted Claude mode this process registers the hosted deployment as the
    service did, after the same startup refusals (a fresh process starts unregistered). False
    stops the run. A development checkout without the mode is unchanged."""

    try:
        from assistant_hosting import profile as hosting_profile
        from assistant_hosting import provider as hosting_provider
    except ImportError:
        return True
    if not hosting_provider.mode():
        return True
    service_settings = AiAssistantSettings()
    if hosting_profile.refusals(service_settings):
        return False
    try:
        hosting_provider.install(service_settings)
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-id", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--profiles", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.qualification_id):
        return 2
    if not take_handoff(sys.stdin.buffer.read(MAX_HANDOFF_BYTES + 1)):
        return 2
    if not hosted_ready():
        return 2
    settings = AiAssistantSettings(model_profiles_file=args.profiles, model_admin_db_path=args.db)
    run_job(args.qualification_id, settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
