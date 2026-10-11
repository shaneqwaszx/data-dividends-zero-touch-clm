"""Count Mongo commands for isolated synthetic review; never log URI or payloads."""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch


def measure(root: Path, *, batch: bool) -> dict[str, object]:
    sys.path[:0] = [str(root), str(root / "apps/backend"), str(root / "apps/backend/tests")]
    import conftest  # noqa: F401 - guarded test environment, no private dotenv
    from app.main import create_app
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    from pymongo import MongoClient, monitoring
    from test_synthetic_company_pack import settings
    from test_zero_touch_orchestration import RecordingMockGoldTier

    from scripts.generate_phase08_synthetic_pdfs import text_pdf
    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        generate_ephemeral_mongo_database,
        require_ephemeral_mongo_database,
    )

    uri = os.environ.get("PHASE12_MONGO_URI")
    if not uri:
        raise RuntimeError("Disposable Mongo configuration is required")

    class Commands(monitoring.CommandListener):
        enabled = False

        def __init__(self):
            self.counts = Counter()

        def started(self, event):
            if self.enabled and event.command_name in {
                "find",
                "aggregate",
                "getMore",
                "insert",
                "update",
                "delete",
                "findAndModify",
            }:
                self.counts[event.command_name] += 1

        def succeeded(self, event):
            pass

        def failed(self, event):
            pass

    commands = Commands()
    monitoring.register(commands)
    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p16"))
    cleanup = MongoClient(uri, serverSelectionTimeoutMS=3000)
    target = RecordingMockGoldTier()
    try:
        config = settings(
            acra_connector_mode="mock",
            clm_persistence_mode="mongo",
            mongo_uri=SecretStr(uri),
            mongo_database=database,
        )
        with (
            patch("app.composition.MockGoldTierConnector", lambda **_: target),
            TestClient(create_app(config)) as client,
        ):
            current = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
            cid = current["case"]["case_id"]
            response = client.post(
                f"/api/clm/zero-touch/cases/{cid}/intake/documents",
                content=text_pdf({}, extra_lines=("LOCAL SYNTHETIC MISSING EVIDENCE ONLY",)),
                headers={
                    "Content-Type": "application/pdf",
                    "X-Document-Name": "synthetic-count.pdf",
                },
            )
            assert response.status_code == 201
            current = client.post(
                f"/api/clm/zero-touch/cases/{cid}/intake/complete",
                json={"expected_document_count": 1},
            ).json()
            doc = client.get(f"/api/onboarding/cases/{cid}/documents").json()[0]
            before = list(target.calls)
            commands.enabled = True
            if batch:
                body = {
                    "expected_automation_version": current["version"],
                    "expected_case_event_count": len(current["case"]["events"]),
                    "documents": [
                        {
                            "document_id": doc["document_id"],
                            "expected_event_count": len(doc["events"]),
                            "source_fingerprint": doc["review_source_fingerprint"],
                            "decisions": [
                                {"field_key": field["field_key"], "decision": "REJECTED"}
                                for field in doc["fields"]
                            ],
                        }
                    ],
                }
                response = client.post(
                    f"/api/clm/zero-touch/cases/{cid}/review-decisions", json=body
                )
                assert response.status_code == 200
                refreshes = 1
            else:
                for field in doc["fields"]:
                    response = client.post(
                        f"/api/onboarding/cases/{cid}/documents/{doc['document_id']}/reviews",
                        json={"field_key": field["field_key"], "decision": "REJECTED"},
                    )
                    assert response.status_code == 200
                    for endpoint in (
                        f"/api/clm/zero-touch/cases/{cid}",
                        f"/api/onboarding/cases/{cid}/documents",
                        f"/api/onboarding/cases/{cid}/ownership",
                        f"/api/clm/zero-touch/cases/{cid}/intelligence",
                    ):
                        assert client.get(endpoint).status_code in {200, 404}
                refreshes = 0
            for _ in range(refreshes):
                for endpoint in (
                    f"/api/clm/zero-touch/cases/{cid}",
                    f"/api/onboarding/cases/{cid}/documents",
                    f"/api/onboarding/cases/{cid}/ownership",
                    f"/api/clm/zero-touch/cases/{cid}/intelligence",
                ):
                    assert client.get(endpoint).status_code in {200, 404}
            commands.enabled = False
            final = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert final["status"] == "WAITING_FOR_REVIEW" and target.calls == before
            return {
                "mode": "batch" if batch else "baseline",
                "samples": 1,
                "workload": (
                    "four missing native-PDF fields rejected; "
                    "confirmation plus supporting GET wave(s)"
                ),
                "commands": dict(sorted(commands.counts.items())),
                "target_calls": 0,
                "final_status": final["status"],
                "cleanup_guard": "generated allowlisted disposable database",
            }
    finally:
        commands.enabled = False
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
            assert database not in cleanup.list_database_names()
        finally:
            cleanup.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.root.resolve(strict=True), batch=args.batch)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
