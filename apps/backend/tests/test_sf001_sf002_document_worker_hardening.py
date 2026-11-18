"""SF-001 / SF-002 hardening of the isolated document worker (synthetic inputs only).

- The worker and OCR children receive a minimal allowlisted environment, never the backend's.
- Only the one expected Pillow decoder plugin may run on uploaded image bytes.
- Malformed images and crafted PDFs fail closed as DOCUMENT_STRUCTURE_INVALID, within bounds.
- On Linux (where the worker is deployed) it caps its own address space.
"""

from __future__ import annotations

import json
import struct
import sys
import time
import zlib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.connectors import local_document_worker, local_process
from app.connectors.local_process import (
    CHILD_ENVIRONMENT_ALLOWLIST,
    child_environment,
    run_bounded_process,
)
from app.services.document_errors import DocumentRequestError
from app.services.document_media import DocumentMediaRouter

SECRETS = {
    "MONGO_URI": "synthetic-mongo-uri-placeholder",
    "GOLDTIER_SANDBOX_USER_ID": "synthetic-goldtier-user",
    "ACRA_API_MARKETPLACE_CLIENT_SECRET": "synthetic-marketplace-secret",
    "PHASE13_SESSION_SECRET": "synthetic-session-secret",
    "AWS_SECRET_ACCESS_KEY": "synthetic-aws-secret",
}
FIXED = {"PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE"}


def test_child_environment_keeps_only_the_allowlist() -> None:
    parent = SECRETS | {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "HOME": "/home/x",
        "APP_ENV": "staging",
    }
    env = child_environment(parent)
    assert set(env) == {"PATH", "LANG"} | FIXED
    assert not set(SECRETS) & set(env)
    assert "HOME" not in env and "APP_ENV" not in env
    assert env["PYTHONDONTWRITEBYTECODE"] == "1" and env["PYTHONNOUSERSITE"] == "1"


def test_a_real_child_process_sees_no_backend_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    output = run_bounded_process(
        [sys.executable, "-B", "-c", "import json, os; print(json.dumps(dict(os.environ)))"],
        timeout_seconds=10,
        output_limit=256 * 1024,
        unavailable_code="UNAVAILABLE",
        timeout_code="TIMEOUT",
        failed_code="FAILED",
    )
    seen = json.loads(output)
    allowed = {name.upper() for name in CHILD_ENVIRONMENT_ALLOWLIST} | FIXED
    assert {name.upper() for name in seen} <= allowed
    assert not set(SECRETS) & set(seen)
    for value in SECRETS.values():
        assert value not in output.decode("utf-8", "replace")


def test_the_real_document_worker_receives_the_minimal_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str] | None] = []
    real_popen = local_process.subprocess.Popen

    def spy(*args: object, **kwargs: object) -> object:
        calls.append(kwargs.get("env"))  # type: ignore[arg-type]
        return real_popen(*args, **kwargs)  # type: ignore[call-overload]

    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(local_process.subprocess, "Popen", spy)
    with pytest.raises(DocumentRequestError):
        DocumentMediaRouter().extract(
            display_name="spoof.png", content_type="image/png", content=b"\x89PNG\r\n\x1a\nbad"
        )
    assert calls and all(env is not None for env in calls)
    for env in calls:
        assert env is not None and not set(SECRETS) & set(env)


@pytest.mark.parametrize(
    ("media", "expected"),
    [("image/png", "PNG"), ("image/jpeg", "JPEG"), ("image/tiff", "TIFF")],
)
def test_only_the_expected_decoder_plugin_is_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, media: str, expected: str
) -> None:
    seen: list[object] = []
    real_open = Image.open

    def spy(fp: object, mode: str = "r", formats: object = None) -> object:
        seen.append(formats)
        return real_open(fp, mode, formats)  # type: ignore[arg-type]

    monkeypatch.setattr(local_document_worker.Image, "open", spy)
    content = BytesIO()
    with Image.new("RGB", (8, 8), "white") as image:
        image.save(content, format=expected)
    local_document_worker._image(content.getvalue(), media, tmp_path, extract=False)
    assert seen == [[expected]]


def _png_chunk(kind: bytes, data: bytes, crc: int | None = None) -> bytes:
    value = zlib.crc32(kind + data) if crc is None else crc
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", value & 0xFFFFFFFF)


def _valid(kind: str) -> bytes:
    content = BytesIO()
    with Image.new("RGB", (32, 32), "white") as image:
        image.save(content, format=kind)
    return content.getvalue()


MALFORMED_IMAGES = [
    # JPEG header, then garbage instead of scan data
    ("truncated.jpg", "image/jpeg", _valid("JPEG")[:40] + b"\x00" * 64),
    # PNG with a corrupted IHDR CRC
    (
        "badcrc.png",
        "image/png",
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 2, 0, 0, 0), crc=0)
        + _png_chunk(b"IEND", b""),
    ),
    # PNG that claims 60000 x 60000 pixels (decompression bomb shape)
    (
        "bomb.png",
        "image/png",
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 60000, 60000, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(b"\x00" * 64))
        + _png_chunk(b"IEND", b""),
    ),
    # TIFF whose first IFD offset points far beyond the file
    ("badifd.tiff", "image/tiff", b"II*\x00" + struct.pack("<I", 0x7FFFFFF0) + b"\x00" * 32),
    # TIFF signature on JPEG bytes (format confusion)
    ("confused.tiff", "image/tiff", b"II*\x00" + _valid("JPEG")[4:]),
]


@pytest.mark.parametrize(("name", "media", "content"), MALFORMED_IMAGES, ids=lambda v: str(v)[:14])
def test_malformed_synthetic_images_fail_closed(name: str, media: str, content: bytes) -> None:
    started = time.monotonic()
    with pytest.raises(DocumentRequestError) as error:
        DocumentMediaRouter().extract(display_name=name, content_type=media, content=content)
    # D-143 R1: a page over the pixel limit (Pillow's bomb guard) is still rejected, with the
    # fixed reason DOCUMENT_PAGE_TOO_LARGE; every other malformed image stays generic.
    expected = "DOCUMENT_PAGE_TOO_LARGE" if name == "bomb.png" else "DOCUMENT_STRUCTURE_INVALID"
    assert error.value.code == expected
    assert time.monotonic() - started < 25


def _pdf(objects: list[bytes], root: int = 1) -> bytes:
    out = BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, root, xref)
    )
    return out.getvalue()


CRAFTED_PDFS = [
    # Page tree whose /Kids points back at itself (cycle)
    (
        "cycle.pdf",
        _pdf([b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [2 0 R] /Count 1 >>"]),
    ),
    # Array nesting far beyond the walk's depth bound
    (
        "deep.pdf",
        _pdf(
            [
                b"<< /Type /Catalog /Pages 2 0 R /Deep " + b"[" * 200 + b"]" * 200 + b" >>",
                b"<< /Type /Pages /Kids [] /Count 0 >>",
            ]
        ),
    ),
    # A startxref that points into the middle of an object
    (
        "badxref.pdf",
        _pdf(
            [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"]
        ).replace(b"startxref\n", b"startxref\n1"),
    ),
]


@pytest.mark.parametrize(("name", "content"), CRAFTED_PDFS, ids=[name for name, _ in CRAFTED_PDFS])
def test_crafted_synthetic_pdfs_fail_closed_within_bounds(name: str, content: bytes) -> None:
    started = time.monotonic()
    with pytest.raises(DocumentRequestError) as error:
        DocumentMediaRouter().extract(
            display_name=name, content_type="application/pdf", content=content
        )
    assert error.value.code == "DOCUMENT_STRUCTURE_INVALID"
    assert time.monotonic() - started < 25


BAD_FLATE_PDF = _pdf(
    [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 16 /Filter /FlateDecode >>\nstream\n"
        + b"\xde\xad\xbe\xef" * 4
        + b"\nendstream",
    ]
)


def test_an_undecodable_content_stream_is_contained_within_bounds() -> None:
    # The structure is valid; the renderer treats the bad stream as an empty page. Either a bounded
    # result or a controlled refusal is acceptable; a crash, hang or unbounded output is not.
    started = time.monotonic()
    try:
        DocumentMediaRouter().extract(
            display_name="badflate.pdf", content_type="application/pdf", content=BAD_FLATE_PDF
        )
    except DocumentRequestError as error:
        assert error.code == "DOCUMENT_STRUCTURE_INVALID"
    except Exception as error:  # noqa: BLE001 - only the documented infrastructure codes may surface
        assert getattr(error, "code", "").startswith("OCR_"), repr(error)
    assert time.monotonic() - started < 25


@pytest.mark.skipif(
    sys.platform in ("win32", "darwin"), reason="RLIMIT_AS is enforced on Linux only"
)
def test_the_worker_caps_its_own_address_space() -> None:
    output = run_bounded_process(
        [
            sys.executable,
            "-B",
            "-c",
            "import resource; from app.connectors import local_document_worker as w; "
            "w._limit_memory(); print(resource.getrlimit(resource.RLIMIT_AS)[0])",
        ],
        timeout_seconds=10,
        output_limit=1024,
        unavailable_code="UNAVAILABLE",
        timeout_code="TIMEOUT",
        failed_code="FAILED",
    )
    assert int(output) <= local_document_worker.MAX_WORKER_ADDRESS_SPACE


@pytest.mark.skipif(
    sys.platform not in ("win32", "darwin"),
    reason="on Linux the cap is set; covered by test_the_worker_caps_its_own_address_space",
)
def test_development_platforms_skip_the_cap_and_leave_rlimit_as_unchanged() -> None:
    # Safe in-process: on these platforms _limit_memory returns before touching any limit.
    if sys.platform == "win32":
        local_document_worker._limit_memory()  # noqa: SLF001 - must return without error
        return
    import resource

    before = resource.getrlimit(resource.RLIMIT_AS)
    local_document_worker._limit_memory()  # noqa: SLF001
    assert resource.getrlimit(resource.RLIMIT_AS) == before


def test_the_real_worker_validates_a_clean_fixture_pdf(tmp_path: Path) -> None:
    # Regression: a failing memory cap made every upload exit 2 on macOS.
    fixture = Path(__file__).parent / "fixtures" / "uat" / "zero-touch-database"
    fixture = fixture / "demo-alpha-scanned.pdf"
    output = run_bounded_process(
        [
            sys.executable,
            "-B",
            "-m",
            "app.connectors.local_document_worker",
            "validate",
            "application/pdf",
            str(fixture),
            str(tmp_path),
        ],
        timeout_seconds=20,
        output_limit=1024 * 1024,
        unavailable_code="UNAVAILABLE",
        timeout_code="TIMEOUT",
        failed_code="FAILED",
    )
    # run_bounded_process raises on any non-zero exit, so reaching here means exit 0.
    assert json.loads(output) == {"pages": []}
