"""Bounded shared-ASGI native intake measurement; local synthetic providers only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def measure_level(label, groups, level, content, perf):
    import anyio.to_thread
    from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider

    started = threading.Event()
    lock = threading.Lock()
    active = 0
    peak = 0
    provider_calls = 0
    original = LocalPdfTextIdpProvider.process

    def observed(provider, document):
        nonlocal active, peak, provider_calls
        with lock:
            active += 1
            peak = max(peak, active)
            provider_calls += 1
        started.set()
        try:
            return original(provider, document)
        finally:
            with lock:
                active -= 1

    with (
        patch.object(LocalPdfTextIdpProvider, "process", observed),
        perf.application("memory", None) as (client, bundle, target, registry),
        ThreadPoolExecutor(max_workers=level) as pool,
    ):

        async def capacity():
            return anyio.to_thread.current_default_thread_limiter().total_tokens

        assert client.portal is not None
        tokens = client.portal.call(capacity)
        assert tokens == 40
        paths = []
        for _ in range((groups + 3) * level):
            response = client.post(
                "/api/clm/zero-touch/cases",
                json={
                    "uen": "202400001A",
                    "country_of_incorporation": "SG",
                    "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                },
            )
            assert response.status_code == 201
            current = response.json()
            case = current["case"]
            path = f"/api/clm/zero-touch/cases/{case['case_id']}"
            response = client.put(
                path + "/target-classification",
                json={
                    "kyc_customer_type": "Company - Private",
                    "client_segment": "Corporate",
                    "expected_automation_version": current["version"],
                    "expected_case_event_count": len(case["events"]),
                },
            )
            assert response.status_code == 200
            paths.append(path)
        target.calls.clear()
        registry.calls.clear()

        def upload(path):
            start = time.perf_counter_ns()
            response = client.post(
                path + "/intake/documents",
                content=content,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Document-Name": "clean-company-profile.pdf",
                },
            )
            end = time.perf_counter_ns()
            assert response.status_code == 201
            document = response.json()
            assert (
                len(document["fields"]) == 4
                and document["state"] == "REVIEWED"
                and document["completion_method"] == "AUTO_CONFIRMED"
            )
            assert (
                len(document["pages"]) == 1
                and document["pages"][0]["extraction_method"] == "NATIVE_PDF_TEXT"
            )
            return {
                "elapsed_ms": (end - start) / 1e6,
                "end_ns": end,
                "state": document["state"],
                "fields": 4,
                "pages": 1,
            }

        cursor = 0

        def cohort():
            nonlocal cursor
            selected = paths[cursor : cursor + level]
            cursor += level
            assert len(selected) == level
            started.clear()
            cpu = time.process_time_ns()
            start = time.perf_counter_ns()
            futures = [pool.submit(upload, path) for path in selected]
            assert started.wait(20), "native provider did not start"
            health_start = time.perf_counter_ns()
            health = client.get("/health")
            health_end = time.perf_counter_ns()
            assert health.status_code == 200
            samples = [future.result(timeout=20) for future in futures]
            used = time.process_time_ns() - cpu
            end = max(s["end_ns"] for s in samples)
            for sample in samples:
                del sample["end_ns"]
            for path in selected:
                current = client.get(path)
                assert current.status_code == 200
                assert current.json()["status"] == "PENDING_INPUTS"
                assert current.json()["target_submission"]["state"] == "NOT_SUBMITTED"
            assert not target.calls and not registry.calls
            return {
                "makespan_ms": (end - start) / 1e6,
                "parent_cpu_ms_per_intake": used / 1e6 / level,
                "health_ms": (health_end - health_start) / 1e6,
                "intakes": samples,
                "http_requests": level + 1,
                "post_window_verification_requests": level,
                "target_mutations": 0,
                "registry_operations": 0,
            }

        for _ in range(2):
            cohort()
        samples = []
        for index in range(groups):
            samples.append(cohort())
            print(
                f"MEASURE shared_native_intake concurrency={level} group={index + 1}/{groups}",
                flush=True,
            )
        with perf.Resources() as resources:
            cohort()
        assert provider_calls == (groups + 3) * level and active == 0 and peak <= level
        raw = ROOT / ".runtime/performance-optimization"
        raw.mkdir(exist_ok=True)
        (raw / f"concurrency-{label}-{level}-samples.json").write_text(
            json.dumps(samples, indent=2) + "\n", encoding="utf-8"
        )
        return {
            **{
                metric: perf.summary([s[metric] for s in samples])
                for metric in ("makespan_ms", "parent_cpu_ms_per_intake", "health_ms")
            },
            "intake_elapsed_ms": perf.summary(
                [i["elapsed_ms"] for s in samples for i in s["intakes"]]
            ),
            "intakes_per_minute": groups * level * 60000 / sum(s["makespan_ms"] for s in samples),
            "completed_intakes": groups * level,
            "errors": 0,
            "timeouts": 0,
            "http_requests_per_group": level + 1,
            "native_calls_primary": groups * level,
            "native_calls_with_warmup_resource": provider_calls,
            "peak_concurrent_provider_calls": peak,
            "framework_thread_tokens": tokens,
            "peak_parent_children_rss_bytes_separate": resources.peak_rss,
            "target_mutations": 0,
            "registry_operations_in_primary": 0,
            "outcome": (
                "REVIEWED document/AUTO_CONFIRMED/4fields/1native page; "
                "all cases remain PENDING_INPUTS/NOT_SUBMITTED"
            ),
        }



class ActiveProviderProbe:
    """Diagnostic-only hold at the end of real native processing, inside its invocation.

    Health completion releases the hold immediately. An independent 100ms guard
    releases a blocked baseline; that release budget is not natural provider latency.
    A separate operation deadline also releases a provider if dispatch never happens.
    """

    def __init__(self, *, hold_seconds=0.1, operation_seconds=20.0):
        self.lock = threading.Lock()
        self.entered = threading.Event()
        self.dispatched = threading.Event()
        self.health_done = threading.Event()
        self.release = threading.Event()
        self.active = 0
        self.held = 0
        self.calls = 0
        self.active_at_dispatch = 0
        self.held_at_dispatch = 0
        self.completed_while_held = False
        self.release_reason = None
        self.hold_seconds = hold_seconds
        self.operation_seconds = operation_seconds
        self.guard = threading.Thread(target=self._guard, daemon=True)

    def _guard(self):
        if not self.dispatched.wait(self.operation_seconds):
            reason = "dispatch_deadline"
        elif self.health_done.wait(self.hold_seconds):
            reason = "health_completed"
        else:
            reason = "diagnostic_deadline"
        with self.lock:
            if not self.release.is_set():
                self.release_reason = reason
                self.release.set()

    def observe(self, operation):
        held = False
        with self.lock:
            self.active += 1
            self.calls += 1
        try:
            result = operation()
            with self.lock:
                self.held += 1
                held = True
                self.entered.set()
            if not self.release.wait(self.operation_seconds):
                raise RuntimeError("benchmark provider hold exceeded operation deadline")
            return result
        finally:
            with self.lock:
                self.active -= 1
                if held:
                    self.held -= 1

    def begin_dispatch(self):
        # Called at TestClient transport entry for /health, after request construction.
        # The guard cannot release before this locked observation/dispatch signal.
        with self.lock:
            if self.active <= 0 or self.held <= 0 or self.release.is_set():
                raise RuntimeError("benchmark health dispatch requires held active provider")
            if self.dispatched.is_set():
                raise RuntimeError("benchmark health probe dispatched more than once")
            self.active_at_dispatch = self.active
            self.held_at_dispatch = self.held
            self.dispatch_ns = time.perf_counter_ns()
            self.dispatched.set()

    def complete_health(self):
        with self.lock:
            self.completion_ns = time.perf_counter_ns()
            self.completed_while_held = self.held > 0 and not self.release.is_set()
            self.health_done.set()

    def __enter__(self):
        self.guard.start()
        return self

    def __exit__(self, *args):
        with self.lock:
            if not self.release.is_set():
                self.release_reason = "cleanup"
                self.release.set()
        self.dispatched.set()
        self.health_done.set()
        self.guard.join(2)
        if self.guard.is_alive():
            raise RuntimeError("benchmark health guard did not stop")


def measure_active_health(groups, level, content, perf):
    from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider

    original = LocalPdfTextIdpProvider.process
    samples: list[dict[str, Any]] = []
    warmup: list[dict[str, Any]] = []
    with perf.application("memory", None) as (client, _bundle, target, registry):
        for index in range(groups + 2):
            paths = []
            for _ in range(level):
                response = client.post(
                    "/api/clm/zero-touch/cases",
                    json={
                        "uen": "202400001A",
                        "country_of_incorporation": "SG",
                        "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                    },
                )
                assert response.status_code == 201
                current = response.json()
                case = current["case"]
                path = f"/api/clm/zero-touch/cases/{case['case_id']}"
                response = client.put(
                    path + "/target-classification",
                    json={
                        "kyc_customer_type": "Company - Private",
                        "client_segment": "Corporate",
                        "expected_automation_version": current["version"],
                        "expected_case_event_count": len(case["events"]),
                    },
                )
                assert response.status_code == 200
                paths.append(path)
            target.calls.clear()
            registry.calls.clear()

            def upload(path):
                response = client.post(
                    path + "/intake/documents",
                    content=content,
                    headers={
                        "Content-Type": "application/pdf",
                        "X-Document-Name": "clean-company-profile.pdf",
                    },
                )
                assert response.status_code == 201
                document = response.json()
                assert document["state"] == "REVIEWED"
                assert document["completion_method"] == "AUTO_CONFIRMED"
                assert len(document["fields"]) == 4 and len(document["pages"]) == 1
                assert document["pages"][0]["extraction_method"] == "NATIVE_PDF_TEXT"

            # Probe must release before executor teardown waits for pending intakes.
            with (
                ThreadPoolExecutor(max_workers=level) as pool,
                ActiveProviderProbe() as probe,
            ):
                def observed(provider, document):
                    return probe.observe(lambda: original(provider, document))

                transport = client._transport
                original_handle = transport.handle_request

                def dispatched(request, handle=original_handle):
                    if request.url.path == "/health":
                        probe.begin_dispatch()
                    return handle(request)

                with (
                    patch.object(LocalPdfTextIdpProvider, "process", observed),
                    patch.object(transport, "handle_request", dispatched),
                ):
                    futures = [pool.submit(upload, path) for path in paths]
                    assert probe.entered.wait(20), "native provider never reached hold"
                    health = client.get("/health")
                    probe.complete_health()
                    assert health.status_code == 200
                    # Release before draining: the optimized health should finish held.
                    probe.health_done.set()
                    for future in futures:
                        future.result(timeout=20)
                assert probe.active == 0 and probe.held == 0 and probe.calls == level
                sample = {
                    "health_ms": (probe.completion_ns - probe.dispatch_ns) / 1e6,
                    "active_provider_count_at_dispatch": probe.active_at_dispatch,
                    "held_provider_count_at_dispatch": probe.held_at_dispatch,
                    "completed_while_provider_held": probe.completed_while_held,
                    "release_reason": probe.release_reason,
                    "completed_intakes": level,
                    "active_provider_count_after_intake": probe.active,
                    "target_mutations": 0,
                    "registry_operations": 0,
                    "external_calls": 0,
                }
            for path in paths:
                current = client.get(path)
                assert current.status_code == 200
                assert current.json()["status"] == "PENDING_INPUTS"
                assert current.json()["target_submission"]["state"] == "NOT_SUBMITTED"
            assert not target.calls and not registry.calls
            (warmup if index < 2 else samples).append(sample)
            print(f"HEALTH concurrency={level} observation={index + 1}/{groups + 2}", flush=True)
    return {"health_ms": perf.summary([s["health_ms"] for s in samples]),
            "samples": samples, "excluded_warmup": warmup}


def run_active_health(label, groups, levels, source_root):
    import importlib.metadata
    import os
    import platform
    import subprocess

    sys.path.insert(0, str(ROOT))
    from scripts import performance_optimization as perf

    source_root = source_root.resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_root, text=True).strip()
    if label == "before" and head != perf.BASE:
        raise RuntimeError("health baseline must be exact authorized BASE")
    if subprocess.check_output(["git", "diff", "HEAD", "--", "apps"], cwd=source_root):
        raise RuntimeError("health product source must match recorded HEAD")
    perf.ROOT = source_root
    perf.initialize()
    import app.main

    if not Path(app.main.__file__).resolve().is_relative_to(source_root):
        raise RuntimeError("health probe imported the wrong product source")
    content_path = source_root / "apps/backend/tests/fixtures/uat/clean-company-profile.pdf"
    content = content_path.read_bytes()
    result = {
        "label": label, "source_head": head, "baseline": perf.BASE,
        "product_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD:apps"], cwd=source_root, text=True
        ).strip(),
        "main_sha256": hashlib.sha256(Path(app.main.__file__).read_bytes()).hexdigest(),
        "method_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "resources_method_sha256": hashlib.sha256(
            Path(perf.__file__).read_bytes()).hexdigest(),
        "pdf_sha256": hashlib.sha256(content).hexdigest(),
        "python": platform.python_version(), "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "versions": {p: importlib.metadata.version(p) for p in (
            "fastapi", "starlette", "anyio", "httpx", "pydantic", "pypdfium2")},
        "groups": groups, "warmup_groups": 2, "release_budget_ms": 100,
        "operation_failsafe_seconds": 20,
        "method": "transport-entry dispatch during hold inside real native provider; "
                  "health completion releases hold, independent 100ms release if blocked; "
                  "not natural provider latency or throughput measurement",
        "workloads": {str(level): measure_active_health(groups, level, content, perf)
                      for level in levels},
    }
    destination = ROOT / ".runtime/performance-optimization/pr79-health"
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{label}-n{groups}.json"
    if output.exists():
        raise RuntimeError("health evidence output already exists; preserve prior observations")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": {
        k: v["health_ms"] for k, v in result["workloads"].items()}}), flush=True)
    return result


def run(label: str, groups: int, levels: list[int]) -> dict:
    sys.path.insert(0, str(ROOT))
    from scripts import performance_optimization as perf

    perf.initialize()

    result = {
        "label": label,
        "claim": "DEVELOPMENT_MEASUREMENT",
        "health_metric_status": "UNSYNCHRONIZED incidental timing; use --health-probe",
        "scope": (
            "one shared in-process ASGI application, document intake only; "
            "not full-case/network capacity"
        ),
        "head": perf.git("rev-parse", "HEAD"),
        "base": perf.BASE,
        "main_source_sha256": hashlib.sha256(
            (ROOT / "apps/backend/app/main.py").read_bytes()
        ).hexdigest(),
        "method_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "groups": groups,
        "warmup_groups": 2,
        "clock": "perf_counter_ns/process_time_ns",
        "method": (
            "setup/seed excluded; no observer/profiler in primary timing; "
            "separate established-app resource cohort; CPU is aggregate parent CPU/cohort "
            "divided by number of intakes, excluding native children"
        ),
        "workloads": {},
    }
    assert (
        perf.git("branch", "--show-current")
        == "feat/performance-computational-throughput-optimization"
    )
    content = (ROOT / "apps/backend/tests/fixtures/uat/clean-company-profile.pdf").read_bytes()
    for level in levels:
        result["workloads"][str(level)] = measure_level(label, groups, level, content, perf)
    path = ROOT / ".runtime/performance-optimization" / f"concurrency-{label}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", choices=["before", "after"], required=True)
    parser.add_argument("--groups", type=int, default=20)
    parser.add_argument("--concurrency", action="append", type=int, choices=[1, 5, 10, 20])
    parser.add_argument("--health-probe", action="store_true")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    if not 1 <= args.groups <= 30:
        parser.error("groups must be between 1 and 30")
    if args.health_probe:
        run_active_health(args.label, args.groups, args.concurrency or [1, 5], args.source_root)
    else:
        run(args.label, args.groups, args.concurrency or [1, 5])
