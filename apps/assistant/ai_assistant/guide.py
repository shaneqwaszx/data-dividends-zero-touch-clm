"""Plain-English wording for the app's own blocker rules and statuses.

These sentences only re-word what the backend's blocker policy already says (see
apps/backend/app/services/blocker_decision_policy.py). They add no business rule: the
backend's own explanation, owner and authorized actions stay the authority.
"""

from .instructions import case_page_terms

AUTOMATION_STATUS = {
    "PENDING_INPUTS": "waiting for required inputs",
    "RUNNING": "running automatically",
    "WAITING_FOR_REVIEW": "paused, waiting for a person to review something",
    "RESUMING": "resuming",
    "RECOVERY_PENDING": "waiting for a recovery step",
    "COMPLETED": "completed",
    "TECHNICAL_FAILURE": "stopped safely because of a system problem",
}

STEP_STATUS = {
    "COMPLETE": "done",
    "IN_PROGRESS": "in progress",
    "REVIEW_REQUIRED": "needs review",
    "BLOCKED": "blocked",
    "FAILED": "failed",
    "NOT_REACHED": "not reached yet",
    "SKIPPED": "skipped",
    "EMPTY": "nothing to process",
    "UNSUPPORTED": "not supported",
}

OWNER = {
    "CASE_OPERATOR": "you (the person running this case)",
    "DOCUMENT_REVIEW_OWNER": "the document reviewer",
    "IDENTITY_REVIEW_OWNER": "the identity reviewer",
    "REGISTRY_INTEGRATION_OWNER": "the registry (ACRA) integration owner",
    "OWNERSHIP_REVIEW_OWNER": "the ownership / UBO reviewer",
    "POLICY_OWNER": "the policy owner",
    "TARGET_OPERATIONS_OWNER": "GoldTier operations (a Director)",
    "TARGET_PROVIDER_OWNER": "the GoldTier provider owner",
}

# Keyed by the backend rule_version recorded on each blocker decision.
RULE_PLAIN = {
    "BPD-IDENTITY-1": "The company details entered at the start (name, UEN or country) could "
    "not be confirmed, so they need to be checked or corrected.",
    "BPD-REGISTRY-RECTIFICATION-1": "A re-check against the registry did not finish, so the "
    "company's registry details are not confirmed yet.",
    "BPD-CANONICAL-INCOMPLETE-1": "The registry record is missing details the app needs "
    "before it can continue.",
    "BPD-JURISDICTION-1": "The app could not work out, or got conflicting answers about, "
    "which country this company is registered in.",
    "BPD-REGISTRY-PROVIDER-1": "There is no registry connection for this company's country. "
    "Only Singapore (ACRA) is supported.",
    "BPD-REGISTRY-EVIDENCE-1": "The registry reply was missing information the app expected.",
    "BPD-REGISTRY-REVIEW-1": "The registry information is not clear enough for the app to "
    "decide automatically.",
    "BPD-REGISTRY-FAILURE-1": "The registry check failed and this cannot be skipped.",
    "BPD-DOCUMENT-REQUIRED-1": "A supporting document has to be uploaded before the document "
    "checks can run.",
    "BPD-DOCUMENT-REPLACEMENT-1": "A document needs to be replaced before the case can continue.",
    "BPD-DOCUMENT-REVIEW-1": "An uploaded document needs to be reviewed or replaced before it "
    "can be used.",
    "BPD-DOCUMENT-PROCESSING-1": "A document is still being processed.",
    "BPD-RECONCILIATION-CONFLICT-1": "A value in an uploaded document is different from the "
    "official registry (ACRA) value, so a person has to decide which one to use.",
    "BPD-RECONCILIATION-INVALID-1": "The comparison between the documents and the registry is "
    "not valid, so no decision can be made from it.",
    "BPD-OWNERSHIP-REQUIRED-1": "Ownership information (shareholders) is needed before the "
    "app can work out who the UBOs are.",
    "BPD-OWNERSHIP-REVIEW-1": "The ownership information needs a person to review it.",
    "BPD-OWNERSHIP-FAILURE-1": "The ownership calculation failed and cannot be skipped.",
    "BPD-SEARCH-AMBIGUITY-1": "GoldTier may already have this customer, so a person has to "
    "confirm whether it is the same company before anything is created.",
    "BPD-SEARCH-FAILURE-1": "The GoldTier customer search did not work, so the app cannot tell "
    "yet whether this customer already exists.",
    "BPD-ENTITY-REVIEW-1": "The extra checks on the company's identity were unclear.",
    "BPD-MOCK-RISK-1": "The demo risk check flagged this case for review. It is not a real "
    "compliance decision.",
    "BPD-TARGET-CLASSIFICATION-1": "The GoldTier customer classification (such as KYC customer "
    "type and client segment) has to be chosen before review.",
    "BPD-TARGET-CONFIRMATION-1": "The case needs a final confirmation before anything is sent "
    "to GoldTier.",
    "BPD-EXISTING-PARTY-1": "GoldTier already has a matching customer, so a person has to "
    "review it before continuing.",
    "BPD-TARGET-PARTIAL-1": "Only part of the GoldTier submission finished, so it needs review.",
    "BPD-TARGET-CONTRACT-1": "GoldTier replied in a way the app does not accept, so it needs "
    "review.",
    "BPD-TARGET-UNCERTAIN-1": "The app sent something to GoldTier but did not get a reply, so it "
    "does not know whether it worked. It will not resend; it has to be checked in GoldTier.",
    "BPD-TARGET-FINALIZATION-1": "GoldTier finished, but the app still has to record the result.",
}

# The case page's own section titles (apps/frontend/src/pages/CaseDetail.tsx).
CASE_PAGE_SECTIONS = (
    "Existing-customer search",
    "Registry verification",
    "Document verification",
    "Ownership & UBO",
    "GoldTier Details & Status",
    "Final review & send",
)

# Blocker codes the backend handles as ONE issue (apps/backend/app/services/
# blocker_decision_policy.py groups them under one rule), so the RM is told about it once.
SAME_ISSUE: tuple[frozenset[str], ...] = (
    frozenset({"DOCUMENT_SOURCE_CONFLICT", "SOURCE_CONFLICT_REQUIRES_POLICY"}),
)

# Where a blocker is handled when READINESS_NEEDS has no entry for its code. Checked
# against apps/frontend/src/pages/CaseDetail.tsx: the source-decision panel
# (BlockerDecisionReview) sits inside the Document verification stage.
BLOCKER_SECTIONS: dict[str, str] = {
    "DOCUMENT_SOURCE_CONFLICT": "Document verification",
}

# The backend readiness check's open items (ClmBlockerCode), re-worded, with the case
# page section where each one is handled.
READINESS_NEEDS: dict[str, tuple[str, str]] = {
    "REGISTRY_NOT_READY": ("The ACRA registry check has not finished.", "Registry verification"),
    "REGISTRY_FAILED": ("The ACRA registry check failed.", "Registry verification"),
    "CANONICAL_DATA_INVALID": (
        "The company details from the registry are not valid.",
        "Registry verification",
    ),
    "DOCUMENT_REQUIRED": (
        "No supporting company document has been uploaded yet. At least one is needed "
        "before the document checks can run.",
        "Document verification",
    ),
    "DOCUMENT_PROCESSING": ("Uploaded documents are still being read.", "Document verification"),
    "DOCUMENT_REVIEW_INCOMPLETE": (
        "The document review is not finished.",
        "Document verification",
    ),
    "DOCUMENT_PROCESSING_FAILED": (
        "A document could not be read and needs to be replaced.",
        "Document verification",
    ),
    "SOURCE_CONFLICT_REQUIRES_POLICY": (
        "A document value differs from ACRA and needs a decision.",
        "Document verification",
    ),
    "OWNERSHIP_REQUIRED": (
        "Ownership (shareholder) evidence is needed before the UBO check can run.",
        "Ownership & UBO",
    ),
    "OWNERSHIP_ANALYSIS_INCOMPLETE": ("The UBO check has not finished.", "Ownership & UBO"),
    "OWNERSHIP_REVIEW_REQUIRED": ("The ownership result needs review.", "Ownership & UBO"),
    "OWNERSHIP_ANALYSIS_FAILED": ("The UBO check failed.", "Ownership & UBO"),
    "GOLDTIER_SEARCH_REQUIRED": (
        "The GoldTier existing-customer search has not run.",
        "Existing-customer search",
    ),
    "GOLDTIER_SEARCH_REVIEW_REQUIRED": (
        "GoldTier may already have this customer; this needs confirming.",
        "Existing-customer search",
    ),
    "GOLDTIER_SEARCH_FAILED": ("The GoldTier customer search failed.", "Existing-customer search"),
    "GOLDTIER_SEARCH_STALE": (
        "The GoldTier customer search is out of date and must be re-run.",
        "Existing-customer search",
    ),
    "GOLDTIER_CLASSIFICATION_REQUIRED": (
        "The GoldTier customer classification (KYC customer type and client segment) "
        "must be chosen.",
        "GoldTier Details & Status",
    ),
}

READINESS_PLAIN = {code: need for code, (need, _) in READINESS_NEEDS.items()}

FIELD_LABEL = {
    "registered_address": "registered address",
    "registration_number": "UEN",
    "legal_name": "legal name",
    "country_of_incorporation": "country of incorporation",
}


# Labels shown on the case page's document check, explained in plain words.
# The case page's "Review blocker decisions" panel. Its two decision groups answer different
# questions, so the AI Assistant must not merge them. Labels are exactly as the page shows them
# (apps/frontend/src/pages/BlockerDecisionReview.tsx); meanings follow how the backend uses each
# review decision (services/document_processing.py, services/reconciliation.py).
REVIEW_PANEL = "Review blocker decisions"
DOCUMENT_REVIEW_GROUP = "Review extracted document fields"
SOURCE_DECISION_GROUP = "Compare registry and document values"
DOCUMENT_REVIEW_CHOICES = {
    "Accept document suggestion": (
        "confirms the system read this value correctly from the document; the value is then "
        "still compared with ACRA"
    ),
    "Reject document suggestion": (
        "says the value read from the document should not be used, so the case has no document "
        "value for this field"
    ),
    "Record correction": (
        "lets the reviewer type the value the document really shows; it replaces what the "
        "system read and is compared with ACRA again"
    ),
}

# Meanings of case page labels live in instructions/case_page_terms.md.
SCREEN_TERMS = case_page_terms()


def sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:]


def field_label(name: str | None) -> str:
    if not name:
        return "field"
    return FIELD_LABEL.get(name, name.replace("_", " "))
