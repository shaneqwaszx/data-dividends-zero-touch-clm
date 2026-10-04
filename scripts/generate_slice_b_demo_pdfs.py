"""Safe client PDFs from tracked normalized identity / existing synthetic fixtures."""

from pathlib import Path

from scripts.generate_phase08_synthetic_pdfs import text_pdf
from scripts.slice_b_registry_fixture import GARDEN_FIELDS, SECOND_FIELDS

FIXTURES = Path(__file__).resolve().parents[1] / "apps/backend/tests/fixtures/uat"


def main() -> None:
    variants = (
        (
            "garden-partnership-reviewed-client.pdf",
            GARDEN_FIELDS,
            (
                "Client identity matches the tracked normalized Marketplace Mock profile.",
                "Singapore country is the existing lane default, not returned evidence.",
                "Legal form: PARTNERSHIP; no official ownership percentage established.",
                "Supplementary ownership declaration: USER_SUPPLIED_DECLARATION",
                "Synthetic Garden Partner A: 60 percent economic interest.",
                "Synthetic Garden Partner B: 40 percent economic interest.",
                "Requires explicit review: LOCAL / MANUAL_DECLARATION_POC.",
                "Fictional declaration; not ACRA ownership or legal UBO authority.",
            ),
        ),
        (
            "multiple-owner-demo-client.pdf",
            SECOND_FIELDS,
            (
                "Existing project synthetic Mock company; not official Marketplace data.",
                "Registry and ownership are fictional SYNTHETIC MOCK test evidence.",
            ),
        ),
    )
    for name, fields, notes in variants:
        (FIXTURES / name).write_bytes(
            text_pdf(
                fields,
                extra_lines=(
                    "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE - Slice B version 1",
                    "This client document is not an ACRA extract.",
                    *notes,
                ),
            )
        )


if __name__ == "__main__":
    main()
