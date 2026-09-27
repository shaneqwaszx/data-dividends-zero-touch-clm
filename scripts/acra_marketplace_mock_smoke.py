"""Bounded sanitized smoke for the official ACRA API Marketplace Mock lane."""

from __future__ import annotations

import json
import ssl
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings
from app.connectors.acra_api_marketplace_auth import (
    AcraApiMarketplaceMockRequestAuthorizer,
    AcraApiMarketplaceMockTokenClient,
)
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import (
    AcraHttpResponse,
    AcraHttpTransport,
    HttpxAcraTransport,
)
from app.connectors.errors import ConnectorError

MAX_EVIDENCE_RECORDS = 4


class RecordingTransport:
    """Retain only the latest bounded response long enough to sanitize it."""

    def __init__(self, delegate: AcraHttpTransport) -> None:
        self._delegate = delegate
        self.responses: list[AcraHttpResponse] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        response = self._delegate.get(
            url,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        self.responses.append(response)
        return response


def _safe_entity(response: AcraHttpResponse) -> Mapping[str, object] | None:
    body = response.body
    if not isinstance(body, Mapping):
        return None
    entities = body.get("entities")
    if not isinstance(entities, list) or len(entities) != 1:
        return None
    entity = entities[0]
    return entity if isinstance(entity, Mapping) else None


def _base_record(
    *,
    operation: str,
    endpoint_path: str,
    requested_uen: str,
    response: AcraHttpResponse | None,
) -> dict[str, object]:
    return {
        "provider": "ACRA_API_MARKETPLACE_MOCK",
        "classification": "MOCK",
        "observed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "operation": operation,
        "safe_endpoint": (
            f"https://api-sandbox.bizfile.gov.sg/api/acra{endpoint_path}"
        ),
        "http_status": response.status_code if response is not None else None,
        "response_content_type": (
            response.content_type.split(";", 1)[0].strip().lower()
            if response is not None and response.content_type
            else None
        ),
        "bounded_response_bytes": (
            response.response_bytes if response is not None else None
        ),
        "requested_uen": requested_uen,
    }


def _entity_operation(
    *,
    connector: AcraApiMarketplaceMockConnector,
    transport: RecordingTransport,
    requested_uen: str,
) -> dict[str, object]:
    before = len(transport.responses)
    record = _base_record(
        operation="entityBasicInformation",
        endpoint_path="/entityQuery/entityBasicInformation",
        requested_uen=requested_uen,
        response=None,
    )
    try:
        company = connector.fetch_company(requested_uen)
    except ConnectorError as error:
        response = transport.responses[-1] if len(transport.responses) > before else None
        record.update(
            _base_record(
                operation="entityBasicInformation",
                endpoint_path="/entityQuery/entityBasicInformation",
                requested_uen=requested_uen,
                response=response,
            )
        )
        record.update(
            {
                "returned_requested_uen_equal": False,
                "strict_schema_validation": "FAIL",
                "outcome": error.code,
            }
        )
        return record
    response = transport.responses[-1]
    entity = _safe_entity(response)
    returned = entity.get("uen") if entity is not None else None
    name = entity.get("name") if entity is not None else None
    record.update(
        _base_record(
            operation="entityBasicInformation",
            endpoint_path="/entityQuery/entityBasicInformation",
            requested_uen=requested_uen,
            response=response,
        )
    )
    record.update(
        {
            "returned_requested_uen_equal": (
                isinstance(returned, str) and returned.upper() == requested_uen
            ),
            "strict_schema_validation": "PASS" if company is not None else "EMPTY",
            "outcome": "SUCCESS" if company is not None else "NOT_FOUND",
            "approved_mock_identity": (
                name if name == "GARDEN BUSINESS" else None
            ),
        }
    )
    return record


def _shareholder_operation(
    *,
    connector: AcraApiMarketplaceMockConnector,
    transport: RecordingTransport,
    requested_uen: str,
    expected_name: str,
) -> dict[str, object]:
    before = len(transport.responses)
    record = _base_record(
        operation="coShareholdersDetails",
        endpoint_path="/entityQuery/coShareholdersDetails",
        requested_uen=requested_uen,
        response=None,
    )
    try:
        ownership = connector.fetch_ownership_parties(requested_uen)
    except ConnectorError as error:
        response = transport.responses[-1] if len(transport.responses) > before else None
        record.update(
            _base_record(
                operation="coShareholdersDetails",
                endpoint_path="/entityQuery/coShareholdersDetails",
                requested_uen=requested_uen,
                response=response,
            )
        )
        record.update(
            {
                "returned_requested_uen_equal": False,
                "strict_schema_validation": "FAIL",
                "outcome": error.code,
            }
        )
        return record
    response = transport.responses[-1]
    entity = _safe_entity(response)
    returned = entity.get("uen") if entity is not None else None
    name = entity.get("name") if entity is not None else None
    record.update(
        _base_record(
            operation="coShareholdersDetails",
            endpoint_path="/entityQuery/coShareholdersDetails",
            requested_uen=requested_uen,
            response=response,
        )
    )
    record.update(
        {
            "returned_requested_uen_equal": (
                isinstance(returned, str) and returned.upper() == requested_uen
            ),
            "strict_schema_validation": "PASS",
            "outcome": "SUCCESS" if entity is not None else "EMPTY",
            "approved_mock_identity": name if name == expected_name else None,
            "shareholder_record_count": len(ownership.ownership_parties),
            "share_count_evidence_present": bool(ownership.ownership_parties)
            and all(
                party.share_allotted is not None
                for party in ownership.ownership_parties
            ),
            "ownership_percentage_derived": any(
                party.ownership_percentage is not None
                for party in ownership.ownership_parties
            ),
        }
    )
    return record


def _schema_paths(value: object, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            paths.update(_schema_paths(nested, path))
    elif isinstance(value, list) and value:
        paths.update(_schema_paths(value[0], f"{prefix}[]"))
    return paths


def _capital_operation(
    *,
    connection: AcraApiMarketplaceMockConnection,
    transport: RecordingTransport,
    authorizer: AcraApiMarketplaceMockRequestAuthorizer,
) -> dict[str, object]:
    requested_uen = "111111111K"
    path = "/entityQuery/coCapitalDetails"
    endpoint = (
        f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}{path}?"
        f"{urlencode({'uen': requested_uen})}"
    )
    try:
        headers = dict(authorizer.authorization_headers())
        headers["Accept"] = "application/json"
        response = transport.get(
            endpoint,
            headers=headers,
            timeout_seconds=connection.timeout_seconds,
        )
    except ConnectorError as error:
        record = _base_record(
            operation="coCapitalDetails",
            endpoint_path=path,
            requested_uen=requested_uen,
            response=None,
        )
        record.update(
            {
                "returned_requested_uen_equal": False,
                "strict_schema_validation": "NOT_IMPLEMENTED",
                "outcome": error.code,
            }
        )
        return record
    entity = _safe_entity(response)
    returned = entity.get("uen") if entity is not None else None
    relevant = sorted(
        path_name
        for path_name in _schema_paths(response.body)
        if any(
            term in path_name.lower()
            for term in ("capital", "share", "issued", "amount", "currency", "type")
        )
    )
    record = _base_record(
        operation="coCapitalDetails",
        endpoint_path=path,
        requested_uen=requested_uen,
        response=response,
    )
    record.update(
        {
            "returned_requested_uen_equal": (
                isinstance(returned, str) and returned.upper() == requested_uen
            ),
            "strict_schema_validation": "SCHEMA_OBSERVED_ONLY",
            "outcome": "SUCCESS" if response.status_code == 200 else "HTTP_FAILURE",
            "relevant_schema_paths": relevant[:32],
        }
    )
    return record


def main() -> int:
    settings = Settings()
    token_client = AcraApiMarketplaceMockTokenClient(
        client_id=settings.acra_api_marketplace_mock_client_id,
        secret_key=settings.acra_api_marketplace_mock_secret_key,
        timeout_seconds=settings.acra_timeout_seconds,
    )
    authorizer = AcraApiMarketplaceMockRequestAuthorizer(token_client)
    transport = RecordingTransport(
        HttpxAcraTransport(
            ssl_context=ssl.create_default_context(),
            trust_env=False,
        )
    )
    connection = AcraApiMarketplaceMockConnection(
        timeout_seconds=settings.acra_timeout_seconds
    )
    connector = AcraApiMarketplaceMockConnector(
        connection=connection,
        transport=transport,
        authorizer=authorizer,
    )
    evidence = [
        _entity_operation(
            connector=connector,
            transport=transport,
            requested_uen="11111999A",
        ),
        _shareholder_operation(
            connector=connector,
            transport=transport,
            requested_uen="111111111M",
            expected_name="SIM LIM PTE. LTD.",
        ),
        _shareholder_operation(
            connector=connector,
            transport=transport,
            requested_uen="11111999A",
            expected_name="GARDEN BUSINESS",
        ),
        _capital_operation(
            connection=connection,
            transport=transport,
            authorizer=authorizer,
        ),
    ]
    if len(evidence) != MAX_EVIDENCE_RECORDS:
        return 2
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
