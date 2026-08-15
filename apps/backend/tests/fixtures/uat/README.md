# Phase 07 Synthetic Document Pack

Every file in this directory is fictional **SYNTHETIC TEST DATA**. It contains no
customer, sponsor, or production data.

The `.pdf` fixtures are deliberately small upload artefacts for the deterministic Mock
IDP boundary. Their visible labels help a presenter select the intended scenario, but
the Mock provider does not OCR or learn from their contents. Scenario behavior is
selected through the gated integrated demo preset.

`invalid-document.pdf` intentionally lacks a PDF signature and must be rejected before
provider invocation.

| Fixture | Intended demonstration |
|---|---|
| `clean-company-profile.pdf` | Straight-through clean evidence |
| `address-mismatch.pdf` | Address discrepancy |
| `legal-name-mismatch.pdf` | Legal-name discrepancy |
| `missing-field.pdf` | Missing extracted field |
| `low-confidence.pdf` | Low-confidence evidence |
| `second-case-isolation.pdf` | Separate synthetic case/isolation |
| `invalid-document.pdf` | Invalid PDF rejection |
