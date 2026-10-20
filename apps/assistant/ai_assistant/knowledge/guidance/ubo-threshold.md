---
id: guidance.ubo-threshold
title: How ultimate beneficial owners are identified
blocker_codes: OWNERSHIP_REQUIRED, OWNERSHIP_ANALYSIS_INCOMPLETE, OWNERSHIP_REVIEW_REQUIRED
fields: ownership
stages: Ownership & UBO
source: docs/decisions/DECISION_LOG.md#D-062, docs/decisions/DECISION_LOG.md#D-010, apps/backend/app/services/ownership_analysis.py
illustrative: false
---
A person is a provisional UBO candidate when their aggregated ownership is 25% or more (greater than or equal to 25%). The sponsor confirmed this default threshold and comparator.

The calculation is deterministic and exact; AI never decides it. If ownership evidence is incomplete, loops back on itself or is too deep, everyone is marked for a person to review instead of being guessed.

Legal or control tests and production UBO policy are not decided in this POC.
