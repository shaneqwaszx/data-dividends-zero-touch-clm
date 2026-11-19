"""Build the D-095 synthetic eligibility manifest (ai_assistant/synthetic_eligibility.json)
from the repository's synthetic sources. No model and no network.

    cd apps/assistant
    ../../.venv/Scripts/python scripts/build_synthetic_eligibility.py          # write the file
    ../../.venv/Scripts/python scripts/build_synthetic_eligibility.py --check  # exit 1 if stale

It records identities and fingerprints only, never business values:

    companies   (UEN, legal name) of every company the backend's Mock ACRA connector serves
                (asked through the connector itself) and of the project's synthetic company
                packs seeded into the local synthetic registry (LOCAL_SYNTHETIC_UAT_V1)
    documents   (SHA-256 of the bytes, media type, exact size, file name for reference) of
                every synthetic client document tracked under the backend's UAT fixtures. The
                backend computes the same digest from each upload; only a match is verified.
    viewers     the backend's seeded POC users

A case's other values (addresses, officers, ownership parties, extracted document fields) are
not listed: they are trusted because of where they came from, not because of what they say.
"""

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
BACKEND = ROOT / "apps" / "backend"
sys.path[:0] = [str(HERE), str(BACKEND), str(ROOT)]

from ai_assistant.synthetic_eligibility import ELIGIBILITY_FILE, SCHEMA  # noqa: E402

UAT_FIXTURES = BACKEND / "tests" / "fixtures" / "uat"
MOCK_ACRA_SOURCES = (
    BACKEND / "app" / "connectors" / "mock_acra.py",
    BACKEND / "app" / "connectors" / "garden_business.py",
    BACKEND / "app" / "demo" / "scenarios.py",
)
SEEDED_USERS = (
    BACKEND / "app" / "domain" / "access.py",
    BACKEND / "app" / "services" / "admin_repository.py",
)
NON_CASE_VIEWERS = frozenset({"Support User"})
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_UEN = re.compile(r"[0-9]{8,9}[A-Z]")


def _uen_constants(paths: tuple[Path, ...]) -> set[str]:
    found: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _UEN.fullmatch(node.value)
            ):
                found.add(node.value)
    return found


def companies() -> list[dict[str, str]]:
    from app.connectors.mock_acra import MockAcraConnector
    from scripts.synthetic_company_pack import SPONSOR_DEMO_COMPANIES, SYNTHETIC_COMPANIES

    pairs: set[tuple[str, str]] = set()
    connector = MockAcraConnector()
    for uen in _uen_constants(MOCK_ACRA_SOURCES):
        payload = connector.fetch_company(uen)
        if payload is not None:
            if payload.source_environment != "MOCK":
                raise SystemExit(f"{uen}: the Mock ACRA connector did not answer as MOCK")
            pairs.add((payload.uen, payload.entity_name))
    for company in (*SYNTHETIC_COMPANIES, *SPONSOR_DEMO_COMPANIES):
        pairs.add((company.uen, company.legal_name))
    # Owner-approved 2026-11-19 (C4 closeout): the D-077 five-layer demo root, served by ACRA's
    # API Marketplace Mock (environment MOCK) with only local synthetic ownership below it; its
    # NL-7 PDFs are already approved fixtures. Exactly this one company; per-answer registry,
    # document, viewer and value checks still apply.
    from app.connectors.hybrid_ownership_overlay import FIVE_LAYER_ROOT_UEN

    pairs.add((FIVE_LAYER_ROOT_UEN, MARKETPLACE_MOCK_ROOT_LEGAL_NAME))
    return [{"uen": uen, "legal_name": name} for uen, name in sorted(pairs)]


# The name ACRA's Marketplace Mock returns for the five-layer root (the backend's
# local_display_name for FIVE_LAYER_ROOT_UEN).
MARKETPLACE_MOCK_ROOT_LEGAL_NAME = "OPQ PTE. LTD."


def documents() -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for path in sorted(UAT_FIXTURES.rglob("*")):
        media = MEDIA_TYPES.get(path.suffix.lower())
        if path.is_file() and media is not None:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            found.setdefault(
                digest,
                {
                    "sha256": digest,
                    "display_name": path.name,
                    "media_type": media,
                    "size_bytes": len(content),
                },
            )
    return [found[digest] for digest in sorted(found)]


def viewers() -> list[str]:
    names: set[str] = set()
    for path in SEEDED_USERS:
        names |= set(
            re.findall(
                r'user_id="[^"]+",\s*display_name="([^"]+)"', path.read_text(encoding="utf-8")
            )
        )
    # D-103: Support has no case pages; it only looks at the case details logged with a
    # feedback ticket (on the review page, or by asking the AI Assistant about that case).
    # Leaving it out of this D-095 manifest means, in D-095 mode, those ticket chats are
    # never sent to an external model. Outside D-095 mode the synthetic boundary decides,
    # and it lists every seeded user (Support included), so only the synthetic test case
    # can reach an external model there.
    return sorted(names - NON_CASE_VIEWERS)


def build() -> str:
    data = {
        "schema": SCHEMA,
        "note": (
            "Generated by scripts/build_synthetic_eligibility.py from the repository's synthetic "
            "sources (D-095). Identities and fingerprints only. Do not edit by hand."
        ),
        "registry": {"source_system": "ACRA", "environments": ["MOCK"]},
        "companies": companies(),
        "documents": documents(),
        "viewers": viewers(),
    }
    return json.dumps(data, indent=1, ensure_ascii=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is not current")
    args = parser.parse_args()
    text = build()
    if args.check:
        current = ELIGIBILITY_FILE.read_text(encoding="utf-8") if ELIGIBILITY_FILE.exists() else ""
        if current != text:
            print("synthetic eligibility is not current: run build_synthetic_eligibility.py")
            return 1
        print("synthetic eligibility is current")
        return 0
    ELIGIBILITY_FILE.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {ELIGIBILITY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
