"""Offline performance control group; no private configuration or provider networking.

Run from the optimization worktree. Raw samples are ignored; aggregates are bounded.
Setup/login, warmup, resource observation and thread-aware profiling are excluded
from elapsed distributions. Primary CPU is parent-process CPU without a sampler.
RSS is a separate sampled observation of parent/live local document children (10ms).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager, suppress
from pathlib import Path
from typing import Any, Self

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".runtime/performance-optimization"
BASE = "198341b059ebf500252ce93d72eb099d2585c60b"
PORT = 27861
SYSTEM_KEYS = {
    "APPDATA",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
}


def summary(values: list[float]) -> dict[str, float | int]:
    if not values or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("measurements must be finite, nonnegative and nonempty")
    ordered = sorted(values)
    return {
        "count": len(values),
        "p50": statistics.median(values),
        "p95": ordered[math.ceil(len(values) * 0.95) - 1],
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def initialize() -> None:
    # Discard inherited application/private configuration without inspecting it.
    safe = {k: v for k, v in os.environ.items() if k.upper() in SYSTEM_KEYS}
    os.environ.clear()
    os.environ.update(safe)
    os.environ["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "apps/backend")))
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    for path in (ROOT, ROOT / "apps/backend", ROOT / "apps/backend/tests"):
        sys.path.insert(0, str(path))
    import conftest  # noqa: F401 - canonical ordinary-test isolation/ephemeral credentials

    # Direct sockets may reach only the task-owned Mongo container.
    original = socket.socket.connect
    original_pair = socket.socketpair
    internal = threading.local()

    def guarded_pair(*args: Any, **kwargs: Any) -> Any:
        internal.socketpair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            internal.socketpair = False

    socket.socketpair = guarded_pair

    def guarded_connect(sock: socket.socket, address: Any) -> Any:
        allowed = isinstance(address, tuple) and (
            address[:2] == ("127.0.0.1", PORT)
            or (getattr(internal, "socketpair", False) and address[0] == "127.0.0.1")
        )
        if not allowed:
            raise RuntimeError("benchmark network boundary rejected connection")
        return original(sock, address)

    socket.socket.connect = guarded_connect


class Resources:
    def __init__(self, *, startup_seconds: float = 1.0, join_seconds: float = 2.0) -> None:
        self.stop = threading.Event()
        self.first_sample = threading.Event()
        self.startup_seconds = startup_seconds
        self.join_seconds = join_seconds
        self.peak_rss = 0
        self.host_cpu: list[float] = []
        self.thread = threading.Thread(target=self.poll, daemon=True)

    def poll(self) -> None:
        import psutil

        try:
            parent = psutil.Process()
            psutil.cpu_percent()
            while not self.stop.is_set():
                processes = [parent, *parent.children(recursive=True)]
                rss = 0
                for process in processes:
                    with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        rss += process.memory_info().rss
                cpu = psutil.cpu_percent()
                if rss <= 0 or not math.isfinite(cpu) or not 0 <= cpu <= 100:
                    return
                self.peak_rss = max(self.peak_rss, rss)
                self.host_cpu.append(cpu)
                self.first_sample.set()
                self.stop.wait(0.01)
        except Exception:
            # A missing/failed sampler must never become accepted resource evidence.
            # Startup fails closed without projecting private OS exception details.
            return

    def __enter__(self) -> Self:
        self.thread.start()
        if not self.first_sample.wait(self.startup_seconds):
            self.__exit__()
            raise RuntimeError("benchmark resource sampler failed to obtain first observation")
        return self

    def __exit__(self, *args: object) -> None:
        self.stop.set()
        self.thread.join(self.join_seconds)
        if self.thread.is_alive():
            raise RuntimeError("benchmark resource sampler did not stop within cleanup deadline")


class DbCounts:
    """Construct the driver listener lazily, never retain command bodies/URIs."""

    @staticmethod
    def create() -> Any:
        from pymongo import monitoring

        class Listener(monitoring.CommandListener):
            def __init__(self) -> None:
                self.counts: Counter[str] = Counter()
                self.allowed: set[str] = set()

            def started(self, event: Any) -> None:
                if event.database_name in self.allowed:
                    self.counts[event.command_name] += 1

            def succeeded(self, event: Any) -> None:
                pass

            def failed(self, event: Any) -> None:
                pass

        listener = Listener()
        monitoring.register(listener)
        return listener


@contextmanager
def application(mode: str, db: Any) -> Iterator[tuple[Any, Any, Any, Any]]:
    from unittest.mock import patch

    from app.config import Settings
    from app.main import create_app
    from app.persistence.composition import build_persistence_bundle
    from fastapi.testclient import TestClient
    from pymongo import MongoClient
    from test_zero_touch_orchestration import RecordingMockGoldTier

    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        generate_ephemeral_mongo_database,
        require_ephemeral_mongo_database,
    )
    from scripts.slice_b_registry_fixture import CountingSyntheticRegistry

    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    uri = f"mongodb://127.0.0.1:{PORT}"
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
    target, acra = RecordingMockGoldTier(), CountingSyntheticRegistry()
    bundle = None
    try:
        bundle = build_persistence_bundle(settings)
        target.benchmark_repositories = Counter()
        from dataclasses import fields
        from functools import wraps

        for descriptor in fields(bundle):
            repository = getattr(bundle, descriptor.name)
            if (
                descriptor.name in {"mode", "mongo_store", "mongo_admin_store"}
                or repository is None
            ):
                continue
            for method_name in (
                "get",
                "get_for_case",
                "list_for_case",
                "list_records",
                "create",
                "save",
                "replace",
                "list_page",
                "list_authorized",
                "list_policies",
            ):
                method = getattr(repository, method_name, None)
                if not callable(method):
                    continue

                def counted(function: Any, key: str) -> Any:
                    @wraps(function)
                    def call(*args: Any, **kwargs: Any) -> Any:
                        target.benchmark_repositories[key] += 1
                        return function(*args, **kwargs)

                    return call

                setattr(
                    repository, method_name, counted(method, f"{descriptor.name}.{method_name}")
                )
        with (
            patch("app.main.build_persistence_bundle", return_value=bundle),
            patch("app.composition.MockGoldTierConnector", return_value=target),
            TestClient(create_app(settings, acra_connector=acra)) as client,
        ):
            client._phase13_login()
            original_request = client.request
            target.benchmark_http = Counter()

            def counted_request(*args: Any, **kwargs: Any) -> Any:
                response = original_request(*args, **kwargs)
                target.benchmark_http["requests"] += 1
                target.benchmark_http["response_bytes"] += len(response.content)
                return response

            client.request = counted_request
            yield client, bundle, target, acra
    finally:
        if bundle is not None:
            bundle.close()
        if mode == "mongo":
            cleanup = MongoClient(uri, serverSelectionTimeoutMS=3000)
            try:
                cleanup_ephemeral_mongo_database(cleanup, database)
            finally:
                cleanup.close()
                db.allowed.discard(database)


def counters(target: Any, acra: Any) -> dict[str, Any]:
    return {
        "registry": dict(Counter(c[0] for c in acra.calls)),
        "target": dict(Counter(target.calls)),
        "repository_calls": dict(target.benchmark_repositories),
        "http_requests": target.benchmark_http["requests"],
        "response_bytes": target.benchmark_http["response_bytes"],
    }


@contextmanager
def workload(name: str, db: Any) -> Iterator[Callable[[], dict[str, Any]]]:
    from test_slice_b_registry_demo import confirm
    from test_zero_touch_exception_remediation import normal_started_case

    if name in {
        "memory_onboarding",
        "mongo_onboarding",
        "mock_target_success",
        "case_detail",
        "portfolio_memory",
        "portfolio_mongo",
    }:
        mode = "mongo" if name in {"mongo_onboarding", "portfolio_mongo"} else "memory"
        with application(mode, db) as (client, bundle, target, acra):
            current = None
            if name in {"mock_target_success", "case_detail"}:
                current = normal_started_case(client, garden=False)
            if name.startswith("portfolio"):
                # 100 bounded retained cases in one authorized team. No target mutations.
                for _index in range(100):
                    response = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
                    assert response.status_code == 201
            target.calls.clear()
            acra.calls.clear()
            target.benchmark_repositories.clear()
            target.benchmark_http.clear()

            def run() -> dict[str, Any]:
                target.benchmark_repositories.clear()
                target.benchmark_http.clear()
                if name.endswith("onboarding"):
                    prepared = normal_started_case(client, garden=False)
                    final = confirm(client, prepared)
                    assert final["status"] == "COMPLETED"
                    assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
                    assert target.calls == [
                        "search",
                        "search",
                        "shell",
                        "policy",
                        "amend",
                        "search",
                    ]
                    result = {"http_requests": 5, "response_bytes": None}
                elif name == "mock_target_success":
                    final = confirm(client, current)
                    assert final["status"] == "COMPLETED"
                    assert target.calls == ["search", "shell", "policy", "amend", "search"]
                    result = {"http_requests": 1, "response_bytes": None}
                elif name == "case_detail":
                    response = client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}")
                    assert response.status_code == 200 and response.json()["case"]
                    result = {"http_requests": 1, "response_bytes": len(response.content)}
                else:
                    response = client.get(
                        "/api/clm/zero-touch/case-portfolio", params={"limit": 50}
                    )
                    assert response.status_code == 200 and len(response.json()["items"]) == 50
                    result = {"http_requests": 1, "response_bytes": len(response.content)}
                return {**result, **counters(target, acra)}

            yield run
    elif name == "blocker_correction_resume":
        from test_zero_touch_orchestration import build_system, start_demo

        client, _, _, target, _ = build_system()
        with client:
            client._phase13_login()
            paused = start_demo(client, "DOCUMENT_DISCREPANCY")
            exception = paused["active_exceptions"][0]
            target.calls.clear()

            def run() -> dict[str, Any]:
                response = client.post(
                    f"/api/clm/zero-touch/cases/{paused['case']['case_id']}/exceptions/"
                    f"{exception['exception_id']}/resolve",
                    json={
                        "action": "KEEP_REGISTRY_VALUE",
                        "expected_automation_version": paused["version"],
                        "evidence_version": exception["evidence_version"],
                    },
                )
                assert response.status_code == 200 and response.json()["status"] == "COMPLETED"
                return {
                    "http_requests": 1,
                    "response_bytes": len(response.content),
                    "target": dict(Counter(target.calls)),
                }

            yield run
    elif name == "uncertain_policy_recovery":
        from test_policy_provider_recovery import (
            UncertainPolicyTransport,
            login_as,
            recovery_payload,
        )
        from test_target_classification_continuation import COMPANIES, prepare, runtime

        target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
        with runtime(target=target) as (client, _bundle, target, acra):
            current = confirm(client, prepare(client, COMPANIES[0]))
            before_calls = len(target.calls)
            login_as(client, "olivia-koh")

            def run() -> dict[str, Any]:
                path = f"/api/clm/zero-touch/cases/{current['case']['case_id']}"
                recovered = client.post(path + "/target-recovery", json=recovery_payload(current))
                assert recovered.status_code == 200 and len(target.calls) == before_calls
                resumed = client.post(path + "/resume")
                assert resumed.status_code == 200 and resumed.json()["status"] == "COMPLETED"
                assert len(target.calls) == before_calls + 1
                mutations = Counter(c[1].rsplit("/", 1)[-1] for c in target.calls if c[0] == "POST")
                assert mutations == {"create": 1, "createPolicy": 1}
                return {
                    "http_requests": 2,
                    "response_bytes": None,
                    "target_total_mutations": dict(mutations),
                    "recovery_mutations": 0,
                }

            yield run
    elif name == "ownership_graph":
        from decimal import Decimal
        from uuid import uuid4

        from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
        from app.connectors.ownership import OwnershipProviderRequest
        from app.services.ownership_analysis import (
            aggregate_ownership_paths,
            build_ownership_candidates,
            build_ownership_graph,
            calculate_ownership_paths,
            validate_ownership_graph,
        )

        source = MockOwnershipProvider(MockOwnershipScenario.MULTIPLE_PATHS).load(
            OwnershipProviderRequest(
                case_id=uuid4(),
                registration_number="202400001A",
                display_name="SYNTHETIC BENCHMARK",
            )
        )

        def run() -> dict[str, Any]:
            graph = build_ownership_graph(source)
            validate_ownership_graph(graph)
            paths = calculate_ownership_paths(
                graph, max_depth=8, max_paths_per_candidate=64, max_total_paths=256
            )
            totals = aggregate_ownership_paths(paths)
            candidates = build_ownership_candidates(
                graph, paths, totals, threshold_percent=Decimal("25")
            )
            assert not paths.issues and candidates
            return {
                "parties": len(graph.parties),
                "edges": len(source.relationships),
                "paths": sum(len(v) for v in paths.paths_by_party.values()),
                "outcome_digest": hashlib.sha256(
                    json.dumps(
                        [c.model_dump(mode="json") for c in candidates], sort_keys=True
                    ).encode()
                ).hexdigest(),
            }

        yield run
    elif name == "native_document":
        from app.connectors.idp import IdpDocumentInput
        from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
        from app.domain.documents import DocumentProfile

        content = (ROOT / "apps/backend/tests/fixtures/uat/clean-company-profile.pdf").read_bytes()
        provider = LocalPdfTextIdpProvider()

        def run() -> dict[str, Any]:
            result = provider.process(
                IdpDocumentInput(profile=DocumentProfile.PROVISIONAL_CORPORATE, content=content)
            )
            assert len(result.fields) == 4 and result.pages
            return {
                "pages": len(result.pages),
                "provider_operations": 1,
                "native": all(str(p.extraction_method) == "NATIVE_PDF_TEXT" for p in result.pages),
            }

        yield run
    else:
        raise ValueError("unknown bounded workload")


WORKLOADS = (
    "memory_onboarding",
    "mongo_onboarding",
    "blocker_correction_resume",
    "mock_target_success",
    "uncertain_policy_recovery",
    "case_detail",
    "portfolio_memory",
    "portfolio_mongo",
    "ownership_graph",
    "native_document",
)


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def run(label: str, count: int, warmup: int, names: list[str]) -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    db = DbCounts.create()
    report: dict[str, Any] = {
        "label": label,
        "claim": "DEVELOPMENT_MEASUREMENT",
        "base": BASE,
        "head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "branch": git("branch", "--show-current"),
        "platform": platform.platform(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "product_tree": git("rev-parse", "HEAD:apps"),
        "product_diff_sha256": hashlib.sha256(
            git("diff", "HEAD", "--", "apps").encode()
        ).hexdigest(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "versions": {
            p: importlib.metadata.version(p)
            for p in (
                "pydantic",
                "pymongo",
                "fastapi",
                "pytest",
                "psutil",
                "yappi",
                "pypdfium2",
                "Pillow",
            )
        },
        "method": {
            "clock": "perf_counter_ns",
            "warmup": warmup,
            "setup_and_login": "excluded",
            "profile": "separate untimed Yappi CPU run across native threads",
            "resources": "separate untimed sampled observation; absent from primary timing",
            "cpu": "parent process only, observer-free; child CPU unavailable",
            "cpu_resolution": "Windows process CPU may quantize short samples to zero",
            "rss": "separate parent plus live children peak, sampled10ms including setup",
            "p95": "nearest rank; no p99",
            "portfolio_size": 100,
            "mongo": "task-owned mongo:7; cpus2; memory1GiB; loopback27861",
        },
        "workloads": {},
    }
    for name in names:
        samples: list[dict[str, Any]] = []
        reusable = name in {
            "case_detail",
            "portfolio_memory",
            "portfolio_mongo",
            "ownership_graph",
            "native_document",
        }
        with ExitStack() as common:
            shared = common.enter_context(workload(name, db)) if reusable else None
            for index in range(warmup + count):
                with ExitStack() as iteration:
                    operation = shared or iteration.enter_context(workload(name, db))
                    db.counts.clear()
                    cpu_start, start = time.process_time_ns(), time.perf_counter_ns()
                    outcome = operation()
                    elapsed = time.perf_counter_ns() - start
                    cpu = time.process_time_ns() - cpu_start
                    sample = {
                        "elapsed_ms": elapsed / 1e6,
                        "parent_cpu_ms": cpu / 1e6,
                        "db": dict(db.counts),
                        "outcome": outcome,
                    }
                if index >= warmup:
                    samples.append(sample)
                print(f"MEASURE {name} {index + 1}/{warmup + count}", flush=True)
        # Resource sampling is deliberately absent from all primary timing/CPU samples.
        with Resources() as resources, workload(name, db) as operation:
            operation()
        import yappi

        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        with workload(name, db) as operation:
            yappi.start(builtins=True, profile_threads=True)
            try:
                operation()
            finally:
                yappi.stop()
        stats = yappi.get_func_stats()
        # Impossible self/cumulative relationships invalidate profiling evidence.
        if any(stat.tsub < 0 or stat.ttot + 1e-9 < stat.tsub for stat in stats):
            raise RuntimeError("thread-aware profile timing invariant failed")
        stats.save(str(RAW / f"{label}-{name}.prof"), type="pstat")
        hotspots = [
            {
                "file": Path(stat.module).name,
                "line": stat.lineno,
                "function": stat.name,
                "calls": stat.ncall,
                "self_cpu_ms": stat.tsub * 1000,
                "cumulative_cpu_ms": stat.ttot * 1000,
            }
            for stat in sorted(stats, key=lambda stat: stat.tsub, reverse=True)[:15]
        ]
        app_hotspots = [
            {
                "file": str(Path(stat.module).relative_to(ROOT)).replace("\\", "/"),
                "line": stat.lineno,
                "function": stat.name,
                "calls": stat.ncall,
                "self_cpu_ms": stat.tsub * 1000,
                "cumulative_cpu_ms": stat.ttot * 1000,
            }
            for stat in sorted(stats, key=lambda stat: stat.tsub, reverse=True)
            if Path(stat.module).is_relative_to(ROOT / "apps/backend/app")
        ][:15]
        yappi.clear_stats()
        signatures = {
            json.dumps(
                {k: v for k, v in sample["outcome"].items() if k != "response_bytes"},
                sort_keys=True,
            )
            for sample in samples
        }
        assert len(signatures) == 1, "operation/outcome counts must be reproducible"
        (RAW / f"{label}-{name}-samples.json").write_text(json.dumps(samples, indent=2) + "\n")
        report["workloads"][name] = {
            "lane": "B_PHYSICAL_MONGO" if "mongo" in name else "A_LOCAL_DETERMINISTIC",
            "elapsed_ms": summary([s["elapsed_ms"] for s in samples]),
            "parent_cpu_ms": summary([s["parent_cpu_ms"] for s in samples]),
            "db_counts": [
                dict(v)
                for v in {json.dumps(s["db"], sort_keys=True): s["db"] for s in samples}.values()
            ],
            "outcome": {k: v for k, v in samples[0]["outcome"].items() if k != "response_bytes"},
            "response_bytes": (
                summary([sample["outcome"]["response_bytes"] for sample in samples])
                if samples[0]["outcome"].get("response_bytes") is not None
                else None
            ),
            "peak_rss_bytes": resources.peak_rss,
            "host_cpu_mean_percent": statistics.mean(resources.host_cpu),
            "hotspots": hotspots,
            "app_hotspots": app_hotspots,
            "correctness": "PASS",
        }
        (RAW / f"{label}-progress.json").write_text(json.dumps(report, indent=2) + "\n")
    report["completed"] = True
    output = (
        RAW / "smoke.json"
        if label == "smoke"
        else ROOT / f".ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_{label.upper()}.json"
    )
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", choices=("baseline", "final", "smoke"), required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--workload", action="append", choices=WORKLOADS)
    args = parser.parse_args()
    if not 1 <= args.count <= 100 or not 0 <= args.warmup <= 5:
        parser.error("bounded repetitions required")
    if args.label in {"baseline", "final"} and (args.count < 20 or args.workload):
        parser.error("complete control-group measurements require all workloads and >=20 samples")
    initialize()
    try:
        run(args.label, args.count, args.warmup, args.workload or list(WORKLOADS))
    except Exception as exc:
        print(f"PERFORMANCE_RESULT=FAILED; TYPE={type(exc).__name__}", flush=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
