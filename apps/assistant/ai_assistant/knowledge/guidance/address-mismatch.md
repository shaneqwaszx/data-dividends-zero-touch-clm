---
id: guidance.address-mismatch
title: Registered address in a document differs from ACRA
blocker_codes: DOCUMENT_SOURCE_CONFLICT, SOURCE_CONFLICT_REQUIRES_POLICY
fields: registered_address
stages: Document verification, Data reconciliation
source: docs/decisions/DECISION_LOG.md#D-030, docs/decisions/DECISION_LOG.md#D-025
illustrative: false
---
When an uploaded document shows a different registered address from ACRA, the app does not pick one automatically. The difference stays open until a person decides.

For an address, the only source decision offered is "Keep registry value". It keeps ACRA's address for the case and records the decision; it does not rewrite what the document says, and it does not clear any other blocker on the case. "Use document value" is not offered for addresses in this POC.

If the document is the problem (for example it was read wrongly, or it is out of date), review the document fields or upload a replacement document.

A Certificate of Incorporation that simply does not show an address is not a conflict: the address then comes from ACRA only.
