# Phase 08 Synthetic Document Pack

Every file in this directory is fictional **SYNTHETIC TEST DATA**. It contains no
customer, sponsor, or production data.

The text-based PDFs are deliberately small and contain visible `SYNTHETIC TEST DATA`.
In the normal sponsor path their labelled content is read by `LocalPdfTextIdpProvider`;
their filename and any Developer/Test selector do not determine the assessment. They
can be regenerated with `scripts/generate_phase08_synthetic_pdfs.py`.

`invalid-document.pdf` intentionally lacks a PDF signature and must be rejected before
provider invocation.

| Fixture | Intended demonstration |
|---|---|
| `clean-company-profile.pdf` | Straight-through clean evidence |
| `address-mismatch.pdf` | Address discrepancy |
| `legal-name-mismatch.pdf` | Legal-name discrepancy |
| `missing-field.pdf` | Missing extracted field |
| `low-confidence.pdf` | Low-confidence evidence |
| `no-text.pdf` | Valid intentional textless fixture; external manifest marks it synthetic, while its bytes stay marker-free to prove `DOCUMENT_TEXT_UNAVAILABLE` (no OCR) |
| `cycle-uen-clean.pdf` | Matching document for UEN `202400006F`; document passes before the UEN-keyed ownership cycle is evaluated |
| `second-case-isolation.pdf` | Separate synthetic case/isolation |
| `invalid-document.pdf` | Invalid PDF rejection |
