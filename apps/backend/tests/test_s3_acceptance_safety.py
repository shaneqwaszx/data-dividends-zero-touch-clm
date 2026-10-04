"""No-network acceptance-budget, private-field and crash-reservation checks."""

import json

import pytest
from scripts.run_s3_sandbox_acceptance import (
    AcceptanceBlocked,
    BoundedAcceptanceTransport,
    OfflineAcceptanceTransport,
    read_required_xpi_configuration,
    reserve_external_identity,
)

from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse

NAME, UEN = "ZERO TOUCH POC ACCEPTANCE SAFETY", "202698761Z"


def dispatch(guard, method="GET", suffix=(
    "/customers/search?legalName=ZERO+TOUCH+POC+ACCEPTANCE+SAFETY&countryOfIncorporation=SG"
), payload=None):
    return guard.request(method, "https://sandbox.goldtier.invalid/synthetic/gt-xpi/v1" + suffix,
                         headers={}, json_body=payload, timeout_seconds=1, max_response_bytes=1024)


def test_crash_reservation_keeps_the_only_identity_and_cannot_be_replaced(tmp_path):
    path = tmp_path / "synthetic-receipt.json"
    reserve_external_identity(path, name=NAME, uen=UEN)
    with pytest.raises(FileExistsError):
        reserve_external_identity(path, name=NAME + "SECOND", uen="202698762Z")
    assert json.loads(path.read_text())["synthetic_name"] == NAME
    assert json.loads(path.read_text())["phase"] == "IDENTITY_RESERVED"


def test_config_consumes_only_three_named_fields_and_rejects_duplicate(tmp_path):
    path = tmp_path / "task-config.txt"
    text = ("UNRELATED_PRIVATE_VALUE=never-consumed\n"
            "GOLDTIER_SANDBOX_BASE_URL=https://portal.gt.deltacapita.net\n"
            "GOLDTIER_SANDBOX_ENVIRONMENT=anz-nutmeg\n"
            "GOLDTIER_SANDBOX_USER_ID=synthetic-api-user\n")
    path.write_text(text)
    values = read_required_xpi_configuration(path)
    assert set(values) == {"GOLDTIER_SANDBOX_BASE_URL", "GOLDTIER_SANDBOX_ENVIRONMENT",
                           "GOLDTIER_SANDBOX_USER_ID"}
    path.write_text(text + "GOLDTIER_SANDBOX_USER_ID=another-synthetic-user\n")
    with pytest.raises(AcceptanceBlocked,
                       match="^DUPLICATE_CONFIGURATION:GOLDTIER_SANDBOX_USER_ID$"):
        read_required_xpi_configuration(path)


def test_budget_blocks_broad_search_unapproved_mutation_and_third_read():
    guard = BoundedAcceptanceTransport(
        OfflineAcceptanceTransport(NAME, UEN), origin="https://sandbox.goldtier.invalid",
        environment="synthetic", name=NAME, uen=UEN,
    )
    with pytest.raises(AcceptanceBlocked, match="UNAUTHORIZED_SEARCH_IDENTITY"):
        dispatch(guard, suffix="/customers/search?countryOfIncorporation=SG")
    with pytest.raises(AcceptanceBlocked, match="MUTATION_NOT_AUTHORIZED"):
        dispatch(guard, "POST", "/customers/create", {})
    assert not any(guard.counts.values())
    dispatch(guard)
    dispatch(guard)
    with pytest.raises(AcceptanceBlocked, match="READ_ONLY_BUDGET_EXHAUSTED"):
        dispatch(guard)
    assert guard.counts["SEARCH"] == 2


def test_malformed_shell_response_remains_uncertain_and_blocks_all_further_writes():
    class Malformed(OfflineAcceptanceTransport):
        def request(self, method, url, **kwargs):
            if method == "POST":
                return GoldTierXpiHttpResponse(200, {"unexpected": "synthetic"})
            return super().request(method, url, **kwargs)
    guard = BoundedAcceptanceTransport(
        Malformed(NAME, UEN), origin="https://sandbox.goldtier.invalid",
        environment="synthetic", name=NAME, uen=UEN,
    )
    dispatch(guard)
    guard.writes_approved = True
    guard.shell_payload = {"legalName": NAME}
    response = dispatch(guard, "POST", "/customers/create", guard.shell_payload)
    assert response.status_code == 200 and response.body == {"unexpected": "synthetic"}
    assert guard.mutations_stopped and guard.party_id is None
    for suffix in ("/customers/create", "/customers/createPolicy", "/customers/amend"):
        with pytest.raises(AcceptanceBlocked, match="MUTATION_NOT_AUTHORIZED"):
            dispatch(guard, "POST", suffix, {})
    assert guard.counts["SHELL"] == 1 and guard.counts["POLICY"] == guard.counts["AMEND"] == 0
