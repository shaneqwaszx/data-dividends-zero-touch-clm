# D-081 UBO candidate presentation — read-only investigation

Owner visual review, 2026-10-24. Stage 3.5 verdict revised to PARTIAL PASS. This step is
read-only: no product, test or document file was changed. The reviewed tree is still
`ff8f7ab5cbadb6349e3561a48fd030bd76567bfc`.
Status: OWNER UI CORRECTION DECISION PENDING.

## 1. Backend fields for the fresh Garden case `4575f70f-1715-4f2c-9c97-e2f46359aa7e`

Taken from `GET /api/onboarding/cases/{id}/ownership` on the running smoke server.
- Analysis state: `REVIEW_REQUIRED`. Threshold `25.000000`, comparator
  `GREATER_THAN_OR_EQUAL_TO`, source classification
  `OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY`.
- Issues: `OWNERSHIP_DENOMINATOR_REQUIRED`, `SYNTHETIC_OWNERSHIP_EVIDENCE`,
  `UBO_REVIEW_REQUIRED`.
- Candidate keys: `party`, `direct_ownership_percent`, `indirect_ownership_percent`,
  `aggregated_ownership_percent`, `threshold_percent`, `threshold_comparator`,
  `threshold_result`, `classification`, `paths`, `synthetic_basis_threshold_result`.

| Candidate | direct | indirect | aggregated | threshold_result | classification | synthetic_basis_threshold_result | path calculation |
|---|---|---|---|---|---|---|---|
| ABCD123 | 0 | 51.13636375000000 | 51.13636375000000 | INDETERMINATE | REVIEW_REQUIRED | **MET** | 62.5% x 81.818182% = 51.13636375% |
| LIM CHOON HUAT | 37.500000 | 0 | 37.500000 | INDETERMINATE | REVIEW_REQUIRED | **MET** | 37.5% = 37.5% |
| TAN WEI LING | 0 | 5.68181812500000 | 5.68181812500000 | INDETERMINATE | REVIEW_REQUIRED | NOT_MET | 62.5% x 9.090909% = 5.681818125% |
| EFGH2345 | 0 | 5.68181812500000 | 5.68181812500000 | INDETERMINATE | REVIEW_REQUIRED | NOT_MET | 62.5% x 9.090909% = 5.681818125% |

`GET /ubo-candidates` returns the same four objects.

**How the backend computes these.**
- `build_ownership_candidates` (`ownership_analysis.py:521-560`). When the analysis has
  any issue, every person gets `INDETERMINATE` / `REVIEW_REQUIRED`. Otherwise the inclusive
  ≥ 25% comparator gives `MET` / `PROVISIONAL_UBO_CANDIDATE`, or `NOT_MET` /
  `BELOW_PROVISIONAL_THRESHOLD`.
- In the hybrid lane only, `synthetic_basis_threshold_results` (`:270-298`, applied at
  `:1458-1475`) runs the same comparator over the assumed basis. That basis is the overlay
  links, plus the D-081 POC links.
- D-077, D-081 and the profile (`OWNERSHIP_UBO_PROFILE.md:358-361`) define it the same
  way: "never a classification or readiness input". The domain validator also allows the
  field only on REVIEW_REQUIRED/INDETERMINATE candidates (`domain/ownership.py:300-307`).
- **So the backend computes both the percentage and the threshold comparison correctly.
  The API projects them as separate fields.** There is no backend or API defect.

## 2. Frontend components and filters

| UI element | Source | Rule |
|---|---|---|
| "People assessed: 4" | `OwnershipPathExplorer.tsx:194` | `record.candidates.length` |
| "Provisional UBOs: 0" | `OwnershipPathExplorer.tsx:195` | NATURAL_PERSON && `classification === "PROVISIONAL_UBO_CANDIDATE"` && `threshold_result === "MET"` |
| "Identified UBO candidates" list | `UboSummary.tsx:5-6`, `:14-30` | same filter (`qualified`). The section title/aria label reads "effective ownership ≥ current policy threshold" |
| "No qualifying natural person is identified by the current retained classification." | `UboSummary.tsx:31` | shown when `qualified` is empty |
| "UBO determination requires review…" | `UboSummary.tsx:32` | `record.state !== "ANALYZED"` |
| Hierarchy chip "0 provisional UBOs" and the `is-ubo` row highlight | `OwnershipStructure.tsx:72`, `:79`, `:94` | same formal filter |
| Graph effective % per row | `OwnershipStructure.tsx` rows | backend `path.effective_ownership_percent`, rounded for display by `formatOwnershipPercent` |
| Selected holder: aggregate, "Threshold comparison → INDETERMINATE", classification | `OwnershipStructure.tsx:133` | `aggregated_ownership_percent`, `threshold_result`, `classification` |
| Technical table threshold column | `OwnershipPathExplorer.tsx:265` | `threshold_result` |
| Client detail "beneficial owners" | `viewModels.ts:170-180` → `ClientDetail.tsx:138-139` | `classification === "PROVISIONAL_UBO_CANDIDATE"` |
| Shared summary on Review & Send | `ReviewAndSend.tsx:383` | renders `UboSummary` |

`types.ts:768-782` (`OwnershipCandidate`) **has no `synthetic_basis_threshold_result`**, and
no frontend file reads it. This omission is deliberate since D-077: the demo guide row says
"not rendered by the unchanged UI" (`FIVE_LAYER_ACRA_HYBRID_DEMO.md:18`), and so does the
E2E comment at `five-layer-hybrid.e2e.ts:91`. It followed the backend-only constraint.

## 3. Why "Provisional UBOs: 0"

The count uses only the formal classification. All four candidates are formally
`REVIEW_REQUIRED` / `INDETERMINATE`: the analysis carries `SYNTHETIC_OWNERSHIP_EVIDENCE`,
which every hybrid analysis raises, plus the denominator and UBO-review issues. **That
matches the contract**: a POC or synthetic-basis match must never become a provisional UBO
classification.

## 4. The empty-state message

It is **technically accurate but misleading**; it is not incorrect.
- Accurate: no person has the formal provisional classification, and the text says "by the
  current retained classification".
- Misleading, for three reasons:
  - The section heading and aria label promise "effective ownership ≥ current policy
    threshold", while two people visibly exceed it (51.14% and 37.5%).
  - The UI never shows the assumed-basis comparison that the API already returns.
  - The selected-holder panel shows "→ INDETERMINATE" with no indication that the
    assumed-basis result is MET.

A reviewer cannot tell "no one reaches 25%" apart from "two people reach 25% on an
unverified basis". No integration defect drops data: the field arrives in the response and
the type ignores it.

## 5. Minimal correction (UI-only; no API, backend or contract-semantics change)

1. `apps/frontend/src/types.ts`: add the optional, already-served
   `synthetic_basis_threshold_result?: "MET" | "NOT_MET" | "INDETERMINATE" | null` to
   `OwnershipCandidate`.
2. `apps/frontend/src/pages/UboSummary.tsx`:
   - Leave the formal list and its filter unchanged.
   - Add a separate block, **"Meets the threshold on an assumed basis — review required"**.
     It lists candidates whose `synthetic_basis_threshold_result === "MET"` and whose
     classification is REVIEW_REQUIRED or INDETERMINATE.
   - Each entry shows the name, the effective percentage, "≥ 25% on the assumed basis", and
     the basis label taken from the candidate's own path links
     (`LOCAL_POC_ASSUMED_EQUAL_UNITS` and/or `LOCAL_SYNTHETIC_RELATIONSHIP`). It ends with
     "Classification REVIEW_REQUIRED — not a verified or provisional UBO".
   - When that block has entries, the empty text becomes "No natural person is formally
     classified as a provisional UBO; N meet the threshold only on an assumed basis
     (below)."
   - With no assumed-basis matches, the text stays byte-identical.
3. `apps/frontend/src/pages/OwnershipStructure.tsx` (selected holder, `:133`): when the
   field is present, add one row: "Assumed-basis comparison: ≥ 25% → MET (not a
   classification)".
4. Optional, for the owner to decide: in `OwnershipPathExplorer.tsx` stats, add "Assumed-basis
   matches: 2" next to "Provisional UBOs: 0".

Not changed:
- the provisional counts, `is-ubo` highlighting and `viewModels.beneficial_owners`
  (Client detail);
- readiness, Option B, GoldTier;
- the comparator, engine, discovery and backend;
- the API.

**Regression tests**
- Vitest, a new `UboSummary.test.tsx` or an extension of
  `OwnershipPathExplorer.test.tsx`, with a POC fixture shaped like the Garden response:
  - the formal list is empty, and the assumed-basis block lists ABCD123 (51.14%,
    LOCAL_POC_ASSUMED_EQUAL_UNITS) and LIM CHOON HUAT (37.5%,
    LOCAL_SYNTHETIC_RELATIONSHIP), not TAN WEI LING or EFGH2345;
  - "Provisional UBOs 0" and "0 provisional UBOs" remain;
  - the empty-state variant appears.
- No field, or all NOT_MET: the original text is unchanged.
- The `PROVISIONAL_UBO_CANDIDATE` fixture (`ownershipStructureFixture.ts`) is unchanged,
  and no assumed-basis block appears.
- The selected-holder row appears only when the field is present.
- `viewModels` beneficial owners never include assumed-basis matches.
- E2E `five-layer-hybrid.e2e.ts`: replace the stale "unchanged UI does not render" comment.
  Assert that the stage lists BEATRICE LIM and DIANA KOH as assumed-basis matches while
  "0 provisional UBOs" remains.
- Gate (FRONTEND_UI): typecheck, Vitest, build, the affected E2E selectors and the full
  browser suite, then a fresh independent QG.
- Docs: the demo guide row and §8, plus one sentence in the profile saying the UI renders
  the field as a labelled assumed-basis match, never a classification.

## 6. Expected screenshots after correction (fresh Garden case)

1. **Explorer stats:** Needs review · ≥ 25% · People assessed 4 · Provisional UBOs 0 (plus
   "Assumed-basis matches 2" if approved).
2. **Identified UBO candidates:**
   - "No natural person is formally classified as a provisional UBO; 2 meet the threshold
     only on an assumed basis (below)."
   - A labelled list: ABCD123 51.14% (LOCAL_POC_ASSUMED_EQUAL_UNITS) and LIM CHOON HUAT
     37.5% (LOCAL_SYNTHETIC_RELATIONSHIP), each with REVIEW_REQUIRED.
   - The existing "UBO determination requires review" warning.
3. **Hierarchy:** unchanged. "0 provisional UBOs" chip, rows not highlighted as UBOs, same
   percentages and source labels.
4. **Selected holder ABCD123:**
   - "Threshold comparison … → INDETERMINATE", classification REVIEW_REQUIRED;
   - the new row "Assumed-basis comparison ≥ 25% → MET (not a classification)";
   - "Calculation: 62.5% × 81.82% = 51.14%".
5. **Option B:** unchanged. Keep current evidence gives 409, readiness stays blocked, no
   GoldTier.
6. **Five-layer case:** BEATRICE LIM and DIANA KOH listed as assumed-basis matches. Provisional
   UBOs stays 0 before any creator decision.

## 7. Decisions needed (no new business rule or source authority)

The field and its meaning already exist (D-077/D-081, profile `:358-361`). The correction
is presentation only. It needs these owner decisions:
- **U1. Authorize the change to the Ownership & UBO frontend and the shared type.** This
  project has kept that UI unchanged without explicit owner authorization.
- **U2. Scope.**
  - The field is shared by the D-077 overlay basis and the D-081 POC basis. Should the
    block show for every hybrid case (recommended; labelled by link provenance), or only
    when POC links are present?
  - `UboSummary` also renders on Review & Send. Show the block there too (recommended,
    because it is honest about the gap), or only in the explorer?
- **U3. Wording.** Recommended label: "Meets the threshold on an assumed basis — review
  required … not a verified or provisional UBO". Avoid "UBO" as a noun for these people.
- **U4. The optional stat cell** "Assumed-basis matches".

Nothing in readiness, Option B, the comparator, the engine, discovery, evidence authority,
reconciliation or GoldTier changes.
