"""Debug script: fetches the raw response AND shows the exact Pydantic
validation error, instead of the generic AcraMalformedResponseError that
swallows the details. Run directly: python debug_acra_decode.py
"""

import json

from pydantic import ValidationError

from app.config import get_settings
from app.connectors.acra_bizfile_sandbox import (
    AcraBizfileConnection,
    _RealEntityEnvelope,
    _RealShareholderEnvelope,
)
from app.connectors.acra_sandbox import HttpxAcraTransport, StaticHeaderAcraRequestAuthorizer

settings = get_settings()
authorizer = StaticHeaderAcraRequestAuthorizer(
    settings.acra_auth_header_name,
    settings.acra_auth_header_value.get_secret_value(),
)
transport = HttpxAcraTransport()
connection = AcraBizfileConnection()


def debug_company(uen: str) -> None:
    print(f"\n=== company endpoint, uen={uen} ===")
    endpoint = connection.company_endpoint(uen)
    print(f"URL: {endpoint}")
    headers = dict(authorizer.authorization_headers())
    headers["Accept"] = "application/json"
    response = transport.get(endpoint, headers=headers, timeout_seconds=10.0)
    print(f"status_code: {response.status_code}")
    print("raw body:")
    print(json.dumps(response.body, indent=2) if response.body is not None else "None")
    if response.body is None:
        return
    try:
        envelope = _RealEntityEnvelope.model_validate(response.body)
        print(f"\nParsed OK. entities count: {len(envelope.entities)}")
    except ValidationError as exc:
        print("\nVALIDATION ERROR:")
        print(exc)


def debug_shareholders(uen: str) -> None:
    print(f"\n=== shareholders endpoint, uen={uen} ===")
    endpoint = connection.shareholders_endpoint(uen)
    print(f"URL: {endpoint}")
    headers = dict(authorizer.authorization_headers())
    headers["Accept"] = "application/json"
    response = transport.get(endpoint, headers=headers, timeout_seconds=10.0)
    print(f"status_code: {response.status_code}")
    print("raw body:")
    print(json.dumps(response.body, indent=2) if response.body is not None else "None")
    if response.body is None:
        return
    try:
        envelope = _RealShareholderEnvelope.model_validate(response.body)
        print(f"\nParsed OK. entities count: {len(envelope.entities)}")
    except ValidationError as exc:
        print("\nVALIDATION ERROR:")
        print(exc)


if __name__ == "__main__":
    debug_company("11111999A")
    debug_shareholders("111111111M")