"""Compare bounded synthetic memory/Mock actions without servers or external requests.

Run: .venv/Scripts/python.exe scripts/profile_garden_local.py --iterations 5
The baseline is a read-only Git archive of apps/backend, extracted into temporary
storage. It is not a Git worktree. Child processes use a clean temporary working
directory, runtime-only test credentials, and the repository's memory/Mock guards.
Times cover representative synthetic service/TestClient actions, not browser,
physical database, official ACRA network, or GoldTier Sandbox latency.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import io
import json
import socket
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "efc31f450f0103766fa812bc0aa80754f801dbe9"


def profile(snapshot: Path, iterations: int) -> dict[str, Any]:
    sys.path[:0] = [str(snapshot / "apps/backend"), str(snapshot / "apps/backend/tests")]

    original_connect = socket.socket.connect

    def prohibit_connection(connection: socket.socket, address: Any) -> None:
        # Windows asyncio creates a loopback self-pipe. Permit that local runtime
        # mechanism; all repository services still use the memory/Mock guards.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(connection, address)
        raise RuntimeError("External connections are prohibited by this local profiler")

    socket.socket.connect = prohibit_connection  # type: ignore[method-assign]
    import conftest  # noqa: F401
    import test_zero_touch_orchestration as fixture
    from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
    from app.domain.access import TeamId
    from app.domain.documents import DocumentFieldKey, ReviewDecision
    from app.services.zero_touch_orchestration import ZeroTouchOrchestrator

    values: dict[str, list[float]] = {}

    def timed(label: str, action: Any) -> Any:
        started = time.perf_counter()
        result = action()
        values.setdefault(label, []).append((time.perf_counter() - started) * 1000)
        return result

    for name in (
        "repair_initial_identity_and_recheck",
        "rebind_case_policy_snapshot",
        "submit_manual_ownership_evidence",
    ):
        original = getattr(ZeroTouchOrchestrator, name)

        def wrapped(self: Any, *args: Any, _name: str = name, _fn: Any = original, **kwargs: Any) -> Any:
            return timed(_name, lambda: _fn(self, *args, **kwargs))

        setattr(ZeroTouchOrchestrator, name, wrapped)

    def run_iteration() -> None:
        client, zero, documents, target, _ = fixture.build_system(require_confirmation=True)
        created = timed("create_service", lambda: zero.create_case("202400001A", team_id=TeamId.TEAM_A))
        timed("attach_service", lambda: zero.attach_document(
            case_id=created.case_id, display_name="synthetic.pdf", content_type="application/pdf",
            content=fixture.PDF, idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ))
        case_id = created.case_id
        document = documents.list_documents(case_id=case_id)[0]
        for _sample in range(5):
            response = timed("detail_GET", lambda: client.get(f"/api/clm/zero-touch/cases/{case_id}"))
            assert response.status_code == 200
        for key, decision, corrected in (
            (DocumentFieldKey.REGISTRATION_NUMBER, ReviewDecision.ACCEPTED, None),
            (DocumentFieldKey.LEGAL_NAME, ReviewDecision.CORRECTED, "MERLION CIRCULAR LABS PTE. LTD."),
            (DocumentFieldKey.REGISTERED_ADDRESS, ReviewDecision.ACCEPTED, None),
            (DocumentFieldKey.COUNTRY_OF_INCORPORATION, ReviewDecision.ACCEPTED, None),
        ):
            before_calls = len(target.calls)
            response = timed("correction_POST" if corrected else "accept_POST", lambda key=key, decision=decision, corrected=corrected: client.post(
                f"/api/onboarding/cases/{case_id}/documents/{document.document_id}/reviews",
                json={"field_key": key.value, "decision": decision.value,
                      **({"corrected_value": corrected} if corrected else {})},
            ))
            assert response.status_code == 200
            def refresh() -> None:
                paths = (
                    f"/api/clm/zero-touch/cases/{case_id}",
                    f"/api/onboarding/cases/{case_id}/documents",
                    f"/api/onboarding/cases/{case_id}/ownership",
                    f"/api/onboarding/cases/{case_id}/intelligence",
                )
                for path in paths:
                    assert client.get(path).status_code in (200, 404)
            timed("review_4_GETs_serial", refresh)
            assert len(target.calls) == before_calls
        fixture.test_same_case_identity_recheck_retains_intent_and_resumes_without_target_write()
        fixture.test_policy_rebind_preserves_case_choices_and_audits_previous_snapshot()
        ownership_test = fixture.test_reviewed_manual_ownership_replaces_blocked_source_without_target_write
        # The current task parametrizes the pre-existing test; choose its unchanged synthetic case.
        if inspect.signature(ownership_test).parameters:
            ownership_test("202400001A")
        else:
            ownership_test()

        rejection_client, rejection_zero, rejection_documents, rejection_target, _ = fixture.build_system(require_confirmation=True)
        rejected_case = rejection_zero.create_case("202400001A", team_id=TeamId.TEAM_A)
        rejection_zero.attach_document(case_id=rejected_case.case_id, display_name="synthetic.pdf", content_type="application/pdf",
                                       content=fixture.PDF, idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH))
        rejected_document = rejection_documents.list_documents(case_id=rejected_case.case_id)[0]
        # Warm runtime-only authentication separately from the field decision.
        assert rejection_client.get(f"/api/clm/zero-touch/cases/{rejected_case.case_id}").status_code == 200
        response = timed("reject_POST", lambda: rejection_client.post(
            f"/api/onboarding/cases/{rejected_case.case_id}/documents/{rejected_document.document_id}/reviews",
            json={"field_key": "legal_name", "decision": "REJECTED"},
        ))
        assert response.status_code == 200
        assert not any(call in rejection_target.calls for call in ("shell", "policy", "amend"))

        reconciliation_client, _, _, reconciliation_target, _ = fixture.build_system(require_confirmation=True)
        paused = fixture.start_demo(reconciliation_client, "DOCUMENT_DISCREPANCY", confirm_if_required=False)
        exception = paused["active_exceptions"][0]
        response = timed("reconciliation_decision_POST", lambda: reconciliation_client.post(
            f"/api/clm/zero-touch/cases/{paused['case']['case_id']}/exceptions/{exception['exception_id']}/resolve",
            json={"action": "KEEP_REGISTRY_VALUE", "expected_automation_version": paused["version"],
                  "evidence_version": exception["evidence_version"]},
        ))
        assert response.status_code == 200
        assert not any(call in reconciliation_target.calls for call in ("shell", "policy", "amend"))

        current_policy = fixture.policy_rebind_snapshots()[1]
        classification_client, _, _, classification_target, _ = fixture.build_system(
            require_confirmation=True, policy_snapshot_provider=lambda: current_policy,
        )
        classification_case = fixture.start_demo(classification_client, "STRAIGHT_THROUGH", confirm_if_required=False)
        response = timed("classification_PUT", lambda: classification_client.put(
            f"/api/clm/zero-touch/cases/{classification_case['case']['case_id']}/target-classification",
            json={"kyc_customer_type": "Company - Private", "client_segment": "Corporate",
                  "expected_automation_version": classification_case["version"],
                  "expected_case_event_count": len(classification_case["case"]["events"])},
        ))
        assert response.status_code == 200
        assert not any(call in classification_target.calls for call in ("shell", "policy", "amend"))

    for _ in range(iterations):
        run_iteration()

    paths = [snapshot / "apps/backend/app/main.py", snapshot / "apps/backend/app/services/zero_touch_orchestration.py",
             snapshot / "apps/backend/tests/test_zero_touch_orchestration.py"]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(snapshot).as_posix().encode())
        digest.update(path.read_bytes())
    return {
        "content_sha256": digest.hexdigest(), "mode": "memory/Mock", "external_requests": 0,
        "document_review_requests": "1 POST + 4 GET (GET timings serialized; UI runs GETs concurrently)",
        "unmeasured": ["browser render", "physical Mongo", "external provider latency"],
        "actions": {name: {"n": len(samples), "median_ms": round(statistics.median(samples), 2),
                           "max_ms": round(max(samples), 2)} for name, samples in values.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--snapshot", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 20:
        parser.error("iterations must be 1..20")
    if args.snapshot:
        try:
            print(json.dumps(profile(args.snapshot, args.iterations)))
        except Exception as exc:  # noqa: BLE001 - emit only sanitized failure location, never raw case/provider data
            frames = traceback.extract_tb(exc.__traceback__)
            print(json.dumps({"status": "FAILED", "exception_type": type(exc).__name__,
                              "file": Path(frames[-1].filename).name, "line": frames[-1].lineno}))
            return 1
        return 0
    with tempfile.TemporaryDirectory(prefix="clm-local-profile-") as temporary:
        temporary_root = Path(temporary)
        baseline = temporary_root / "baseline"
        baseline.mkdir()
        archive = subprocess.run(["git", "archive", BASE, "apps/backend"], cwd=ROOT, check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tracked:
            tracked.extractall(baseline, filter="data")
        report: dict[str, Any] = {"baseline_revision": BASE, "current_HEAD": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip(), "scope": "representative synthetic local workflow; no official Garden network evidence"}
        for label, snapshot in (("before", baseline), ("after", ROOT)):
            process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--snapshot", str(snapshot),
                                      "--iterations", str(args.iterations)], cwd=temporary_root, capture_output=True, text=True, check=False)
            if process.returncode:
                detail = json.loads(process.stdout.strip().splitlines()[-1]) if process.stdout.strip() else {}
                print(json.dumps({"status": "FAILED", "stage": label, "exit_code": process.returncode, "detail": detail}))
                return 1
            report[label] = json.loads(process.stdout.strip().splitlines()[-1])
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
