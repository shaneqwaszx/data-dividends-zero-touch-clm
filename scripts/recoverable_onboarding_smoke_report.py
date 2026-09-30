"""Serialize bounded onboarding-smoke outcomes without making provider calls.

The external read run is intentionally not repeated. This module only formats an
already-created case and uses the current ``initial_target_search`` owner.
"""

from __future__ import annotations

from typing import TypedDict


class RecoverableOnboardingSmokeReport(TypedDict):
    profile: str
    goldtier_search: str
    registry: str
    unsupported_operations: tuple[str, ...]


def _value(value: object | None, default: str) -> str:
    if value is None:
        return default
    raw = getattr(value, "value", value)
    return str(raw)


def serialize_recoverable_onboarding_smoke(case: object) -> RecoverableOnboardingSmokeReport:
    """Return status-only evidence from a retained case; never include payload data."""

    acquisition = getattr(case, "registry_acquisition", None)
    entity = getattr(case, "entity", None)
    registry = _value(getattr(acquisition, "status", None), "NOT_EXECUTED")
    profile = "PROFILE_VERIFIED" if entity is not None and registry == "COMPLETE" else registry

    # OnboardingCase owns the initial read-only Search evidence. The obsolete harness
    # incorrectly looked for CLM's later target_search_checkpoint on this object.
    search = getattr(case, "initial_target_search", None)
    search_status = _value(getattr(search, "disposition", None), "NOT_EXECUTED")

    unsupported = tuple(
        _value(getattr(operation, "operation", None), "UNKNOWN")
        for operation in getattr(acquisition, "operation_results", ())
        if _value(getattr(operation, "status", None), "NOT_ATTEMPTED")
        in {"NOT_ATTEMPTED", "UNSUPPORTED"}
    )
    return {
        "profile": profile,
        "goldtier_search": search_status,
        "registry": registry,
        "unsupported_operations": unsupported,
    }
