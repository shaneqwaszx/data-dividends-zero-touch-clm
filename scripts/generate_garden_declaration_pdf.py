"""Deterministic synthetic client PDF supporting Garden's full D-076 ownership declaration.

D-112 (owner decision, 2026-11-01): Garden's demo happy path uses the existing reviewed
creator declaration instead of the legacy supplement. This document is the case-bound
evidence for that declaration. Every value is the fictional D-076 register already used
by the demo; nothing here is ACRA-returned ownership or legal UBO authority.
"""

from pathlib import Path

from scripts.generate_phase08_synthetic_pdfs import text_pdf
from scripts.slice_b_registry_fixture import GARDEN_FIELDS

OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "apps/backend/tests/fixtures/uat/garden-d076-ownership-declaration-client.pdf"
)
NOTES = (
    "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE - Garden D-076 declaration version 1",
    "This client document is not an ACRA extract.",
    "Legal form: PARTNERSHIP; no official ownership percentage established.",
    "Supplementary ownership declaration: USER_SUPPLIED_DECLARATION (D-076 register).",
    "GARDEN BUSINESS owners: SIM LIM PTE. LTD. (UEN 111111111M) 62.5 percent;",
    "LIM CHOON HUAT 37.5 percent.",
    "SIM LIM PTE. LTD. owners: ABCD123 81.818182 percent; TAN WEI LING 9.090909",
    "percent; EFGH2345 9.090909 percent.",
    "Requires explicit review: LOCAL / MANUAL_DECLARATION_POC.",
    "Fictional declaration; not ACRA ownership or legal UBO authority.",
)


def render() -> bytes:
    return text_pdf(GARDEN_FIELDS, extra_lines=NOTES)


def main() -> None:
    OUTPUT.write_bytes(render())


if __name__ == "__main__":
    main()
