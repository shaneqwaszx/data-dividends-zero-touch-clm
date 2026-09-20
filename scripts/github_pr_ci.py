"""Report pull-request checks for one observed head SHA without mutating GitHub."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

VIEW_FIELDS = (
    "number,url,state,isDraft,headRefName,headRefOid,baseRefName,"
    "reviewDecision,mergeStateStatus"
)
CHECK_FIELDS = "bucket,event,link,name,state,workflow"
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
_SAFE_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_SAFE_CHECK_TEXT = re.compile(r"^[A-Za-z0-9 ._:/()\[\]+-]{0,200}$")
_REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_KNOWN_STATES = {"OPEN", "CLOSED", "MERGED"}
_KNOWN_REVIEW_DECISIONS = {"", "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED"}
_KNOWN_MERGE_STATES = {
    "BEHIND",
    "BLOCKED",
    "CLEAN",
    "DIRTY",
    "DRAFT",
    "HAS_HOOKS",
    "UNKNOWN",
    "UNSTABLE",
}
_PASS_BUCKETS = {"pass"}
_FAIL_BUCKETS = {"fail", "cancel"}
_PENDING_BUCKETS = {"pending"}
_SKIP_BUCKETS = {"skipping", "skip"}
_SUBPROCESS_ENV_KEYS = (
    "APPDATA",
    "GH_CONFIG_DIR",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
)


class ObservationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Target:
    argument: str | None
    kind: str
    repository: str | None = None
    number: int | None = None
    branch: str | None = None


@dataclass(frozen=True)
class ExpectedObservation:
    repository: str
    argument: str
    number: int | None
    branch: str | None


def _valid_branch(value: object) -> bool:
    return (
        isinstance(value, str)
        and _BRANCH_PATTERN.fullmatch(value) is not None
        and not value.startswith("-")
        and ".." not in value
        and "//" not in value
        and "@{" not in value
        and not value.endswith(("/", ".", ".lock"))
    )


def _repository(owner: str, name: str) -> str:
    if not _REPOSITORY_COMPONENT.fullmatch(owner) or not _REPOSITORY_COMPONENT.fullmatch(name):
        raise ObservationError("REPOSITORY_IDENTITY_INVALID")
    return f"{owner}/{name}"


def _parse_pr_url(value: object) -> tuple[str, int, str]:
    if not isinstance(value, str) or not value.isascii() or len(value) > 1000:
        raise ObservationError("PR_URL_INVALID")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ObservationError("PR_URL_INVALID") from exc
    path = parsed.path.strip("/").split("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or len(path) != 4
        or path[2] != "pull"
        or not path[3].isascii()
        or not path[3].isdecimal()
        or int(path[3]) <= 0
        or parsed.path != f"/{path[0]}/{path[1]}/pull/{path[3]}"
    ):
        raise ObservationError("PR_URL_INVALID")
    repository = _repository(path[0], path[1])
    number = int(path[3])
    return repository, number, f"https://github.com/{repository}/pull/{number}"


def _target(value: str | None, environment: Mapping[str, str] | None = None) -> Target:
    del environment
    if value is None:
        return Target(None, "current")
    if value.isascii() and value.isdecimal() and int(value) > 0:
        number = int(value)
        return Target(str(number), "number", number=number)
    if value.startswith("https://"):
        try:
            repository, number, canonical = _parse_pr_url(value)
        except ObservationError:
            raise argparse.ArgumentTypeError("PR URL is not an accepted GitHub pull-request URL")
        return Target(canonical, "url", repository=repository, number=number)
    if not _valid_branch(value):
        raise argparse.ArgumentTypeError("target must be a positive PR number, PR URL, or safe branch")
    return Target(value, "branch", branch=value)


def _subprocess_environment() -> dict[str, str]:
    return {key: os.environ[key] for key in _SUBPROCESS_ENV_KEYS if key in os.environ}


def _run_text(command: Sequence[str], deadline: float) -> str:
    allowed = {
        ("git", "remote", "get-url", "origin"),
        ("git", "branch", "--show-current"),
    }
    if tuple(command) not in allowed:
        raise ObservationError("LOCAL_GIT_COMMAND_INVALID")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ObservationError("TIMEOUT")
    try:
        completed = subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=min(10.0, remaining),
            check=False,
            shell=False,
            env=_subprocess_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ObservationError("LOCAL_GIT_UNAVAILABLE") from exc
    value = completed.stdout.strip()
    if completed.returncode != 0 or not value or len(value) > 1000 or not value.isascii():
        raise ObservationError("LOCAL_GIT_UNAVAILABLE")
    return value


def _repository_from_remote(value: str) -> str:
    try:
        https = urlsplit(value)
    except ValueError as exc:
        raise ObservationError("REPOSITORY_IDENTITY_INVALID") from exc
    if https.scheme:
        path = https.path.strip("/").split("/")
        if (
            https.scheme != "https"
            or https.hostname != "github.com"
            or https.username
            or https.password
            or https.port is not None
            or https.query
            or https.fragment
            or len(path) != 2
            or https.path != f"/{path[0]}/{path[1]}"
        ):
            raise ObservationError("REPOSITORY_IDENTITY_INVALID")
        name = path[1].removesuffix(".git")
        return _repository(path[0], name)
    match = re.fullmatch(
        r"git@github\.com:([A-Za-z0-9][A-Za-z0-9._-]{0,99})/"
        r"([A-Za-z0-9][A-Za-z0-9._-]{0,103})",
        value,
    )
    if not match:
        raise ObservationError("REPOSITORY_IDENTITY_INVALID")
    name = match.group(2).removesuffix(".git")
    return _repository(match.group(1), name)


def _expected_observation(target: Target, deadline: float) -> ExpectedObservation:
    if target.kind == "url":
        if target.repository is None or target.number is None or target.argument is None:
            raise ObservationError("TARGET_IDENTITY_INVALID")
        return ExpectedObservation(target.repository, target.argument, target.number, None)

    repository = _repository_from_remote(
        _run_text(["git", "remote", "get-url", "origin"], deadline)
    )
    if target.kind == "number":
        if target.number is None:
            try:
                number = int(target.argument or "")
            except ValueError as exc:
                raise ObservationError("TARGET_IDENTITY_INVALID") from exc
        else:
            number = target.number
        return ExpectedObservation(repository, str(number), number, None)
    if target.kind == "branch":
        branch = target.branch or target.argument
    elif target.kind == "current":
        branch = _run_text(["git", "branch", "--show-current"], deadline)
    else:
        raise ObservationError("TARGET_IDENTITY_INVALID")
    if not _valid_branch(branch):
        raise ObservationError("LOCAL_BRANCH_UNAVAILABLE")
    return ExpectedObservation(repository, branch, None, branch)


def _run_json(command: Sequence[str], deadline: float) -> tuple[int, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ObservationError("TIMEOUT")
    try:
        completed = subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=min(30.0, remaining),
            check=False,
            shell=False,
            env=_subprocess_environment(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ObservationError("COMMAND_TIMEOUT") from exc
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else None
    except json.JSONDecodeError as exc:
        raise ObservationError("INVALID_GH_JSON") from exc
    return completed.returncode, payload


def _view(
    argument: str,
    expected: ExpectedObservation,
    deadline: float,
) -> dict[str, Any]:
    command = [
        "gh",
        "pr",
        "view",
        argument,
        "--repo",
        expected.repository,
        "--json",
        VIEW_FIELDS,
    ]
    return_code, payload = _run_json(command, deadline)
    if return_code != 0 or not isinstance(payload, dict):
        raise ObservationError("PR_VIEW_UNAVAILABLE")
    number = payload.get("number")
    head_sha = payload.get("headRefOid")
    head_ref_name = payload.get("headRefName")
    state = payload.get("state")
    review_decision = payload.get("reviewDecision")
    is_draft = payload.get("isDraft")
    base_ref_name = payload.get("baseRefName")
    merge_state = payload.get("mergeStateStatus")
    if (
        not isinstance(number, int)
        or isinstance(number, bool)
        or number <= 0
        or (expected.number is not None and number != expected.number)
        or not _valid_branch(head_ref_name)
        or (expected.branch is not None and head_ref_name != expected.branch)
        or not isinstance(head_sha, str)
        or not isinstance(state, str)
        or state not in _KNOWN_STATES
        or not isinstance(is_draft, bool)
        or not _valid_branch(base_ref_name)
        or not isinstance(merge_state, str)
        or merge_state not in _KNOWN_MERGE_STATES
    ):
        raise ObservationError("PR_VIEW_INVALID")
    if not _SAFE_SHA.fullmatch(head_sha):
        raise ObservationError("PR_HEAD_INVALID")
    normalized_review = "" if review_decision is None else review_decision
    if (
        not isinstance(normalized_review, str)
        or normalized_review not in _KNOWN_REVIEW_DECISIONS
    ):
        raise ObservationError("PR_VIEW_INVALID")
    try:
        repository, url_number, _ = _parse_pr_url(payload.get("url"))
    except ObservationError as exc:
        raise ObservationError("PR_VIEW_INVALID") from exc
    if repository.casefold() != expected.repository.casefold() or url_number != number:
        raise ObservationError("PR_IDENTITY_MISMATCH")
    return {
        "number": number,
        "url": f"https://github.com/{expected.repository}/pull/{number}",
        "state": state,
        "isDraft": is_draft,
        "headRefName": head_ref_name,
        "headRefOid": head_sha,
        "baseRefName": base_ref_name,
        "reviewDecision": normalized_review,
        "mergeStateStatus": merge_state,
    }


def _checks(
    number: int,
    repository: str,
    deadline: float,
    *,
    required: bool,
) -> list[dict[str, str]]:
    command = ["gh", "pr", "checks", str(number), "--repo", repository]
    if required:
        command.append("--required")
    command.extend(["--json", CHECK_FIELDS])
    return_code, payload = _run_json(command, deadline)
    if return_code not in {0, 8}:
        if payload == []:
            return []
        raise ObservationError("CHECKS_UNAVAILABLE")
    if not isinstance(payload, list):
        raise ObservationError("CHECKS_INVALID")
    result: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ObservationError("CHECKS_INVALID")
        normalized: dict[str, str] = {}
        for field in ("bucket", "event", "name", "state", "workflow"):
            value = item.get(field)
            if value is None:
                value = ""
            if not isinstance(value, str) or not _SAFE_CHECK_TEXT.fullmatch(value):
                raise ObservationError("CHECKS_INVALID")
            normalized[field] = value
        link = item.get("link") or ""
        if not isinstance(link, str) or len(link) > 500 or not link.isascii():
            raise ObservationError("CHECKS_INVALID")
        if link:
            parsed_link = urlsplit(link)
            if (
                parsed_link.scheme != "https"
                or not parsed_link.hostname
                or parsed_link.username
                or parsed_link.password
            ):
                raise ObservationError("CHECKS_INVALID")
            link = urlunsplit(("https", parsed_link.netloc, parsed_link.path, "", ""))
        normalized["link"] = link
        normalized["bucket"] = normalized["bucket"].lower()
        result.append(normalized)
    return sorted(result, key=lambda item: (item["workflow"], item["name"], item["link"]))


def _identity(check: Mapping[str, str]) -> tuple[str, str, str]:
    return (check["workflow"], check["name"], check["event"])


def _outcome(required: Sequence[Mapping[str, str]]) -> str:
    if not required:
        return "NO_REQUIRED_CHECKS"
    buckets = {check["bucket"] for check in required}
    known = _PASS_BUCKETS | _FAIL_BUCKETS | _PENDING_BUCKETS | _SKIP_BUCKETS
    if not buckets <= known:
        return "CHECKS_UNAVAILABLE"
    if buckets <= _SKIP_BUCKETS:
        return "REQUIRED_CHECKS_NOT_EXECUTED"
    if buckets & _FAIL_BUCKETS:
        return "REQUIRED_CHECKS_FAILED"
    if buckets & _PENDING_BUCKETS:
        return "PENDING"
    if buckets <= (_PASS_BUCKETS | _SKIP_BUCKETS) and buckets & _PASS_BUCKETS:
        return "REQUIRED_CHECKS_PASSED"
    return "CHECKS_UNAVAILABLE"


def _safe_view(view: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "number": view.get("number"),
        "url": view.get("url"),
        "state": view.get("state"),
        "is_draft": view.get("isDraft"),
        "head_ref_name": view.get("headRefName"),
        "head_sha": view.get("headRefOid"),
        "base_ref_name": view.get("baseRefName"),
        "review_decision": view.get("reviewDecision"),
        "merge_state_status": view.get("mergeStateStatus"),
    }


def _error_report(code: str) -> tuple[int, dict[str, Any]]:
    return 2, {
        "outcome": code,
        "required_checks": [],
        "optional_failures": [],
        "advisory": "Evidence reporter only; not merge approval.",
    }


def observe(target: Target, *, wait: bool, timeout_seconds: float, poll_seconds: float) -> tuple[int, dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    try:
        expected = _expected_observation(target, deadline)
    except ObservationError as exc:
        return _error_report(exc.code)
    argument = expected.argument
    while True:
        try:
            initial = _view(argument, expected, deadline)
            number = int(initial["number"])
            required = _checks(number, expected.repository, deadline, required=True)
            all_checks = _checks(number, expected.repository, deadline, required=False)
            final_view = _view(str(number), expected, deadline)
        except ObservationError as exc:
            return _error_report(exc.code)
        if initial["headRefOid"] != final_view["headRefOid"]:
            if wait and time.monotonic() < deadline:
                argument = str(number)
                continue
            return 2, {
                "outcome": "HEAD_CHANGED",
                "pr": _safe_view(final_view),
                "observed_head_sha": initial["headRefOid"],
                "required_checks": [],
                "optional_failures": [],
                "advisory": "Evidence reporter only; not merge approval.",
            }

        required_ids = {_identity(check) for check in required}
        optional_failures = [
            check
            for check in all_checks
            if _identity(check) not in required_ids and check["bucket"] in _FAIL_BUCKETS
        ]
        outcome = _outcome(required)
        report = {
            "outcome": outcome,
            "pr": _safe_view(initial),
            "observed_head_sha": initial["headRefOid"],
            "required_checks": required,
            "optional_failures": optional_failures,
            "advisory": "Evidence reporter only; not merge approval.",
        }
        if initial.get("state") != "OPEN":
            report["outcome"] = "PR_NOT_OPEN"
            return 2, report
        if initial.get("isDraft"):
            report["outcome"] = "DRAFT"
            return 2, report
        if outcome == "REQUIRED_CHECKS_PASSED":
            return 0, report
        if not wait or outcome != "PENDING":
            return (8 if outcome == "PENDING" else 2), report
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            report["outcome"] = "TIMEOUT"
            return 2, report
        time.sleep(min(poll_seconds, remaining))
        argument = str(number)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", help="PR number, GitHub PR URL, or branch")
    parser.add_argument("--wait", action="store_true", help="wait for pending required checks")
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        target = _target(args.target)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if not 1 <= args.timeout_seconds <= 3600:
        parser.error("--timeout-seconds must be between 1 and 3600")
    if not 1 <= args.poll_seconds <= 300:
        parser.error("--poll-seconds must be between 1 and 300")
    try:
        return_code, report = observe(
            target,
            wait=args.wait,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
    except ObservationError as exc:
        return_code = 2
        report = {
            "outcome": exc.code,
            "required_checks": [],
            "optional_failures": [],
            "advisory": "Evidence reporter only; not merge approval.",
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
