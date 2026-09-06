"""Standalone smoke test -- run this directly, no pytest needed.

    python check_acra_connector.py

Verifies the FULL wiring: .env -> Settings -> composition.py ->
BizfileMockAcraConnector -> real API, using the two UENs from your
Postman samples. Requires .env to have:
    ACRA_CONNECTOR_MODE=bizfile_mock
    ACRA_AUTH_HEADER_NAME=token
    ACRA_AUTH_HEADER_VALUE=<your token>
"""

from app.config import get_settings
from app.composition import build_acra_connector
from app.connectors.errors import ConnectorError

CONNECTOR = build_acra_connector(get_settings())


def check_company() -> None:
    print("--- fetch_company('11111999A') ---")
    try:
        company = CONNECTOR.fetch_company("11111999A")
    except ConnectorError as exc:
        print(f"FAILED: raised {type(exc).__name__}: {exc}")
        return
    if company is None:
        print("FAILED: got None -- expected a company, this UEN should exist")
        return
    print(f"uen={company.uen}")
    print(f"entity_name={company.entity_name}")
    print(f"entity_type={company.entity_type}")
    print(f"registration_date={company.registration_date}")
    print(f"entity_status={company.entity_status}")
    if company.registered_address:
        addr = company.registered_address
        print(f"address: block={addr.block} street={addr.street} unit={addr.unit}")
    else:
        print("address: None")
    # Sanity checks against the values in your pasted sample response.
    assert company.entity_name == "GARDEN BUSINESS", "entity_name mismatch vs sample"
    assert company.registration_date is not None, "registration_date should be set"
    print("OK -- matches expected sample values")


def check_officers() -> None:
    print("\n--- fetch_officers('11111999A') ---")
    try:
        officers = CONNECTOR.fetch_officers("11111999A")
    except ConnectorError as exc:
        print(f"FAILED: raised {type(exc).__name__}: {exc}")
        return
    print(f"officer count: {len(officers.officers)}")
    for officer in officers.officers:
        print(f"  {officer.officer_id}  {officer.name}  role={officer.role}")
    assert len(officers.officers) > 0, "expected at least one officer"
    print("OK")


def check_ownership_parties() -> None:
    print("\n--- fetch_ownership_parties('111111111M') ---")
    try:
        parties = CONNECTOR.fetch_ownership_parties("111111111M")
    except ConnectorError as exc:
        print(f"FAILED: raised {type(exc).__name__}: {exc}")
        return
    print(f"party count: {len(parties.ownership_parties)}")
    for party in parties.ownership_parties:
        print(f"  {party.party_id}  {party.name}  type={party.party_type}")
    assert len(parties.ownership_parties) > 0, "expected at least one ownership party"
    print("OK")


def check_unknown_uen() -> None:
    print("\n--- fetch_company('00000000Z') (should not exist) ---")
    try:
        company = CONNECTOR.fetch_company("00000000Z")
    except ConnectorError as exc:
        print(f"raised {type(exc).__name__}: {exc} -- check this is expected")
        return
    print(f"result: {company}")


if __name__ == "__main__":
    check_company()
    check_officers()
    check_ownership_parties()
    check_unknown_uen()