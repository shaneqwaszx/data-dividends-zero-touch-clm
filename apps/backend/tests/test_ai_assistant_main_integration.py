"""Read-only AI Assistant consumes the current authenticated schema10 case projection."""

import os
import sys
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from scripts.zero_touch_happy_path_fixtures import COMPANIES
from starlette.testclient import TestClient as DirectTestClient
from test_classification_conflict_review import conflict_case
from test_target_classification_continuation import runtime, save, upload

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/assistant"))
from ai_assistant.config import AiAssistantSettings  # noqa: E402

AiAssistantSettings.model_config = {**AiAssistantSettings.model_config, "env_file": None}
os.environ["AI_ASSISTANT_LLM_ENABLED"] = "false"
from ai_assistant.main import create_app  # noqa: E402


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_ai_assistant_reads_conflict_fresh_review_and_later_invalidation_without_authority(mode):
    with runtime(provider_mode=mode) as (backend, bundle, target, acra):
        current, _ = conflict_case(backend)
        cid = UUID(current["case"]["case_id"])
        reads = []

        def bridge(request):
            assert request.method == "GET"
            reads.append(request.url.path)
            response = backend.get(
                request.url.path, headers={"Cookie": request.headers.get("cookie", "")}
            )
            return httpx.Response(response.status_code, json=response.json())

        settings = AiAssistantSettings(_env_file=None, llm_enabled=False)
        app = create_app(settings, clm_transport=httpx.MockTransport(bridge))
        with DirectTestClient(app, headers={"Origin": "http://127.0.0.1:5173"}) as ai_assistant:
            ai_assistant.cookies.set("clm_session", backend.cookies.get("clm_session"))
            path = f"/assistant/cases/{cid}"

            def read_and_check():
                before = bundle.onboarding.get(cid).model_dump_json()
                before_clm = bundle.clm.get_for_case(cid).model_dump_json()
                calls = list(target.calls)
                brief = ai_assistant.get(path + "/brief")
                assert brief.status_code == 200
                answer = ai_assistant.post(
                    path + "/chat", json={"message": "What more do I need to do?"}
                )
                assert answer.status_code == 200
                assert answer.json()["answered_by"] == "case_data"
                assert "Readiness check" not in answer.json()["answer"]
                assert "Preparing GoldTier Submission" not in answer.json()["answer"]
                assert bundle.onboarding.get(cid).model_dump_json() == before
                assert bundle.clm.get_for_case(cid).model_dump_json() == before_clm
                assert bundle.target_executions.list_for_case(cid) == ()
                assert target.calls == calls
                return answer.json()["answer"]

            blocked = read_and_check()
            assert "Submission readiness" in blocked
            assert "classification" in blocked.lower()
            assert not current["target_classification"]["current"]
            response = save(backend, current)
            assert response.status_code == 200
            reviewed = response.json()
            assert reviewed["target_classification"]["current"]
            assert reviewed["clm"]["readiness"]["blockers"] == []
            ready = read_and_check()
            final_step = next(
                node
                for node in reviewed["processing_pipeline"]
                if node["node_id"] == "FINAL_REVIEW_SEND"
            )
            assert final_step["status"] == "REVIEW_REQUIRED"
            assert final_step["label"] in ready
            assert "nothing else outstanding" not in ready.lower()
            upload(backend, reviewed, COMPANIES[0].target_profile)
            changed = backend.get(f"/api/clm/zero-touch/cases/{cid}").json()
            assert not changed["target_classification"]["current"]
            assert "Submission readiness" in read_and_check()
            assert ai_assistant.post(path + "/target-confirmation").status_code == 404
            assert ai_assistant.put(path + "/target-classification").status_code == 404
        assert set(reads) == {
            "/api/auth/me",
            f"/api/clm/zero-touch/cases/{cid}",
            f"/api/onboarding/cases/{cid}/documents",
        }
        assert acra.calls == []
        assert not any(call[0] != "GET" for call in target.calls)
