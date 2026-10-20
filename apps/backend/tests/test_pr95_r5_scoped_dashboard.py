"""PR95-R5 eager scoped capture, final observation and retained timing regressions."""

from copy import deepcopy
from uuid import uuid4

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from test_phase13_dashboard import NOW, _actor, _record, _service_for

from app.domain.access import TeamId
from app.domain.zero_touch import AutomationStage, AutomationStatus, validate_automation_record
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import MongoZeroTouchAutomationRepository
from app.services.dashboard import DashboardService
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository


def fixture(*, team=TeamId.TEAM_A, days=1, duration=0, creator="maya-lim"):
    case, automation = _record(
        team,
        None,
        AutomationStatus.RUNNING,
        created_days_ago=days,
        updated_hours_ago=1,
        created_by_actor_id=creator,
        stage_durations_ms={AutomationStage.REGISTRY: duration},
    )
    automation = automation.model_copy(update={"started_at": case.created_at})
    validate_automation_record(automation)
    envelope = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        automation=automation,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
    return case, automation, object.__new__(MongoCaseStore)._encode(envelope)


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []
        self.captures = 0

    def find(self, query):
        self.queries.append(deepcopy(query))
        ids = query.get("_id", {}).get("$in")
        owner = self

        class Cursor:
            def sort(self, *_args):
                return self

            def close(self):
                return None

            def __iter__(self):
                for row in owner.rows:
                    if ids is None or row.get("_id") in ids:
                        owner.captures += 1
                        yield deepcopy(row)

        return Cursor()


def mongo_repository(rows):
    store = object.__new__(MongoCaseStore)
    store._collection = Collection(rows)
    return MongoZeroTouchAutomationRepository(store), store


def test_capture_is_eager_subset_only_one_shot_and_closes_without_raw_projection():
    a = fixture()
    b = fixture(team=TeamId.TEAM_B)
    repo, store = mongo_repository([a[2], b[2]])
    with repo.capture_for_cases(frozenset({a[0].case_id})) as batch:
        assert store._collection.captures == 1
        assert store._collection.queries == [{"_id": {"$in": [str(a[0].case_id)]}}]
        assert not hasattr(batch, "raw_documents")
        with pytest.raises(ValueError):
            batch.read_selected(frozenset({b[0].case_id}))
    with pytest.raises(ValueError):
        batch.read_selected(frozenset({a[0].case_id}))
    with repo.capture_for_cases(frozenset({a[0].case_id})) as batch:
        assert [v.case_id for v in batch.read_selected(frozenset({a[0].case_id}))] == [a[0].case_id]
        with pytest.raises(ValueError):
            batch.read_selected(frozenset())


@pytest.mark.parametrize("mode", ["memory", "mongo"])
def test_capture_defensive_snapshot_order_missing_and_empty(mode):
    a = fixture()
    b = fixture()
    if mode == "mongo":
        repo, store = mongo_repository([a[2], b[2]])
    else:
        repo = InMemoryZeroTouchAutomationRepository()
        repo.save(a[1], expected_version=None)
        repo.save(b[1], expected_version=None)
    ids = frozenset({a[0].case_id, b[0].case_id, uuid4()})
    with repo.capture_for_cases(ids) as batch:
        if mode == "mongo":
            store._collection.rows.clear()
        else:
            repo.delete_for_case(a[0].case_id)
            repo.delete_for_case(b[0].case_id)
        records = batch.read_selected(ids)
        assert [v.case_id for v in records] == sorted(
            [a[0].case_id, b[0].case_id], key=str, reverse=True
        )
        records[0].metrics.stage_durations_ms[AutomationStage.REGISTRY] = 999
    with repo.capture_for_cases(frozenset()) as empty:
        assert empty.read_selected(frozenset()) == []


def test_dashboard_excluded_full_envelopes_never_decode_but_selected_are_strict():
    a = fixture()
    old = fixture(days=45)
    foreign = fixture(team=TeamId.TEAM_B)
    for bad in (old, foreign):
        bad[2]["automation"]["unknown_unprojected_field"] = "synthetic"
    service, _ = _service_for([(v[0], v[1]) for v in (a, old, foreign)])
    repo, store = mongo_repository([v[2] for v in (a, old, foreign)])
    service._automation = repo
    clocks = []

    def clock():
        assert store._collection.captures == 2 * (len(clocks) + 1)
        clocks.append(NOW)
        return NOW

    service._clock = clock
    result = service.get_dashboard(_actor("maya-lim"), date_range="7d")
    assert result.totals.total_cases == 1 and len(clocks) == 1
    assert set(store._collection.queries[0]["_id"]["$in"]) == {
        str(a[0].case_id),
        str(old[0].case_id),
    }
    with pytest.raises(PersistenceDataInvalidError):
        service.get_dashboard(_actor("maya-lim"), date_range="all")


def test_selected_duplicate_envelope_is_rejected_without_decoding_excluded_duplicates():
    a = fixture()
    old = fixture(days=45)
    repo, _ = mongo_repository([a[2], old[2], old[2]])
    ids = frozenset({a[0].case_id, old[0].case_id})
    with repo.capture_for_cases(ids) as batch:
        assert len(batch.read_selected(frozenset({a[0].case_id}))) == 1
    with repo.capture_for_cases(ids) as batch, pytest.raises(PersistenceDataInvalidError):
        batch.read_selected(frozenset({old[0].case_id}))


@pytest.mark.parametrize("mode", ["memory", "mongo"])
@pytest.mark.parametrize("days, selected", [(1, True), (45, False)])
def test_negative_stage_evidence_is_contained_only_when_selected(monkeypatch, mode, days, selected):
    a = fixture(days=days, duration=-1)
    service, _ = _service_for([(a[0], a[1])])
    if mode == "mongo":
        service._automation, _ = mongo_repository([a[2]])
    else:
        repo = InMemoryZeroTouchAutomationRepository()
        repo.save(a[1], expected_version=None)
        service._automation = repo
    original = service.get_dashboard
    monkeypatch.setattr(
        DashboardService, "get_dashboard", lambda self, actor, **kwargs: original(actor, **kwargs)
    )
    with RawTestClient(
        create_app(ordinary_test_settings(), clock=lambda: NOW), raise_server_exceptions=False
    ) as client:
        assert (
            client.post(
                "/api/auth/login", json={"user_id": "maya-lim", "password": TEST_PASSWORD}
            ).status_code
            == 200
        )
        response = client.get("/api/clm/zero-touch/dashboard?date_range=7d")
        if selected:
            assert response.status_code == 503
            assert response.json() == {
                "detail": {
                    "code": "DASHBOARD_UNAVAILABLE",
                    "message": "Dashboard data is temporarily unavailable.",
                }
            }
        else:
            assert response.status_code == 200 and response.json()["totals"]["total_cases"] == 0


@pytest.mark.parametrize(
    "durations", [{}, {AutomationStage.REGISTRY: 0}, {AutomationStage.REGISTRY: 1001}]
)
def test_valid_zero_missing_and_precise_stage_samples_are_preserved(durations):
    a = fixture()
    a[1].metrics.stage_durations_ms.clear()
    a[1].metrics.stage_durations_ms.update(durations)
    service, _ = _service_for([(a[0], a[1])])
    row = service.get_dashboard(_actor("maya-lim")).stage_timing[0]
    assert row.combined_mean_ms == durations.get(AutomationStage.REGISTRY)


@pytest.mark.parametrize("mode", ["memory", "mongo"])
def test_batch_failure_consumes_selection_and_context_exit_closes(mode):
    value = fixture()
    if mode == "memory":
        repo = InMemoryZeroTouchAutomationRepository()
        repo.save(value[1], expected_version=None)
    else:
        repo, _ = mongo_repository([value[2]])
    ids = frozenset({value[0].case_id})
    context = repo.capture_for_cases(ids)
    with context as batch:
        with pytest.raises(ValueError):
            batch.read_selected(frozenset({uuid4()}))
        with pytest.raises(ValueError):
            batch.read_selected(ids)
    with pytest.raises((AttributeError, RuntimeError)), context:
        pytest.fail("a captured request context must not be reusable")
    with repo.capture_for_cases(ids) as unread:
        pass
    with pytest.raises(ValueError):
        unread.read_selected(ids)
    with repo.capture_for_cases(ids) as selected:
        records = selected.read_selected(ids)
        assert records[0].ownership_provider_binding_id == value[1].ownership_provider_binding_id


@pytest.mark.parametrize("selection", [[], {uuid4()}, frozenset({"foreign"})])
def test_invalid_capture_arguments_fail_before_database_query(selection):
    repo, store = mongo_repository([])
    with pytest.raises(ValueError), repo.capture_for_cases(selection):
        pytest.fail("invalid capture cannot yield")
    assert store._collection.queries == []


def test_strict_selected_identity_failure_consumes_batch():
    value = fixture()
    value[2]["case_id"] = str(uuid4())
    repo, _ = mongo_repository([value[2]])
    ids = frozenset({value[0].case_id})
    with repo.capture_for_cases(ids) as batch:
        with pytest.raises(PersistenceDataInvalidError):
            batch.read_selected(ids)
        with pytest.raises(ValueError):
            batch.read_selected(ids)


def test_driver_failure_closes_cursor_and_has_only_safe_unavailable_error():
    from pymongo.errors import ConnectionFailure

    from app.persistence.errors import PersistenceUnavailableError

    repo, store = mongo_repository([])
    calls = []

    class FailedCursor:
        def __iter__(self):
            raise ConnectionFailure("synthetic-private-detail")

        def close(self):
            calls.append("closed")

    store._collection.find = lambda query: FailedCursor()
    with (
        pytest.raises(PersistenceUnavailableError) as raised,
        repo.capture_for_cases(frozenset({uuid4()})),
    ):
        pytest.fail("failed capture cannot yield")
    assert calls == ["closed"]
    assert str(raised.value) == ""


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("invalid_key", ["foreign", "missing", "null", "integer"])
def test_unexpected_raw_query_identity_fails_before_decode_and_consumes_batch(
    selected, invalid_key
):
    from app.persistence.mongo_case_store import CapturedCaseBatch

    value = fixture()
    authorized = frozenset({value[0].case_id})
    raw = {"unselected_malformed_envelope": object()}
    if invalid_key != "missing":
        raw["_id"] = {"foreign": str(uuid4()), "null": None, "integer": 7}[invalid_key]
    decoded = []

    def decode(record):
        decoded.append(record)
        pytest.fail("unexpected query results must never reach full decoding")

    batch = CapturedCaseBatch(authorized, [raw], decode)
    with pytest.raises(PersistenceDataInvalidError):
        batch.read_selected(authorized if selected else frozenset())
    assert decoded == []
    assert batch._raw_records == [] and batch._decode is None
    assert batch._authorized == frozenset()
    with pytest.raises(ValueError):
        batch.read_selected(authorized)
