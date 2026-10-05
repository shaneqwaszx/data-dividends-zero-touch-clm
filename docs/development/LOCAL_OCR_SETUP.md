# Bounded local OCR setup and evidence

The S2 implementation merged through PR #69 extends LOCAL_PDF_TEXT through the existing IDP port. It uses pinned
Pillow 12.3.0 and pypdfium2 5.13.0 plus optional English Tesseract. Original documents
and full extraction remain local/transient. No vendor/AI upload is authorized or used.
Native PDF pages with at least 40 non-whitespace characters use native extraction;
other PDF pages and PNG/JPEG/TIFF require OCR. DOCX/TXT use native labelled text.

## Reproducible Docker runtime on Windows and CI

From the managed checkout, provision the task-owned Linux runtime:

```powershell
docker build -f scripts/ocr_validation.Dockerfile -t clm-s2-ocr:20261004 .
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,size=256m --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 1g --cpus 2 --user 65534:65534 clm-s2-ocr:20261004 python -B -m pytest apps/backend/tests/test_s2_local_ocr.py -q -p no:cacheprovider -o addopts=
```

The Dockerfile pins the Python 3.12.10 Bookworm release tag, Debian Tesseract 5.3.0-2,
English data 1:4.1.0-2 and DejaVu fonts 2.37-6. Its specific dockerignore allowlists
only required backend/source/tests/build files and excludes .env, caches and private
repository metadata. Dependency acquisition occurs during provisioning; acceptance
runs with no network, read-only image, unprivileged user and bounded temporary storage.
No host system package is silently installed. The CI local-ocr job uses the same pack.

On 2026-10-04, the task-owned runtime executed 31/31 acceptance/adverse tests, zero
skips, including actual PNG/JPEG/TIFF, image-only PDF, mixed native/scan PDF and poor
OCR. A compressed synthetic TIFF fixture respects the unchanged 5 MiB intake limit.
This is actual local OCR evidence, not a mock or vendor accuracy/production claim.
Subsequent candidates still require current execution and independent review.

## Optional host executable

This Windows session has no observed host Tesseract, so required OCR safely returns
OCR_RUNTIME_UNAVAILABLE. Native PDF/DOCX/TXT still work. An owner-provisioned executable
may be selected with LOCAL_OCR_EXECUTABLE as an absolute local path ending in
tesseract.exe; otherwise the backend detects tesseract on PATH. English eng trained
data must be available to that runtime. LOCAL_OCR_TIMEOUT_SECONDS defaults to 12 and
is limited to 20; no request can select executable/options/path. Verify a host setup
with tesseract --version and --list-langs, then run the actual OCR pack with no skips.
The tested supported setup here is the pinned Docker runtime above. No private .env is
edited by this program, and Windows host OCR is not reported as passing.

## Bounds and safe failure

See MULTI_DOCUMENT_INTAKE_PROFILE for unchanged 5 MiB/file, 20 current files and 25 MiB
case; ten pages/frames; 8000 dimension/16M page/64M document pixels; 150 DPI rendering;
20s structural worker/60s aggregate extraction and per-page OCR deadline; 64k text,
1 MiB worker/2 MiB TSV output; 32 field candidates and 128 ownership observations.
Validation plus processing is separately bounded and can take up to 80 seconds.
Pillow/PDFium work stays in a child process, handles close and generated temporary
files retire on failure/success. Argument arrays use no shell. Public codes never
include engine stderr, document text, private paths or arbitrary provider error names.
PDF actions, remote resources, macros, encrypted/embedded formats and bomb sizes fail
closed. Extraction scores are deterministic evidence, never correctness probabilities.

Implementation references: [Tesseract TSV](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html),
[PDFium process safety](https://pypdfium2.readthedocs.io/en/stable/python_api.html),
[Pillow image bounds](https://pillow.readthedocs.io/en/stable/reference/Image.html).
