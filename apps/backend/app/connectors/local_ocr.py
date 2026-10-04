"""Bounded local Tesseract TSV adapter: no network, shell, user path, or raw errors."""

import csv
import math
import shutil
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Protocol

from app.connectors.idp import LocalDocumentProcessingError
from app.connectors.local_process import run_bounded_process


@dataclass(frozen=True)
class LocalOcrResult:
    text: str = field(repr=False)
    raw_mean_confidence: float | None
    word_count: int


class LocalOcrAdapter(Protocol):
    def recognize(self, image_path: Path, *, timeout_seconds: float) -> LocalOcrResult: ...


class TesseractOcrAdapter:
    """Fixed English TSV operation; executable configuration is backend-only."""

    def __init__(self, *, executable: str | None = None, timeout_seconds: float = 12.0) -> None:
        if not 0 < timeout_seconds <= 20:
            raise ValueError("OCR timeout must be positive and at most twenty seconds")
        if executable is not None:
            path = Path(executable)
            if not path.is_absolute() or path.name.lower() not in {"tesseract", "tesseract.exe"}:
                raise ValueError("OCR executable must be an absolute Tesseract path")
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def recognize(self, image_path: Path, *, timeout_seconds: float) -> LocalOcrResult:
        executable = self._executable or shutil.which("tesseract")
        if executable is None:
            raise LocalDocumentProcessingError("OCR_RUNTIME_UNAVAILABLE")
        output = run_bounded_process(
            [executable, str(image_path), "stdout", "-l", "eng", "--psm", "6", "tsv"],
            timeout_seconds=min(timeout_seconds, self._timeout_seconds),
            output_limit=2 * 1024 * 1024,
            unavailable_code="OCR_RUNTIME_UNAVAILABLE",
            timeout_code="OCR_PROCESSING_TIMEOUT",
            failed_code="OCR_PROCESSING_FAILED",
        )
        return decode_tesseract_tsv(output)


def decode_tesseract_tsv(output: bytes) -> LocalOcrResult:
    """Arithmetic mean of valid word confidences (0..100), excluding structural -1."""

    try:
        text = output.decode("utf-8")
        reader = csv.DictReader(StringIO(text), delimiter="\t")
        required = {
            "level",
            "page_num",
            "block_num",
            "par_num",
            "line_num",
            "word_num",
            "left",
            "top",
            "width",
            "height",
            "conf",
            "text",
        }
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ValueError
        lines: dict[tuple[int, int, int, int], list[str]] = {}
        scores: list[float] = []
        characters = 0
        rows = 0
        for row in reader:
            rows += 1
            if rows > 64000 or None in row:
                raise ValueError
            if row["level"] != "5":
                continue
            word = row["text"].strip()
            if not word:
                continue
            if any(ord(character) < 32 for character in word):
                raise ValueError
            score = float(row["conf"])
            if not math.isfinite(score) or not 0 <= score <= 100:
                raise ValueError
            key = tuple(int(row[item]) for item in ("page_num", "block_num", "par_num", "line_num"))
            if len(key) != 4 or min(key) < 0:
                raise ValueError
            for item in ("left", "top", "width", "height", "word_num"):
                if not 0 <= int(row[item]) <= 64000:
                    raise ValueError
            characters += len(word) + 1
            if characters > 64000:
                raise ValueError
            lines.setdefault((key[0], key[1], key[2], key[3]), []).append(word)
            scores.append(score)
        extracted = "\n".join(" ".join(words) for words in lines.values())
        return LocalOcrResult(extracted, sum(scores) / len(scores) if scores else None, len(scores))
    except (ValueError, KeyError, TypeError, UnicodeError, csv.Error):
        raise LocalDocumentProcessingError("OCR_OUTPUT_INVALID") from None
