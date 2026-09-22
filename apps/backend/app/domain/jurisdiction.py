"""Source-aware jurisdiction evidence and deterministic resolution outcomes."""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SINGAPORE_UEN_PATTERN = re.compile(
    r"^(?:[0-9]{8}[A-Z]|[0-9]{9}[A-Z]|[TSR][0-9]{2}[A-Z]{2}[0-9]{4}[A-Z])$"
)


def is_eligible_singapore_uen(identifier: str) -> bool:
    """Apply the bounded project Singapore UEN syntax at provider boundaries."""

    return _SINGAPORE_UEN_PATTERN.fullmatch(identifier) is not None


class JurisdictionCode(StrEnum):
    """Jurisdictions recognised by the Phase 09 decision gateway."""

    SINGAPORE = "SG"
    AUSTRALIA = "AU"
    MALAYSIA = "MY"
    HONG_KONG = "HK"


class JurisdictionObservationSource(StrEnum):
    """Known evidence sources; only the first two are active in Phase 09."""

    USER_INPUT = "USER_INPUT"
    IDENTIFIER_FORMAT = "IDENTIFIER_FORMAT"
    EXISTING_CASE = "EXISTING_CASE"
    DOCUMENT_IDP = "DOCUMENT_IDP"
    UPSTREAM_SYSTEM = "UPSTREAM_SYSTEM"


class JurisdictionResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


class RegistryProviderCode(StrEnum):
    ACRA = "ACRA"


class RegistryRoutingStatus(StrEnum):
    SELECTED = "SELECTED"
    PROVIDER_NOT_IMPLEMENTED = "PROVIDER_NOT_IMPLEMENTED"


class JurisdictionObservation(BaseModel):
    """One bounded jurisdiction assertion with explicit provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    jurisdiction: JurisdictionCode
    source: JurisdictionObservationSource
    observed_at: datetime
    source_reference: str | None = Field(default=None, min_length=1, max_length=128)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_utc_timestamp(self) -> "JurisdictionObservation":
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() != timedelta(0):
            raise ValueError("jurisdiction observation time must be timezone-aware UTC")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(UTC))
        return self


class JurisdictionResolution(BaseModel):
    """Deterministic result that retains every input observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: JurisdictionResolutionStatus
    resolved_jurisdiction: JurisdictionCode | None = None
    observations: tuple[JurisdictionObservation, ...] = Field(default_factory=tuple, max_length=8)
    resolved_at: datetime

    @model_validator(mode="after")
    def enforce_resolution_invariants(self) -> "JurisdictionResolution":
        if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() != timedelta(0):
            raise ValueError("jurisdiction resolution time must be timezone-aware UTC")
        observed_jurisdictions = {item.jurisdiction for item in self.observations}
        if self.status == JurisdictionResolutionStatus.RESOLVED:
            if self.resolved_jurisdiction is None or not self.observations:
                raise ValueError("resolved jurisdiction requires supporting observations")
            if observed_jurisdictions != {self.resolved_jurisdiction}:
                raise ValueError(
                    "resolved jurisdiction must match every supporting observation"
                )
        elif self.status == JurisdictionResolutionStatus.UNRESOLVED:
            if self.resolved_jurisdiction is not None or self.observations:
                raise ValueError(
                    "unresolved jurisdiction cannot contain a selection or observations"
                )
        else:
            if self.resolved_jurisdiction is not None:
                raise ValueError("conflicting jurisdiction cannot select a country")
            if len(self.observations) < 2 or len(observed_jurisdictions) < 2:
                raise ValueError(
                    "conflicting jurisdiction requires at least two disagreeing observations"
                )
        return self


class RegistryRoutingDecision(BaseModel):
    """Safe provider decision; no endpoint, credentials, or dynamic class names."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RegistryRoutingStatus
    jurisdiction: JurisdictionCode
    provider: RegistryProviderCode | None = None
    decided_at: datetime

    @model_validator(mode="after")
    def enforce_routing_invariants(self) -> "RegistryRoutingDecision":
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() != timedelta(0):
            raise ValueError("registry routing time must be timezone-aware UTC")
        if self.status == RegistryRoutingStatus.SELECTED:
            if (
                self.jurisdiction != JurisdictionCode.SINGAPORE
                or self.provider != RegistryProviderCode.ACRA
            ):
                raise ValueError("only Singapore can select the ACRA registry provider")
        elif (
            self.jurisdiction == JurisdictionCode.SINGAPORE
            or self.provider is not None
        ):
            raise ValueError(
                "only recognised foreign jurisdictions can omit an unimplemented provider"
            )
        return self


class JurisdictionResolver:
    """Resolve observations without source precedence or implicit tie-breaking."""

    def resolve(
        self,
        observations: tuple[JurisdictionObservation, ...] | list[JurisdictionObservation],
        *,
        resolved_at: datetime,
    ) -> JurisdictionResolution:
        retained = tuple(observations)
        jurisdictions = {item.jurisdiction for item in retained}
        if not retained:
            return JurisdictionResolution(
                status=JurisdictionResolutionStatus.UNRESOLVED,
                observations=(),
                resolved_at=resolved_at,
            )
        if len(jurisdictions) == 1:
            return JurisdictionResolution(
                status=JurisdictionResolutionStatus.RESOLVED,
                resolved_jurisdiction=next(iter(jurisdictions)),
                observations=retained,
                resolved_at=resolved_at,
            )
        return JurisdictionResolution(
            status=JurisdictionResolutionStatus.CONFLICT,
            observations=retained,
            resolved_at=resolved_at,
        )
