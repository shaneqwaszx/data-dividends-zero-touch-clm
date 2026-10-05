"""Reproducible fictional Garden scan for offline browser/OCR regression only."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.slice_b_registry_fixture import GARDEN_FIELDS


def scanned_garden_png() -> bytes:
    font_paths = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    font_path = next((path for path in font_paths if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("Synthetic scan requires a provisioned local font")
    font = ImageFont.truetype(str(font_path), 40)
    with Image.new("RGB", (2400, 640), "white") as image:
        draw = ImageDraw.Draw(image)
        for index, line in enumerate((
            "SYNTHETIC OFFLINE GARDEN OCR REGRESSION",
            *(f"{key}: {value}" for key, value in GARDEN_FIELDS.items()),
        )):
            draw.text((50, 50 + index * 90), line, fill="black", font=font)
        output = BytesIO()
        image.save(output, format="PNG", dpi=(150, 150))
        return output.getvalue()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    destination = root / "apps/backend/tests/fixtures/uat/garden-post-uat-scanned.png"
    destination.write_bytes(scanned_garden_png())
