# Provisional IDP Field Profile

## Status

`PROVISIONAL_CORPORATE` is **PROJECT-DEFINED / PROVISIONAL**. Delta Capita has not
approved this document type, field list, confidence threshold, comparison behavior, or
review rules. Q-003 and Q-014 await sponsor confirmation.

## Fields

| Field key | Candidate meaning | Canonical comparison source | Status |
|---|---|---|---|
| `registration_number` | UEN / registration number | canonical `registration_number` | Project-defined, provisional |
| `legal_name` | legal entity name | canonical `legal_name` | Project-defined, provisional |
| `registered_address` | conservative single-line registered address | canonical registered address join | Project-defined, provisional |
| `country_of_incorporation` | incorporation country/code | canonical `country_of_incorporation` | Project-defined, provisional |

The four identity keys remain closed. The S2 implementation merged through PR #69 additionally retains
proposed ownership observations under the existing ownership owner; see ADR-009.

## Extraction evidence and review

- The legacy API key `confidence` is an extraction evidence score in `[0, 1]`, not a
  calibrated probability. Historical extraction method/quality is explicitly UNKNOWN.
- The development attention threshold defaults to `0.85` and is configurable.
- Low extraction evidence requires review; source agreement and verification state
  are separate and cannot change the original extraction score.
- The integrated zero-touch owner may auto-confirm current, unambiguous matching
  observations that meet the case-frozen threshold and cross-document guards. Missing
  optional fields are not fabricated. Other current exceptions require the supported
  `ACCEPTED`, `REJECTED`, or `CORRECTED` review path; review does not manufacture an
  extraction score. The legacy standalone review lane remains explicit.
- Extraction evidence never approves a customer, compliance decision, or GoldTier state.

All thresholds and completion rules are project-defined and await sponsor confirmation.

Native primary/alternate labels score `0.97`/`0.90`; absent values score `0` and
ambiguous distinct values have no chosen value and score at most `0.40`. OCR uses
`label score × arithmetic mean of valid Tesseract word confidences / 100`; structural
TSV rows with confidence `-1` are excluded. Raw OCR mean/count are retained separately.
Native labelled quality is HIGH; OCR is HIGH at raw mean >=85, otherwise LOW, with
UNAVAILABLE for no usable words. These deterministic quality bands are technical POC
descriptors, not a business-policy or accuracy claim. Multiple candidates retain page,
method, quality and opaque reference, and remain replacement-required even for address.

Ownership observations retain document ID/version, page/reference, extraction metadata,
explicit name/type/identifier, share count/percentage/denominator, share class, owned
entity and ISO as-of date where actually supplied. Missing values remain null. They are
PROPOSED and never infer provider IDs, integration constants, party type or denominator.

## Normalization and comparison

Normalization trims outer whitespace, collapses internal whitespace, and uppercases
case-insensitive corporate text. UEN comparison removes whitespace and uppercases.
Address comparison uses a stable join of populated canonical address parts followed by
the same conservative text normalization. No punctuation-stripping, abbreviation
expansion, transliteration, fuzzy matching, or AI matching is performed.

Comparison values are `MATCH`, `MISMATCH`, `MISSING_FROM_DOCUMENT`,
`MISSING_FROM_REGISTRY`, and `NOT_COMPARABLE`. Original extraction, normalized value,
canonical value, and human-reviewed value remain distinct. Corrections never destroy or
overwrite the original suggestion or canonical entity.

These rules are project-defined, provisional, and awaiting sponsor confirmation.

## Provenance

Each candidate records a bounded provider label, environment, optional page number,
and source reference where available. Provider labels and source references are
trimmed, nonempty, bounded, and reject control characters. Environments are
provider-neutral (`MOCK`, `LOCAL`, `SANDBOX`, or `LIVE`). They cannot carry credentials,
headers, raw provider output, or raw document text. Mock provenance proves only which
synthetic Mock IDP scenario produced a candidate; it is not evidence that OCR read the
uploaded PDF.

## Sponsor confirmations required

1. Final document types and exact required/optional fields (Q-003).
2. Sponsor-approved confidence thresholds and routing policy (Q-014).
3. Approved normalization/comparison rules and validation ownership (Q-005/Q-014).
4. Authenticated reviewer roles, allowed actions, maker-checker policy, and audit
   retention (Q-014).
5. Privacy, storage, retention, fixture, and upload security controls (Q-013).
