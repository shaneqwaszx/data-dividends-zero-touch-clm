"""Run the explicit physical Mongo suites with contained output."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
PHYSICAL_SUITES = (
    BACKEND_ROOT / "tests" / "test_garden_uen_partial_resume_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_final_review_editing_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_sponsor_demo_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_batch_review_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_synthetic_company_pack_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_zero_touch_database_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_classification_conflict_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase12_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase13_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase14_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase14_5_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase16_registry_cache_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase17_case_activity_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase18_case_portfolio_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase19_case_timing_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_provider_identity_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_slice_c_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_phase24c_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_slice_d_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_slice_e_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_s1_date_filters_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_s2_intelligence_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_s3_submission_real_mongo.py",
    BACKEND_ROOT / "tests" / "test_policy_recovery_real_mongo.py",
)
_SUMMARY_PATTERN = re.compile(
    r"(?P<count>\d+)\s+(?P<kind>passed|failed|skipped|errors?)\b",
    re.IGNORECASE,
)
_TIMED_SUMMARY_PATTERN = re.compile(r"\bin\s+\d+(?:\.\d+)?s\b", re.IGNORECASE)
_SYSTEM_ENV_KEYS = (
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


def _child_environment(uri: str, source: Mapping[str, str] | None = None) -> dict[str, str]:
    current = os.environ if source is None else source
    environment = {key: current[key] for key in _SYSTEM_ENV_KEYS if key in current}
    environment.update(
        {
            "PHASE12_MONGO_URI": uri,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(BACKEND_ROOT))),
            "PYTEST_ADDOPTS": "",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    return environment


def _run_pytest(
    arguments: Sequence[str], *, uri: str, deadline: float,
) -> subprocess.CompletedProcess[str]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("physical Mongo test deadline exceeded")
    return subprocess.run(
        [sys.executable, "-m", "pytest", *arguments],
        cwd=ROOT,
        env=_child_environment(uri),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=remaining,
        check=False,
        shell=False,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def _summary(output: str) -> dict[str, int] | None:
    for line in reversed(output.splitlines()):
        if not _TIMED_SUMMARY_PATTERN.search(line):
            continue
        matches = list(_SUMMARY_PATTERN.finditer(line))
        if not matches:
            continue
        counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        for match in matches:
            kind = match.group("kind").lower()
            if kind == "error":
                kind = "errors"
            counts[kind] += int(match.group("count"))
        return {"total": sum(counts.values()), **counts}
    return None


def _suite_arguments() -> list[str]:
    return [str(path.relative_to(ROOT)) for path in PHYSICAL_SUITES]


def run(*, timeout_seconds: float) -> int:
    uri = os.environ.get("PHASE12_MONGO_URI", "")
    if not uri:
        print("PHYSICAL_MONGO_RESULT=BLOCKED; REASON=PHASE12_MONGO_URI_UNAVAILABLE")
        return 2
    missing = [path.name for path in PHYSICAL_SUITES if not path.is_file()]
    if missing:
        print(f"PHYSICAL_MONGO_RESULT=FAILED; REASON=MISSING_SUITES; COUNT={len(missing)}")
        return 2
    deadline = time.monotonic() + timeout_seconds
    suite_arguments = _suite_arguments()
    common = ["-o", "addopts=", "-p", "no:cacheprovider", "--tb=no", "-q"]
    try:
        collection = _run_pytest(
            [*suite_arguments, *common, "--collect-only"],
            uri=uri,
            deadline=deadline,
        )
        collected_output = _combined_output(collection)
        if collection.returncode == 5:
            print("PHYSICAL_MONGO_RESULT=BLOCKED; REASON=NO_TESTS_COLLECTED")
            return 2
        if collection.returncode != 0:
            print(
                "PHYSICAL_MONGO_RESULT=FAILED; REASON=COLLECTION_FAILED; "
                f"EXIT_CODE={collection.returncode}"
            )
            return 2
        uncollected = [
            path.name
            for path in PHYSICAL_SUITES
            if path.name not in collected_output.replace("\\", "/")
        ]
        if uncollected:
            print(
                "PHYSICAL_MONGO_RESULT=FAILED; REASON=SUITE_OWNERSHIP_MISMATCH; "
                f"COUNT={len(uncollected)}"
            )
            return 2

        execution = _run_pytest(
            [*suite_arguments, *common],
            uri=uri,
            deadline=deadline,
        )
    except subprocess.TimeoutExpired:
        print("PHYSICAL_MONGO_RESULT=FAILED; REASON=TIMEOUT")
        return 2
    except TimeoutError:
        print("PHYSICAL_MONGO_RESULT=FAILED; REASON=TIMEOUT")
        return 2
    counts = _summary(_combined_output(execution))
    if execution.returncode == 5:
        print("PHYSICAL_MONGO_RESULT=BLOCKED; REASON=NO_TESTS_COLLECTED")
        return 2
    if counts is None:
        print("PHYSICAL_MONGO_RESULT=FAILED; REASON=SUMMARY_UNAVAILABLE")
        return 2
    summary = (
        f"COLLECTED={counts['total']}; PASSED={counts['passed']}; FAILED={counts['failed']}; "
        f"ERRORS={counts['errors']}; SKIPPED={counts['skipped']}"
    )
    if counts["total"] == 0:
        print(f"PHYSICAL_MONGO_RESULT=BLOCKED; REASON=NO_TESTS_COLLECTED; {summary}")
        return 2
    if execution.returncode != 0:
        print(
            "PHYSICAL_MONGO_RESULT=FAILED; REASON=EXECUTION_FAILED; "
            f"EXIT_CODE={execution.returncode}; {summary}"
        )
        return 1
    if counts["failed"] or counts["errors"]:
        print(f"PHYSICAL_MONGO_RESULT=FAILED; REASON=RESULT_REPORT_INCONSISTENT; {summary}")
        return 2
    if counts["passed"] == 0:
        print(f"PHYSICAL_MONGO_RESULT=BLOCKED; REASON=ALL_SKIPPED; {summary}")
        return 2
    if counts["skipped"]:
        print(f"PHYSICAL_MONGO_RESULT=BLOCKED; REASON=REQUIRED_TESTS_SKIPPED; {summary}")
        return 2
    print(f"PHYSICAL_MONGO_RESULT=PASSED; SUITES={len(PHYSICAL_SUITES)}; {summary}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    args = parser.parse_args(argv)
    if not 30 <= args.timeout_seconds <= 3600:
        parser.error("--timeout-seconds must be between 30 and 3600")
    return run(timeout_seconds=args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
