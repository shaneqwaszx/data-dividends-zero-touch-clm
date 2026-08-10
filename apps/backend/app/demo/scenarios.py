"""Scenario catalogue kept outside corporate-registry connector protocols."""

from typing import Literal, Protocol

from pydantic import BaseModel

VALID_SME_UEN = "202400001A"
INCOMPLETE_ENTITY_UEN = "202400002B"
GOLDTIER_FAILURE_UEN = "202400003C"
GOLDTIER_PARTIAL_UEN = "202400004D"


class MockScenario(BaseModel):
    """Safe synthetic scenario metadata for the demo UI."""

    uen: str
    label: str
    expected_outcome: str
    description: str


class SimulationProfile(BaseModel):
    """Backend-owned environment metadata displayed by the frontend."""

    is_simulated: Literal[True] = True
    registry_system: Literal["ACRA"] = "ACRA"
    registry_environment: Literal["MOCK"] = "MOCK"
    target_system: Literal["GOLDTIER"] = "GOLDTIER"
    target_environment: Literal["MOCK"] = "MOCK"


class MockScenarioDiscovery(BaseModel):
    """Application response for simulation profile and scenario discovery."""

    simulation: SimulationProfile
    scenarios: list[MockScenario]


class MockScenarioCatalogue(Protocol):
    """Demo-only boundary, intentionally separate from `AcraConnector`."""

    def discovery(self) -> MockScenarioDiscovery: ...

    def policy_validation_failure_uens(self) -> frozenset[str]: ...

    def partial_amend_uens(self) -> frozenset[str]: ...


class Phase01MockScenarioCatalogue:
    """Own all public scenario metadata and cross-mock behavior configuration."""

    _scenarios = (
        MockScenario(
            uen=VALID_SME_UEN,
            label="Valid synthetic SME",
            expected_outcome="COMPLETED",
            description="Complete registry data and successful mock GoldTier sequence.",
        ),
        MockScenario(
            uen=INCOMPLETE_ENTITY_UEN,
            label="Incomplete synthetic entity",
            expected_outcome="REVIEW_REQUIRED",
            description="Missing registered address; processing stops before GoldTier.",
        ),
        MockScenario(
            uen=GOLDTIER_FAILURE_UEN,
            label="Mock GoldTier validation failure",
            expected_outcome="FAILED",
            description="Complete ACRA data with a deterministic policy validation failure.",
        ),
        MockScenario(
            uen=GOLDTIER_PARTIAL_UEN,
            label="Mock GoldTier partial amend",
            expected_outcome="REVIEW_REQUIRED",
            description="Shell and policy succeed; amend returns a partial result for review.",
        ),
    )

    def discovery(self) -> MockScenarioDiscovery:
        return MockScenarioDiscovery(
            simulation=SimulationProfile(),
            scenarios=[scenario.model_copy(deep=True) for scenario in self._scenarios],
        )

    def policy_validation_failure_uens(self) -> frozenset[str]:
        return frozenset({GOLDTIER_FAILURE_UEN})

    def partial_amend_uens(self) -> frozenset[str]:
        return frozenset({GOLDTIER_PARTIAL_UEN})
