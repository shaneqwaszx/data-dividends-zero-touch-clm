"""D-107: Claude Sonnet 5.5 set up by an HR administrator in AI Models, with no decision or
attestation settings: a free workspace read with the key in force, the owner's confirmations
and monthly limit, then enable. The workspace pin, the Anthropic ledger, the limits, the
preflight and the D-095 checks are unchanged. Mock Anthropic API and fake CLM backend only;
nothing is spent and no real key is read."""

import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import anthropic_runtime
from ai_assistant.anthropic_profiles import BALANCED, FAST
from ai_assistant.model_admin_store import ModelAdminStore, RevisionConflict
from tests.test_claude_runtime import ATTESTS, KEY, VAR, WORKSPACE, ClaudeJourney
from tests.test_model_management import API

SETUP = f"{API}/provider/anthropic"
READ = f"{SETUP}/workspace-read"
CONFIRMATIONS = sorted(ATTESTS.split(","))
OTHER_KEY = "sk-" + "ant-" + "api03-" + "OtherWorkspaceSentinel" * 3

# No D-099 decision, no attestations, no workspace, and none of the D-091, D-092, D-094 or
# D-095 decision names: only the approved local deployment and the Anthropic ledger.
NO_DECISIONS: dict[str, Any] = {
    "anthropic_decision": "",
    "anthropic_owner_attests": "",
    "anthropic_workspace_id": "",
    "anthropic_workspace_limit_micro_usd": 0,
    "local_api_test_decision": "",
    "remote_inference_decision": "",
    "remote_live_decision": "",
    "synthetic_dev_decision": "",
}


class HrJourney(ClaudeJourney):
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: Any) -> None:
        super().__init__(tmp_path, monkeypatch, **{**NO_DECISIONS, **extra})

    def profile(self, profile_id: str) -> dict[str, Any]:
        return next(
            p for p in self.client.get(API).json()["profiles"] if p["profile_id"] == profile_id
        )

    def setup(self) -> dict[str, Any]:
        return self.client.get(API).json()["anthropic_setup"]

    def enable(self, **body: Any) -> Any:
        values = {
            "expected_revision": self.setup()["record"]["revision"]
            if self.setup()["record"]
            else 0,
            "enabled": True,
            "workspace_id": WORKSPACE,
            "workspace_limit_micro_usd": 5_000_000,
            "confirmations": CONFIRMATIONS,
            **body,
        }
        return self.client.put(SETUP, json=values)


def _setup(journey: HrJourney) -> dict[str, Any]:
    read = journey.client.post(READ)
    assert read.status_code == 200 and read.json()["workspace_id"] == WORKSPACE, read.text
    enabled = journey.enable()
    assert enabled.status_code == 200, enabled.text
    return enabled.json()


def test_without_any_decision_setting_claude_is_listed_and_set_up_by_hr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    for profile_id in (BALANCED.profile_id, FAST.profile_id):
        item = journey.profile(profile_id)
        assert item["status"] == "pending_authorisation"
        assert item["reason"] == "ANTHROPIC_NOT_AUTHORISED"
    setup = journey.setup()
    assert setup["source"] == "none" and not setup["enabled"] and setup["record"] is None
    assert setup["local_deployment"] and setup["confirmations_required"] == CONFIRMATIONS
    # The Claude key and spending views no longer need the D-094 decision name.
    budget = journey.client.get(API).json()["budget"]
    assert (
        budget["configured"] is False and budget["claude"]["credential"]["source"] == "environment"
    )

    read = journey.client.post(READ)
    assert read.json() == {**read.json(), "outcome": "passed", "workspace_id": WORKSPACE}
    assert KEY not in read.text and "key" not in read.json()
    assert journey.claude.posts == 0  # a free read only
    setup = journey.enable().json()
    assert setup["source"] == "hr" and setup["enabled"] and setup["readiness"] is None
    record = setup["record"]
    assert (
        record["workspace_id"] == WORKSPACE and record["workspace_limit_basis"] == "owner_confirmed"
    )
    assert record["confirmations"] == CONFIRMATIONS and record["changed_by"] == "hr-admin"
    for profile_id in (BALANCED.profile_id, FAST.profile_id):
        item = journey.profile(profile_id)
        assert (
            item["status"] == "selectable"
            and item["details"]["scope"] == "VERIFIED_SYNTHETIC_CASES"
        )
    events = journey.client.get(f"{API}/audit").json()["events"]
    assert any(e["action"] == "ANTHROPIC_ENABLED" and e["outcome"] == "applied" for e in events)
    assert any(e["action"] == "ANTHROPIC_WORKSPACE_READ" for e in events)


def test_hr_enabled_claude_qualifies_activates_and_answers_a_verified_synthetic_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    journey.activate_claude(BALANCED.profile_id)
    assert journey.claude.posts == 2
    serve(monkeypatch, GARDEN)  # digest-verified synthetic documents (D-095 provenance)
    reply = journey.ask(stream=True)
    assert reply["answered_by"] == "model" and reply["model"] == "claude-sonnet-5-5"
    assert journey.claude.posts == 3
    # Every Claude request named the HR-confirmed workspace.
    assert all(r.headers.get("x-api-key") == KEY for r in journey.claude.requests)


def test_disabling_claude_stops_its_calls_without_switching_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_synthetic_eligibility import GARDEN, serve

    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    journey.activate_claude(BALANCED.profile_id)
    serve(monkeypatch, GARDEN)
    posts = journey.claude.posts
    disabled = journey.enable(enabled=False)
    assert disabled.status_code == 200 and disabled.json()["readiness"] == "ANTHROPIC_NOT_ENABLED"
    reply = journey.ask()
    assert reply["answered_by"] == "case_data" and journey.claude.posts == posts
    assert journey.client.get(API).json()["active"]["profile_id"] == BALANCED.profile_id
    again = journey.enable(enabled=False)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "NOT_ENABLED"


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"confirmations": CONFIRMATIONS[:3]}, 400, "ENABLEMENT_INVALID"),
        ({"confirmations": [*CONFIRMATIONS[:3], "other"]}, 400, "ENABLEMENT_INVALID"),
        ({"workspace_limit_micro_usd": 0}, 400, "ENABLEMENT_INVALID"),
        ({"workspace_limit_micro_usd": 30_000_001}, 400, "ENABLEMENT_INVALID"),
        ({"workspace_limit_micro_usd": None}, 400, "ENABLEMENT_INVALID"),
        ({"workspace_id": "wrkspc_SomeOtherWorkspace01"}, 409, "WORKSPACE_NOT_READ"),
        ({"expected_revision": 3}, 409, "ENABLEMENT_CONFLICT"),
    ],
)
def test_enabling_needs_every_confirmation_a_limit_and_the_workspace_the_key_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: dict[str, Any], status: int, code: str
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    assert journey.client.post(READ).json()["outcome"] == "passed"
    refused = journey.enable(**body)
    assert refused.status_code == status and refused.json()["detail"]["code"] == code, refused.text
    assert journey.setup()["record"] is None


def test_enabling_needs_a_read_with_the_key_now_in_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    refused = journey.enable()  # nothing read yet
    assert refused.json()["detail"]["code"] == "WORKSPACE_NOT_READ"
    assert journey.client.post(READ).json()["outcome"] == "passed"
    journey.selector.environ = {VAR: OTHER_KEY}  # the key changed after the read
    assert journey.enable().json()["detail"]["code"] == "WORKSPACE_NOT_READ"


def test_a_read_that_names_no_workspace_enables_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    journey.claude.workspace = None
    read = journey.client.post(READ).json()
    assert read["outcome"] == "failed" and read["code"] == "WORKSPACE_NOT_NAMED"
    assert read["workspace_id"] is None
    assert journey.enable().json()["detail"]["code"] == "WORKSPACE_NOT_READ"


def test_the_workspace_cannot_change_once_set_and_must_match_a_server_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    assert journey.enable(enabled=False).status_code == 200
    journey.claude.workspace = "wrkspc_SomeOtherWorkspace01"
    assert journey.client.post(READ).json()["workspace_id"] == "wrkspc_SomeOtherWorkspace01"
    refused = journey.enable(workspace_id="wrkspc_SomeOtherWorkspace01")
    assert refused.json()["detail"]["code"] == "WORKSPACE_CHANGE_REFUSED"

    (tmp_path / "second").mkdir()
    other = HrJourney(
        tmp_path / "second", monkeypatch, anthropic_workspace_id="wrkspc_EnvWorkspace0001"
    )
    assert other.client.post(READ).json()["workspace_id"] == WORKSPACE
    assert other.enable().json()["detail"]["code"] == "WORKSPACE_MISMATCH"


@pytest.mark.parametrize("session", ["rm-session", "co-session", "director-session"])
def test_only_hr_may_read_or_change_claudes_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session: str
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    journey.client.cookies.set("clm_session", session)
    assert journey.client.post(READ).status_code == 403
    body = {"expected_revision": 0, "enabled": False}
    assert journey.client.put(SETUP, json=body).status_code == 403
    journey.client.cookies.set("clm_session", "hr-session")
    assert journey.setup()["record"] is None and journey.claude.requests == []


def test_a_change_needs_the_page_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    assert journey.client.post(READ, headers={"Origin": ""}).status_code == 403
    assert (
        journey.client.put(
            SETUP, json={"expected_revision": 0, "enabled": False}, headers={"Origin": ""}
        ).status_code
        == 403
    )


def test_outside_the_local_deployment_nothing_is_read_or_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    remote = journey.settings.model_copy(update={"clm_backend_url": "https://clm.example.com"})
    assert anthropic_runtime.readiness(remote) == "NOT_DEVELOPMENT_ENVIRONMENT"
    assert not anthropic_runtime.synthetic_mode(remote)
    read = anthropic_runtime.read_workspace(remote, environ={VAR: KEY})
    assert read["outcome"] == "refused" and read["code"] == "NOT_DEVELOPMENT_ENVIRONMENT"


def test_hr_record_decides_over_the_environment_and_unreadable_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The environment configuration (D-099) still works with no HR record (ClaudeJourney).
    (tmp_path / "legacy").mkdir()
    legacy = ClaudeJourney(tmp_path / "legacy", monkeypatch)
    assert anthropic_runtime.readiness(legacy.settings) is None
    store = ModelAdminStore(Path(legacy.settings.model_admin_db_path))
    store.set_anthropic_enablement(
        0,
        enabled=False,
        workspace_id=WORKSPACE,
        workspace_limit_micro_usd=5_000_000,
        confirmations=anthropic_runtime.OWNER_ATTESTATIONS,
        by="hr-admin",
    )
    # Once HR has a record, it decides: disabled means off, whatever the environment says.
    assert anthropic_runtime.readiness(legacy.settings) == "ANTHROPIC_NOT_ENABLED"
    assert anthropic_runtime.workspace_id(legacy.settings) == ""
    # The table's CHECKs refuse a malformed row; an unreadable database fails closed.
    db = sqlite3.connect(legacy.settings.model_admin_db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE anthropic_enablement SET revision = 0")
    finally:
        db.close()
    Path(legacy.settings.model_admin_db_path).write_bytes(b"not a database" * 512)
    assert anthropic_runtime.readiness(legacy.settings) == "ANTHROPIC_ENABLEMENT_UNREADABLE"
    assert not anthropic_runtime.synthetic_mode(legacy.settings)


def test_the_preflight_pins_the_hr_confirmed_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    test = journey.client.post(f"{API}/{BALANCED.profile_id}/connection-test").json()
    assert test["outcome"] == "passed", test
    journey.claude.workspace = "wrkspc_SomeOtherWorkspace01"
    test = journey.client.post(f"{API}/{BALANCED.profile_id}/connection-test").json()
    assert test["outcome"] == "failed" and "anthropic.workspace_matches" in test["code"]
    assert journey.claude.posts == 0


def test_the_workspace_limit_shown_is_owner_confirmed_and_bounds_the_ledger_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = HrJourney(tmp_path, monkeypatch)
    assert journey.client.post(READ).json()["outcome"] == "passed"
    assert journey.enable(workspace_limit_micro_usd=4_000_000).status_code == 200
    claude = journey.client.get(API).json()["budget"]["claude"]
    assert claude["workspace_limit_micro_usd"] == 4_000_000
    # The ledger's US$5.00 cap is above the confirmed US$4.00 limit: the preflight refuses.
    test = journey.client.post(f"{API}/{BALANCED.profile_id}/connection-test").json()
    assert test["outcome"] == "failed" and "ledger.cap_within_ceiling" in test["code"]


# --- QG R1 remediation: L1, L4, T1 -------------------------------------------------------------


def test_every_d095_check_still_applies_to_hr_enabled_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG T1: a tampered or missing document digest gets the case-data answer; nothing sent."""

    from tests.test_synthetic_eligibility import GARDEN, _fixture, _tampered, digests_for, serve

    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    journey.activate_claude(BALANCED.profile_id)
    posts = journey.claude.posts
    documents = GARDEN[1]
    name = documents[0]["display_name"]
    serve(monkeypatch, GARDEN, digests_for(documents, **{name: _tampered(_fixture(name))}))
    assert journey.ask()["answered_by"] == "case_data"
    serve(monkeypatch, GARDEN, [])
    assert journey.ask(stream=True)["answered_by"] == "case_data"
    assert journey.claude.posts == posts


def test_concurrent_enables_have_one_winner_and_one_audit_row(tmp_path: Path) -> None:
    """QG T1: compare-and-set, with the audit row in the same transaction."""

    store = ModelAdminStore(tmp_path / "state.sqlite3")
    barrier = threading.Barrier(8)
    results: list[Any] = []

    def enable(index: int) -> None:
        barrier.wait()
        try:
            results.append(
                store.set_anthropic_enablement(
                    0,
                    enabled=True,
                    workspace_id=f"wrkspc_Race{index:020d}",
                    workspace_limit_micro_usd=1_000_000,
                    confirmations=anthropic_runtime.OWNER_ATTESTATIONS,
                    by=f"hr-{index}",
                )
            )
        except RevisionConflict:
            results.append("conflict")

    threads = [threading.Thread(target=enable, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(1) == 1 and results.count("conflict") == 7
    events = [e for e in store.events(limit=50) if e["action"] == "ANTHROPIC_ENABLED"]
    assert len(events) == 1


def test_hr_can_disable_a_claude_configured_on_the_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG L1: the earlier D-099 configuration can be switched off from the console."""

    journey = ClaudeJourney(tmp_path, monkeypatch)
    setup = journey.client.get(API).json()["anthropic_setup"]
    assert setup["source"] == "environment" and setup["enabled"] and setup["record"] is None
    disabled = journey.client.put(SETUP, json={"expected_revision": 0, "enabled": False})
    assert disabled.status_code == 200, disabled.text
    setup = disabled.json()
    assert setup["source"] == "hr" and not setup["enabled"]
    assert setup["readiness"] == "ANTHROPIC_NOT_ENABLED"
    assert setup["record"]["workspace_id"] == WORKSPACE
    test = journey.client.post(f"{API}/{BALANCED.profile_id}/connection-test")
    assert test.status_code == 409 and journey.claude.requests == []


def test_a_server_workspace_that_differs_from_hrs_turns_claude_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG L4: the workspace match is a standing rule, not only checked when enabling."""

    journey = HrJourney(tmp_path, monkeypatch)
    _setup(journey)
    assert anthropic_runtime.readiness(journey.settings) is None
    later = journey.settings.model_copy(
        update={"anthropic_workspace_id": "wrkspc_EnvWorkspace0001"}
    )
    assert anthropic_runtime.readiness(later) == "WORKSPACE_MISMATCH"
    same = journey.settings.model_copy(update={"anthropic_workspace_id": WORKSPACE})
    assert anthropic_runtime.readiness(same) is None
