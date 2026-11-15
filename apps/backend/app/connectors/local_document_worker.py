"""Private isolated PDF/image worker. Never imports workflow, network, or persistence."""

import json
import math
import sys
import warnings
from contextlib import closing
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from PIL import Image, ImageOps
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

MAX_PAGES = 10
MAX_DIMENSION = 8000
MAX_PAGE_PIXELS = 16_000_000
MAX_DOCUMENT_PIXELS = 64_000_000
MAX_TEXT = 64_000
RENDER_DPI = 150
MIN_NATIVE_TEXT_CHARACTERS = 40
# SF-002: bound the child's address space (POSIX), so a crafted PDF or image cannot exhaust
# host memory inside the 20-second window.
MAX_WORKER_ADDRESS_SPACE = 1536 * 1024 * 1024
_UNSAFE_PDF_KEYS = frozenset(
    {
        "/JS",
        "/JavaScript",
        "/OpenAction",
        "/AA",
        "/Launch",
        "/URI",
        "/SubmitForm",
        "/GoToR",
        "/EmbeddedFiles",
        "/RichMedia",
        "/XFA",
        "/FS",
        "/EF",
    }
)
# A rejection leaves the child only as one of these fixed exit codes: never document
# content, names, object ids or library text. Every other failure exits with
# EXIT_MALFORMED. The parent's copy lives in local_document_runtime.py.
EXIT_MALFORMED = 2
REJECTION_EXIT_CODES = {
    "TOO_MANY_PAGES": 10,
    "ENCRYPTED": 11,
    "ACTIVE_CONTENT": 12,
    "PAGE_TOO_LARGE": 13,
    "CONTENT_TOO_LARGE": 14,
}


class _Rejection(Exception):
    """A specific, fixed reason the document fails a local check."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _dimensions(width: int, height: int) -> int:
    pixels = width * height
    if min(width, height) < 1:
        raise ValueError("image bounds")
    if max(width, height) > MAX_DIMENSION or pixels > MAX_PAGE_PIXELS:
        raise _Rejection("PAGE_TOO_LARGE")
    return pixels


def _safe_pdf(reader: PdfReader) -> None:
    if reader.is_encrypted:
        raise _Rejection("ENCRYPTED")
    page_count = len(reader.pages)
    if page_count > MAX_PAGES:
        raise _Rejection("TOO_MANY_PAGES")
    if page_count < 1:
        raise ValueError("pdf bounds")
    seen: set[tuple[int, int]] = set()
    pending: list[tuple[object, int]] = [(reader.trailer, 0)]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 10000 or depth > 40:
            raise ValueError("pdf structure bounds")
        if isinstance(value, IndirectObject):
            identity = (value.idnum, value.generation)
            if identity in seen:
                continue
            seen.add(identity)
            pending.append((value.get_object(), depth + 1))
        elif isinstance(value, DictionaryObject):
            if _UNSAFE_PDF_KEYS.intersection(value) or (
                "/F" in value and ("/Type" not in value or str(value["/Type"]) == "/Filespec")
            ):
                raise _Rejection("ACTIVE_CONTENT")
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, ArrayObject):
            pending.extend((item, depth + 1) for item in value)


def _pdf(content: bytes, directory: Path, *, extract: bool) -> list[dict[str, object]]:
    if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
        raise ValueError("pdf markers")
    reader = PdfReader(BytesIO(content), strict=True)
    _safe_pdf(reader)
    total_pixels = 0
    for page in reader.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if not math.isfinite(width) or not math.isfinite(height):
            raise ValueError("pdf dimensions")
        total_pixels += _dimensions(
            math.ceil(width * RENDER_DPI / 72), math.ceil(height * RENDER_DPI / 72)
        )
    if total_pixels > MAX_DOCUMENT_PIXELS:
        raise _Rejection("CONTENT_TOO_LARGE")
    if not extract:
        return []
    pages: list[dict[str, object]] = []
    total_text = 0
    with closing(pdfium.PdfDocument(content)) as document:
        if len(document) != len(reader.pages):
            raise ValueError("page count disagreement")
        for index in range(len(document)):
            with closing(document[index]) as page:
                with closing(page.get_textpage()) as textpage:
                    count = textpage.count_chars()
                    total_text += count
                    if total_text > MAX_TEXT:
                        raise _Rejection("CONTENT_TOO_LARGE")
                    text = textpage.get_text_range()
                if len("".join(text.split())) >= MIN_NATIVE_TEXT_CHARACTERS:
                    pages.append({"page_number": index + 1, "text": text, "image_name": None})
                else:
                    name = f"page-{index + 1}.png"
                    with closing(page.render(scale=RENDER_DPI / 72)) as bitmap:
                        image = bitmap.to_pil()
                        try:
                            _dimensions(*image.size)
                            image.save(directory / name, format="PNG")
                        finally:
                            image.close()
                    pages.append({"page_number": index + 1, "text": "", "image_name": name})
    return pages


def _image(
    content: bytes, media_type: str, directory: Path, *, extract: bool
) -> list[dict[str, object]]:
    expected = {"image/png": "PNG", "image/jpeg": "JPEG", "image/tiff": "TIFF"}[media_type]
    signatures = {
        "PNG": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "JPEG": content.startswith(b"\xff\xd8\xff"),
        "TIFF": content[:4] in {b"II*\x00", b"MM\x00*"},
    }
    if not signatures[expected]:
        raise ValueError("image signature")
    Image.MAX_IMAGE_PIXELS = MAX_PAGE_PIXELS
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    try:
        # SF-001: only the one expected decoder plugin may run on uploaded bytes.
        with Image.open(BytesIO(content), formats=[expected]) as image:
            if image.format != expected:
                raise ValueError("decoded format")
            frames = getattr(image, "n_frames", 1)
            if frames < 1 or (expected != "TIFF" and frames != 1):
                raise ValueError("frame bounds")
            if frames > MAX_PAGES:
                raise _Rejection("TOO_MANY_PAGES")
            total_pixels = 0
            pages: list[dict[str, object]] = []
            for index in range(frames):
                image.seek(index)
                total_pixels += _dimensions(*image.size)
                if total_pixels > MAX_DOCUMENT_PIXELS:
                    raise _Rejection("CONTENT_TOO_LARGE")
                image.load()
                if extract:
                    name = f"page-{index + 1}.png"
                    oriented = ImageOps.exif_transpose(image)
                    try:
                        with oriented.convert("RGB") as normalized:
                            normalized.save(directory / name, format="PNG")
                    finally:
                        oriented.close()
                    pages.append({"page_number": index + 1, "text": "", "image_name": name})
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        # Pillow's own per-image pixel guard (MAX_IMAGE_PIXELS = MAX_PAGE_PIXELS).
        raise _Rejection("PAGE_TOO_LARGE") from None
    return pages


def _limit_memory() -> None:
    if sys.platform == "win32":  # Windows development only; the deployed worker runs on Linux
        return
    import resource

    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = MAX_WORKER_ADDRESS_SPACE
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))


def main() -> int:
    try:
        _limit_memory()
        operation, media_type, input_name, directory_name = sys.argv[1:]
        if operation not in {"validate", "extract"}:
            return 2
        content = Path(input_name).read_bytes()
        if not 0 < len(content) <= 5 * 1024 * 1024:
            return 2
        directory = Path(directory_name)
        pages = (
            _pdf(content, directory, extract=operation == "extract")
            if media_type == "application/pdf"
            else _image(content, media_type, directory, extract=operation == "extract")
        )
        output = json.dumps({"pages": pages}, ensure_ascii=True).encode("ascii")
        if len(output) > 1024 * 1024:
            return 2
        sys.stdout.buffer.write(output)
        return 0
    except _Rejection as rejection:
        return REJECTION_EXIT_CODES[rejection.reason]
    except Exception:
        return EXIT_MALFORMED


if __name__ == "__main__":
    raise SystemExit(main())
