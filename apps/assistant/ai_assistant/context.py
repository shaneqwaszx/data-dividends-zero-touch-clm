"""Turn the CLM API responses into a small set of case facts for the AI assistant.

The backend is the authority: blockers, owners, next steps and allowed actions are copied
from what it already computed, never re-derived here. Every fact carries where it came
from. Text read out of uploaded documents is marked as untrusted document content.
"""

import re
from typing import Any

from .clm_client import CaseSnapshot
from .guide import (
    AUTOMATION_STATUS,
    BLOCKER_SECTIONS,
    CASE_PAGE_SECTIONS,
    DOCUMENT_REVIEW_CHOICES,
    DOCUMENT_REVIEW_GROUP,
    OWNER,
    READINESS_NEEDS,
    REVIEW_PANEL,
    RULE_PLAIN,
    SCREEN_TERMS,
    SOURCE_DECISION_GROUP,
    STEP_REVIEW_ADVISED,
    STEP_STATUS,
    field_label,
)

MAX_TIMELINE = 10
MAX_DOCUMENTS = 6
MAX_FIELDS_PER_DOCUMENT = 8


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] if text else None


def _address(value: Any) -> str | None:
    address = _dict(value)
    parts = [
        address.get(key)
        for key in ("address_line_1", "address_line_2", "postal_code", "country_code")
    ]
    joined = ", ".join(str(part) for part in parts if part)
    return joined or None


def _source_label(source: Any) -> str | None:
    data = _dict(source)
    system = data.get("source_system")
    if not system:
        return None
    environment = data.get("environment")
    label = f"{system} ({environment})" if environment else str(system)
    retrieved = readable_time(data.get("retrieved_at"))
    return f"{label}, retrieved {retrieved}" if retrieved else label


def readable_time(value: Any) -> str | None:
    """'2026-10-12T18:08:11.4Z' -> '12 Oct 2026, 18:08 UTC' (left as is if unreadable)."""

    if not value:
        return None
    from datetime import datetime

    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    zone = "UTC" if moment.utcoffset() is not None and not moment.utcoffset() else ""
    return f"{moment.day} {moment:%b %Y, %H:%M} {zone}".strip()


def _company(summary: dict[str, Any]) -> dict[str, Any]:
    case = _dict(summary.get("case"))
    entity = _dict(case.get("entity"))
    initial = _dict(case.get("initial_identity"))
    source = _source_label(entity.get("source"))
    return {
        "legal_name": entity.get("legal_name") or initial.get("legal_name"),
        "uen": entity.get("registration_number") or case.get("requested_uen"),
        "country": entity.get("country_of_incorporation")
        or initial.get("country_of_incorporation"),
        "entity_status": entity.get("entity_status"),
        "registration_date": entity.get("registration_date"),
        "registered_address": _address(entity.get("registered_address")),
        "source": source or "Details entered when the case was created",
    }


def _advisory_review(node: dict[str, Any]) -> bool:
    """D-137: the backend's own flag, only on a complete OWNERSHIP_UBO node."""

    return (
        node.get("advisory_review") is True
        and node.get("node_id") == "OWNERSHIP_UBO"
        and node.get("status") == "COMPLETE"
    )


def _steps(summary: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for node in _list(summary.get("processing_pipeline")):
        data = _dict(node)
        status = str(data.get("status") or "")
        steps.append(
            {
                "step": data.get("label"),
                # D-137: complete for readiness only because the ownership review is advisory.
                "status": STEP_REVIEW_ADVISED
                if _advisory_review(data)
                else STEP_STATUS.get(status, status.lower() or "unknown"),
                "result": _text(data.get("safe_result"), 160),
                "blocker_code": data.get("blocker_code"),
            }
        )
    return steps


def _evidence_for(exception: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in _list(exception.get("evidence")):
        data = _dict(item)
        if not data.get("field_key"):
            continue
        rows.append(
            {
                "field": field_label(data.get("field_key")),
                "registry_value": data.get("registry_value"),
                "document_value": data.get("document_value"),
                "document_confidence": data.get("confidence"),
                "comparison": data.get("comparison"),
            }
        )
    return rows


def _blockers(summary: dict[str, Any]) -> list[dict[str, Any]]:
    exceptions = {
        str(_dict(item).get("exception_id")): _dict(item)
        for item in _list(summary.get("active_exceptions"))
    }
    by_code = {
        str(_dict(item).get("blocker_code")): _dict(item)
        for item in _list(summary.get("active_exceptions"))
    }
    blockers = []
    for item in _list(summary.get("interventions")):
        data = _dict(item)
        decisions = _list(data.get("decisions"))
        metadata = _dict(_dict(decisions[-1]).get("metadata")) if decisions else {}
        rule = metadata.get("rule_version")
        exception = exceptions.get(str(data.get("intervention_id"))) or by_code.get(
            str(data.get("blocker_code")), {}
        )
        blockers.append(
            {
                "title": data.get("title"),
                "stage": data.get("owning_stage_label"),
                "code": data.get("blocker_code"),
                "kind": data.get("blocker_class"),
                "plain_explanation": RULE_PLAIN.get(str(rule)) if rule else None,
                "app_explanation": _text(data.get("explanation")),
                "what_is_needed": [_text(x) for x in _list(data.get("required_evidence_or_input"))],
                "actions_available_to_this_user": [
                    {
                        "label": _dict(action).get("label"),
                        "meaning": _text(_dict(action).get("description"), 200),
                    }
                    for action in _list(data.get("authorized_actions"))
                ],
                "screens_to_open": [
                    _dict(action).get("label") for action in _list(data.get("evidence_actions"))
                ],
                "why_no_action": _text(data.get("no_action_reason")),
                "expected_next_step": _text(data.get("expected_next_step")),
                "who_resolves": OWNER.get(str(metadata.get("owner")), metadata.get("owner")),
                "resolution_condition": _text(data.get("resolution_condition")),
                "differences": _evidence_for(exception),
                "where_on_the_case_page": blocker_section(
                    data.get("blocker_code"), data.get("owning_stage_label")
                ),
            }
        )
    return blockers


def blocker_section(code: object, stage: object) -> str | None:
    """The case page section where this blocker is handled, or None when unknown.

    Only real section titles are returned: a blocker's own title or a backend stage name
    that is not a case page section is never offered as a place to look.
    """

    section = READINESS_NEEDS.get(str(code), ("", ""))[1] or BLOCKER_SECTIONS.get(str(code))
    if section in CASE_PAGE_SECTIONS:
        return section
    return str(stage) if stage in CASE_PAGE_SECTIONS else None


def _discrepancies(summary: dict[str, Any]) -> list[dict[str, Any]]:
    reconciliation = _dict(summary.get("reconciliation"))
    rows = []
    for item in _list(reconciliation.get("discrepancies")):
        data = _dict(item)
        values = []
        for observation in _list(data.get("observations")):
            obs = _dict(observation)
            source = obs.get("document_display_name") or " ".join(
                str(part) for part in (obs.get("source_system"), obs.get("environment")) if part
            )
            values.append(
                {
                    "value": obs.get("normalized_value"),
                    "from": source or obs.get("source_kind"),
                    "source_kind": obs.get("source_kind"),
                    "confidence": obs.get("confidence"),
                }
            )
        decision = _dict(data.get("decision"))
        rows.append(
            {
                "field": field_label(data.get("field_name")),
                "status": data.get("status"),
                "values": values,
                "decision": decision.get("action"),
                "decided_value": decision.get("selected_value"),
            }
        )
    return rows


def _documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    current_documents = [
        document for document in documents if document.get("superseded_by_document_id") is None
    ]
    for document in current_documents[:MAX_DOCUMENTS]:
        fields = []
        for field in _list(document.get("fields"))[:MAX_FIELDS_PER_DOCUMENT]:
            data = _dict(field)
            fields.append(
                {
                    "field": field_label(data.get("field_key")),
                    "value_read_from_document": _text(
                        data.get("normalized_value") or data.get("original_extracted_value"), 160
                    ),
                    "confidence": data.get("confidence"),
                    "compared_with_registry": data.get("comparison_status"),
                    "review_status": data.get("review_status"),
                }
            )
        rows.append(
            {
                "name": document.get("display_name"),
                "detected_type": document.get("profile"),
                "state": document.get("state"),
                "fields": fields,
            }
        )
    return rows


def _document_field_review(
    summary: dict[str, Any], documents: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Document fields this user can review on the case page, and the choices offered.

    Uses the same conditions as the case page's review panel, so the AI Assistant offers
    exactly the choices the RM can see there, no more and no fewer.
    """

    if summary.get("evidence_decision_authorized") is not True:
        return None
    rows = []
    for document in documents:
        if (
            document.get("superseded_by_document_id") is not None
            or document.get("state") != "REVIEW_REQUIRED"
            or document.get("semantic_completion")
            or not document.get("review_source_fingerprint")
        ):
            continue
        for field in _list(document.get("fields")):
            data = _dict(field)
            if data.get("review_status") != "PENDING":
                continue
            choices = [
                label
                for label in DOCUMENT_REVIEW_CHOICES
                if label != "Accept document suggestion"
                or data.get("original_extracted_value") is not None
            ]
            rows.append(
                {
                    "document": document.get("display_name"),
                    "field": field_label(data.get("field_key")),
                    "document_value": _text(data.get("original_extracted_value"), 160),
                    "acra_value": _text(data.get("canonical_value"), 160),
                    "choices": choices,
                }
            )
    if not rows:
        return None
    return {
        "where": f'{REVIEW_PANEL} panel, decision group "{DOCUMENT_REVIEW_GROUP}"',
        "what_it_decides": "whether the system read the document correctly",
        "not_the_same_as": (
            f'the decision group "{SOURCE_DECISION_GROUP}", which decides which value the '
            'case uses (for example "Keep registry value")'
        ),
        "choice_meanings": {
            label: DOCUMENT_REVIEW_CHOICES[label] for label in DOCUMENT_REVIEW_CHOICES
        },
        "fields": rows,
    }


def _timeline(summary: dict[str, Any]) -> list[dict[str, Any]]:
    events = _list(summary.get("timeline"))[-MAX_TIMELINE:]
    return [
        {
            "when": _dict(event).get("timestamp") or _dict(event).get("occurred_at"),
            "what": _text(_dict(event).get("message"), 200),
        }
        for event in events
    ]


def _readiness(summary: dict[str, Any]) -> dict[str, Any]:
    readiness = _dict(_dict(summary.get("clm")).get("readiness"))
    sections = {
        name: _dict(readiness.get(name)).get("status")
        for name in ("registry", "document", "ownership", "goldtier")
        if readiness.get(name) is not None
    }
    # D-137: ownership is READY only because its open review is advisory (D-121).
    if sections.get("ownership") == "READY" and any(
        _advisory_review(_dict(node)) for node in _list(summary.get("processing_pipeline"))
    ):
        sections["ownership"] = "REVIEW_ADVISED"
    return {
        "sections": sections,
        "blockers": _list(readiness.get("blockers")),
        "warnings": _list(readiness.get("warnings")),
    }


# Facts that only choose catalog lines (D-092 P11): never shown to the model and never
# grounding for knowledge text (guardrails.Context), so they cannot vouch for a quoted label.
SELECTION_ONLY_FACTS = ("goldtier_readback", "registry_officers", "registry_officer_records")

# Statuses of the backend's registry operation result (domain RegistryOperationStatus).
_OFFICER_LOOKUP_STATUSES = frozenset(
    {"COMPLETE", "EMPTY", "FAILED", "NOT_ATTEMPTED", "UNSUPPORTED"}
)


def _registry_officers(summary: dict[str, Any]) -> str | None:
    """The status of the registry officer lookup on this case's own registry acquisition
    (D-092 P11), or None. Only the status: never officer names, roles, ids or counts.

    The result must belong to the case's company (same UEN). EMPTY is used only when the
    lookup itself succeeded with no records on a COMPLETE or PARTIAL acquisition, from the same
    registry and environment as the company details; it is never inferred from a failed or
    missing lookup.
    """

    case = _dict(summary.get("case"))
    entity = _dict(case.get("entity"))
    acquisition = _dict(case.get("registry_acquisition"))
    uen = str(entity.get("registration_number") or "").strip().upper()
    if not uen or str(acquisition.get("requested_identifier") or "").strip().upper() != uen:
        return None
    results = [
        _dict(item)
        for item in _list(acquisition.get("operation_results"))
        if _dict(item).get("operation") == "OFFICERS"
    ]
    if len(results) != 1 or results[0].get("status") not in _OFFICER_LOOKUP_STATUSES:
        return None
    result = results[0]
    status = str(result["status"])
    if status == "EMPTY":
        provenance = _dict(result.get("provenance"))
        source = _dict(entity.get("source"))
        if (
            acquisition.get("status") not in ("COMPLETE", "PARTIAL")
            or result.get("error") is not None
            or result.get("record_count") != 0
            or _list(acquisition.get("officers"))
            or not source.get("source_system")
            or provenance.get("provider") != source.get("source_system")
            or provenance.get("environment") != source.get("environment")
        ):
            return None
    return status


# At most this many officers are offered as lines; a longer list offers none.
MAX_OFFICER_RECORDS = 10
_ROLE = re.compile(r"[A-Z_]{1,40}")


def _registry_officer_records(summary: dict[str, Any]) -> list[dict[str, str]] | None:
    """D-095 answer coverage: the current officers (name and role code only) that this case's
    own registry officer lookup returned, or None. Only when the lookup is COMPLETE for the
    case's UEN, the acquisition is COMPLETE or PARTIAL without error, the record count matches,
    and the lookup and every officer come from the same registry and environment as the
    company details. Selection only: the model sees an officer only inside its catalog line."""

    case = _dict(summary.get("case"))
    entity = _dict(case.get("entity"))
    acquisition = _dict(case.get("registry_acquisition"))
    if _registry_officers(summary) != "COMPLETE":
        return None
    result = next(
        _dict(item)
        for item in _list(acquisition.get("operation_results"))
        if _dict(item).get("operation") == "OFFICERS"
    )
    source = _dict(entity.get("source"))
    officers = [_dict(item) for item in _list(acquisition.get("officers"))]

    def same_source(provenance: Any) -> bool:
        data = _dict(provenance)
        return bool(source.get("source_system")) and (
            data.get("provider") == source.get("source_system")
            and data.get("environment") == source.get("environment")
        )

    if (
        acquisition.get("status") not in ("COMPLETE", "PARTIAL")
        or result.get("error") is not None
        or result.get("record_count") != len(officers)
        or not officers
        or len(officers) > MAX_OFFICER_RECORDS
        or not same_source(result.get("provenance"))
        or not all(same_source(item.get("provenance")) for item in officers)
    ):
        return None
    records = []
    for officer in officers:
        if officer.get("cessation_date"):
            continue  # a former officer is not offered as a current one
        name, role = officer.get("name"), officer.get("role")
        if not isinstance(name, str) or not isinstance(role, str) or not _ROLE.fullmatch(role):
            return None
        records.append({"name": " ".join(name.split()), "role": role})
    return records or None


def _goldtier_readback(summary: dict[str, Any]) -> str | None:
    """The status of the GoldTier customer readback operation, when the backend lists one."""

    for item in _list(summary.get("target_operations")):
        if _dict(item).get("operation") == "READBACK":
            status = _dict(item).get("status")
            return str(status) if status else None
    return None


def _still_needed(summary: dict[str, Any]) -> list[dict[str, str]]:
    """What the backend readiness check says is still open, in plain words."""

    readiness = _dict(_dict(summary.get("clm")).get("readiness"))
    needs = []
    for code in _list(readiness.get("blockers")):
        need, section = READINESS_NEEDS.get(str(code), (f"Open readiness item {code}.", ""))
        needs.append({"code": str(code), "what": need, "where_on_the_case_page": section})
    return needs


def build_case_facts(snapshot: CaseSnapshot) -> dict[str, Any]:
    summary = snapshot.summary
    profile = _dict(snapshot.actor.get("profile"))
    status = str(summary.get("status") or "")
    steps = _steps(summary)
    done = sum(1 for step in steps if step["status"] == "done")
    failure = _dict(summary.get("technical_failure"))
    target = _dict(summary.get("target_submission"))
    return {
        "case_id": _dict(summary.get("case")).get("case_id"),
        "viewer": {"name": profile.get("display_name"), "role": profile.get("role")},
        "company": _company(summary),
        "overall": {
            "status": AUTOMATION_STATUS.get(status, status.lower() or "unknown"),
            "current_stage": summary.get("current_stage"),
            "steps_done": done,
            "steps_total": len(steps),
        },
        "steps": steps,
        "blockers": _blockers(summary),
        "still_needed_before_goldtier": _still_needed(summary),
        "case_page_sections": list(CASE_PAGE_SECTIONS),
        "case_page_terms": dict(SCREEN_TERMS),
        "system_problem": (
            {"code": failure.get("code"), "message": _text(failure.get("message"))}
            if failure
            else None
        ),
        "readiness": _readiness(summary),
        "discrepancies": _discrepancies(summary),
        "documents": _documents(snapshot.documents),
        "document_field_review": _document_field_review(summary, snapshot.documents),
        "goldtier": (
            {"state": target.get("state"), "goldtier_id": target.get("goldtier_id")}
            if target
            else None
        ),
        # Used only to choose catalog lines; prompts.facts_for_model does not show them.
        "goldtier_readback": _goldtier_readback(summary),
        "registry_officers": _registry_officers(summary),
        "registry_officer_records": _registry_officer_records(summary),
        "timeline": _timeline(summary),
    }
