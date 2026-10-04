# ADR-009 — Bounded local OCR and creator-reviewed ownership evidence

## Status

Proposed — Session 2 implemented candidate; integrated verification and independent
acceptance pending. No acceptance of changed content is borrowed from Session 1.

## Date

2026-10-04

## Context

The post-merge owner program authorizes scanned/image documents, proposed ownership
observations, creator-controlled reconciliation and pre-submission ownership editing.
Session 1 independently passed candidate `acc325730273d83d1bb39bbc066a89584b21dad7eebd2f8baee0afe73aed6bff`.
The starting LOCAL_PDF_TEXT had no OCR, flattened page provenance and used deterministic
scores; manual evidence only replaced a blocked analysis. Windows and the
inspected CI image have no Tesseract. Original bytes and full text remain transient.

## Decision

Extend the existing IDP/document owners with native-first page extraction and a bounded
local Tesseract process boundary. Pillow and PDFium handle validated images/rendering;
PDFium rendering is isolated or serialized, and all processing limits remain technical
safeguards. No external OCR service or request-controlled executable is introduced.
Missing OCR runtime produces an explicit safe failure when OCR is required.

Retain page/method/quality metadata and proposed ownership observations separately from
the four identity fields. Numeric parser scores are evidence scores, not probabilities;
raw OCR engine confidence, source agreement and review state remain distinct. Parser
code never calculates ownership or accepts ambiguous observations as canonical truth.

Extend the existing ownership normalization, manual declaration, Decimal analysis and
zero-touch owners. Decisions preserve original observations/graphs and version-bound
actor, time, chosen source/value and rationale. The backend case access owner and owning
case lock enforce creator-only ownership decisions; unknown historical creators are
not invented. Calculable evidence is editable before submission and revised evidence
invalidates downstream readiness/confirmation before automatic progression. Submitted
snapshots and retained target attempts cannot be rewritten or replayed.

An explicit Garden setting may combine successful official Marketplace Mock acquisition
with the current known-case local fixture. Official entity/officer/empty/unsupported
facts remain intact; supplement ownership retains LOCAL_SYNTHETIC_SUPPLEMENT provenance.
It is never a provider-error fallback or a general denominator rule. Conflicting client
observations require the onboarding user's current decision.

## Alternatives considered

- External OCR/AI: outside owner authorization and introduces document transfer.
- A second extraction/reconciliation/ownership service: existing owners already fit.
- Infer percentages by summing arbitrary holders: violates explicit denominator meaning.
- Treat local Garden facts as official ACRA: violates source provenance.
- Extend old envelopes implicitly: would make historical versions accept new evidence.

## Consequences

Two pinned image/rendering libraries and a documented optional Tesseract runtime add
operational requirements. Native documents remain usable without Tesseract. Actual OCR
acceptance requires a provisioned executable; a mock or skip cannot prove it. A new
strict case envelope version is required for creator/evidence additions, while old
versions remain read-only compatible with explicitly unknown historical metadata.

## Architecture invariants affected

Existing IDP, document, access, policy, reconciliation, Decimal, workflow, persistence
and target-ledger owners remain sole authorities. No route-to-Mongo, frontend authority,
automatic source precedence, duplicate calculation, provider fallback or replay path.

## Security and persistence implications

Validate matching MIME/signature/format, dimensions/pixels/pages/frames, bytes/text/output
and deadlines. Executables/options are backend controlled; temporary paths are generated
and cleaned, commands use argument arrays without a shell, and public failures exclude
document/provider bodies and exception details. No script/remote resource execution.
Creator identity is server-authored and immutable. New schema decoding rejects new fields
in old versions; reads do not rewrite or infer historical provenance. Existing insert-only
create, update-only mutation, identity/revision CAS and deletion safety remain required.

## Migration and retirement implications

No automatic data migration or creator reassignment. Legacy metadata remains unknown;
new evidence decisions require current supported bindings. The existing local provider
is extended rather than duplicated; no alternate calculator or fallback is retained.

## Verification

Native/scanned/mixed/poor/ambiguous extraction; supported image formats and adverse file
processing; absent runtime/deadline/output bounds; page/field/proposed provenance; exact
legacy/current schema, restart/CAS/deletion and physical Mongo cleanup; source conflicts,
creator-only stale/racing decisions, calculable editing and frozen submission; Decimal
share-count/explicit-percent/incomplete/multipath/Garden scenarios; frozen policy change;
collapsed keyboard/responsive tree; frontend/type/build/backend/lint/contracts/security;
fresh independent Session 2 gate. Real OCR is verified separately in a task-owned runtime.

Initial actual runtime evidence: task-owned pinned Docker image executed 31/31 OCR
tests, including six actual scan/image/mixed/poor cases, without network or skips.
Windows host runtime remains absent and its six real-OCR tests are explicitly skipped;
that host absence is not represented as OCR PASS. The final frozen S2 evidence and
independent verdict are recorded separately in program reports. Exact setup/bounds and
formula are in LOCAL_OCR_SETUP and IDP_FIELD_PROFILE; case schema9 is documented in
PERSISTENCE_RECOVERY_PROFILE. D-067 records current authority and retained limitations.

## Revisit conditions

Sponsor-controlled schema/privacy/reviewer/source policy, supported provider evidence,
production integration requirements, runtime/library security changes or new ownership
forms reopen the relevant boundary. No legal compliance or Live claim follows this ADR.

## Related contracts and sponsor questions

IDP_FIELD_PROFILE, IDP_REVIEW_CONTRACT, MULTI_DOCUMENT_INTAKE_PROFILE,
OWNERSHIP_UBO_PROFILE, PERSISTENCE_RECOVERY_PROFILE, POLICY_ACTIVATION_CONTRACT,
ADR-007, ADR-008, D-062/D-066 and Q-003/Q-004/Q-005/Q-012/Q-013/Q-014/Q-015/Q-016.
