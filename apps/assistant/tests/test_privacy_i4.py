"""D-142 I-4: regressions for the C10 I-3 re-review's P2-1 and P2-2
(outputs/c10-final-review-7dcc2e15/review/C10_I3_REREVIEW.md).

    P2-2  a person's name held only in a blocker's differences, a discrepancy's values or
          decided value, a document field to review (or that field's document), or an ownership
          relationship beyond the shown links is a known identity, so it leaves as a typed
          placeholder on the Claude and OpenRouter request shapes, complete and streamed
    P2-1  dashboard insights never reach an API-key model, so no staff name the browser sends
          leaves this machine; the local model still writes them, unchanged

Invented values only; no key, no network, no paid call.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from ai_assistant import controlled_intents as ci
from ai_assistant import copilot
from ai_assistant import privacy_boundary as pb
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.dashboard_insights import DashboardInsights, InsightsRequest
from ai_assistant.main import FIELD_LABELS
from ai_assistant.prompts import build_messages
from ai_assistant.provider_payload import provider_facts
from tests.test_dashboard_insights import LOCAL_URL, LocalModel, PaidModel

# Name-capable service words (the residual list) and ordinary unknown names.
DIFFERENCE_REGISTRY = "MAX LOW"
DIFFERENCE_DOCUMENT = "May Page"
DISCREPANCY_VALUE = "Mark Long"
DISCREPANCY_DECIDED = "MAX PAGE"
REVIEW_VALUE = "Odile Brennan"
REVIEW_ACRA = "Ingrid Solberg"
REVIEW_DOCUMENT = "PAGE MAX scan.pdf"
BEYOND_LINKS = "PAGE LOW"
REPLY = json.dumps({"summary": "", "notes": [{"id": "F1", "text": "Workload is uneven."}]})
NAMES = (
    DIFFERENCE_REGISTRY,
    DIFFERENCE_DOCUMENT,
    DISCREPANCY_VALUE,
    DISCREPANCY_DECIDED,
    REVIEW_VALUE,
    REVIEW_DOCUMENT,
    BEYOND_LINKS,
)


def _summary() -> dict[str, Any]:
    return {
        "case": {
            "case_id": "c-1",
            "entity": {"legal_name": "SYNTHETIC CO PTE. LTD.", "registration_number": "200000001Z"},
        },
        "status": "WAITING_FOR_HUMAN",
        "evidence_decision_authorized": True,
        "interventions": [{"intervention_id": "x-1", "blocker_code": "DOC_MISMATCH"}],
        "active_exceptions": [
            {
                "exception_id": "x-1",
                "blocker_code": "DOC_MISMATCH",
                "evidence": [
                    {
                        "field_key": "director_name",
                        "registry_value": DIFFERENCE_REGISTRY,
                        "document_value": DIFFERENCE_DOCUMENT,
                        "comparison": "MISMATCH",
                    }
                ],
            }
        ],
        "reconciliation": {
            "discrepancies": [
                {
                    "field_name": "legal_name",
                    "status": "OPEN",
                    "observations": [
                        {
                            "normalized_value": DISCREPANCY_VALUE,
                            "source_kind": "REGISTRY",
                            "source_system": "ACRA",
                            "environment": "MOCK",
                        }
                    ],
                    "decision": {"action": "SELECT", "selected_value": DISCREPANCY_DECIDED},
                }
            ]
        },
    }


def _documents() -> list[dict[str, Any]]:
    # Six shown documents, then a seventh (beyond the shown list) whose field awaits review.
    rows: list[dict[str, Any]] = [
        {"display_name": f"doc{i}.pdf", "profile": "BIZFILE", "state": "PROCESSED", "fields": []}
        for i in range(6)
    ]
    rows.append(
        {
            "display_name": REVIEW_DOCUMENT,
            "profile": "BIZFILE",
            "state": "REVIEW_REQUIRED",
            "review_source_fingerprint": "f" * 64,
            "fields": [
                {
                    "field_key": "legal_name",
                    "review_status": "PENDING",
                    "original_extracted_value": REVIEW_VALUE,
                    "canonical_value": REVIEW_ACRA,
                }
            ],
        }
    )
    return rows


def _ownership() -> dict[str, Any]:
    # One path of nine links: the relationships hold all nine, the links the first eight.
    chain = [f"HOLDCO {i} PTE. LTD." for i in range(9)] + [BEYOND_LINKS]
    edges = [
        {
            "parent_display_name": chain[i + 1],
            "child_display_name": chain[i],
            "ownership_percent": "100",
            "parent_party_id": f"p{i + 1}",
            "child_party_id": f"p{i}",
        }
        for i in range(9)
    ]
    return copilot.ownership_facts(
        {
            "candidates": [
                {
                    "party": {"display_name": "SYNTHETIC ROOT HOLDER", "party_id": "r"},
                    "paths": [{"is_direct": False, "edges": edges}],
                    "classification": "REVIEW_REQUIRED",
                }
            ]
        }
    )


def _facts() -> dict[str, Any]:
    actor = {"profile": {"display_name": "Synthetic Viewer", "role": "RM", "user_id": "u1"}}
    facts = build_case_facts(CaseSnapshot(_summary(), _documents(), actor))
    facts["ownership"] = _ownership()
    return facts


def _external(builder: Any, facts: dict[str, Any]) -> list[dict[str, str]]:
    external = pb.minimise_facts(provider_facts(facts), known_labels=FIELD_LABELS)
    return builder(external, [], ci.CANONICAL[ci.BLOCKERS])


def _anthropic(messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
    return {
        "model": "claude-sonnet-5-5",
        "max_tokens": 600,
        "system": [
            {"type": "text", "text": m["content"]} for m in messages if m["role"] == "system"
        ],
        "messages": [
            {"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"
        ],
        "stream": stream,
    }


def _openai(messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
    return {
        "model": "openai/gpt-oss-120b",
        "messages": [dict(m) for m in messages],
        "temperature": 0.2,
        "max_tokens": 600,
        "stream": stream,
    }


def _core(name: str) -> str:
    return name.removesuffix(" scan.pdf")


def test_p2_2_every_value_of_those_fields_is_a_known_identity() -> None:
    known = {item[-1] for item in pb.identities_from_facts(_facts())}
    for name in (*NAMES, REVIEW_ACRA):
        assert name in known, name


def test_p2_2_the_older_evidence_key_is_still_read() -> None:
    facts = {"blockers": [{"evidence": [{"field": "director name", "registry_value": "MAX LOW"}]}]}
    assert ("PERSON", "MAX LOW") in pb.identities_from_facts(facts)


@pytest.mark.parametrize(
    "builder", [build_messages, copilot.build_messages], ids=["case", "copilot"]
)
def test_p2_2_the_names_are_in_the_built_prompt(builder: Any) -> None:
    # The fixture is meaningful: each name (or, for the case prompt, the fields it uses) is
    # really in what an external model would be given before protection.
    text = json.dumps(_external(builder, _facts()), ensure_ascii=False)
    assert DIFFERENCE_REGISTRY in text and DISCREPANCY_DECIDED in text
    if builder is copilot.build_messages:
        assert all(_core(name) in text for name in NAMES)


@pytest.mark.parametrize(
    "builder", [build_messages, copilot.build_messages], ids=["case", "copilot"]
)
@pytest.mark.parametrize("shape", [_anthropic, _openai], ids=["anthropic", "openai"])
@pytest.mark.parametrize("stream", [False, True], ids=["complete", "stream"])
def test_p2_2_the_names_leave_as_placeholders_and_the_wire_check_passes(
    builder: Any, shape: Any, stream: bool
) -> None:
    facts = _facts()
    messages = pb.admit(
        _external(builder, facts), pb.identities_from_facts(facts), person_written=False
    )
    protected = pb.outbound(messages)
    try:
        assert pb.clear_call(protected.messages)
        body = json.dumps(shape(list(protected.messages), stream)).encode("utf-8")
        pb.verify_wire(protected.messages, body)  # raises PrivacyRefused if refused
        wire = body.decode("utf-8").casefold()
        for name in NAMES:
            assert _core(name).casefold() not in wire, name
        assert "[PERSON-" in body.decode("utf-8")
    finally:
        pb.release(protected)


def _insights(busiest: str, lightest: str) -> InsightsRequest:
    return InsightsRequest.model_validate(
        {
            "period": "Last 30 days",
            "findings": [
                {
                    "id": "F1",
                    "topic": "WORKLOAD",
                    "severity": "INFO",
                    "actionable": False,
                    "facts": {"busiest": busiest, "busiest_open": 9, "lightest": lightest},
                }
            ],
        }
    )


@pytest.mark.parametrize(
    ("busiest", "lightest"), [("MAX LOW", "May Page"), ("Mark Long", "Odile Brennan")]
)
def test_p2_1_insights_never_call_an_api_key_model(busiest: str, lightest: str) -> None:
    request = _insights(busiest, lightest)
    paid, local = PaidModel(answer=REPLY), LocalModel(answer=REPLY)
    assert DashboardInsights.kind(paid, "https://api.example.com", external=True) is None
    assert DashboardInsights.candidates(
        (paid, "https://api.example.com"), (local, LOCAL_URL), external=True
    ) == [(local, False)]
    result = DashboardInsights().write(
        "u", request, paid, "https://api.example.com", fallback=(local, LOCAL_URL), external=True
    )
    assert result.model == "local-model" and paid.calls == []
    # Without a local model nothing is written: the route answers "unavailable".
    with pytest.raises(Exception, match="no usable model"):
        DashboardInsights().write("u", request, paid, "https://api.example.com", external=True)
    assert paid.calls == []


def test_p2_1_a_local_loopback_model_still_gets_the_findings_unchanged() -> None:
    request = _insights("MAX LOW", "Odile Brennan")
    local = LocalModel(answer=REPLY)
    assert DashboardInsights.kind(local, LOCAL_URL, external=True) == "local"
    assert DashboardInsights.kind(local, LOCAL_URL, external=False) == "local"
    result = DashboardInsights().write("u", request, local, LOCAL_URL)
    assert result.model == "local-model"
    sent = json.dumps(local.calls, ensure_ascii=False)
    assert "MAX LOW" in sent and "Odile Brennan" in sent


def test_p2_2_a_local_model_keeps_its_case_facts() -> None:
    # Local models are unchanged: their prompt is built from the facts as they are.
    facts = _facts()
    text = json.dumps(build_messages(pb.strip_entity_refs(facts), [], "Who?"), ensure_ascii=False)
    assert DIFFERENCE_REGISTRY in text and DISCREPANCY_DECIDED in text
