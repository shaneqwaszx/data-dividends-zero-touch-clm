"""Typed policy catalogue mutation, reset, and per-case snapshot owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.policy import (
    IDP_POLICY_ID,
    MAX_POLICY_AUDIT_EVENTS,
    UBO_POLICY_ID,
    CasePolicySnapshot,
    DecimalPolicyValue,
    PolicyAuditEvent,
    PolicyCatalogue,
    PolicyClassification,
    PolicyEnforcement,
    PolicyRule,
    PolicyValue,
    PolicyValueType,
    StringListPolicyValue,
    StringPolicyValue,
    validate_showcase_plain_text_value,
)
from app.services.admin_repository import (
    AdministrationAuditCapacityError,
    AdministrationConflictError,
    PolicyRepository,
    new_event_id,
)


class PolicyForbiddenError(Exception):
    pass


class PolicyNotFoundError(Exception):
    pass


class PolicyValidationError(Exception):
    pass


class PolicyManagementService:
    def __init__(
        self,
        repository: PolicyRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        if repository.get() is None:
            repository.create(default_policy_catalogue(self._clock()))

    def catalogue(self) -> PolicyCatalogue:
        value = self._repository.get()
        if value is None:
            raise PolicyNotFoundError
        return value

    def get(self, policy_id: str) -> PolicyRule:
        rule = self.catalogue().rule(policy_id)
        if rule is None:
            raise PolicyNotFoundError
        return rule

    def create_showcase(
        self,
        actor: AuthenticatedActor,
        *,
        expected_catalogue_version: int,
        policy_id: str,
        category: str,
        name: str,
        description: str,
        value: PolicyValue,
    ) -> PolicyCatalogue:
        self._require_mutation(actor)
        current = self.catalogue()
        if current.version != expected_catalogue_version or current.rule(policy_id) is not None:
            raise AdministrationConflictError
        if len(current.rules) >= 64:
            raise PolicyValidationError
        try:
            validate_showcase_plain_text_value(value)
        except ValueError:
            raise PolicyValidationError from None
        now = self._clock()
        rule = PolicyRule(
            policy_id=policy_id,
            category=category,
            name=name,
            description=description,
            value=value,
            value_type=value.type,
            default_value=value,
            classifications=(PolicyClassification.DISPLAY_ONLY_NOT_RUNTIME_ENFORCED,),
            enforcement=PolicyEnforcement.DISPLAY_SHOWCASE_ONLY,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by=actor.profile.user_id,
        )
        return self._save(
            current,
            rules=(*current.rules, rule),
            actor=actor,
            action="POLICY_CREATED",
            target=policy_id,
            expected_version=expected_catalogue_version,
        )

    def update(
        self,
        actor: AuthenticatedActor,
        policy_id: str,
        *,
        expected_catalogue_version: int,
        expected_rule_version: int,
        value: PolicyValue,
        name: str | None = None,
        description: str | None = None,
    ) -> PolicyCatalogue:
        self._require_mutation(actor)
        current = self.catalogue()
        rule = current.rule(policy_id)
        if (
            current.version != expected_catalogue_version
            or rule is None
            or rule.version != expected_rule_version
        ):
            raise AdministrationConflictError
        if rule.enforcement == PolicyEnforcement.NOT_EDITABLE:
            raise PolicyValidationError
        if rule.enforcement == PolicyEnforcement.DISPLAY_SHOWCASE_ONLY:
            try:
                validate_showcase_plain_text_value(value)
            except ValueError:
                raise PolicyValidationError from None
        now = self._clock()
        candidate_rule = rule.model_copy(
            update={
                "value": value,
                "name": name if name is not None else rule.name,
                "description": description if description is not None else rule.description,
                "version": rule.version + 1,
                "updated_at": now,
                "updated_by": actor.profile.user_id,
            },
            deep=True,
        )
        candidate_rule = PolicyRule.model_validate(candidate_rule)
        return self._save(
            current,
            rules=tuple(
                candidate_rule if item.policy_id == policy_id else item for item in current.rules
            ),
            actor=actor,
            action="POLICY_UPDATED",
            target=policy_id,
            expected_version=expected_catalogue_version,
        )

    def reset_one(
        self,
        actor: AuthenticatedActor,
        policy_id: str,
        *,
        expected_catalogue_version: int,
        expected_rule_version: int,
    ) -> PolicyCatalogue:
        self._require_mutation(actor)
        current = self.catalogue()
        rule = current.rule(policy_id)
        if (
            current.version != expected_catalogue_version
            or rule is None
            or rule.version != expected_rule_version
        ):
            raise AdministrationConflictError
        now = self._clock()
        reset = PolicyRule.model_validate(
            rule.model_copy(
                update={
                    "value": rule.default_value,
                    "version": rule.version + 1,
                    "updated_at": now,
                    "updated_by": actor.profile.user_id,
                },
                deep=True,
            )
        )
        return self._save(
            current,
            rules=tuple(reset if item.policy_id == policy_id else item for item in current.rules),
            actor=actor,
            action="POLICY_RESET_DEFAULT",
            target=policy_id,
            expected_version=expected_catalogue_version,
        )

    def reset_all(
        self,
        actor: AuthenticatedActor,
        *,
        expected_catalogue_version: int,
    ) -> PolicyCatalogue:
        self._require_mutation(actor)
        current = self.catalogue()
        if current.version != expected_catalogue_version:
            raise AdministrationConflictError
        now = self._clock()
        rules = tuple(
            PolicyRule.model_validate(
                rule.model_copy(
                    update={
                        "value": rule.default_value,
                        "version": rule.version + 1,
                        "updated_at": now,
                        "updated_by": actor.profile.user_id,
                    },
                    deep=True,
                )
            )
            for rule in current.rules
        )
        return self._save(
            current,
            rules=rules,
            actor=actor,
            action="POLICY_CATALOGUE_RESET",
            target=current.catalogue_id,
            expected_version=expected_catalogue_version,
        )

    def case_snapshot(self) -> CasePolicySnapshot:
        catalogue = self.catalogue()
        idp = catalogue.rule(IDP_POLICY_ID)
        ubo = catalogue.rule(UBO_POLICY_ID)
        if (
            idp is None
            or ubo is None
            or not isinstance(idp.value, DecimalPolicyValue)
            or not isinstance(ubo.value, DecimalPolicyValue)
            or idp.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
            or ubo.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
        ):
            raise PolicyValidationError
        return CasePolicySnapshot(
            snapshot_label=f"GLOBAL_POLICY_CATALOGUE_V{catalogue.version}",
            catalogue_version=catalogue.version,
            idp_review_confidence_threshold=Decimal(idp.value.value),
            ubo_threshold_percent=Decimal(ubo.value.value),
            bound_at=self._clock(),
        )

    def _require_mutation(self, actor: AuthenticatedActor) -> None:
        if Capability.POLICY_MUTATE not in ROLE_CAPABILITIES[actor.profile.role]:
            raise PolicyForbiddenError

    def _save(
        self,
        current: PolicyCatalogue,
        *,
        rules: tuple[PolicyRule, ...],
        actor: AuthenticatedActor,
        action: str,
        target: str,
        expected_version: int,
    ) -> PolicyCatalogue:
        if len(current.audit_events) >= MAX_POLICY_AUDIT_EVENTS:
            raise AdministrationAuditCapacityError
        now = self._clock()
        next_version = current.version + 1
        event = PolicyAuditEvent.model_validate(
            {
                "event_id": new_event_id(),
                "action": action,
                "actor_user_id": actor.profile.user_id,
                "target_id": target,
                "timestamp": now,
                "resulting_version": next_version,
                "metadata": {"rule_count": len(rules)},
            }
        )
        candidate = PolicyCatalogue(
            catalogue_id=current.catalogue_id,
            version=next_version,
            rules=rules,
            created_at=current.created_at,
            updated_at=now,
            updated_by=actor.profile.user_id,
            audit_events=(*current.audit_events, event),
        )
        return self._repository.update(candidate, expected_version=expected_version)


def default_policy_catalogue(now: datetime) -> PolicyCatalogue:
    pending = PolicyClassification.PENDING_SPONSOR_CONFIRMATION
    derived = PolicyClassification.SYSTEM_DERIVED
    project = PolicyClassification.PROJECT_DEFAULT

    def decimal_rule(
        policy_id: str,
        category: str,
        name: str,
        description: str,
        value: str,
        minimum: str,
        maximum: str,
    ) -> PolicyRule:
        typed = DecimalPolicyValue(value=value)
        return PolicyRule(
            policy_id=policy_id,
            category=category,
            name=name,
            description=description,
            value=typed,
            value_type=PolicyValueType.DECIMAL,
            default_value=typed,
            minimum=minimum,
            maximum=maximum,
            classifications=(project, pending),
            enforcement=PolicyEnforcement.RUNTIME_ENFORCED,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by="system-bootstrap",
        )

    def fixed(
        policy_id: str,
        category: str,
        name: str,
        description: str,
        value: PolicyValue,
        classifications: tuple[PolicyClassification, ...],
        allowed: tuple[str, ...] = (),
    ) -> PolicyRule:
        return PolicyRule(
            policy_id=policy_id,
            category=category,
            name=name,
            description=description,
            value=value,
            value_type=value.type,
            default_value=value,
            allowed_values=allowed,
            classifications=classifications,
            enforcement=PolicyEnforcement.NOT_EDITABLE,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by="system-bootstrap",
        )

    rules = (
        decimal_rule(
            IDP_POLICY_ID,
            "Document",
            "IDP review confidence threshold",
            "Minimum confidence for provisional automated document continuation.",
            "0.85",
            "0",
            "1",
        ),
        decimal_rule(
            UBO_POLICY_ID,
            "Ownership",
            "UBO threshold percent",
            "Provisional inclusive ownership candidate threshold.",
            "25.000000",
            "0",
            "100",
        ),
        fixed(
            "OWNERSHIP_UBO_COMPARATOR",
            "Ownership",
            "UBO comparator",
            "Fixed inclusive comparison used by deterministic ownership analysis.",
            StringPolicyValue(value="GREATER_THAN_OR_EQUAL_TO"),
            (derived, pending),
            ("GREATER_THAN_OR_EQUAL_TO",),
        ),
        fixed(
            "REGISTRY_SUPPORTED_JURISDICTIONS",
            "Registry",
            "Supported registry jurisdictions",
            "Jurisdictions with an implemented registry route.",
            StringListPolicyValue(value=("SG",)),
            (derived,),
            ("SG",),
        ),
        fixed(
            "REGISTRY_PROVIDER",
            "Registry",
            "Registry provider",
            "Current Singapore registry provider.",
            StringPolicyValue(value="ACRA"),
            (derived,),
            ("ACRA",),
        ),
        fixed(
            "DOCUMENT_SUPPORTED_MEDIA_TYPES",
            "Document",
            "Supported document media types",
            "Current bounded technical document formats.",
            StringListPolicyValue(value=("PDF", "DOCX", "UTF-8 TXT")),
            (derived, project),
            ("PDF", "DOCX", "UTF-8 TXT"),
        ),
        fixed(
            "WORKFLOW_SUPPORTED_STAGES",
            "Workflow",
            "Supported workflow stages",
            "Current implemented onboarding stage sequence.",
            StringListPolicyValue(
                value=(
                    "Registry",
                    "Document",
                    "Ownership",
                    "Readiness",
                    "Mock GoldTier",
                    "Complete",
                )
            ),
            (derived,),
            ("Registry", "Document", "Ownership", "Readiness", "Mock GoldTier", "Complete"),
        ),
        fixed(
            "RECONCILIATION_SOURCE_PRECEDENCE",
            "Reconciliation",
            "Source precedence",
            "No automatic source precedence is configured.",
            StringPolicyValue(value="NONE"),
            (derived, pending),
            ("NONE",),
        ),
    )
    return PolicyCatalogue(
        version=1,
        rules=rules,
        created_at=now,
        updated_at=now,
        updated_by="system-bootstrap",
    )
