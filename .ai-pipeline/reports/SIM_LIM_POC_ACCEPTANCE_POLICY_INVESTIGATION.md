# POC ownership acceptance policy — investigation and proposal (no implementation)

Owner policy direction, 2026-10-24: remove unnecessary manual ownership verification in the
approved POC lane. Outcome: **STOP AND PROPOSE**, as the owner instructed for the case where
"the existing model cannot distinguish POC acceptance from verified ownership". No product
file was changed.
- Worktree tree: `97fcc8c94876a5811018787ba4bb579501524c76` (structure cleanup; QG not yet run).
- HEAD = `origin/main` = `ceefe1e`.

## 1. What blocks Garden readiness today

Fresh Garden case `092cb3e8…` on the live Marketplace Mock, hybrid lane:
- ownership `REVIEW_REQUIRED`;
- CLM readiness blocker `OWNERSHIP_REVIEW_REQUIRED`;
- zero-touch exception `OWNERSHIP_INCOMPLETE` at stage OWNERSHIP;
- no GoldTier result or submission.

The chain:
- `ownership_analysis.py` sets `REVIEW_REQUIRED` whenever `record.issues` is non-empty.
- `clm_orchestration.py:1599-1606`: `ANALYZED` → ownership READY; `REVIEW_REQUIRED` →
  `OWNERSHIP_REVIEW_REQUIRED` blocker.
- `zero_touch_orchestration.py:3150-3155`: `REVIEW_REQUIRED` raises the ownership exception
  and pauses; `ANALYZED` completes the stage (`OWNERSHIP_AUTOMATED`).
- Further state-keyed paths: `:590` (manual intake), `:2868-2880` (checkpoint restoration)
  and `:1531-1552` (manual replacement outcome).

## 2. Issue codes on the Garden case and what each means

| Code | Source | Classification |
|---|---|---|
| `OWNERSHIP_DENOMINATOR_REQUIRED` | D-079/D-081: SIM LIM's rows retained without an entity profile; all retained issuers are POC-distributed ("percentages shown assume equal POC units, not an ACRA denominator") | **POC assumption marker** (only when every retained issuer is POC-distributed) |
| `SYNTHETIC_OWNERSHIP_EVIDENCE` | Always raised for hybrid analyses: links are `LOCAL_SYNTHETIC_RELATIONSHIP` declarations or `LOCAL_POC_ASSUMED_EQUAL_UNITS` estimates | **POC assumption marker** |
| `UBO_REVIEW_REQUIRED` | `ownership_analysis.py:1365-1395` `has_unresolved_semantics`. Garden is `BUSINESS_PARTNERSHIP`; the official Marketplace Mock `OFFICERS` evidence carries **4 `ROLE = Owner`** rows (3 person-format identifiers, 1 UEN-format identifier) bound to 11111999A. No graph edge from Garden explains any of them; the overlay declares only SIM LIM 62.5% and LIM CHOON HUAT 37.5%. The legacy `garden_legacy_supplement` lane explicitly exempts officer roles ("descriptive context"); the hybrid lane does not | **Independent unresolved divergence** between official ACRA Mock role evidence and the local POC declarations. It is not a POC assumption |

Codes that must always remain independent blockers:
- `CORPORATE_OWNERSHIP_UNRESOLVED`, `INCOMPLETE_LEGAL_ENTITY`;
- `CYCLE_DETECTED`, `MAXIMUM_DEPTH_EXCEEDED`, `PATH_LIMIT_EXCEEDED`;
- `PERSON_IDENTITY_UNRESOLVED`, `CONTRADICTORY_OWNERSHIP_EVIDENCE`;
- `OWNERSHIP_METHOD_UNSUPPORTED`, `OWNERSHIP_REQUIRED`;
- the non-POC `OWNERSHIP_DENOMINATOR_REQUIRED` variant, any document discrepancy needing
  review, and any discovery record that is not topology-resolved.

## 3. How Option B interacts

Option B (D-081 F1) only refuses the creator's `CURRENT_EVIDENCE` and unchanged redeclaration
of POC links (`replace_review_required_source`). It does not block readiness: readiness is
blocked by the ownership state. An acceptance policy at the readiness boundary would not need
Option B relaxed. Option B can stay as the guard against relabelling POC estimates as a manual
declaration.

## 4. Why the existing model cannot express "POC basis accepted"

- `ANALYZED` is the only state that readiness and zero-touch treat as complete. It is an
  authoritative "calculable" status: the UI shows "Calculable provisional view", and
  candidates become `PROVISIONAL_UBO_CANDIDATE` when there are no issues.
- There is no field recording that an analysis was accepted on a declared assumption, under
  which policy, or with which issues.
- Formal classification is derived from the issues (`build_ownership_candidates`).
- Downstream: the CLM submission snapshot records only `PROVISIONAL_UBO_CANDIDATE` ids
  (`clm_orchestration.py:1405-1410`). Reusing `ANALYZED`, or dropping issues, would silently
  make POC estimates authoritative and push them into GoldTier submission evidence.

## 5. Smallest explicit change (proposal)

1. **Opt-in policy setting.** For example `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE=
   accept_eligible_poc`, default off. The config validator rejects it unless
   `acra_connector_mode=api_marketplace_mock` and `hybrid_direct_overlay` are set.
   Production-facing and default lanes are untouched.
2. **New explicit acceptance record** on the ownership analysis: `poc_acceptance: {policy_id,
   accepted_at, accepted_issue_codes, eligibility snapshot}`.
   - It is computed by `OwnershipAnalysisService` for new analyses only.
   - State stays `REVIEW_REQUIRED`, and the issues and provenance stay intact. Historical
     analyses are never rewritten.
   - Persistence: an optional field. Case envelope 14 is unreleased, so it can either extend
     14 with exact-v13 rejection or bump to 15.
3. **Eligibility (pure function, fail-closed).** All of these must hold:
   - the issue set ⊆ {`OWNERSHIP_DENOMINATOR_REQUIRED` (POC variant only),
     `SYNTHETIC_OWNERSHIP_EVIDENCE`}, plus `UBO_REVIEW_REQUIRED` only if decision D1 = B;
   - `topology_complete`, a whitelisted overlay scenario, exact official issuer bindings;
   - every retained issuer POC-distributed;
   - no document discrepancy needing review, no non-POC denominator issue, no limits or
     cycles.
4. **Readiness boundary.** `clm_orchestration` gives ownership READY with an explicit basis
   marker (for example `basis = POC_ASSUMPTION_ACCEPTED`) instead of the blocker.
   - Zero-touch completes the OWNERSHIP stage with a distinct audit event
     (`OWNERSHIP_POC_BASIS_ACCEPTED`) and does not raise the exception.
   - Target confirmation stays mandatory; nothing is sent to GoldTier automatically.
5. **Formal classification.** Recommended: unchanged (`REVIEW_REQUIRED`/`INDETERMINATE`).
   The two people stay assumed-basis matches, so no POC estimate enters the CLM submission
   snapshot's UBO ids.
6. **UI.** The RM status reads "Ownership calculated — POC basis accepted" from the backend
   field (no frontend authority). The technical disclosure stays, and the manual form stays
   available for corrections.

Change classes: BACKEND_DOMAIN, BACKEND_API, PERSISTENCE, configuration, FRONTEND_UI.
- Required evidence: full backend, physical Mongo, contract tests, full E2E and a fresh QG.
- New decision record (D-082) superseding D-081's readiness restriction for eligible cases
  only.

## 6. Owner decisions required before implementation

- **D1 (blocks Garden):** the 4 official `Owner` roles that the declared overlay does not
  explain.
  - (A) Keep them as a genuine unresolved divergence. Garden is not eligible, which is
    truthful; the policy would apply only to scenarios whose declarations explain all
    official owner roles.
  - (B) Authorize an explicit, demo-lane-only rule: official `OFFICERS` owner roles are
    descriptive context when an accepted POC declaration is present, mirroring the legacy
    Garden supplement exemption.
  - (C) Bind those roles in the overlay declaration. That is a fixture/source change and is
    not currently authorized.
- **D2:** accepted POC results remain formally `REVIEW_REQUIRED`/`INDETERMINATE`
  (recommended), or become provisional candidates that enter the GoldTier submission
  snapshot.
- **D3:** confirm the opt-in setting name and its default-off behavior.
- **D4:** schema handling: extend the unreleased envelope 14, or bump to 15.
