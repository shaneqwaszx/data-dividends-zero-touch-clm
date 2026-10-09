"""Bounded synthetic shared-ASGI full-case load; no external providers or private config."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
DEADLINE_SECONDS = 60


@contextmanager
def application(mode, db, fixture, perf):
    from app.config import Settings
    from app.connectors.mock_goldtier import MockGoldTierConnector
    from app.main import create_app
    from app.persistence.composition import build_persistence_bundle
    from fastapi.testclient import TestClient
    from pymongo import MongoClient

    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        generate_ephemeral_mongo_database,
        require_ephemeral_mongo_database,
    )

    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    uri = f"mongodb://127.0.0.1:{perf.PORT}"
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode=mode,
        mongo_uri=uri if mode == "mongo" else None,
        mongo_database=database,
        acra_connector_mode="mock",
        goldtier_connector_mode="mock",
        idp_connector_mode="local_pdf_text",
        registry_cache_mode="disabled",
        demo_controls_enabled=False,
    )
    assert settings.clm_persistence_mode == mode and settings.goldtier_connector_mode == "mock"
    if mode == "mongo":
        db.allowed.add(database)
    target = MockGoldTierConnector()
    bundle = None
    try:
        bundle = build_persistence_bundle(settings)
        with (
            patch("app.main.build_persistence_bundle", return_value=bundle),
            patch("app.composition.MockGoldTierConnector", return_value=target),
            TestClient(create_app(settings, acra_connector=fixture)) as client,
        ):
            client._phase13_login()
            yield client, bundle, target
    finally:
        if bundle is not None:
            bundle.close()
        if mode == "mongo":
            with MongoClient(uri, serverSelectionTimeoutMS=3000) as cleanup:
                cleanup_ephemeral_mongo_database(cleanup, database)
            db.allowed.discard(database)


def measure(mode, level, groups, db, db_lock, perf):
    import anyio.to_thread
    import psutil
    from app.connectors.acra import AcraCompanyPayload
    from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
    from app.connectors.mock_acra import MockAcraConnector
    from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
    from test_slice_b_registry_demo import confirm

    from scripts.generate_phase08_synthetic_pdfs import text_pdf

    lock = threading.Lock()
    native = active = peak = 0
    ownership = Counter()
    journal = defaultdict(list)
    fixtures = {}
    for index in range((groups + 2) * level):
        uen = f"2099{index:05d}A"
        fixtures[uen] = text_pdf(
            {
                "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
                "UEN": uen,
                "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
                "Country": "SG",
            }
        )

    class Registry(MockAcraConnector):
        def __init__(self):
            super().__init__()
            self.calls = defaultdict(list)

        def counted(self, operation, uen):
            with lock:
                self.calls[uen].append(operation)

        def fetch_company(self, uen):
            assert uen in fixtures
            self.counted("company", uen)
            base = super().fetch_company("202400001A").model_dump(mode="python")
            return AcraCompanyPayload.model_validate(
                base
                | {"uen": uen, "source_endpoint": f"https://mock.acra.gov.sg/api/entities/{uen}"}
            )

        def fetch_officers(self, uen):
            self.counted("officers", uen)
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen):
            self.counted("ownership_parties", uen)
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen):
            self.counted("relationships", uen)
            return super().fetch_relationships(uen)

    registry = Registry()
    original_native = LocalPdfTextIdpProvider.process
    original_ownership = RegistryAcquisitionOwnershipProvider.load

    def observed_native(provider, document):
        nonlocal native, active, peak
        with lock:
            native += 1
            active += 1
            peak = max(peak, active)
        try:
            return original_native(provider, document)
        finally:
            with lock:
                active -= 1

    def observed_ownership(provider, request):
        with lock:
            ownership[str(request.case_id)] += 1
        return original_ownership(provider, request)

    with (
        patch.object(LocalPdfTextIdpProvider, "process", observed_native),
        patch.object(RegistryAcquisitionOwnershipProvider, "load", observed_ownership),
        application(mode, db, registry, perf) as (client, bundle, target),
        ThreadPoolExecutor(max_workers=level) as pool,
    ):

        async def tokens():
            return anyio.to_thread.current_default_thread_limiter().total_tokens

        assert client.portal is not None
        assert client.portal.call(tokens) == 40
        for method, label in [
            ("search_party", "search"),
            ("create_shell_customer", "shell"),
            ("create_policy", "policy"),
            ("amend_party", "amend"),
        ]:
            original = getattr(target, method)

            def wrap(function, operation):
                def recorded(*args, **kwargs):
                    metadata = kwargs.get("metadata", args[-1] if args else None)
                    with lock:
                        journal[metadata.source_case_id].append(operation)
                    return function(*args, **kwargs)

                return recorded

            setattr(target, method, wrap(original, label))

        def response_value(response, status=200):
            assert response.status_code == status
            return response.json()

        def complete(uen):
            start = time.perf_counter_ns()
            current = response_value(
                client.post(
                    "/api/clm/zero-touch/cases",
                    json={
                        "uen": uen,
                        "country_of_incorporation": "SG",
                        "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                    },
                ),
                201,
            )
            case = current["case"]
            path = f"/api/clm/zero-touch/cases/{case['case_id']}"
            response_value(
                client.put(
                    path + "/target-classification",
                    json={
                        "kyc_customer_type": "Company - Private",
                        "client_segment": "Corporate",
                        "expected_automation_version": current["version"],
                        "expected_case_event_count": len(case["events"]),
                    },
                )
            )
            document = response_value(
                client.post(
                    path + "/intake/documents",
                    content=fixtures[uen],
                    headers={
                        "Content-Type": "application/pdf",
                        "X-Document-Name": "load-native.pdf",
                    },
                ),
                201,
            )
            assert (
                document["state"] == "REVIEWED"
                and document["completion_method"] == "AUTO_CONFIRMED"
            )
            current = response_value(
                client.post(path + "/intake/complete", json={"expected_document_count": 1})
            )
            final = confirm(client, current)
            assert (
                final["status"] == "COMPLETED"
                and final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
            )
            end = time.perf_counter_ns()
            return {
                "case_id": case["case_id"],
                "source_case_id": case["source_case_id"],
                "uen": uen,
                "elapsed_ms": (end - start) / 1e6,
                "status": final["status"],
                "target_state": final["target_submission"]["state"],
            }

        identifiers = iter(fixtures)
        expected_target = ["search", "search", "shell", "policy", "amend", "search"]

        def cohort():
            nonlocal native, peak
            with lock:
                assert active == 0
                native = peak = 0
                ownership.clear()
                journal.clear()
                registry.calls.clear()
            with db_lock:
                db.counts.clear()
            selected = [next(identifiers) for _ in range(level)]
            cpu = time.process_time_ns()
            start = time.perf_counter_ns()
            futures = [pool.submit(complete, uen) for uen in selected]
            _, pending = wait(futures, timeout=DEADLINE_SECONDS)
            if pending:
                raise RuntimeError("bounded load cohort deadline exceeded")
            cases = [future.result() for future in futures]
            end = time.perf_counter_ns()
            cpu_end = time.process_time_ns()
            assert all(case["elapsed_ms"] <= DEADLINE_SECONDS * 1000 for case in cases)
            with db_lock:
                operations = dict(db.counts)
            with lock:
                assert native == level and active == 0
                assert all(
                    journal[c["source_case_id"]] == expected_target and ownership[c["case_id"]] == 1
                    for c in cases
                )
                assert all(
                    registry.calls[c["uen"]]
                    == ["company", "officers", "ownership_parties", "relationships"]
                    for c in cases
                )
                provider_peak = peak
            # Post-window scope/read/currentness verification must add no target operation.
            for case in cases:
                read = response_value(client.get(f"/api/clm/zero-touch/cases/{case['case_id']}"))
                assert (
                    read["status"] == "COMPLETED"
                    and read["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
                )
                documents = bundle.documents.list_for_case(UUID(case["case_id"]))
                assert (
                    len(documents) == 1
                    and len(documents[0].fields) == 4
                    and len(documents[0].pages) == 1
                )
                assert documents[0].pages[0].extraction_method == "NATIVE_PDF_TEXT"
                graph = bundle.ownership.get_for_case(UUID(case["case_id"]))
                assert {c.aggregated_ownership_percent for c in graph.candidates} == {
                    Decimal("60"),
                    Decimal("40"),
                }
                assert all(
                    len(c.paths) == 1 and c.indirect_ownership_percent == Decimal("0")
                    for c in graph.candidates
                )
            with lock:
                assert all(journal[c["source_case_id"]] == expected_target for c in cases)
            return {
                "makespan_ms": (end - start) / 1e6,
                "parent_cpu_ms_per_case": (cpu_end - cpu) / 1e6 / level,
                "db": operations,
                "native_peak": provider_peak,
                "http_requests": level * 5,
                "post_window_http_reads": level,
                "registry_calls": level * 4,
                "native_calls": level,
                "ownership_loads": level,
                "target": {"search": level * 3, "shell": level, "policy": level, "amend": level},
                "cases": cases,
                "errors": 0,
                "timeouts": 0,
                "equality": (
                    "confirmed/native4fields1page/Decimal60+40/ordered target/no replay on read"
                ),
            }

        cohort()  # one excluded warmup cohort
        with perf.Resources() as resources:
            resource_cohort = cohort()
        stable = (
            resources.peak_rss < 2 * 1024**3
            and psutil.virtual_memory().available > 4 * 1024**3
            and statistics.mean(resources.host_cpu) < 80
            and resource_cohort["makespan_ms"] < 45000
        )
        observations = {
            "peak_parent_children_rss_bytes": resources.peak_rss,
            "mean_host_cpu_percent": statistics.mean(resources.host_cpu),
            "host_available_after_bytes": psutil.virtual_memory().available,
            "resource_probe_makespan_ms": resource_cohort["makespan_ms"],
            "stable_for_escalation": stable,
        }
        if level == 20 and not stable:
            return {"status": "RESOURCE_PROBE_ONLY", "resources": observations}, []
        samples = []
        for index in range(groups):
            print(f"LOAD {mode} concurrency={level} cohort={index + 1}/{groups}", flush=True)
            samples.append(cohort())
        elapsed = [case["elapsed_ms"] for sample in samples for case in sample["cases"]]
        return {
            "status": "MEASURED",
            "completed_cases": level * groups,
            "cohorts": groups,
            "latency_ms": perf.summary(elapsed),
            "makespan_ms": perf.summary([s["makespan_ms"] for s in samples]),
            "parent_cpu_ms_per_case": perf.summary([s["parent_cpu_ms_per_case"] for s in samples]),
            "cases_per_minute": level * groups * 60000 / sum(s["makespan_ms"] for s in samples),
            "db_per_cohort": list(
                {json.dumps(s["db"], sort_keys=True): s["db"] for s in samples}.values()
            ),
            "native_peak": max(s["native_peak"] for s in samples),
            "resources": observations,
            "counts_per_case": {
                "registry": 4,
                "native": 1,
                "ownership": 1,
                "search": 3,
                "shell": 1,
                "policy": 1,
                "amend": 1,
                "http": 5,
            },
            "errors": 0,
            "timeouts": 0,
            "correctness": "PASS",
        }, samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=["pilot", "before", "after"], required=True)
    parser.add_argument("--groups", type=int, choices=range(1, 11), default=5)
    parser.add_argument(
        "--levels", nargs="+", type=int, choices=[1, 5, 10, 20], default=[1, 5, 10, 20]
    )
    parser.add_argument(
        "--modes", nargs="+", choices=["memory", "mongo"], default=["memory", "mongo"]
    )
    args = parser.parse_args()
    assert args.levels == sorted(set(args.levels)) and (20 not in args.levels or 10 in args.levels)
    sys.path.insert(0, str(ROOT))
    from scripts import performance_optimization as perf

    perf.initialize()
    assert (
        perf.git("branch", "--show-current")
        == "feat/performance-computational-throughput-optimization"
    )
    db = perf.DbCounts.create()
    db_lock = threading.Lock()
    original_started = db.started

    def locked_started(event):
        with db_lock:
            original_started(event)

    db.started = locked_started
    report = {
        "label": args.label,
        "claim": "SYNTHETIC_LOCAL_LOAD",
        "scope": (
            "closed cohorts of complete cases in one shared in-process ASGI "
            "application/runtime per mode/level; not network/production capacity"
        ),
        "head": perf.git("rev-parse", "HEAD"),
        "base": perf.BASE,
        "method_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "groups": args.groups,
        "warmup_cohorts": 1,
        "separate_resource_cohorts": 1,
        "cohort_deadline_seconds": DEADLINE_SECONDS,
        "CPU": (
            "aggregate parent process CPU/cohort divided bycases; "
            "excludes native children and Mongo CPU; "
            "resources separate and include post-window verification"
        ),
        "workloads": {},
    }
    for mode in args.modes:
        prior_stable = False
        for level in args.levels:
            if level == 20 and not prior_stable:
                report["workloads"][f"{mode}_{level}"] = {
                    "status": "NOT_ESCALATED",
                    "reason": "preceding resource cohort did not support stable20",
                }
                continue
            result, samples = measure(mode, level, args.groups, db, db_lock, perf)
            prior_stable = result["resources"]["stable_for_escalation"]
            report["workloads"][f"{mode}_{level}"] = result
            (perf.RAW / f"load-{args.label}-{mode}-{level}-samples.json").write_text(
                json.dumps(samples, indent=2) + "\n", encoding="utf-8"
            )
            (perf.RAW / f"load-{args.label}.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            print(
                "RESULT", mode, level, result["status"], result.get("cases_per_minute"), flush=True
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
