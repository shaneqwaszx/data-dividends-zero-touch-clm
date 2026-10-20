---
id: guidance.legal-name-mismatch
title: Legal name in a document differs from ACRA
blocker_codes: DOCUMENT_SOURCE_CONFLICT, SOURCE_CONFLICT_REQUIRES_POLICY
fields: legal_name
stages: Document verification, Data reconciliation
source: docs/decisions/DECISION_LOG.md#D-030
illustrative: false
---
When a document's legal name differs from ACRA, the difference stays open until a person decides.

Two source decisions can be offered: "Keep registry value" keeps ACRA's name, and "Use document value" uses the name read from the document. "Use document value" is only offered when there is exactly one clear document value that the app can check and apply. Neither choice changes the original ACRA or document evidence.

If a required value is missing, invalid or cannot be checked, a replacement document is needed instead.
