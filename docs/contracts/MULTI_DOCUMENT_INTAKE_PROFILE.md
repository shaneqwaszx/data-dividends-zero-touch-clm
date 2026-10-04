# Multi-Document Intake Profile (POC)

This is a project technical profile, not a sponsor-approved document policy.

| Format | Extension | Required media type | Validation/extraction |
|---|---|---|---|
| PDF | `.pdf` | `application/pdf` | bounded bytes, signature/EOF checks plus strict `pypdf` structure/page-tree parsing before IDP; no encryption or zero-page input |
| DOCX | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | safe OOXML ZIP structure and member namespace, bounded entries/expanded bytes, no rooted/UNC/drive/traversal/backslash/NUL names, encryption, macros, or embedded objects; `word/document.xml` text only |
| TXT | `.txt` | `text/plain` | UTF-8 or UTF-8 BOM, bounded characters, binary/control-content rejection |
| PNG | `.png` | `image/png` | signature, Pillow format verification, isolated decode/dimension/pixel limits, local OCR |
| JPEG | `.jpg`, `.jpeg` | `image/jpeg` | signature, Pillow format verification, isolated decode/dimension/pixel limits, local OCR |
| TIFF | `.tif`, `.tiff` | `image/tiff` | little/big endian TIFF signature, format verification, bounded frames and local OCR |

Both extension and declared MIME must match. Filenames are basename-only, 5–99
characters, start with an alphanumeric character, and use only alphanumerics, dot,
underscore, space, or hyphen. Browser relative paths are not sent or trusted.

PDF markers alone are not sufficient evidence of a PDF. A structural parser rejection is
projected as `DOCUMENT_STRUCTURE_INVALID` before IDP. DOCX ZIP member names are validated
as package names in memory; filesystem extraction is never used.

Defaults:

- maximum current files per case: 20;
- maximum bytes per file: 5 MiB;
- maximum total current intake: 25 MiB;
- maximum locally extracted text: 64,000 characters;
- maximum DOCX entries: 128;
- maximum DOCX expanded bytes: 10 MiB.
- maximum PDF pages/TIFF frames: 10;
- maximum image dimension: 8,000 pixels; maximum pixels/page: 16,000,000;
- maximum document rendered pixels: 64,000,000; PDF render resolution: 150 DPI;
- isolated structural validation: 20 seconds; provider aggregate: 60 seconds;
- OCR/page: 12 seconds by default, backend setting at most 20 seconds and bounded
  by remaining aggregate deadline; worker output: 1 MiB; OCR TSV: 2 MiB.

Explicitly unsupported include `.doc`, `.docm`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.zip`,
`.exe`, `.html`, macro-enabled OOXML, encrypted containers, and embedded Office
objects. Executable PDF actions, scripts, URI/remote files and embedded payloads are
rejected. No external fetch/execution occurs. Native PDF text is used per page when
there are at least 40 non-whitespace characters; other pages require local Tesseract.
DOCX/TXT page 1 means a logical extraction unit, not claimed rendered pagination.

Each accepted file produces one `DocumentProcessingRecord` with document ID, safe display
name, media type, byte count, provider/environment, timestamps, extraction score/provenance,
field observations, state, and supersession links. Raw bytes and extracted bodies are
transient and never stored in repositories, API responses, events, or logs.

The intake-only API accepts one file per request. Automation begins only through explicit
intake completion bound to `expected_document_count`. A failed upload does not complete
intake; successful files remain attached and the same case may be retried. The existing
single-document auto-start route remains for compatibility.

The frontend selected-file total is advisory and includes only accepted, deduplicated
files. Backend count, per-file size, and total-current-intake checks remain authoritative.
