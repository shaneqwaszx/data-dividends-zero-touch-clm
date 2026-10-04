# Final POC Architecture

Current owner map: [ARCHITECTURE](../ARCHITECTURE.md). Source baseline is merged
PR #69 / `73967401379378927c810d6227b0c7aa95fba061`. See
[PROJECT_STATE](../PROJECT_STATE.md) for current source and separately attributed
historical gates, external receipts and post-merge validation.

## Sponsor flow

```text
Authenticated request -> backend actor/team/capability -> frozen ACTIVE case policy
  -> initial legal name/UEN/country -> eligible Singapore read-only GoldTier Search
  -> required registry evidence through the existing registry/cache coordinator
  -> document intake/extraction -> source-neutral reconciliation
  -> registry or reviewed LOCAL ownership evidence -> one Decimal engine
  -> advisory intelligence -> readiness -> explicit Review & Send
  -> target ledger: new Shell/Policy or verified prior-target reuse, required operations/readback
  -> COMPLETED / Mock submission or confirmed bounded Sandbox submission
     (Review & Send is final local approval; external/regulatory approval is separate)
```

Ambiguous/failed Search permits independent eligible case evidence while all target
mutations remain blocked. Exact reuse requires prior finalized same-ID ledger proof;
it skips duplicate Shell/new Policy and still acquires required current registry evidence.
Compatible fresh COMPLETE cache adds zero source calls. Identity conflict invalidates reuse;
required source failure remains technical failure. No source winner or prior ownership
analysis is silently copied.

## Responsibility boundaries

- Onboarding and RegistryAcquisitionCoordinator own canonical acquisition, evidence freshness
  and exact namespace reuse; external DTOs never map directly to GoldTier.
- Document/reconciliation owners retain current observations, bounded authorized decisions
  and superseded history. Native-first LOCAL extraction and optional local Tesseract
  OCR retain proposed ownership observations; extraction scores are not probabilities
  or sponsor confidence policy. Wrong-UEN correction preserves structured originals.
- OwnershipAnalysisService owns deterministic Decimal graph/path/aggregation. The semantic
  tagger explains evidence; it cannot create percentages, legal control or approval.
- ZeroTouchOrchestrator owns stages, current typed blockers and bounded continuation.
  CLM owns readiness and frozen submission; the single target ledger owns ordering,
  call stopping, uncertainty and replay-free finalization.
- PolicyManagementService owns HR proposals and distinct-Director decisions under capability,
  lock and CAS. New ACTIVE affects new cases; impact comparison is prospective synthetic advice.
- React renders backend evidence and available controls. Authorization and workflow remain
  backend-owned. Scoped server state is cancelled/cleared across identity/session changes.

## Replacement architecture

| Surface | Current supported composition | Expansion requires |
|---|---|---|
| Registry | Synthetic Mock default; official Marketplace Mock opt-in; generic sandbox Partial; BizFile Dormant | Contract, access, strict source DTO/canonical mapping and independent acceptance |
| IDP | LOCAL native PDF/DOCX/TXT and bounded Tesseract scanned PDF/PNG/JPEG/TIFF; Mock fault seam | Approved document/OCR profile, privacy/security and provider authority |
| Ownership | Registry/manual LOCAL evidence into one Decimal engine; synthetic fault seams | Quantitative legal-form/hierarchy contract and full legal/control policy |
| GoldTier | Enhanced project-owned local Mock default; separate XPI SANDBOX_PARTIAL | Current operation/mapping/auth authority and separately authorized interoperability |
| Workflow/policy | Application orchestration and versioned POC policy control plane | Production placement, handoff, role and operational decisions |

No Camunda runtime, trained semantic ML, production compliance engine or second owner exists.

## State and trust

Memory mode is process-local. Explicit Mongo mode retains structured schema9 cases,
target ledgers and supported administration/cache aggregates with strict identity/revision CAS.
Valid schemas1..8 decode in memory without read rewrite; policy/cache schema2 are separate.
Sessions, locks, single-flight and Mock provider customer facts remain process-local.
Durable ledgers cannot reconstruct lost provider facts or replay uncertain mutations.
These are bounded single-process POC guarantees, not distributed exactly-once or regulatory audit.

Uploads are transient; safe browser/export projections omit raw provider/document bytes,
auth material and private exception detail. Unsupported/malformed evidence fails closed.

## Claim boundary

Mock, Local, Partial, Dormant and Live remain distinct. Official Marketplace Mock network
observations and synthetic offline protocol replay have different evidence identities.
XPI is Sandbox Partial; no current path is Live. Completion/readback proves POC submission,
not Ready-for-Approval, screening clearance, final legal UBO, customer or regulatory approval.
Phase25 inspected three retained original clm_poc cases read-only and rendered all
three through normal startup against an exact disposable clone. No original writes
occurred; the clone was removed after independent acceptance. This proves bounded
reader/render compatibility, not new recovery, migration or production durability.
