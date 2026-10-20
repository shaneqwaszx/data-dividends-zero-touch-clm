---
id: guidance.evidence-score
title: What the evidence score on a document value means
blocker_codes: DOCUMENT_REVIEW_INCOMPLETE
stages: Document verification
source: docs/decisions/DECISION_LOG.md#D-027, apps/backend/app/services/policy_management.py
illustrative: false
---
The evidence score shows how reliably a value was found in a document, from 0 to 1. It is a fixed rule-based score, not a probability and not a measure of agreement with ACRA.

For text read straight from a file: 0.97 when the standard label was found once, 0.90 for an accepted alternative label, 0.40 when the value was ambiguous, 0.00 when it was missing. For scanned pages read by OCR, the score is lowered by the OCR's own confidence.

The policy default for continuing without review is 0.85. Each case keeps the policy that applied when it started, so check the case's own policy if a value was flagged.
