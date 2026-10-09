"""Generate only the four deterministic native-text SYNTHETIC MOCK client PDFs."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/backend")]

from scripts.generate_phase08_synthetic_pdfs import (
    FIXTURE_DIRECTORY,
    text_pdf,
)
from scripts.synthetic_company_pack import SYNTHETIC_COMPANIES


def main() -> None:
    for company in SYNTHETIC_COMPANIES:
        (FIXTURE_DIRECTORY / "zero-touch-database" / company.document_name).write_bytes(
            text_pdf(
                company.document_fields,
                extra_lines=(
                    "LOCAL PROJECT SYNTHETIC MOCK - fictional identity only.",
                    "Ownership evidence comes from the synthetic registry graph.",
                ),
            )
        )
    print("SYNTHETIC_MOCK_NATIVE_PDF_COUNT=4")


if __name__ == "__main__":
    main()
