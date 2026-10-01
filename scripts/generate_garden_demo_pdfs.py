"""Versioned fictional client evidence for the offline Garden protocol demo."""

from pathlib import Path

from scripts.generate_phase08_synthetic_pdfs import text_pdf

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / "apps/backend/tests/fixtures/uat"
GARDEN_FIELDS = {
    "Legal Name": "GARDEN BUSINESS",
    "UEN": "11111999A",
    "Registered Address": "18 GARDEN WALK, #01-01, 018919, SG",
    "Country": "SG",
}


def main() -> None:
    variants = {
        "garden-business-clean-onboarding-profile.pdf": GARDEN_FIELDS,
        "garden-business-conflicting-onboarding-profile.pdf": GARDEN_FIELDS | {
            "Legal Name": "GARDEN DEMO TRADING",
            "UEN": "11111998B",
            "Registered Address": "25 DEMO ROAD, #02-02, 048547, SG",
            "Country": "MY",
        },
    }
    for name, fields in variants.items():
        (FIXTURE_DIRECTORY / name).write_bytes(text_pdf(fields, extra_lines=(
            "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE - version 1",
            "Fictional client profile; this document is not an ACRA extract.",
            "Identity and address match the offline synthetic protocol fixture only.",
            "Client ownership declaration (synthetic economic-interest evidence):",
            "DEMO OWNER ONE - 60 percent; DEMO OWNER TWO - 40 percent.",
            "Requires explicit structured operator review; not verified ownership.",
        )))


if __name__ == "__main__":
    main()
