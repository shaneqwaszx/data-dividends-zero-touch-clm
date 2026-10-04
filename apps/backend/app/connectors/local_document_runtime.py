"""Application-owned temporary paths and isolated media validation/rendering."""

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from app.connectors.idp import LocalDocumentProcessingError
from app.connectors.local_process import run_bounded_process


@dataclass(frozen=True)
class LocalDocumentPage:
    page_number: int
    text: str = field(repr=False)
    image_path: Path | None = field(default=None, repr=False)


@contextmanager
def isolated_document_pages(
    content: bytes,
    media_type: str,
    *,
    extract: bool = True,
    timeout_seconds: float = 20.0,
) -> Iterator[tuple[LocalDocumentPage, ...]]:
    """All native library calls stay in the child; every handle/temp retires here."""

    with TemporaryDirectory(prefix="clm-document-") as directory_name:
        directory = Path(directory_name)
        source = directory / "input.bin"
        source.write_bytes(content)
        output = run_bounded_process(
            [
                sys.executable,
                "-B",
                "-m",
                "app.connectors.local_document_worker",
                "extract" if extract else "validate",
                media_type,
                str(source),
                str(directory),
            ],
            timeout_seconds=timeout_seconds,
            output_limit=1024 * 1024,
            unavailable_code="DOCUMENT_RUNTIME_UNAVAILABLE",
            timeout_code="DOCUMENT_PROCESSING_TIMEOUT",
            failed_code="DOCUMENT_STRUCTURE_INVALID",
        )
        try:
            decoded = json.loads(output)
            if not isinstance(decoded, dict) or set(decoded) != {"pages"}:
                raise ValueError
            raw_pages = decoded["pages"]
            if not isinstance(raw_pages, list) or len(raw_pages) > 10:
                raise ValueError
            pages: list[LocalDocumentPage] = []
            total_text = 0
            for index, value in enumerate(raw_pages, 1):
                if not isinstance(value, dict) or set(value) != {
                    "page_number",
                    "text",
                    "image_name",
                }:
                    raise ValueError
                if value["page_number"] != index or not isinstance(value["text"], str):
                    raise ValueError
                text = value["text"]
                total_text += len(text)
                if total_text > 64_000:
                    raise ValueError
                name = value["image_name"]
                if name is not None and name != f"page-{index}.png":
                    raise ValueError
                image_path = None if name is None else directory / name
                if image_path is not None and (
                    not image_path.is_file() or image_path.stat().st_size > 50 * 1024 * 1024
                ):
                    raise ValueError
                pages.append(LocalDocumentPage(index, text, image_path))
        except (ValueError, KeyError, TypeError):
            raise LocalDocumentProcessingError("DOCUMENT_STRUCTURE_INVALID") from None
        yield tuple(pages)


def validate_local_media(content: bytes, media_type: str) -> None:
    with isolated_document_pages(content, media_type, extract=False):
        pass
