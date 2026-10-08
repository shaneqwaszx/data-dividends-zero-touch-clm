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


def run(label: str, groups: int, levels: list[int]) -> dict:
    sys.path.insert(0, str(ROOT))
    from scripts import performance_optimization as perf

    perf.initialize()

    result = {
        "label": label,
        "claim": "DEVELOPMENT_MEASUREMENT",
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
    args = parser.parse_args()
    if not 1 <= args.groups <= 30:
        parser.error("groups must be between 1 and 30")
    run(args.label, args.groups, args.concurrency or [1, 5])
