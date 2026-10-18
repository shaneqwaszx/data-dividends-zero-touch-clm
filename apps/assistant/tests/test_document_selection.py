from copy import deepcopy
from typing import Any

import pytest

from ai_assistant.briefing import fallback_answer, suggested_questions
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import (
    MAX_DOCUMENTS,
    MAX_FIELDS_PER_DOCUMENT,
    _documents,
    build_case_facts,
)
from tests.test_ai_assistant import CASE_ID, ME, SUMMARY, FakeBackend, _client


def document(index: int, *, superseded: bool = False) -> dict[str, Any]:
    return {
        "document_id": f"synthetic-{index}",
        "display_name": f"Synthetic document {index}",
        "profile": "PROVISIONAL_CORPORATE",
        "state": "REVIEW_REQUIRED",
        "superseded_by_document_id": f"synthetic-{index + 1}" if superseded else None,
        "supersedes_document_id": f"synthetic-{index - 1}" if index else None,
        "fields": [
            {
                "field_key": "legal_name",
                "normalized_value": f"Synthetic value {field}",
                "original_extracted_value": "Original synthetic value",
                "confidence": 0.85,
                "comparison_status": "MATCH",
                "review_status": "PENDING",
            }
            for field in range(10)
        ],
    }


@pytest.mark.parametrize(
    "indices,expected",
    [
        ([(i, True) for i in range(6)] + [(6, False)], [6]),
        (
            [
                (0, True),
                (1, False),
                (2, True),
                (3, False),
                (4, True),
                (5, False),
                (6, False),
                (7, True),
                (8, False),
                (9, False),
                (10, False),
            ],
            [1, 3, 5, 6, 8, 9],
        ),
        ([(i, False) for i in range(8)], list(range(6))),
        ([(i, False) for i in range(6)], list(range(6))),
        ([], []),
        ([(i, True) for i in range(7)], []),
    ],
)
def test_current_documents_are_selected_before_limit(
    indices: list[tuple[int, bool]], expected: list[int]
) -> None:
    records = [document(i, superseded=old) for i, old in indices]
    original = deepcopy(records)
    rows = _documents(records)
    assert [row["name"] for row in rows] == [f"Synthetic document {i}" for i in expected]
    assert len(rows) <= MAX_DOCUMENTS == 6
    assert records == original


def test_document_projection_preserves_fields_confidence_and_document_provenance() -> None:
    current = document(6)
    current["fields"][0]["normalized_value"] = None
    original = deepcopy(current)
    row = _documents([document(i, superseded=True) for i in range(6)] + [current])[0]
    assert row["name"] == current["display_name"]
    assert row["detected_type"] == current["profile"]
    assert row["state"] == current["state"]
    assert len(row["fields"]) == MAX_FIELDS_PER_DOCUMENT == 8
    assert row["fields"][0] == {
        "field": "legal name",
        "value_read_from_document": "Original synthetic value",
        "confidence": 0.85,
        "compared_with_registry": "MATCH",
        "review_status": "PENDING",
    }
    assert row["fields"][-1]["value_read_from_document"] == "Synthetic value 7"
    assert current == original


def test_seven_records_reach_facts_questions_and_fallback_without_mutation() -> None:
    records = [document(i, superseded=True) for i in range(6)] + [document(6)]
    snapshot = CaseSnapshot(summary=deepcopy(SUMMARY), documents=records, actor=deepcopy(ME))
    original = deepcopy(snapshot)
    facts = build_case_facts(snapshot)
    assert [row["name"] for row in facts["documents"]] == ["Synthetic document 6"]
    assert "What was read from the documents?" in suggested_questions(facts)
    answer = fallback_answer("What was read from the documents?", facts)
    assert "Synthetic document 6 (REVIEW_REQUIRED)" in answer
    assert "Synthetic value 0" in answer
    assert "No documents have been uploaded" not in answer
    assert snapshot == original
    empty = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=[], actor=ME))
    assert fallback_answer("What documents were uploaded?", empty) == (
        "No documents have been uploaded for this case yet."
    )
    assert "What was read from the documents?" not in suggested_questions(empty)


class ReplacementBackend(FakeBackend):
    def handler(self, request: Any) -> Any:
        import httpx

        response = super().handler(request)
        if response.status_code == 200 and request.url.path.endswith("/documents"):
            return httpx.Response(
                200, json=[document(i, superseded=True) for i in range(6)] + [document(6)]
            )
        return response


def test_replacement_answers_remain_authorized_and_get_only() -> None:
    backend = ReplacementBackend()
    with _client(backend, None) as client:
        brief = client.get(f"/assistant/cases/{CASE_ID}/brief")
        assert brief.status_code == 200
        assert "What was read from the documents?" in brief.json()["suggested_questions"]
        answer = client.post(
            f"/assistant/cases/{CASE_ID}/chat", json={"message": "What documents were uploaded?"}
        )
        assert answer.status_code == 200
        assert "Synthetic document 6" in answer.json()["answer"]
    assert {request.method for request in backend.requests} == {"GET"}
    assert all(
        "clm_session=valid-session" in request.headers.get("cookie", "")
        for request in backend.requests
    )
    for status in (403, 404):
        with _client(FakeBackend(case_status=status), None) as client:
            assert client.get(f"/assistant/cases/{CASE_ID}/brief").status_code == 404
    with _client(ReplacementBackend(), None, cookie=None) as client:
        assert client.get(f"/assistant/cases/{CASE_ID}/brief").status_code == 401
