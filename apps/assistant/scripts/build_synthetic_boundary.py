"""Build the D-094 synthetic boundary (ai_assistant/synthetic_boundary.json) from the
repository's synthetic fixtures. No model and no network: every evaluation and Phase B question
is put through the real service against its synthetic fixture case (the evaluation harness's
mock CLM backend), and what the service would send is recorded.

    cd apps/assistant
    ../../.venv/Scripts/python scripts/build_synthetic_boundary.py          # write the file
    ../../.venv/Scripts/python scripts/build_synthetic_boundary.py --check  # exit 1 if stale

Sources (all synthetic or system text, never client data):

    case, documents, values   the saved Garden fixtures and their evaluation variants, and the
                              file names and field values of the fictional Garden PDFs in the
                              backend's UAT fixtures (scripts/generate_garden_demo_pdfs.py)
    viewers                   the fixture user and the backend's seeded POC users
    knowledge                 repository guidance files and the synthetic seed (id, hash)
    conversation_vocabulary   what a question may use: the evaluation and Phase B questions
                              (and synthetic user history turns), the guidance, seed and
                              instruction files, the approved fixture values, the app's screen
                              terms (guide.py) and a reviewed list of everyday words
    prompt_vocabulary         additionally, for assistant history and system messages: every
                              word of every message the service builds for those questions
    code_vocabulary           additionally, for system messages only: the alphabetic string
                              constants of the assistant and backend application code
"""

import argparse
import ast
import atexit
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

# B0: importing assistant_eval imports ai_assistant.main, whose module-level app opens the
# knowledge store (and, with a profiles file, the model state database) at import. This
# generator only captures prompts, so it uses a temporary knowledge folder and no model
# management: regenerating or checking the boundary never opens a real runtime store.
_SCRATCH = tempfile.mkdtemp(prefix="boundary-build-")
atexit.register(shutil.rmtree, _SCRATCH, ignore_errors=True)
os.environ["AI_ASSISTANT_KNOWLEDGE_DATA_DIR"] = os.path.join(_SCRATCH, "knowledge")
os.environ["AI_ASSISTANT_MODEL_PROFILES_FILE"] = ""

from ai_assistant.clm_client import CaseSnapshot  # noqa: E402
from ai_assistant.context import build_case_facts  # noqa: E402
from ai_assistant.knowledge.ingest import (  # noqa: E402
    GUIDANCE_DIR,
    SYNTHETIC_AUTHOR,
    SYNTHETIC_RESOLUTIONS,
    parse_guidance,
)
from ai_assistant.knowledge.models import Entry, EntryKind, Visibility  # noqa: E402
from ai_assistant.llm import ModelAnswer, Piece  # noqa: E402
from ai_assistant.synthetic_boundary import (  # noqa: E402
    BOUNDARY_FILE,
    SCHEMA,
    data_values,
    normalize,
    tokens,
)
from assistant_eval.models import Capture  # noqa: E402
from assistant_eval.runner import Workspace, run  # noqa: E402
from assistant_eval.scenarios import EVAL_FIXTURES, ScenarioSet, load_scenarios  # noqa: E402
from assistant_eval.variants import case_inputs  # noqa: E402

BACKEND = HERE.parent / "backend"
UAT_FIXTURES = BACKEND / "tests" / "fixtures" / "uat"
GARDEN_PDF_GENERATOR = HERE.parent.parent / "scripts" / "generate_garden_demo_pdfs.py"
SEEDED_USERS = (
    BACKEND / "app" / "domain" / "access.py",
    BACKEND / "app" / "services" / "admin_repository.py",
)
QUESTION_FILES = ("scenarios.json", "phase_b_questions.json")
# D-115: modules whose words never widen what the D-094 text check lets an external model's
# system message use. Their text reaches an external model only in D-095 development mode,
# through the per-call eligibility check and its single-use ticket (the D-115 conversational
# contract); a D-094-only external model keeps exact lines.
LOCAL_ONLY_MODULES = ("copilot.py", "claims.py", "evidence.py")
# Reviewed everyday words an RM uses in a question (no names, places or identifiers).
EVERYDAY_WORDS = [
    "block",
    "blocking",
    "fix",
    "fixed",
    "long",
    "ok",
    "okay",
    "take",
    "takes",
    "wait",
    "waiting",
    "summarise",
    "summarize",
    "summary",
    "status",
    "statuses",
    "discrepancy",
    "discrepancies",
    "created",
    "create",
    "rating",
    "rate",
    "thanks",
    "thank",
    "please",
    "explain",
    "explanation",
    "help",
    "why",
    "how",
    "when",
    "where",
    "which",
    "who",
    "what",
    "whose",
    "can",
    "could",
    "would",
    "should",
    "will",
    "does",
    "do",
    "did",
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "tell",
    "show",
    "list",
    "give",
    "me",
    "my",
    "our",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "case",
    "cases",
    "company",
    "step",
    "steps",
    "stage",
    "next",
    "now",
    "still",
    "yet",
    "left",
    "remaining",
    "done",
    "finished",
    "complete",
    "completed",
    "open",
    "pending",
    "blocked",
    "blocker",
    "blockers",
    "issue",
    "issues",
    "problem",
    "problems",
    "reason",
    "reasons",
    "mean",
    "means",
    "meaning",
    "happen",
    "happens",
    "happened",
    "again",
    "more",
    "about",
    "any",
    "all",
]
UEN, LEGAL_NAME = "11111999A", "GARDEN BUSINESS"


class Recorder:
    """Records each prompt the service builds, and answers nothing (the case-data answer)."""

    name = "synthetic-boundary-recorder"

    def __init__(self, capture: Capture, prompts: list[tuple[dict[str, Any], list[Any]]]) -> None:
        self._capture = capture
        self._prompts = prompts

    def _record(self, messages: list[dict[str, str]]) -> None:
        prep = self._capture.latest
        if prep is None:
            raise RuntimeError("no prepared question")
        self._prompts.append((prep.facts, [dict(item) for item in messages]))

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._record(messages)
        return ModelAnswer("")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self._record(messages)
        yield Piece(cut_short=False)

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def _seed_entries() -> list[Entry]:
    """The synthetic seed as ``ingest_synthetic_resolutions`` builds it."""

    entries = []
    for item in json.loads(SYNTHETIC_RESOLUTIONS.read_text(encoding="utf-8")):
        entries.append(
            Entry(
                entry_id=item["id"],
                kind=EntryKind.RESOLUTION,
                title=item["title"],
                body=item["body"],
                blocker_codes=tuple(item.get("blocker_codes", ())),
                fields=tuple(item.get("fields", ())),
                stages=tuple(item.get("stages", ())),
                follow_ups=tuple(item.get("follow_ups", ())),
                visibility=Visibility(
                    roles=tuple(item.get("roles", ())), teams=tuple(item.get("teams", ()))
                ),
                source_ref="synthetic demo data",
                illustrative=True,
                author=SYNTHETIC_AUTHOR,
            )
        )
    return entries


def _dict_strings(path: Path) -> set[str]:
    """String values written in dictionary literals (the generator's field tables)."""

    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Dict):
            found |= {
                value.value
                for value in node.values
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            }
    return found


def _string_constants(paths: list[Path]) -> set[str]:
    words: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                words |= tokens(node.value)
    return words


def build() -> str:
    prompts: list[tuple[dict[str, Any], list[Any]]] = []
    documents: set[str] = set()
    viewers: set[str] = set()
    questions: list[str] = []
    with Workspace() as workspace:
        for name in QUESTION_FILES:
            scenarios: ScenarioSet = load_scenarios(EVAL_FIXTURES / name)
            for scenario in scenarios.scenarios:
                questions += list(scenario.questions)
                questions += [
                    turn.content for turn in scenario.forged_history if turn.role == "user"
                ]
                case = case_inputs(scenario.base, scenario.variants)
                facts = build_case_facts(CaseSnapshot(case.summary, case.documents, case.actor))
                if facts["company"].get("uen") != UEN or facts["company"].get("legal_name") != (
                    LEGAL_NAME
                ):
                    raise SystemExit(f"{scenario.id}: not the Garden synthetic case")
                documents |= {str(item.get("display_name")) for item in case.documents}
                viewers.add(str(facts["viewer"].get("name")))
            run(
                scenarios,
                lambda capture: Recorder(capture, prompts),
                workspace=workspace,
            )
    documents |= {path.name for path in UAT_FIXTURES.glob("garden-business-*.pdf")}
    for path in SEEDED_USERS:
        viewers |= set(
            re.findall(
                r'user_id="[^"]+",\s*display_name="([^"]+)"', path.read_text(encoding="utf-8")
            )
        )
    # The fictional client PDFs' field values, as their generator writes them.
    values: set[str] = {normalize(text) for text in _dict_strings(GARDEN_PDF_GENERATOR)}
    # What a person may write (a question, a user history turn): only words the synthetic
    # questions, guidance, seed, instructions and fixture values use. Not the viewer names
    # and not the prompts' own wording, so common surnames and system text stay out.
    conversation: set[str] = set()
    # The service's own messages and assistant history may also use the fixture prompts.
    prompt_words: set[str] = set()
    for facts, messages in prompts:
        values |= set(data_values(facts))
        for message in messages:
            prompt_words |= tokens(message["content"])
    guidance = [parse_guidance(path) for path in sorted(GUIDANCE_DIR.glob("*.md"))]
    knowledge = sorted(
        (entry.entry_id, entry.content_hash()) for entry in [*guidance, *_seed_entries()]
    )
    for entry in [*guidance, *_seed_entries()]:
        conversation |= tokens(" ".join([entry.title, entry.body, *entry.follow_ups]))
    for path in sorted((HERE / "ai_assistant" / "instructions").glob("*.md")):
        conversation |= tokens(path.read_text(encoding="utf-8"))
    for question in questions:
        conversation |= tokens(question)
    values |= {normalize(name) for name in documents}
    for value in values:
        conversation |= tokens(value)
    # The app's own screen and status terms (guide.py holds no names) and everyday question
    # words, so ordinary questions are not refused.
    conversation |= {
        word for word in _string_constants([HERE / "ai_assistant" / "guide.py"]) if word.isalpha()
    }
    conversation |= set(EVERYDAY_WORDS)
    prompt = prompt_words - conversation
    # System messages may also use the application's own strings, alphabetic words only (no
    # identifier-shaped constants). Never the question or assistant history.
    code = [
        path
        for path in sorted((HERE / "ai_assistant").rglob("*.py"))
        if path.relative_to(HERE / "ai_assistant").as_posix() not in LOCAL_ONLY_MODULES
    ] + sorted((BACKEND / "app").rglob("*.py"))
    code_words = {word for word in _string_constants(code) if word.isalpha()}
    code_only = code_words - conversation - prompt_words
    data = {
        "schema": SCHEMA,
        "note": (
            "Generated by scripts/build_synthetic_boundary.py from the repository's synthetic "
            "fixtures (D-094). Do not edit by hand."
        ),
        "company": {
            "uen": UEN,
            "legal_name": LEGAL_NAME,
            "source_system": "ACRA",
            "environments": ["MOCK"],
        },
        "documents": sorted(documents),
        "viewers": sorted(viewers),
        "values": sorted(values),
        "knowledge": [
            {"entry_id": entry_id, "content_hash": digest} for entry_id, digest in knowledge
        ],
        "conversation_vocabulary": sorted(conversation),
        "prompt_vocabulary": sorted(prompt),
        "code_vocabulary": sorted(code_only),
    }
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is not current")
    args = parser.parse_args()
    text = build()
    if args.check:
        current = BOUNDARY_FILE.read_text(encoding="utf-8") if BOUNDARY_FILE.exists() else ""
        if current != text:
            print("synthetic boundary is not current: run scripts/build_synthetic_boundary.py")
            return 1
        print("synthetic boundary is current")
        return 0
    BOUNDARY_FILE.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {BOUNDARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
