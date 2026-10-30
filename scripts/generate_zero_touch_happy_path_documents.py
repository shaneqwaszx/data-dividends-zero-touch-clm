"""Create reproducible image-only fictional FYP identity PDFs for local OCR UAT.

By default only the D-101 partnership agreement and Government status letter are written;
the four existing company scans keep their committed bytes unless --company-scans is given.
"""

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/backend")]

from scripts.zero_touch_happy_path_fixtures import (
    COMPANIES,
    GOVERNMENT,
    HappyPathCompany,
)

DOCUMENT_DIRECTORY = ROOT / "apps/backend/tests/fixtures/uat/zero-touch-database"


_COMPANY_SCAN_FONTS = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)
# D-101: local Tesseract misreads short "P1".."P6" tokens in Arial; Verdana-style glyphs
# (DejaVu Sans is Verdana-derived) read back exactly at HIGH quality.
_LABELLED_SCAN_FONTS = (
    Path("C:/Windows/Fonts/verdana.ttf"),
    Path("/System/Library/Fonts/Supplemental/Verdana.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)


def _font(fonts: tuple[Path, ...] = _COMPANY_SCAN_FONTS) -> ImageFont.FreeTypeFont:
    font_path = next((path for path in fonts if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("Synthetic scan requires a provisioned local font")
    return ImageFont.truetype(str(font_path), 40)


def scanned_document(company: HappyPathCompany) -> bytes:
    font = _font()
    with Image.new("RGB", (2600, 1550), "white") as image:
        draw = ImageDraw.Draw(image)
        lines = (
            "FICTIONAL FYP TEST DATA - LOCAL DATABASE DEMONSTRATION",
            *(f"{key}: {value}" for key, value in company.fields.items()),
            *(f"{key}: {value}" for key, value in company.target_profile.items()),
            "Entirely synthetic. No real company or personal identity.",
            "ACRA-style normalized fixture. No ACRA request generated this document.",
        )
        for index, line in enumerate(lines):
            draw.text((65, 55 + index * 105), line, fill="black", font=font)
        output = BytesIO()
        image.save(
            output,
            format="PDF",
            resolution=150.0,
            title=f"FICTIONAL FYP TEST DATA - {company.code}",
            creationDate="D:20261005000000Z",
            modDate="D:20261005000000Z",
        )
        return output.getvalue()


def labelled_scan(code: str, lines: tuple[str, ...]) -> bytes:
    """D-101: same image-only style; the single page is visibly labelled fictional."""
    font = _font(_LABELLED_SCAN_FONTS)
    footer = "FICTIONAL FYP TEST DATA - not a real document, organisation or person."
    rows = (*lines, footer)
    with Image.new("RGB", (3000, 110 + len(rows) * 105), "white") as image:
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(rows):
            draw.text((65, 55 + index * 105), line, fill="black", font=font)
        output = BytesIO()
        image.save(
            output,
            format="PDF",
            resolution=150.0,
            title=f"FICTIONAL FYP TEST DATA - {code}",
            creationDate="D:20261029000000Z",
            modDate="D:20261029000000Z",
        )
        return output.getvalue()


GAMMA = COMPANIES[2]
PARTNERSHIP_AGREEMENT_NAME = "demo-gamma-partnership-agreement.pdf"


if __name__ == "__main__":
    DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if "--company-scans" in sys.argv[1:]:
        for company in COMPANIES:
            (DOCUMENT_DIRECTORY / company.document_name).write_bytes(scanned_document(company))
    (DOCUMENT_DIRECTORY / PARTNERSHIP_AGREEMENT_NAME).write_bytes(
        labelled_scan("GAMMA-AGREEMENT", GAMMA.partnership_agreement_lines)
    )
    (DOCUMENT_DIRECTORY / GOVERNMENT.document_name).write_bytes(
        labelled_scan("GOVERNMENT-STATUS", GOVERNMENT.government_status_lines)
    )
    print("FICTIONAL_IMAGE_ONLY_PDF_COUNT=2")
