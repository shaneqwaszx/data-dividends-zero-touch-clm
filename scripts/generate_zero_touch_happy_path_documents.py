"""Create reproducible image-only fictional FYP identity PDFs for local OCR UAT."""

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


def scanned_document(company: HappyPathCompany) -> bytes:
    fonts = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    font_path = next((path for path in fonts if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("Synthetic scan requires a provisioned local font")
    font = ImageFont.truetype(str(font_path), 40)
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


if __name__ == "__main__":
    DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for company in (*COMPANIES, GOVERNMENT):
        (DOCUMENT_DIRECTORY / company.document_name).write_bytes(scanned_document(company))
    print("FICTIONAL_IMAGE_ONLY_PDF_COUNT=5")
