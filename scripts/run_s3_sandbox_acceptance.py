"""One synthetic, case-bound XPI acceptance; safe output and no mutation replay.

External mode is a separately authorized, interactive run. It consumes only the
three required backend XPI values from the explicitly supplied configuration file.
It pauses at the frozen final review until an exact independent pre-mutation PASS.
The default is offline and does not read configuration or contact any provider.
"""

from __future__ import annotations

import argparse
import json
import secrets
from collections.abc import Mapping
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from app.config import Settings
from app.connectors.acra import AcraAddressPayload, AcraCompanyPayload
from app.connectors.goldtier_xpi import (
    GoldTierXpiHttpResponse,
    GoldTierXpiHttpTransport,
    GoldTierXpiMalformedResponseError,
    HttpxGoldTierXpiTransport,
    _response_identifier,
)
from app.connectors.mock_acra import MockAcraConnector
from app.services.authentication import generate_scrypt_password_hash
from fastapi.testclient import TestClient
from pydantic import SecretStr

from scripts.mongo_test_safety import (
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)


class AcceptanceBlocked(RuntimeError):
    """Only fixed, public diagnostic codes may leave this runner."""


class SyntheticAcceptanceAcra(MockAcraConnector):
    """Task-only, single-identity Mock DTOs; never official registry evidence."""

    def __init__(self, name: str, uen: str) -> None:
        super().__init__()
        self.name, self.uen = name, uen

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        if uen != self.uen:
            return None
        return AcraCompanyPayload(
            uen=uen, entity_name=self.name, country_code="SG",
            entity_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
            entity_status="SYNTHETIC", registration_date=date(2026, 10, 4),
            registered_address=AcraAddressPayload(
                block="1", street="SYNTHETIC ACCEPTANCE WAY", unit="#01-01",
                postal_code="018956", country_code="SG",
            ),
            source_environment="MOCK",
            source_endpoint=f"https://synthetic.acra.invalid/entities/{uen}",
            retrieved_at=datetime.now(UTC),
        )

    def fetch_ownership_parties(self, uen: str):  # type: ignore[no-untyped-def]
        original = super().fetch_ownership_parties(uen)
        return original.model_copy(update={"ownership_parties": (
            self._person_party("SYNTHETIC_A", "POC Synthetic Owner A", "70"),
            self._person_party("SYNTHETIC_B", "POC Synthetic Owner B", "30"),
        )})

    def fetch_relationships(self, uen: str):  # type: ignore[no-untyped-def]
        original = super().fetch_relationships(uen)
        return original.model_copy(update={"relationships": (
            self._relationship("SYNTHETIC_REL_A", f"ENTITY_{uen}", "SYNTHETIC_A", "70"),
            self._relationship("SYNTHETIC_REL_B", f"ENTITY_{uen}", "SYNTHETIC_B", "30"),
        )})


class OfflineAcceptanceTransport:
    """Deterministic protocol responses, explicitly labelled offline in receipts."""

    def __init__(self, name: str, uen: str) -> None:
        self.name, self.uen, self.created = name, uen, False

    def request(self, method: str, url: str, **kwargs: Any) -> GoldTierXpiHttpResponse:
        del kwargs
        path = urlsplit(url).path
        if method == "GET":
            body = ([{"goldTierId": "SYNTHETIC-GT-S3", "legalName": self.name,
                      "registrationNumber": self.uen, "countryOfIncorporation": "SG"}]
                    if self.created else [])
            return GoldTierXpiHttpResponse(200, body)
        if path.endswith("/customers/create"):
            self.created = True
            return GoldTierXpiHttpResponse(200, {"goldTierId": "SYNTHETIC-GT-S3"})
        if path.endswith("/customers/createPolicy"):
            return GoldTierXpiHttpResponse(200, {"policyId": "SYNTHETIC-POLICY-S3"})
        raise AcceptanceBlocked("OFFLINE_UNEXPECTED_OPERATION")


class BoundedAcceptanceTransport:
    """Reserve a fixed single-identity budget before the existing real transport."""

    def __init__(self, delegate: GoldTierXpiHttpTransport, *, origin: str,
                 environment: str, name: str, uen: str) -> None:
        self.delegate = delegate
        self.origin, self.environment, self.name, self.uen = origin.rstrip("/"), environment, name, uen
        self.counts = {"SEARCH": 0, "SHELL": 0, "POLICY": 0, "AMEND": 0, "READBACK": 0}
        self.writes_approved = False
        self.mutations_stopped = False
        self.no_match = False
        self.party_id: str | None = None
        self.shell_payload: dict[str, Any] | None = None
        self.external_key: str | None = None
        self.events: list[dict[str, Any]] = []
        self.case_id: str | None = None
        self.preparation_diagnostics: dict[str, Any] = {}

    def bind_review(self, preview: dict[str, Any], case_id: str) -> None:
        shell = next(item for item in preview["operations"] if item["operation"] == "SHELL")
        payload: dict[str, Any] = {}
        for field in shell["fields"]:
            parts = field["target_field"].split(".")
            if len(parts) == 1:
                payload[parts[0]] = field["value"]
            else:
                payload.setdefault(parts[0], {})[parts[1]] = field["value"]
        expected_key = "FYP-" + case_id.replace("-", "").upper()
        if (payload["legalName"] != self.name
                or payload["registration"]["registrationNumber"] != self.uen
                or payload["systemReference"]["customerExternalSystemKey"] != expected_key):
            raise AcceptanceBlocked("FROZEN_REVIEW_IDENTITY_MISMATCH")
        self.shell_payload, self.external_key = payload, expected_key

    def request(self, method: str, url: str, *, headers: Mapping[str, str],
                json_body: object | None, timeout_seconds: float,
                max_response_bytes: int) -> GoldTierXpiHttpResponse:
        parsed = urlsplit(url)
        root = f"/{self.environment}/gt-xpi/v1"
        if f"{parsed.scheme}://{parsed.netloc}" != self.origin or parsed.fragment:
            raise AcceptanceBlocked("UNAUTHORIZED_PROVIDER_ORIGIN")
        if method == "GET" and parsed.path == root + "/customers/search":
            query = parse_qs(parsed.query, keep_blank_values=True)
            if query == {"legalName": [self.name], "countryOfIncorporation": ["SG"]}:
                operation = "SEARCH" if self.counts["SHELL"] == 0 else "READBACK"
            elif self.party_id is not None and query == {"goldTierID": [self.party_id]}:
                operation = "READBACK"
            else:
                raise AcceptanceBlocked("UNAUTHORIZED_SEARCH_IDENTITY")
            if self.counts[operation] >= 2:
                raise AcceptanceBlocked("READ_ONLY_BUDGET_EXHAUSTED")
        elif method == "POST" and not parsed.query:
            if not self.writes_approved or self.mutations_stopped or not self.no_match:
                raise AcceptanceBlocked("MUTATION_NOT_AUTHORIZED")
            if parsed.path == root + "/customers/create":
                operation = "SHELL"
                if self.shell_payload is None or json_body != self.shell_payload:
                    raise AcceptanceBlocked("UNREVIEWED_SHELL_PAYLOAD")
            elif parsed.path == root + "/customers/createPolicy":
                operation = "POLICY"
                expected = {
                    "customerExternalSystem": "DSD", "customerExternalSystemKey": self.external_key,
                    "goldTierId": self.party_id, "policy": "Singapore",
                    "bookingEntity": "ANZBGL (Singapore Branch)",
                    "accountEntityType": "", "productType": "",
                }
                if self.party_id is None or json_body != expected:
                    raise AcceptanceBlocked("UNREVIEWED_POLICY_PAYLOAD")
            else:
                raise AcceptanceBlocked("UNAUTHORIZED_MUTATION_OPERATION")
            if self.counts[operation] >= 1:
                raise AcceptanceBlocked("MUTATION_BUDGET_EXHAUSTED")
        else:
            raise AcceptanceBlocked("UNAUTHORIZED_OPERATION")
        self.counts[operation] += 1
        event: dict[str, Any] = {"operation": operation, "attempt": self.counts[operation]}
        self.events.append(event)
        try:
            response = self.delegate.request(
                method, url, headers=headers, json_body=json_body,
                timeout_seconds=timeout_seconds, max_response_bytes=max_response_bytes,
            )
        except Exception:
            event["outcome"] = "TRANSPORT_STOP"
            if method == "POST":
                self.mutations_stopped = True
            raise
        event["http_status"] = response.status_code
        if method == "POST" and response.status_code != 200:
            self.mutations_stopped = True
        if operation == "SEARCH" and response.status_code == 200:
            self.no_match = response.body == []
        if operation == "SHELL" and response.status_code == 200:
            try:
                self.party_id = _response_identifier(
                    response.body, frozenset({"goldTierId", "goldTierID"})
                )
                if self.party_id is None:
                    self.mutations_stopped = True
            except GoldTierXpiMalformedResponseError:
                # The real connector must classify an invalid POST response as
                # uncertain. This budget wrapper never changes that classification.
                self.mutations_stopped = True
                self.party_id = None
        return response


def read_required_xpi_configuration(path: Path) -> dict[str, str]:
    """Skip all unrequested values; never log private data or parse ambient Mongo."""
    keys = {
        "GOLDTIER_SANDBOX_BASE_URL", "GOLDTIER_SANDBOX_ENVIRONMENT", "GOLDTIER_SANDBOX_USER_ID",
    }
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in keys:
            if key.strip() in values:
                raise AcceptanceBlocked("DUPLICATE_CONFIGURATION:" + key.strip())
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key.strip()] = value
    missing = sorted(key for key in keys if not values.get(key))
    if missing:
        raise AcceptanceBlocked("MISSING_CONFIGURATION:" + ",".join(missing))
    parsed = urlsplit(values["GOLDTIER_SANDBOX_BASE_URL"])
    if (parsed.scheme != "https" or parsed.hostname != "portal.gt.deltacapita.net"
            or parsed.port not in {None, 443} or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or values["GOLDTIER_SANDBOX_ENVIRONMENT"] != "anz-nutmeg"):
        raise AcceptanceBlocked("CONFIGURATION_NOT_AUTHORIZED_SANDBOX")
    return values


def reserve_external_identity(path: Path, *, name: str, uen: str) -> None:
    """Create the run reservation before any provider call; an interrupted run stays reserved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"phase": "IDENTITY_RESERVED", "mode": "EXTERNAL_SANDBOX",
                   "synthetic_name": name, "synthetic_uen": uen}, stream, indent=2)


def require_response(response: Any, status: int = 200) -> dict[str, Any]:
    if response.status_code != status:
        detail = response.json().get("detail", {})
        code = detail.get("code", "LOCAL_API_FAILURE") if isinstance(detail, dict) else "LOCAL_API_FAILURE"
        if not isinstance(code, str) or not code.replace("_", "").isalnum():
            code = "LOCAL_API_FAILURE"
        raise AcceptanceBlocked(code)
    return response.json()


def prepare_case(client: TestClient, guard: BoundedAcceptanceTransport,
                 credential: str) -> tuple[dict[str, Any], dict[str, Any]]:
    session = require_response(client.post("/api/auth/login", json={
        "user_id": "maya-lim", "password": credential,
    }))
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    summary = require_response(client.post("/api/clm/zero-touch/cases", json={
        "uen": guard.uen, "country_of_incorporation": "SG", "legal_name": guard.name,
    }), 201)
    case_id = summary["case"]["case_id"]
    guard.case_id = case_id
    document_text = (
        f"Legal Name: {guard.name}\nUEN: {guard.uen}\n"
        "Registered Address: 1 SYNTHETIC ACCEPTANCE WAY, #01-01, 018956, SG\nCountry: SG\n"
        "Shareholder | Type | Percentage | Owned entity registration number | As of\n"
        f"POC Synthetic Owner A | NATURAL_PERSON | 70% | {guard.uen} | 2026-10-04\n"
        f"POC Synthetic Owner B | NATURAL_PERSON | 30% | {guard.uen} | 2026-10-04\n"
    )
    document = require_response(client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        content=document_text.encode(), headers={
            "Content-Type": "text/plain", "X-Document-Name": "synthetic-acceptance.txt",
        },
    ), 201)
    summary = require_response(client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 1},
    ))
    summary = require_response(client.put(
        f"/api/clm/zero-touch/cases/{case_id}/target-classification", json={
            "kyc_customer_type": "Company - Private", "client_segment": "Corporate",
            "expected_automation_version": summary["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    ))
    ownership = require_response(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    document = require_response(client.get(
        f"/api/onboarding/cases/{case_id}/documents/{document['document_id']}"
    ))
    if ownership["state"] == "REVIEW_REQUIRED":
        declaration = {
            "root_registration_number": guard.uen,
            "evidence_document_id": document["document_id"],
            "evidence_document_version": len(document["events"]),
            "source_selection": "CURRENT_EVIDENCE",
            "observed_document_versions": ownership["document_bindings"],
            "selected_observation_ids": [],
            "as_of_date": "2026-10-04",
            "rationale": "Synthetic acceptance creator reviewed both matching explicit document owners.",
            "root_party_id": ownership["root_party_id"], "parties": ownership["parties"],
            "relationships": [{
                key: edge[key] for key in
                ("relationship_id", "parent_party_id", "child_party_id", "ownership_percent")
            } for edge in ownership["relationships"]],
            "expected_automation_version": summary["version"],
            "expected_ownership_version": ownership["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        }
        summary = require_response(client.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence", json=declaration,
        ))
        ownership = require_response(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    if ({item["exception_type"] for item in summary["active_exceptions"]}
            != {"TARGET_CONFIRMATION_REQUIRED"}):
        guard.preparation_diagnostics = {
            "status": summary["status"], "technical_failure": summary["technical_failure"],
            "blockers": [{"code": item["exception_type"], "stage": item["stage"]}
                         for item in summary["active_exceptions"]],
            "target_submission": summary["target_submission"],
            "target_operations": summary["target_operations"],
        }
        raise AcceptanceBlocked("PREPARATION_HAS_REAL_BLOCKER")
    preview = summary["clm"]["submission_plan"]["request_preview"]
    if not preview["dispatch_ready"] or any(item["operation"] == "AMEND" for item in preview["operations"]):
        raise AcceptanceBlocked("PREVIEW_NOT_SUPPORTED_PARENT_PACKAGE")
    if len(document["ownership_observations"]) != 2 or len(ownership["candidates"]) != 2:
        raise AcceptanceBlocked("DOCUMENT_OWNERSHIP_ACCEPTANCE_INCOMPLETE")
    guard.bind_review(preview, case_id)
    return summary, {"document_id": document["document_id"], "document_state": document["state"],
                     "ownership": ownership, "preview": preview}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external", action="store_true")
    parser.add_argument("--configuration-file", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.external and (args.configuration_file is None or args.receipt.exists()):
        raise AcceptanceBlocked("EXTERNAL_RUN_REQUIRES_CONFIGURATION_AND_FRESH_RECEIPT")
    root = Path(__file__).resolve().parents[1]
    if args.external:
        prerequisites = {
            ".ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_QUALITY_GATE.md":
                "813c495bdca13531204b4ed8e8f054c3855952fc4f9ba0ce13038ce398b202e4",
            ".ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_QUALITY_GATE.md":
                "f3460459000d73e69cb4d0d465efd404d92ee8d01b2e1f73cc6884c82b5fd608",
        }
        if any(sha256((root / path).read_bytes()).hexdigest() != digest
               for path, digest in prerequisites.items()):
            raise AcceptanceBlocked("ACCEPTED_SESSION_GATE_CHANGED")
        matrix = root / "docs/integration/ONBOARDING_INTELLIGENCE_S3_FIELD_MATRIX.md"
        local = root / ".ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_LOCAL_CHECKS.json"
        if not matrix.is_file() or not local.is_file():
            raise AcceptanceBlocked("FIELD_MATRIX_OR_LOCAL_CHECKS_MISSING")
        proof = json.loads(local.read_text())
        if proof.get("verdict") != "PASS":
            raise AcceptanceBlocked("LOCAL_MAPPER_LEDGER_CHECKS_NOT_PASS")
        for relative, digest in proof["files"].items():
            candidate = (root / relative).resolve()
            if not candidate.is_relative_to(root) or sha256(candidate.read_bytes()).hexdigest() != digest:
                raise AcceptanceBlocked("LOCAL_CHECKED_SOURCE_CHANGED")
    suffix = uuid4().hex[:8].upper()
    name, uen = f"ZERO TOUCH POC ACCEPTANCE {suffix}", f"2026{secrets.randbelow(100000):05d}Z"
    credential = secrets.token_urlsafe(32)
    encoded = SecretStr(generate_scrypt_password_hash(credential))
    hashes = {key: encoded for key in (
        "phase13_maya_lim_password_hash", "phase13_ethan_tan_password_hash",
        "phase13_sophia_ng_password_hash", "phase13_ryan_lee_password_hash",
        "phase13_olivia_koh_password_hash", "phase14_5_hr_admin_password_hash",
    )}
    values = read_required_xpi_configuration(args.configuration_file) if args.external else {
        "GOLDTIER_SANDBOX_BASE_URL": "https://sandbox.goldtier.invalid",
        "GOLDTIER_SANDBOX_ENVIRONMENT": "synthetic",
        "GOLDTIER_SANDBOX_USER_ID": "synthetic-user",
    }
    if args.external:
        reserve_external_identity(args.receipt, name=name, uen=uen)
    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    settings = Settings(
        _env_file=None, app_env="test", acra_connector_mode="mock",
        idp_connector_mode="local_pdf_text", goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url=values["GOLDTIER_SANDBOX_BASE_URL"],
        goldtier_sandbox_environment=values["GOLDTIER_SANDBOX_ENVIRONMENT"],
        goldtier_sandbox_user_id=SecretStr(values["GOLDTIER_SANDBOX_USER_ID"]),
        goldtier_sandbox_allow_writes=True,
        clm_persistence_mode="mongo" if args.external else "memory",
        mongo_uri=("mongo" + "db://" + "127.0.0.1" + ":27078") if args.external else None,
        mongo_database=database,
        **hashes,
    )
    delegate = HttpxGoldTierXpiTransport() if args.external else OfflineAcceptanceTransport(name, uen)
    guard = BoundedAcceptanceTransport(
        delegate, origin=settings.goldtier_sandbox_base_url,
        environment=settings.goldtier_sandbox_environment, name=name, uen=uen,
    )
    with patch("app.config.get_settings", return_value=Settings(
        _env_file=None, app_env="test", **hashes
    )):
        from app.main import create_app
    receipt: dict[str, Any] = {
        "mode": "EXTERNAL_SANDBOX" if args.external else "OFFLINE_XPI_PROTOCOL",
        "synthetic_name": name, "synthetic_uen": uen,
        "database": database if args.external else None,
        "original_clm_poc_touched": False,
        "configuration": {
            "backend_required_fields_present": True,
            "authorized_sandbox_origin_verified": args.external,
            "private_environment_edited": False,
            "explicit_process_mode": "sandbox", "explicit_process_writes_enabled": True,
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    try:
        with TestClient(create_app(settings, acra_connector=SyntheticAcceptanceAcra(name, uen),
                                  goldtier_transport=guard)) as client:
            summary, prepared = prepare_case(client, guard, credential)
            receipt.update({"case_id": summary["case"]["case_id"], "prepared": prepared,
                            "phase": "PREPARED_AWAITING_INDEPENDENT_GATE",
                            "calls": guard.counts, "events": guard.events})
            args.receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"phase": receipt["phase"], "case_id": receipt["case_id"],
                              "calls": guard.counts}), flush=True)
            if args.external:
                command = input().strip().split()
                if len(command) != 3 or command[0] != "SEND":
                    raise AcceptanceBlocked("INDEPENDENT_GATE_NOT_SUPPLIED")
                manifest = json.loads((root / ".ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_PRE_MUTATION_MANIFEST.json").read_text())
                gate = root / ".ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_PRE_MUTATION_GATE.md"
                if (sha256(gate.read_bytes()).hexdigest() != command[1]
                        or manifest["candidate_sha256"] != command[2]
                        or "PRE_MUTATION: PASS" not in gate.read_text()
                        or command[2] not in gate.read_text()):
                    raise AcceptanceBlocked("INDEPENDENT_GATE_MISMATCH")
                calculated = sha256(json.dumps(
                    manifest["files"], sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
                if calculated != command[2]:
                    raise AcceptanceBlocked("INDEPENDENT_MANIFEST_DIGEST_MISMATCH")
                for relative, digest in manifest["files"].items():
                    path = (root / relative).resolve()
                    if not path.is_relative_to(root) or sha256(path.read_bytes()).hexdigest() != digest:
                        raise AcceptanceBlocked("REVIEWED_CANDIDATE_CHANGED")
            guard.writes_approved = True
            final = require_response(client.post(
                f"/api/clm/zero-touch/cases/{receipt['case_id']}/target-confirmation", json={
                    "expected_automation_version": summary["version"],
                    "expected_clm_version": summary["clm"]["version"],
                    "expected_case_event_count": len(summary["case"]["events"]),
                },
            ))
            receipt.update({"phase": "ATTEMPT_RETAINED", "final_status": final["status"],
                            "target_submission": final["target_submission"],
                            "target_operations": final["target_operations"],
                            "target_error": final["technical_failure"]})
            baseline_document = require_response(client.get(
                f"/api/onboarding/cases/{guard.case_id}/documents/{prepared['document_id']}"
            ))
            baseline_ownership = require_response(client.get(
                f"/api/onboarding/cases/{guard.case_id}/ownership"
            ))
            target = final.get("target_submission") or {}
            if target.get("state") == "SUBMISSION_OUTCOME_UNCERTAIN":
                guard.mutations_stopped = True
                check = require_response(client.post(
                    f"/api/clm/zero-touch/cases/{receipt['case_id']}/target-status-check",
                    json={"expected_submission_id": target["submission_id"]},
                ))
                receipt["read_only_check"] = check
        if args.external and guard.case_id is not None:
            before_restart = dict(guard.counts)
            with TestClient(create_app(
                settings, acra_connector=SyntheticAcceptanceAcra(name, uen),
                goldtier_transport=guard,
            )) as restored:
                session = require_response(restored.post("/api/auth/login", json={
                    "user_id": "maya-lim", "password": credential,
                }))
                restored.headers["X-CSRF-Token"] = session["csrf_token"]
                state = require_response(restored.get(
                    f"/api/clm/zero-touch/cases/{guard.case_id}"
                ))
                restored_document = require_response(restored.get(
                    f"/api/onboarding/cases/{guard.case_id}/documents/{prepared['document_id']}"
                ))
                restored_ownership = require_response(restored.get(
                    f"/api/onboarding/cases/{guard.case_id}/ownership"
                ))
                receipt["restart"] = {
                    "target_submission": state["target_submission"],
                    "target_operations": state["target_operations"],
                    "provider_calls_unchanged": before_restart == guard.counts,
                    "document_evidence_retained": restored_document == baseline_document,
                    "ownership_evidence_retained": restored_ownership == baseline_ownership,
                }
                if not all(receipt["restart"][key] for key in (
                    "provider_calls_unchanged", "document_evidence_retained",
                    "ownership_evidence_retained",
                )):
                    raise AcceptanceBlocked("PHYSICAL_RESTART_EVIDENCE_CHANGED")
        # Application completion precedes required evidence/restart proof. Mark overall
        # acceptance only after every applicable proof above has completed successfully.
        if receipt.get("final_status") == "COMPLETED":
            receipt["phase"] = "ACCEPTANCE_VERIFIED"
    except AcceptanceBlocked as exc:
        receipt.update({"phase": "BLOCKED", "safe_code": str(exc)})
    except Exception:  # noqa: BLE001 - fixed safe boundary, no exception/body/credential output
        receipt.update({"phase": "BLOCKED", "safe_code": "ACCEPTANCE_STOPPED_SAFELY"})
    receipt.update({"calls": guard.counts, "events": guard.events, "case_id": guard.case_id,
                    "preparation_diagnostics": guard.preparation_diagnostics})
    args.receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({key: receipt.get(key) for key in
                      ("phase", "safe_code", "final_status", "target_submission", "calls")}), flush=True)
    return 0 if (
        receipt.get("phase") == "ACCEPTANCE_VERIFIED"
        and receipt.get("final_status") == "COMPLETED"
    ) else 2


if __name__ == "__main__":
    try:
        result = main()
    except AcceptanceBlocked as error:
        print(json.dumps({"phase": "BLOCKED", "safe_code": str(error)}), flush=True)
        result = 2
    except Exception:  # noqa: BLE001 - safe configuration/startup failure boundary
        print(json.dumps({"phase": "BLOCKED", "safe_code": "STARTUP_STOPPED_SAFELY"}), flush=True)
        result = 2
    raise SystemExit(result)
