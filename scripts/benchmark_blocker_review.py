"""Synthetic in-process HTTP review measurement; never calls external providers."""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/backend"), str(ROOT / "apps/backend/tests")]

import conftest  # noqa: E402, F401 - existing guarded synthetic auth/test environment
from app.connectors.mock_idp import MockIdpProvider  # noqa: E402
from test_zero_touch_orchestration import PDF, build_system  # noqa: E402


class FourFieldReviewIdp(MockIdpProvider):
    def process(self, document):
        result = super().process(document)
        return result.model_copy(
            update={
                "fields": [field.model_copy(update={"confidence": 0.6}) for field in result.fields],
            }
        )


def measure(*, batch: bool, samples: int) -> dict:
    rows = []
    for _ in range(samples):
        client, zero, documents, target, _ = build_system(require_confirmation=True)
        with client:
            created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
            assert created.status_code == 201
            case_id = created.json()["case"]["case_id"]
            from uuid import UUID

            zero.attach_document(
                case_id=UUID(case_id),
                display_name="synthetic-review.pdf",
                content_type="application/pdf",
                content=PDF,
                idp_provider=FourFieldReviewIdp(),
            )
            current = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
            document = client.get(f"/api/onboarding/cases/{case_id}/documents").json()[0]
            assert len([f for f in document["fields"] if f["review_status"] == "PENDING"]) == 4
            timings = []
            gets = 0
            before = list(target.calls)
            with (
                patch.object(
                    zero._reconciliation,
                    "reconcile_current",
                    wraps=zero._reconciliation.reconcile_current,
                ) as reconciliation,
                patch.object(zero, "_advance_locked", wraps=zero._advance_locked) as advance,
                patch.object(
                    documents._repository, "save", wraps=documents._repository.save
                ) as saves,
            ):
                groups = [document["fields"]] if batch else [[f] for f in document["fields"]]
                start = time.perf_counter()
                for fields in groups:
                    request_start = time.perf_counter()
                    if batch:
                        response = client.post(
                            f"/api/clm/zero-touch/cases/{case_id}/review-decisions",
                            json={
                                "expected_automation_version": current["version"],
                                "expected_case_event_count": len(current["case"]["events"]),
                                "documents": [
                                    {
                                        "document_id": document["document_id"],
                                        "expected_event_count": len(document["events"]),
                                        "source_fingerprint": document["review_source_fingerprint"],
                                        "decisions": [
                                            {"field_key": f["field_key"], "decision": "ACCEPTED"}
                                            for f in fields
                                        ],
                                    }
                                ],
                            },
                        )
                    else:
                        response = client.post(
                            f"/api/onboarding/cases/{case_id}/documents/{document['document_id']}/reviews",
                            json={"field_key": fields[0]["field_key"], "decision": "ACCEPTED"},
                        )
                    assert response.status_code == 200, response.json()
                    for path in (
                        f"/api/clm/zero-touch/cases/{case_id}",
                        f"/api/onboarding/cases/{case_id}/documents",
                        f"/api/onboarding/cases/{case_id}/ownership",
                        f"/api/clm/zero-touch/cases/{case_id}/intelligence",
                    ):
                        client.get(path)
                        gets += 1
                    timings.append((time.perf_counter() - request_start) * 1000)
                elapsed = (time.perf_counter() - start) * 1000
                rows.append(
                    {
                        "mutations": len(groups),
                        "gets": gets,
                        "reconciliation_calls": reconciliation.call_count,
                        "continuation_calls": advance.call_count,
                        "document_saves": saves.call_count,
                        "four_decisions_ms": elapsed,
                        "request_and_refresh_ms": timings,
                    }
                )
            assert target.calls == before
    waits = sorted(t for r in rows for t in r["request_and_refresh_ms"])
    totals = sorted(r["four_decisions_ms"] for r in rows)
    return {
        "mode": "batch" if batch else "baseline",
        "samples": samples,
        "measurement": (
            "in-process TestClient HTTP + four explicit supporting GETs; "
            "not browser/production SLA"
        ),
        "median_request_and_refresh_ms": statistics.median(waits),
        "p95_request_and_refresh_ms": waits[int(0.95 * (len(waits) - 1))],
        "median_four_decisions_ms": statistics.median(totals),
        "p95_four_decisions_ms": totals[int(0.95 * (len(totals) - 1))],
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = measure(batch=args.batch, samples=args.samples)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
