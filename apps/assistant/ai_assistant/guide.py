"""Plain-English wording for the app's own blocker rules and statuses.

These sentences only re-word what the backend's blocker policy already says (see
apps/backend/app/services/blocker_decision_policy.py). They add no business rule: the
backend's own explanation, owner and authorized actions stay the authority.
"""

import re

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

# Reviewed explanation sentences (D-090, ADR-012 Amendment 2, PROPOSED). They are allowed
# lines only when their field or readiness item is on the case (guardrails.allowed_guidance).
# Each one stands alone, holds no case value, never says which source is right, and names
# only sections that exist. "can"/"can mean" sentences give general reasons a value may
# differ; they do not describe something the app worked out for this case.
# (reasons, what to check) for any field where a document value differs from ACRA. The app
# compares each document value with the current ACRA record (backend services/reconciliation.py).
ANY_DIFFERENCE: tuple[tuple[str, ...], tuple[str, ...]] = (
    (
        "The app compares the value read from a document with the current ACRA record.",
        "A difference between a document and ACRA can come from a reading error, an old "
        "document or a real change.",
    ),
    (
        "Before choosing a value, compare what was read with the document itself.",
        "Choosing a value is not official verification of either source.",
    ),
)
# Keyed by FIELD_LABEL values. Documents carry no issue date in this app, so the address check
# names the document type and company, not the date.
FIELD_DIFFERENCE: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "registered address": (
        (
            "A different registered address can mean the document is older than the current "
            "ACRA record, or the company has moved.",
        ),
        (
            "Before choosing an address, check the type of the document and which company it "
            "is for.",
        ),
    ),
    "legal name": (
        ("A different company name can be a former name, a trading name or a reading error.",),
        (),
    ),
    "UEN": (
        (
            "A different UEN can come from a reading error or a document that belongs to "
            "another company.",
        ),
        ("Before choosing a UEN, check that the document belongs to this company.",),
    ),
}
# Keyed by readiness code (READINESS_NEEDS). Document review: backend
# services/clm_orchestration.py readiness (REVIEW_REQUIRED documents, low confidence, missing
# required fields). Ownership: domain/ownership.py and services/manual_ownership_evidence.py.
READINESS_EXPLANATIONS: dict[str, tuple[str, ...]] = {
    "DOCUMENT_REVIEW_INCOMPLETE": (
        "When a person reviews a document, every field read from it needs a review decision.",
        "A field read with low confidence, or a required field that could not be read, keeps "
        "the document review open.",
    ),
    "OWNERSHIP_REQUIRED": (
        "The UBO check needs the company's owners and each owner's economic interest in percent.",
        "Ownership evidence can come from the registry, an uploaded ownership document or a "
        "manual ownership declaration.",
        "A manual ownership declaration needs a reviewed current document first.",
    ),
}


# Fixed catalog lines (D-090, PROPOSED), each offered only under its condition
# (guardrails.allowed_guidance). The approval line is worded so it passes the sentence checks
# ("<action> is not offered" is the recognised negation).
NOT_READY = "This case is not ready for GoldTier submission yet."
APPROVAL_NOT_OFFERED = "Approving the case is not offered to you on this case."
NO_CONTACT = "The case data does not name a contact for this."
OUT_OF_SCOPE = "I can't answer that from this case's data."
# Owner-approved wording (Phase B, D-092 proposed). Offered only while the case has no
# ownership analysis (guardrails.ubo_check_not_run): it names no one and does not say there
# are no UBOs.
UBO_CHECK_NOT_RUN = "This case cannot name any UBOs yet because the UBO check has not run."
# Owner-approved wording (Phase B, D-092 proposed). Allowed only while ownership is not
# complete and no action that completes it is offered (guardrails.ubo_completion_not_offered);
# topic-only: the model sees it only in the steering message for a request to complete it.
UBO_COMPLETION_NOT_OFFERED = "Marking the UBO check as complete is not offered to you on this case."
# Owner-approved wording (Phase B answer quality, D-092 P11 to P14 proposed), each allowed only
# under its condition in guardrails.allowed_guidance and topic-only.
# Directors (P12). The app reads only legal name, UEN, address and country from documents
# (backend DocumentFieldKey) and never reconciles directors. DIRECTOR_DIFFERENCE_* are general
# and conditional: they never say that a difference exists on this case.
DIRECTORS_NOT_READ = (
    "The app does not read directors from uploaded documents, so it does not compare directors "
    "between a document and ACRA."
)
OFFICERS_NOT_RETRIEVED = (
    "Officer (director) records were not retrieved from the registry for this case."
)
DIRECTOR_DIFFERENCE_CHECK = (
    "If a document and the registry differ on directors, check the document's type, date and "
    "which company it is for."
)
DIRECTOR_DIFFERENCE_REASONS = (
    "A director difference can come from a recent appointment or resignation, or from an "
    "out-of-date document."
)
# Entity status (P13): the company's registry status, not the registry connection.
ENTITY_STATUS_LIVE = (
    'The entity status "LIVE" is the company\'s registration status in the registry record, '
    "not a live connection to ACRA."
)
# UEN (P13).
UEN_MEANING = (
    "A UEN (Unique Entity Number) identifies an entity registered in Singapore. The number alone "
    "does not confirm its legal name, address or other company details."
)
# GoldTier handoff (P14). Review & Send is the final local human approval (D-062); the early
# GoldTier search is read-only; the ledger keeps the submission result and readback.
SEND_BEFORE_SUBMISSION = (
    'A person must confirm Send in "Final review & send" before the final GoldTier submission; '
    "the app may search GoldTier for an existing customer earlier."
)
SUBMISSION_RESULT_KEPT = (
    "When a GoldTier submission is confirmed, the app retains the submission result and "
    'required customer readback. The result is shown in "GoldTier Details & Status".'
)
SENDING_IS_NOT_APPROVAL = (
    "Sending a case does not mean GoldTier has approved the customer or that KYC is complete. "
    "Those outcomes are not confirmed by this application."
)


def officers_empty_line(environment: str) -> str:
    """D2 (P12): the registry officer lookup returned no records, in that registry environment."""

    return (
        f"The ACRA ({environment}) result for this case has no officer (director) records; "
        "this does not show that the company has no directors."
    )


_OFFICERS_EMPTY = re.compile(
    r"^The ACRA \((?:MOCK|LOCAL|SANDBOX|PARTIAL|DORMANT)\) result for this case has no officer "
    r"\(director\) records; this does not show that the company has no directors\.$"
)


# D-095 (project-defined wording, pending owner acceptance): one current officer that the
# case's own non-live ACRA officer lookup returned, named exactly as the registry record names
# it; never a document's or a person's claim. (Comments, not docstrings, here: this module's
# strings are part of the D-094 question vocabulary.)
def officer_record_line(environment: str, name: str, role: str) -> str:
    return (
        f"The ACRA ({environment}) record for this case lists {name} as an officer (role: {role})."
    )


_OFFICER_RECORD = re.compile(
    r"^The ACRA \((?:MOCK|LOCAL|SANDBOX|PARTIAL|DORMANT)\) record for this case lists .+ as an "
    r"officer \(role: [^()]{1,40}\)\.$"
)

# Allowed lines the model is shown only in a QUESTION TOPIC message, never in the case facts
# every question carries (keeps the everyday prompt unchanged).
TOPIC_ONLY_LINES = frozenset(
    {
        UBO_COMPLETION_NOT_OFFERED,
        DIRECTORS_NOT_READ,
        OFFICERS_NOT_RETRIEVED,
        DIRECTOR_DIFFERENCE_CHECK,
        DIRECTOR_DIFFERENCE_REASONS,
        ENTITY_STATUS_LIVE,
        UEN_MEANING,
        SEND_BEFORE_SUBMISSION,
        SUBMISSION_RESULT_KEPT,
        SENDING_IS_NOT_APPROVAL,
    }
)


def is_topic_only(line: str) -> bool:
    """A topic-only line, including the officer line filled with its environment."""

    return (
        line in TOPIC_ONLY_LINES
        or _OFFICERS_EMPTY.match(line) is not None
        or _OFFICER_RECORD.match(line) is not None
    )


MOCK_NOT_LIVE = (
    "Mock, Local and Sandbox evidence do not establish Live integration or KYC approval."
)


def who_resolves_line(item: str, who: str) -> str:
    """Who handles a blocker, as the backend's blocker policy names the owner."""

    return f"{item}: this is for {who}."


def difference_line(row: dict[str, object]) -> str:
    """One difference on a blocker, in the wording the case-data answer uses."""

    return (
        f'{sentence_case(str(row["field"]))}: ACRA says "{row.get("registry_value")}", '
        f'the document says "{row.get("document_value")}".'
    )


def difference_explanations(field: str) -> tuple[list[str], list[str]]:
    """(reasons, what to check) for a difference in ``field``: the field's own, then general."""

    reasons, checks = FIELD_DIFFERENCE.get(field, ((), ()))
    return [*reasons, *ANY_DIFFERENCE[0]], [*checks, *ANY_DIFFERENCE[1]]


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
