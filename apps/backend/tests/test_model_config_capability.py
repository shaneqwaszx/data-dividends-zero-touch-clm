"""D-093: the AI Assistant model-management capability is HR's alone and changes no other
role boundary (HR still has no case access; Director publishing is unchanged)."""

from app.domain.access import ROLE_CAPABILITIES, Capability, Role, has_capability


def test_only_hr_may_manage_the_ai_model() -> None:
    holders = {role for role in Role if has_capability(role, Capability.MODEL_CONFIG_MANAGE)}
    assert holders == {Role.HR}


def test_model_management_leaves_every_other_capability_unchanged() -> None:
    assert ROLE_CAPABILITIES[Role.HR] == frozenset(
        {
            Capability.POLICY_VIEW,
            Capability.POLICY_MUTATE,
            Capability.IDENTITY_ADMIN,
            Capability.TEAM_ADMIN,
            Capability.PROVIDER_SANDBOX_TEST,
            Capability.MODEL_CONFIG_MANAGE,
        }
    )
    assert Capability.CASE_ACCESS not in ROLE_CAPABILITIES[Role.HR]
    assert Capability.POLICY_APPROVE not in ROLE_CAPABILITIES[Role.HR]
    assert ROLE_CAPABILITIES[Role.DIRECTOR] == frozenset(
        {
            Capability.POLICY_VIEW,
            Capability.POLICY_APPROVE,
            Capability.CASE_ACCESS,
            Capability.CASE_GLOBAL,
            Capability.TARGET_RECOVERY,
        }
    )
    for role in (Role.RELATIONSHIP_MANAGER, Role.CLIENT_ONBOARDER):
        assert ROLE_CAPABILITIES[role] == frozenset(
            {Capability.POLICY_VIEW, Capability.CASE_ACCESS}
        )


def test_support_reviews_knowledge_and_views_policy_without_case_access() -> None:
    """D-099: SUPPORT alone reviews knowledge; Director keeps policy approval only."""

    assert ROLE_CAPABILITIES[Role.SUPPORT] == frozenset(
        {
            Capability.POLICY_VIEW,
            Capability.KNOWLEDGE_REVIEW,
            Capability.KNOWLEDGE_CASE_READ,
        }
    )
    for capability in (Capability.KNOWLEDGE_REVIEW, Capability.KNOWLEDGE_CASE_READ):
        assert {role for role in Role if has_capability(role, capability)} == {Role.SUPPORT}
    assert not has_capability(Role.SUPPORT, Capability.CASE_ACCESS)
    assert not has_capability(Role.SUPPORT, Capability.POLICY_APPROVE)
    assert not has_capability(Role.SUPPORT, Capability.POLICY_MUTATE)
