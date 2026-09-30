"""Offline regression for the bounded external-smoke result serializer."""

from types import SimpleNamespace

import pytest
from scripts.recoverable_onboarding_smoke_report import (
    serialize_recoverable_onboarding_smoke,
)


def _case(
    *,
    search: str,
    registry: str = "COMPLETE",
    entity: object | None = object(),
    operations: tuple[SimpleNamespace, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        entity=entity,
        initial_target_search=SimpleNamespace(disposition=search),
        registry_acquisition=SimpleNamespace(
            status=registry,
            operation_results=operations,
        ),
    )


@pytest.mark.parametrize(
    ("case", "profile", "search", "registry", "unsupported"),
    [
        (_case(search="EXACT_MATCH"), "PROFILE_VERIFIED", "EXACT_MATCH", "COMPLETE", ()),
        (_case(search="NO_MATCH"), "PROFILE_VERIFIED", "NO_MATCH", "COMPLETE", ()),
        (
            _case(search="REVIEW_REQUIRED"),
            "PROFILE_VERIFIED",
            "REVIEW_REQUIRED",
            "COMPLETE",
            (),
        ),
        (_case(search="FAILED"), "PROFILE_VERIFIED", "FAILED", "COMPLETE", ()),
        (
            _case(
                search="NO_MATCH",
                registry="PARTIAL",
                entity=None,
                operations=(
                    SimpleNamespace(operation="ENTITY_PROFILE", status="COMPLETE"),
                    SimpleNamespace(operation="RELATIONSHIPS", status="NOT_ATTEMPTED"),
                ),
            ),
            "PARTIAL",
            "NO_MATCH",
            "PARTIAL",
            ("RELATIONSHIPS",),
        ),
    ],
    ids=[
        "profile-verified",
        "no-match",
        "review-required",
        "technical-failure",
        "unsupported-partial-operation",
    ],
)
def test_serializer_uses_current_case_search_evidence_offline(
    case: SimpleNamespace,
    profile: str,
    search: str,
    registry: str,
    unsupported: tuple[str, ...],
) -> None:
    report = serialize_recoverable_onboarding_smoke(case)

    assert report == {
        "profile": profile,
        "goldtier_search": search,
        "registry": registry,
        "unsupported_operations": unsupported,
    }
