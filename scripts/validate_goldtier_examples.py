"""Classify sponsor GoldTier JSON examples against standalone OpenAPI schemas.

The validator reads the two ignored sponsor ZIP archives in memory. It never
modifies or exports sponsor material and reports only file names, JSON pointers,
and failed schema-rule names—not example values.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENAPI_ZIP = ROOT / "private" / "sponsor-artifacts" / "gt_eds_openapi_yaml_final.zip"
DEFAULT_EXAMPLES_ZIP = ROOT / "private" / "sponsor-artifacts" / "gt_eds_api_specs_json.zip"

VALID = "VALID"
INVALID = "INVALID / QUARANTINED"
NOT_VALIDATED = "NOT VALIDATED"

OPERATION_FILES = {
    "01_createRelatedParty": "createRelatedParty.yaml",
    "02_createPolicy": "createPolicy.yaml",
    "03_amendParty": "amendParty.yaml",
    "04_searchParty": "searchParty.yaml",
    "05_retrieveParty": "retrieveParty.yaml",
    "06_getPolicy": "getPolicy.yaml",
    "07_createShellCustomer": "createShellCustomer.yaml",
}
SEARCH_CRITERIA = {
    "dateOfBirth",
    "externalSystem",
    "externalSystemKey",
    "firstName",
    "lastName",
    "legalName",
    "lei",
    "middleName",
    "registrationNumber",
    "registrationNumberType",
}


@dataclass(frozen=True)
class Issue:
    section: str
    pointer: str
    rule: str


@dataclass(frozen=True)
class Result:
    example: str
    status: str
    issues: tuple[Issue, ...] = ()
    note: str | None = None


def _load_dependencies() -> tuple[Any, Any, Any]:
    try:
        import yaml
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        print(
            "Contract validation dependencies are unavailable. Install the pinned local "
            "requirements; no sponsor example was read.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    return yaml, Draft202012Validator, FormatChecker


def _zip_members_by_basename(archive: zipfile.ZipFile) -> dict[str, str]:
    members: dict[str, str] = {}
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        basename = Path(name).name
        if basename in members:
            raise ValueError(f"Duplicate archive basename: {basename}")
        members[basename] = name
    return members


def _operation(document: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    for route, path_item in document.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in {"get", "post"}:
                return route, method.upper(), operation
    raise ValueError("Standalone OpenAPI contains no supported operation")


def _schema_validator(
    document: dict[str, Any], schema: dict[str, Any], validator_class: Any, format_checker: Any
) -> Any:
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "components": document.get("components", {}),
        **schema,
    }
    return validator_class(wrapper, format_checker=format_checker())


def _pointer(parts: Iterable[object]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"


def _schema_issues(
    validator: Any, instance: Any, section: str, prefix: tuple[object, ...] = ()
) -> list[Issue]:
    issues: list[Issue] = []
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    for error in errors:
        path = prefix + tuple(error.absolute_path)
        if error.validator == "required" and isinstance(error.instance, dict):
            missing = sorted(set(error.validator_value) - set(error.instance))
            issues.extend(
                Issue(section, _pointer(path + (field,)), "required") for field in missing
            )
            continue
        if error.validator == "additionalProperties" and isinstance(error.instance, dict):
            allowed = set(error.schema.get("properties", {}))
            unexpected = sorted(set(error.instance) - allowed)
            issues.extend(
                Issue(section, _pointer(path + (field,)), "additionalProperties")
                for field in unexpected
            )
            continue
        issues.append(Issue(section, _pointer(path), str(error.validator)))
    return issues


def _route_pattern(route: str) -> re.Pattern[str]:
    escaped = re.escape(route)
    pattern = re.sub(r"\\\{[^{}]+\\\}", r"[^/]+", escaped)
    return re.compile(f"^{pattern}$")


def _find_parameter(
    operation: dict[str, Any], document: dict[str, Any], name: str, location: str
) -> dict[str, Any] | None:
    for raw in operation.get("parameters", []):
        parameter = raw
        if "$ref" in raw:
            target: Any = document
            for part in raw["$ref"][2:].split("/"):
                target = target[part]
            parameter = target
        if parameter.get("name") == name and parameter.get("in") == location:
            return parameter
    return None


def _request_issues(
    example: dict[str, Any],
    document: dict[str, Any],
    route: str,
    method: str,
    operation: dict[str, Any],
    validator_class: Any,
    format_checker: Any,
    body_only: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    body = example if body_only else example.get("body")
    request_body = operation.get("requestBody")
    if request_body is not None:
        if body is None:
            issues.append(Issue("body", "/body", "required"))
        else:
            schema = request_body["content"]["application/json"]["schema"]
            validator = _schema_validator(document, schema, validator_class, format_checker)
            issues.extend(_schema_issues(validator, body, "body"))

    if body_only:
        return issues

    if example.get("method") != method:
        issues.append(Issue("request", "/method", "const"))
    endpoint = example.get("endpoint")
    if not isinstance(endpoint, str) or _route_pattern(route).fullmatch(endpoint) is None:
        issues.append(Issue("request", "/endpoint", "canonicalPath"))

    containers = {
        "header": example.get("headers", {}),
        "path": example.get("pathParams", {}),
        "query": example.get("queryParams", {}),
    }
    headers = {str(key).lower(): value for key, value in containers["header"].items()}
    containers["header"] = headers

    for location, values in containers.items():
        for raw in operation.get("parameters", []):
            parameter = raw
            if "$ref" in raw:
                target: Any = document
                for part in raw["$ref"][2:].split("/"):
                    target = target[part]
                parameter = target
            if parameter.get("in") != location:
                continue
            name = str(parameter["name"])
            lookup = name.lower() if location == "header" else name
            if lookup not in values:
                if parameter.get("required"):
                    issues.append(Issue(location, _pointer((location, name)), "required"))
                continue
            validator = _schema_validator(
                document, parameter.get("schema", {}), validator_class, format_checker
            )
            issues.extend(
                _schema_issues(validator, values[lookup], location, (location, name))
            )

    if "authorization" not in headers:
        issues.append(Issue("header", "/header/Authorization", "securityRequired"))
    if method == "POST" and "content-type" not in headers:
        issues.append(Issue("header", "/header/Content-Type", "required"))

    if method == "POST" and isinstance(body, dict):
        source_context = body.get("sourceContext")
        source_case = source_context.get("sourceCaseId") if isinstance(source_context, dict) else None
        header_case = headers.get("x-source-case-id")
        if source_case is not None and header_case is not None and source_case != header_case:
            issues.append(
                Issue("cross-field", "/body/sourceContext/sourceCaseId", "matchesHeader")
            )

    if operation.get("operationId") == "searchParty":
        query = containers["query"]
        if not SEARCH_CRITERIA.intersection(query):
            issues.append(Issue("query", "/query", "atLeastOneSearchCriterion"))

    return issues


def _parameter_fragment_issues(
    example: dict[str, Any],
    document: dict[str, Any],
    operation: dict[str, Any],
    validator_class: Any,
    format_checker: Any,
) -> list[Issue]:
    issues: list[Issue] = []
    for location, container_name in (("path", "pathParams"), ("query", "queryParams")):
        values = example.get(container_name, {})
        if not isinstance(values, dict):
            issues.append(Issue(location, _pointer((container_name,)), "type"))
            continue
        for name, value in values.items():
            parameter = _find_parameter(operation, document, name, location)
            if parameter is None:
                issues.append(Issue(location, _pointer((container_name, name)), "definedParameter"))
                continue
            validator = _schema_validator(
                document, parameter.get("schema", {}), validator_class, format_checker
            )
            issues.extend(
                _schema_issues(validator, value, location, (container_name, name))
            )
    if operation.get("operationId") == "searchParty":
        query = example.get("queryParams", {})
        if not isinstance(query, dict) or not SEARCH_CRITERIA.intersection(query):
            issues.append(Issue("query", "/queryParams", "atLeastOneSearchCriterion"))
    return issues


def _response_status(filename: str, data: dict[str, Any], operation: dict[str, Any]) -> str | None:
    if "partial_207" in filename:
        return "207"
    if "error" in filename:
        status = data.get("status")
        return str(status) if isinstance(status, int) else "422"
    if "success" in filename:
        for status in operation.get("responses", {}):
            if str(status).startswith("2") and str(status) != "207":
                return str(status)
    return None


def _classify_example(
    relative_name: str,
    data: Any,
    document: dict[str, Any],
    validator_class: Any,
    format_checker: Any,
) -> Result:
    route, method, operation = _operation(document)
    filename = Path(relative_name).name
    if not isinstance(data, dict):
        return Result(relative_name, INVALID, (Issue("document", "/", "type"),))

    if filename.startswith(("full_request", "minimum_viable_request")):
        issues = _request_issues(
            data,
            document,
            route,
            method,
            operation,
            validator_class,
            format_checker,
            body_only=False,
        )
    elif filename.startswith(("request_body",)):
        issues = _request_issues(
            data,
            document,
            route,
            method,
            operation,
            validator_class,
            format_checker,
            body_only=True,
        )
    elif filename.startswith("request_parameters"):
        issues = _parameter_fragment_issues(
            data,
            document,
            operation,
            validator_class,
            format_checker,
        )
    elif filename.startswith("response"):
        status = _response_status(filename, data, operation)
        response = next(
            (
                value
                for key, value in operation.get("responses", {}).items()
                if status is not None and str(key) == status
            ),
            None,
        )
        content = response.get("content", {}) if isinstance(response, dict) else {}
        media = next(
            (value for key, value in content.items() if key.endswith("json")),
            None,
        )
        schema = media.get("schema") if isinstance(media, dict) else None
        if schema is None:
            return Result(relative_name, NOT_VALIDATED, note="no matching response schema")
        validator = _schema_validator(document, schema, validator_class, format_checker)
        issues = _schema_issues(validator, data, "response")
    else:
        return Result(relative_name, NOT_VALIDATED, note="no deterministic operation binding")

    return Result(relative_name, INVALID if issues else VALID, tuple(issues))


def validate_archives(openapi_zip: Path, examples_zip: Path) -> list[Result]:
    yaml, validator_class, format_checker = _load_dependencies()
    with zipfile.ZipFile(openapi_zip) as openapi_archive, zipfile.ZipFile(
        examples_zip
    ) as examples_archive:
        openapi_members = _zip_members_by_basename(openapi_archive)
        documents = {
            directory: yaml.safe_load(openapi_archive.read(openapi_members[filename]))
            for directory, filename in OPERATION_FILES.items()
        }

        results: list[Result] = []
        for name in sorted(examples_archive.namelist()):
            if not name.lower().endswith(".json"):
                continue
            relative = "/".join(Path(name).parts[1:])
            directory = Path(relative).parts[0] if Path(relative).parts else ""
            if directory not in OPERATION_FILES:
                note = (
                    "future operation is outside the provisional seven-operation contract"
                    if directory.startswith("99_")
                    else "reusable/shared object has no deterministic operation binding"
                )
                results.append(Result(relative, NOT_VALIDATED, note=note))
                continue
            try:
                data = json.loads(examples_archive.read(name).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                results.append(
                    Result(relative, INVALID, (Issue("document", "/", "validJson"),))
                )
                continue
            results.append(
                _classify_example(
                    relative,
                    data,
                    documents[directory],
                    validator_class,
                    format_checker,
                )
            )
    return results


def _print_results(results: list[Result]) -> None:
    for result in results:
        print(f"{result.status}: {result.example}")
        for issue in result.issues:
            print(f"  - {issue.section} {issue.pointer} [{issue.rule}]")
        if result.note:
            print(f"  - {result.note}")
    counts = Counter(result.status for result in results)
    print(
        "SUMMARY: "
        f"VALID={counts[VALID]} "
        f"INVALID_QUARANTINED={counts[INVALID]} "
        f"NOT_VALIDATED={counts[NOT_VALIDATED]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openapi-zip", type=Path, default=DEFAULT_OPENAPI_ZIP)
    parser.add_argument("--examples-zip", type=Path, default=DEFAULT_EXAMPLES_ZIP)
    parser.add_argument(
        "--if-present",
        action="store_true",
        help="Exit successfully as NOT VALIDATED when private archives are absent.",
    )
    parser.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Return exit code 1 when any example is quarantined.",
    )
    args = parser.parse_args()

    missing = [path for path in (args.openapi_zip, args.examples_zip) if not path.is_file()]
    if missing:
        print("NOT VALIDATED: sponsor OpenAPI/example archives are absent; no private file was read.")
        return 0 if args.if_present else 2

    results = validate_archives(args.openapi_zip, args.examples_zip)
    _print_results(results)
    return 1 if args.fail_on_invalid and any(result.status == INVALID for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
