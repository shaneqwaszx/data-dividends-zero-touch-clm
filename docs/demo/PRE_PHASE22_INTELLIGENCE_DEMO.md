# Pre-Phase 22 Advisory Intelligence Demo

This walkthrough is entirely synthetic/local and keeps Phase 22 on hold. It demonstrates
Mock ACRA, local document extraction, the deterministic Decimal ownership engine,
advisory intelligence, the existing Mock GoldTier target, the Attention Queue, and
bounded Case Activity export. It does not demonstrate GoldTier XPI Sandbox, production
ML, legal UBO, compliance risk, assignment/SLA, or final approval.

## Straight-through SME

1. Start the ordinary demo with demo controls enabled and sign in as an authorized
   Alpha user.
2. Open New onboarding and choose **SME straight through with advisory intelligence**.
3. Create the Singapore SME case and upload the existing fictional clean company-profile
   PDF.
4. In Case Detail, show Registry evidence and document/reconciliation evidence as
   **Observed / Mock or Local**.
5. Show ownership paths and provisional candidates as the authoritative local Decimal
   calculation.
6. Show Onboarding intelligence:
   - entity resolution is a project-defined deterministic probability proxy;
   - UBO output is `ML_ASSISTED / NOT_LEGAL_UBO_DETERMINATION`;
   - risk is `MOCK_ADVISORY_RISK / NOT_COMPLIANCE_DECISION` and missing signals are
     explicitly unassessed.
7. Show the completed target result as **Mock GoldTier** only.
8. Open Case Activity, filter by case, inspect `INTELLIGENCE_EVALUATED`, and export the
   current authorized page as CSV.

## Ambiguous entity adverse case

1. Start a fresh case and select **SME ambiguous entity review**.
2. Upload the same fictional clean profile.
3. Confirm the workflow stops at Readiness with
   `ENTITY_RESOLUTION_REVIEW_REQUIRED` before any target call.
4. Open the case from the Attention Queue. Show the two safe candidate IDs, equal
   probability proxies, top contributing features, and synthetic source labels.
5. Explain that no generic Resolve action exists: authoritative corrected evidence or a
   sponsor-approved review policy is required.

## Blocked GoldTier and workbench statements

- This walkthrough intentionally uses the Mock GoldTier path. Separately, the POC has a
  guarded `SANDBOX_PARTIAL` XPI request preview and proved read-only Customer Search.
  That capability is not Live or Production interoperability, and this walkthrough
  performs no GoldTier customer or related-party mutation.
- Assignment, notes, and SLA/due times are unavailable because Q-016 does not authorize
  roles, capabilities, assignees, or mutation history.
- The current workbench expansion is limited to the new typed exception categories,
  existing authorized queue filters/open-case actions, intelligence evidence, activity
  event, and safe CSV export.
