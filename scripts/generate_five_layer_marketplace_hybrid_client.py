"""Deterministic synthetic client PDF for the five-layer hybrid onboarding demo (D-077)."""

from pathlib import Path

from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from scripts.generate_phase08_synthetic_pdfs import text_pdf

OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "apps/backend/tests/fixtures/uat/five-layer-marketplace-hybrid-client.pdf"
)
# Supported intake labels only. No percentage, share count or person identifier is
# written, so document ownership extraction cannot create authoritative ownership data.
NOTES = (
    "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE - five-layer hybrid version 1",
    "Fictional onboarding document for FIVE_LAYER_MARKETPLACE_HYBRID_V1; not an ACRA extract.",
    "Legal name and UEN follow the sample catalogue Entity Basic Information example.",
    "Registered address intentionally not declared: no official address was confirmed.",
    "The corporate chain and declared share allotments are a fictional demonstration",
    "held in the project overlay, not ACRA-returned ownership. This document declares",
    "no ownership values and carries no token, provider payload or person identifier.",
)


def render() -> bytes:
    return text_pdf(FIVE_LAYER_FIELDS, extra_lines=NOTES)


def main() -> None:
    OUTPUT.write_bytes(render())


if __name__ == "__main__":
    main()
