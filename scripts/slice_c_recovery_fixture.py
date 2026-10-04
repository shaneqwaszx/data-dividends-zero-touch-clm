"""Explicit synthetic offline Slice C composition through existing owner seams.

No external HTTP client is constructed. The real XPI connector and mapper consume
an inert protocol transport; no target result or retained case state is fabricated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
from app.composition import build_onboarding_service
from app.config import Settings
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.domain.policy import (
    AuthorityLabelledTargetValue,
    CasePolicySnapshot,
    PolicyAuthority,
)
from app.services.admin_repository import InMemoryPolicyRepository
from app.services.onboarding import OnboardingService
from app.services.policy_management import PolicyManagementService
from pydantic import SecretStr

from scripts.run_e2e import RECOVERY_DEMO_MODES
from scripts.slice_b_registry_fixture import CountingSyntheticRegistry


class OfflineXpiRecoveryTransport:
    """Allowlisted fictional protocol results; retain operation names only."""

    def __init__(self, *, fail_first_search: bool = False) -> None:
        self.operations: list[str] = []
        self._fail_first_search = fail_first_search
        self._shell_created = False

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GoldTierXpiHttpResponse:
        # Request metadata is consumed by the normal connector but never retained.
        del headers, json_body, timeout_seconds, max_response_bytes
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "slice-c-offline.invalid":
            raise ValueError("Offline XPI fixture rejects unapproved destinations")
        prefix = "/synthetic-offline/gt-xpi/v1/customers/"
        if not parsed.path.startswith(prefix):
            raise ValueError("Offline XPI fixture rejects unapproved operations")
        operation = parsed.path.removeprefix(prefix)
        if method == "GET" and operation == "search":
            query = parse_qs(parsed.query)
            if "goldTierID" in query:
                if query["goldTierID"] != ["900001"] or not self._shell_created:
                    raise ValueError(
                        "Offline readback requires the completed fictional Shell"
                    )
                self.operations.append("READBACK")
                return GoldTierXpiHttpResponse(
                    status_code=200, body=[{"goldTierId": 900001}]
                )
            self.operations.append("SEARCH")
            if self._fail_first_search:
                self._fail_first_search = False
                raise httpx.ReadTimeout("Synthetic offline Search interruption")
            return GoldTierXpiHttpResponse(status_code=200, body=[])
        if method == "POST" and operation == "create" and not self._shell_created:
            self.operations.append("SHELL")
            self._shell_created = True
            return GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 900001})
        if method == "POST" and operation == "createPolicy" and self._shell_created:
            self.operations.append("POLICY")
            return GoldTierXpiHttpResponse(status_code=200, body={})
        raise ValueError(
            "Offline fixture forbids Amend, replay and unsupported target operations"
        )


class BoundedFinalizationFault:
    """Interrupt receipt construction twice; subsequent owner resume can finalize."""

    def __init__(self) -> None:
        self.attempts = 0

    def __call__(self, case_id: UUID) -> bool:
        del case_id
        self.attempts += 1
        return self.attempts <= 2


class CreationPolicyFixture:
    """Bind a supported historical policy on creation, current policy on rebind."""

    def __init__(self, *, legacy_creation: bool) -> None:
        self._policies = PolicyManagementService(InMemoryPolicyRepository())
        self._legacy_creation = legacy_creation

    def __call__(self) -> CasePolicySnapshot:
        current = self._policies.case_snapshot()
        if not self._legacy_creation:
            return current
        self._legacy_creation = False
        target = current.goldtier_target
        assert target is not None
        legacy_target = target.model_copy(
            update={
                name: AuthorityLabelledTargetValue(
                    value=value, authority=PolicyAuthority.TBD_SPONSOR
                )
                for name, value in {
                    "customer_external_system": "LEGACY_DSD",
                    "registration_type": "LEGACY_ACRA",
                    "policy": "LEGACY_SINGAPORE",
                    "booking_entity": "LEGACY_SG_BRANCH",
                }.items()
            },
            deep=True,
        )
        return CasePolicySnapshot.model_validate(
            {
                **current.model_dump(),
                "snapshot_label": "SYNTHETIC_LEGACY_TARGET_CONFIG",
                "catalogue_version": 0,
                "registry": None,
                "evidence_classifier": None,
                "policy_identity": None,
                "goldtier_target": legacy_target.model_dump(),
            }
        )


@dataclass
class OfflineRecoveryFixture:
    mode: str
    settings: Settings
    onboarding: OnboardingService
    transport: OfflineXpiRecoveryTransport
    registry: CountingSyntheticRegistry
    finalization_fault: BoundedFinalizationFault | None

    def metadata(self) -> dict[str, object]:
        return {
            "fixture": self.mode,
            "classification": "SYNTHETIC_OFFLINE",
            "external_calls": 0,
            "operations": list(self.transport.operations),
            "registry_operations": [operation for operation, _ in self.registry.calls],
            "finalization_attempts": self.finalization_fault.attempts
            if self.finalization_fault
            else 0,
        }


def build_offline_recovery_fixture(
    settings: Settings, mode: str
) -> OfflineRecoveryFixture:
    if mode not in RECOVERY_DEMO_MODES:
        raise ValueError("Unknown Slice-C offline recovery fixture")
    if (
        settings.app_env != "test"
        or settings.clm_persistence_mode != "memory"
        or settings.acra_connector_mode != "mock"
        or settings.idp_connector_mode != "local_pdf_text"
    ):
        raise ValueError(
            "Offline recovery fixture requires isolated test/memory/local composition"
        )
    isolated = settings.model_copy(
        update={
            "goldtier_connector_mode": "sandbox",
            "goldtier_sandbox_base_url": "https://slice-c-offline.invalid",
            "goldtier_sandbox_environment": "synthetic-offline",
            "goldtier_sandbox_user_id": SecretStr("SYNTHETIC_OFFLINE_NON_CREDENTIAL"),
            "goldtier_sandbox_allow_writes": True,
        }
    )
    transport = OfflineXpiRecoveryTransport(fail_first_search=mode == "search-recheck")
    registry = CountingSyntheticRegistry()
    fault = BoundedFinalizationFault() if mode == "retained-recovery" else None
    onboarding = build_onboarding_service(
        settings=isolated,
        acra_connector=registry,
        goldtier_transport=transport,
        target_finalization_fault=fault,
        policy_snapshot_provider=CreationPolicyFixture(
            legacy_creation=mode == "stale-policy"
        ),
    )
    return OfflineRecoveryFixture(
        mode, isolated, onboarding, transport, registry, fault
    )
