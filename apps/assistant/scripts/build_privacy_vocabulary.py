"""Build the D-142 privacy vocabulary (ai_assistant/privacy_vocabulary.json). No model, no network.

    cd apps/assistant
    ../../.venv/Scripts/python scripts/build_privacy_vocabulary.py          # write the file
    ../../.venv/Scripts/python scripts/build_privacy_vocabulary.py --check  # exit 1 if stale

The privacy boundary (ai_assistant/privacy_boundary.py) keeps a word in what goes to an external
model only when it is in this vocabulary. Every other word, and every identifier-like token, is
replaced with a placeholder that only the service can turn back into the original.

    words   lower-case words the service itself uses: the three reviewed D-094 vocabularies
            (synthetic_boundary.json), the instruction and repository guidance files, and the
            alphabetic string constants of the assistant and backend code (docstrings,
            SKIPPED_MODULES and SKIPPED_CONSTANTS excluded)
    terms   the capitalised forms (GoldTier, ACRA, Ownership) that the service's own text uses
            (string constants of the assistant and backend code, instruction and guidance
            files). A capitalised word in the middle
            of a sentence, and any word written in capitals, is kept only when it is a term

Removed from both: the words of every person name the repository knows (the seeded users and
viewers) and a reviewed list of common given names and surnames (NAME_WORDS). Removed from terms
only: every form of the synthetic companies' distinctive words (FIXTURE_COMPANY_WORDS), so their
names written in capitals are replaced even though "garden" is an ordinary word. A company's
generic words (BUSINESS, TRADING, PTE) stay terms: a known company is replaced as a whole, and an
unknown one loses its distinctive words. Added to words: a reviewed lexicon of onboarding
document types (DOCUMENT_TERMS, R1 P2-2), so a Support rule keeps its meaning. R1: a capitalised
word passes only as a term wherever it stands (privacy_boundary.py), so a distinctive word at the
start of a sentence is replaced too. The list cannot be complete: a person name made only of
ordinary lower-case words ("ask will about it") can still pass (D-142 OD-3, not yet accepted).
"""

import argparse
import ast
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PACKAGE = HERE / "ai_assistant"
OUTPUT = PACKAGE / "privacy_vocabulary.json"
BACKEND_APP = HERE.parent / "backend" / "app"
SCHEMA = "clm-assistant-privacy-vocabulary/1"

WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?")

# Modules whose string constants are fixture or identity data, not the service's own wording:
# the boundary's name-detection lists, and the credential-free mock connectors' made-up
# companies, officers and addresses (C10 I-3). Skipped in the assistant and backend scans.
SKIPPED_MODULES = frozenset({"privacy_boundary.py", "mock_acra.py", "mock_ownership.py"})

# Constants that are matcher-only word lists in a module that also holds service wording: what
# the service recognises in a question, never what it writes (C10 I-3).
SKIPPED_CONSTANTS = {"copilot.py": frozenset({"_OFF_TOPIC", "_CONTEXTUAL_WORDS"})}

# Common given names and surnames (Singapore and English usage). Reviewed list; extend by review.
# C10 I-3: beatrice, choon and huat are synthetic fixture persons' names declared in modules that
# also hold service wording (hybrid_ownership_overlay.py, garden_business.py).
_NAMES = """
    abdul abdullah adam adrian ahmad aisha alan albert alex alexander alice amanda amir amy ana
    andrew ang angela anna anne anthony arjun arun aw beatrice benjamin bob boon brian bryan carol
    caroline catherine chan chang charles charlotte chee chen cheng cheong cheryl chew chia chin
    chloe choo choon chong chou chow christopher chua chun claire daniel david deborah dennis devi
    diana edward
    elizabeth emily emma eric ethan eugene fatimah fiona foo frank fu gabriel gary george goh grace
    gupta hafiz hamid han hannah hao harry hassan heng henry ho hoon huat hui hussain ian ibrahim
    isaac ivan jack jacob james jane jasmine jason jen jennifer jeremy jessica jia jian jin john
    joseph joshua joyce julia kai kang karen kaur kelvin kenneth kevin khoo kiat kim koh kok kong
    kumar kwek kwok lai lakshmi lau laura lee leng leon leong li liang lian lily lim lin ling liu
    loh lucas lucy mahmood maria mary matthew maya mei melissa michael michelle ming mohamed
    mohammad mohd muhammad mui nair nathan neo ng ngiam nicholas nicole noor nur olivia ong pang
    patrick paul peter pillai poh priya quek rachel rahman raj rajesh ramesh raymond rebecca richard
    robert ryan sam samuel sarah seah sharon shi shu siew sim singh siti sophia stephen steven
    susan tan tay teo teoh terence thomas tiong toh tong ung victor vincent wang wei william
    wong woo wu xavier xin xu yan yang yap yeo yeoh yi yong yu yusof zhang zhao zheng zhou zhu
"""
NAME_WORDS = frozenset(_NAMES.split())


# D-142 R3: the service's role titles as it writes them for people ("Relationship Manager"):
# terms, so a question naming a role in title case is classified, never taken for a name.
ROLE_TERMS = frozenset(
    [
        "Relationship",
        "Manager",
        "Client",
        "Onboarder",
        "Director",
        "Compliance",
        "Reviewer",
        "Officer",
        "Support",
        "Administrator",
    ]
)


# Distinctive words of the synthetic companies' names: never a term in any casing (ordinary
# company words such as Ownership or Holdings stay terms in their mixed-case form only).
FIXTURE_COMPANY_WORDS = frozenset(
    {"garden", "merlion", "orchid", "orion", "straits", "harbour", "lion", "cyclic", "sim", "opq"}
)


# D-142 R1 (P2-2): the reviewed lexicon of onboarding document types and evidence terms that a
# Support rule names ("a recent utility bill", "a tenancy agreement"). They are ordinary words,
# not identities, and a rule loses its meaning without them. Extend by review only.
DOCUMENT_TERMS = frozenset(
    [
        "utility",
        "utilities",
        "bill",
        "bills",
        "electricity",
        "water",
        "gas",
        "telephone",
        "broadband",
        "tenancy",
        "agreement",
        "agreements",
        "invoice",
        "invoices",
        "payslip",
        "payslips",
        "licence",
        "licenses",
        "license",
        "permit",
        "permits",
        "deed",
        "deeds",
        "memorandum",
        "articles",
        "constitution",
        "constitutions",
        "resolution",
        "resolutions",
        "minutes",
        "certificate",
        "certificates",
        "incorporation",
        "statement",
        "statements",
        "bank",
        "lease",
        "leases",
        "letter",
        "letters",
        "authority",
        "authorisation",
        "authorization",
        "proof",
        "identity",
        "passport",
        "passports",
        "card",
        "cards",
        "driving",
        "residence",
        "residency",
        "employment",
        "tax",
        "assessment",
        "notice",
        "notices",
        "audited",
        "accounts",
        "annual",
        "return",
        "returns",
        "extract",
        "extracts",
        "register",
        "registers",
        "shareholding",
        "shareholdings",
        "chart",
        "charts",
        "organisation",
        "organization",
        "declaration",
        "declarations",
        "signatory",
        "signatories",
        "mandate",
        "mandates",
        "power",
        "attorney",
        "trust",
        "trusts",
        "partnership",
        "partnerships",
        "cheque",
        "cheques",
        "copy",
        "copies",
        "certified",
        "notarised",
        "notarized",
        "apostille",
        "translated",
        "translation",
        "recent",
        "dated",
        "issued",
        "expiry",
        "expired",
        "valid",
        "validity",
        "months",
    ]
)


def _words(text: str) -> set[str]:
    return set(WORD.findall(text))


def _constants(path: Path) -> set[str]:
    """Words of the string constants of one module, docstrings and SKIPPED_CONSTANTS excluded."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    skipped = SKIPPED_CONSTANTS.get(path.name, frozenset())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in skipped for target in node.targets
        ):
            docstrings |= {id(item) for item in ast.walk(node.value)}  # excluded like docstrings
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            found |= _words(node.value)
    return found


def _identity_words() -> tuple[set[str], set[str]]:
    """(person-name words, company-name words) from the repository's synthetic identities."""

    boundary = json.loads((PACKAGE / "synthetic_boundary.json").read_text("utf-8"))
    eligibility = json.loads((PACKAGE / "synthetic_eligibility.json").read_text("utf-8"))
    people: set[str] = set()
    for name in [*boundary.get("viewers", []), *eligibility.get("viewers", [])]:
        if isinstance(name, str):
            people |= {word.lower() for word in _words(name)}
    companies: set[str] = set()
    legal = [boundary.get("company", {}).get("legal_name")]
    legal += [item.get("legal_name") for item in eligibility.get("companies", [])]
    for name in legal:
        if isinstance(name, str):
            companies |= {word.lower() for word in _words(name)}
    # Seeded role names are service wording, not people.
    people -= {"poc", "hr", "administrator", "support", "user"}
    return people, companies


def build() -> str:
    boundary = json.loads((PACKAGE / "synthetic_boundary.json").read_text("utf-8"))
    words: set[str] = set()
    for key in ("conversation_vocabulary", "prompt_vocabulary", "code_vocabulary"):
        words |= {word.lower() for word in boundary.get(key, []) if word.isalpha()}
    texts = sorted((PACKAGE / "instructions").glob("*.md"))
    texts += sorted((PACKAGE / "knowledge" / "guidance").glob("*.md"))
    service: set[str] = set()
    for path in texts:
        service |= _words(path.read_text("utf-8"))
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name not in SKIPPED_MODULES:
            service |= _constants(path)
    # The backend's own codes and labels (step names, states, document profiles) reach the
    # case facts as values; their casing is the service's.
    for path in sorted(BACKEND_APP.rglob("*.py")):
        if path.name not in SKIPPED_MODULES:
            service |= _constants(path)
    words |= {word.lower() for word in service}
    words |= DOCUMENT_TERMS
    people, _companies = _identity_words()
    names = people | NAME_WORDS
    words -= names
    terms = {
        word
        for word in service
        if any(char.isupper() for char in word)
        and word.lower() in words
        and word.lower() not in FIXTURE_COMPANY_WORDS
        and len(word) > 1
    }
    terms |= {word for word in ROLE_TERMS if word.lower() in words}
    data = {
        "schema": SCHEMA,
        "note": ("Generated by scripts/build_privacy_vocabulary.py (D-142). Do not edit by hand."),
        "words": sorted(words),
        "terms": sorted(terms),
    }
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is not current")
    args = parser.parse_args()
    text = build()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print("privacy vocabulary is not current: run scripts/build_privacy_vocabulary.py")
            return 1
        print("privacy vocabulary is current")
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
