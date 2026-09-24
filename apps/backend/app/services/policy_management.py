"""Typed policy catalogue mutation, reset, and per-case snapshot owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.policy import (
    ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID,
    ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID,
    ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID,
    ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID,
    ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID,
    ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID,
    ENTITY_RESOLUTION_NAME_WEIGHT_ID,
    ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID,
    GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
    GOLDTIER_BOOKING_ENTITY_ID,
    GOLDTIER_CLIENT_SEGMENT_ID,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
    GOLDTIER_KYC_CUSTOMER_TYPE_ID,
    GOLDTIER_POLICY_ID,
    GOLDTIER_PRODUCT_TYPE_ID,
    GOLDTIER_REGISTRATION_TYPE_ID,
    GOLDTIER_TARGET_POLICY_IDS,
    IDP_POLICY_ID,
    MAX_POLICY_AUDIT_EVENTS,
    MOCK_RISK_BLOCKS_READINESS_ID,
    MOCK_RISK_HIGH_THRESHOLD_ID,
    MOCK_RISK_MEDIUM_THRESHOLD_ID,
    UBO_ADVISORY_LIKELY_THRESHOLD_ID,
    UBO_ADVISORY_UNLIKELY_THRESHOLD_ID,
    UBO_POLICY_ID,
    AuthorityLabelledTargetValue,
    BooleanPolicyValue,
    CasePolicySnapshot,
    DecimalPolicyValue,
    EntityResolutionWeights,
    GoldTierTargetPolicySnapshot,
    IntegerPolicyValue,
    IntelligencePolicySnapshot,
    PolicyAuditEvent,
    PolicyAuthority,
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
        current = repository.get()
        if current is None:
            repository.create(default_policy_catalogue(self._clock()))
        else:
            self._upgrade_legacy_catalogue(current)

    def _upgrade_legacy_catalogue(self, current: PolicyCatalogue) -> None:
        defaults = default_policy_catalogue(self._clock())
        required_ids = tuple(rule.policy_id for rule in defaults.rules)
        current_ids = tuple(rule.policy_id for rule in current.rules)
        if all(policy_id in current_ids for policy_id in required_ids):
            return
        if (
            current_ids != required_ids[: len(current_ids)]
            or len(current_ids) not in {8, 21}
            or len(current.audit_events) >= MAX_POLICY_AUDIT_EVENTS
        ):
            raise PolicyValidationError
        now = self._clock()
        next_version = current.version + 1
        event = PolicyAuditEvent(
            event_id=new_event_id(),
            action="POLICY_CATALOGUE_MIGRATED",
            actor_user_id="system-bootstrap",
            target_id=current.catalogue_id,
            timestamp=now,
            resulting_version=next_version,
            metadata={"added_rule_count": len(defaults.rules) - len(current.rules)},
        )
        candidate = PolicyCatalogue(
            catalogue_id=current.catalogue_id,
            version=next_version,
            rules=(*current.rules, *defaults.rules[len(current.rules) :]),
            created_at=current.created_at,
            updated_at=now,
            updated_by="system-bootstrap",
            audit_events=(*current.audit_events, event),
        )
        self._repository.update(candidate, expected_version=current.version)

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
        authority: PolicyAuthority | None = None,
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
        if authority is not None and policy_id not in GOLDTIER_TARGET_POLICY_IDS:
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
                "authority": authority if authority is not None else rule.authority,
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
                    "authority": rule.default_authority,
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
                        "authority": rule.default_authority,
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
        intelligence = self._intelligence_snapshot(catalogue)
        goldtier_target = self._goldtier_target_snapshot(catalogue)
        return CasePolicySnapshot(
            snapshot_label=f"GLOBAL_POLICY_CATALOGUE_V{catalogue.version}",
            catalogue_version=catalogue.version,
            idp_review_confidence_threshold=Decimal(idp.value.value),
            ubo_threshold_percent=Decimal(ubo.value.value),
            intelligence=intelligence,
            goldtier_target=goldtier_target,
            bound_at=self._clock(),
        )

    @staticmethod
    def _goldtier_target_snapshot(catalogue: PolicyCatalogue) -> GoldTierTargetPolicySnapshot:
        def value(policy_id: str) -> AuthorityLabelledTargetValue:
            rule = catalogue.rule(policy_id)
            if (
                rule is None
                or not isinstance(rule.value, StringPolicyValue)
                or rule.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
                or rule.authority is None
            ):
                raise PolicyValidationError
            return AuthorityLabelledTargetValue(
                value=rule.value.value,
                authority=rule.authority,
            )

        return GoldTierTargetPolicySnapshot(
            kyc_customer_type=value(GOLDTIER_KYC_CUSTOMER_TYPE_ID),
            client_segment=value(GOLDTIER_CLIENT_SEGMENT_ID),
            customer_external_system=value(GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID),
            registration_type=value(GOLDTIER_REGISTRATION_TYPE_ID),
            policy=value(GOLDTIER_POLICY_ID),
            booking_entity=value(GOLDTIER_BOOKING_ENTITY_ID),
            account_entity_type=value(GOLDTIER_ACCOUNT_ENTITY_TYPE_ID),
            product_type=value(GOLDTIER_PRODUCT_TYPE_ID),
        )

    @classmethod
    def _intelligence_snapshot(cls, catalogue: PolicyCatalogue) -> IntelligencePolicySnapshot:
        decimal_values = {
            policy_id: cls._runtime_decimal(catalogue, policy_id)
            for policy_id in (
                ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID,
                ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID,
                ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID,
                ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID,
                ENTITY_RESOLUTION_NAME_WEIGHT_ID,
                ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID,
                ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID,
                ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID,
                UBO_ADVISORY_LIKELY_THRESHOLD_ID,
                UBO_ADVISORY_UNLIKELY_THRESHOLD_ID,
            )
        }
        risk_block = catalogue.rule(MOCK_RISK_BLOCKS_READINESS_ID)
        if (
            risk_block is None
            or not isinstance(risk_block.value, BooleanPolicyValue)
            or risk_block.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
        ):
            raise PolicyValidationError
        try:
            return IntelligencePolicySnapshot(
                entity_resolution_auto_match_threshold=decimal_values[
                    ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID
                ],
                entity_resolution_review_threshold=decimal_values[
                    ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID
                ],
                entity_resolution_ambiguity_margin=decimal_values[
                    ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID
                ],
                entity_resolution_weights=EntityResolutionWeights(
                    identifier=decimal_values[ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID],
                    name=decimal_values[ENTITY_RESOLUTION_NAME_WEIGHT_ID],
                    address=decimal_values[ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID],
                    legal_form=decimal_values[ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID],
                    incorporation_date=decimal_values[
                        ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID
                    ],
                ),
                ubo_advisory_likely_threshold=decimal_values[
                    UBO_ADVISORY_LIKELY_THRESHOLD_ID
                ],
                ubo_advisory_unlikely_threshold=decimal_values[
                    UBO_ADVISORY_UNLIKELY_THRESHOLD_ID
                ],
                mock_risk_medium_threshold=cls._runtime_integer(
                    catalogue, MOCK_RISK_MEDIUM_THRESHOLD_ID
                ),
                mock_risk_high_threshold=cls._runtime_integer(
                    catalogue, MOCK_RISK_HIGH_THRESHOLD_ID
                ),
                mock_risk_blocks_readiness=risk_block.value.value,
            )
        except ValueError:
            raise PolicyValidationError from None

    @staticmethod
    def _runtime_decimal(catalogue: PolicyCatalogue, policy_id: str) -> Decimal:
        rule = catalogue.rule(policy_id)
        if (
            rule is None
            or not isinstance(rule.value, DecimalPolicyValue)
            or rule.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
        ):
            raise PolicyValidationError
        return Decimal(rule.value.value)

    @staticmethod
    def _runtime_integer(catalogue: PolicyCatalogue, policy_id: str) -> int:
        rule = catalogue.rule(policy_id)
        if (
            rule is None
            or not isinstance(rule.value, IntegerPolicyValue)
            or rule.enforcement != PolicyEnforcement.RUNTIME_ENFORCED
        ):
            raise PolicyValidationError
        return rule.value.value

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
        self._intelligence_snapshot(candidate)
        self._goldtier_target_snapshot(candidate)
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
        classifications: tuple[PolicyClassification, ...] = (project, pending),
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
            classifications=classifications,
            enforcement=PolicyEnforcement.RUNTIME_ENFORCED,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by="system-bootstrap",
        )

    def integer_rule(
        policy_id: str,
        category: str,
        name: str,
        description: str,
        value: int,
        minimum: int,
        maximum: int,
    ) -> PolicyRule:
        typed = IntegerPolicyValue(value=value)
        return PolicyRule(
            policy_id=policy_id,
            category=category,
            name=name,
            description=description,
            value=typed,
            value_type=PolicyValueType.INTEGER,
            default_value=typed,
            minimum=minimum,
            maximum=maximum,
            classifications=(project,),
            enforcement=PolicyEnforcement.RUNTIME_ENFORCED,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by="system-bootstrap",
        )

    def boolean_rule(
        policy_id: str,
        category: str,
        name: str,
        description: str,
        value: bool,
    ) -> PolicyRule:
        typed = BooleanPolicyValue(value=value)
        return PolicyRule(
            policy_id=policy_id,
            category=category,
            name=name,
            description=description,
            value=typed,
            value_type=PolicyValueType.BOOLEAN,
            default_value=typed,
            classifications=(project,),
            enforcement=PolicyEnforcement.RUNTIME_ENFORCED,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by="system-bootstrap",
        )

    def target_rule(
        policy_id: str,
        name: str,
        description: str,
    ) -> PolicyRule:
        typed = StringPolicyValue(value="TBD_SPONSOR")
        return PolicyRule(
            policy_id=policy_id,
            category="GoldTier target preparation",
            name=name,
            description=description,
            value=typed,
            value_type=PolicyValueType.STRING,
            default_value=typed,
            classifications=(pending,),
            authority=PolicyAuthority.TBD_SPONSOR,
            default_authority=PolicyAuthority.TBD_SPONSOR,
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
        decimal_rule(
            ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID,
            "Intelligence",
            "Entity-resolution auto-match threshold",
            "Project-defined minimum score for a probable automatic identity match.",
            "0.85",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID,
            "Intelligence",
            "Entity-resolution review threshold",
            "Project-defined minimum score for identity review.",
            "0.60",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID,
            "Intelligence",
            "Entity-resolution ambiguity margin",
            "Project-defined maximum top-candidate gap requiring human review.",
            "0.03",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID,
            "Intelligence",
            "Identifier and country weight",
            "Explainable entity-resolution weight for identifier and country.",
            "0.55",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_NAME_WEIGHT_ID,
            "Intelligence",
            "Legal-name weight",
            "Explainable entity-resolution weight for normalized legal name.",
            "0.25",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID,
            "Intelligence",
            "Registered-address weight",
            "Explainable entity-resolution weight for normalized registered address.",
            "0.10",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID,
            "Intelligence",
            "Legal-form weight",
            "Explainable entity-resolution weight for legal form.",
            "0.05",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID,
            "Intelligence",
            "Incorporation-date weight",
            "Explainable entity-resolution weight for incorporation date.",
            "0.05",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            UBO_ADVISORY_LIKELY_THRESHOLD_ID,
            "Intelligence",
            "UBO advisory likely threshold",
            "Project-defined advisory probability threshold for likely UBO.",
            "0.65",
            "0",
            "1",
            (project,),
        ),
        decimal_rule(
            UBO_ADVISORY_UNLIKELY_THRESHOLD_ID,
            "Intelligence",
            "UBO advisory unlikely threshold",
            "Project-defined advisory probability threshold for unlikely UBO.",
            "0.35",
            "0",
            "1",
            (project,),
        ),
        integer_rule(
            MOCK_RISK_MEDIUM_THRESHOLD_ID,
            "Intelligence",
            "Mock risk medium threshold",
            "Project-defined lower bound for the mock advisory medium band.",
            30,
            0,
            100,
        ),
        integer_rule(
            MOCK_RISK_HIGH_THRESHOLD_ID,
            "Intelligence",
            "Mock risk high threshold",
            "Project-defined lower bound for the mock advisory high band.",
            60,
            0,
            100,
        ),
        boolean_rule(
            MOCK_RISK_BLOCKS_READINESS_ID,
            "Intelligence",
            "Mock risk blocks readiness",
            "Project-defined switch for routing assessed mock risk to human review.",
            False,
        ),
        target_rule(
            GOLDTIER_KYC_CUSTOMER_TYPE_ID,
            "GoldTier KYC customer type",
            "Authority-labelled XPI Shell customer type; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_CLIENT_SEGMENT_ID,
            "GoldTier client segment",
            "Authority-labelled XPI Shell client segment; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
            "GoldTier customer external system",
            "Authority-labelled XPI external-system label; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_REGISTRATION_TYPE_ID,
            "GoldTier registration type",
            "Authority-labelled XPI registration type; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_POLICY_ID,
            "GoldTier policy",
            "Authority-labelled XPI customer policy; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_BOOKING_ENTITY_ID,
            "GoldTier booking entity",
            "Authority-labelled XPI booking entity; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
            "GoldTier account entity type",
            "Authority-labelled XPI account entity type; the default blocks dispatch.",
        ),
        target_rule(
            GOLDTIER_PRODUCT_TYPE_ID,
            "GoldTier product type",
            "Authority-labelled XPI product type; the default blocks dispatch.",
        ),
    )
    return PolicyCatalogue(
        version=1,
        rules=rules,
        created_at=now,
        updated_at=now,
        updated_by="system-bootstrap",
    )
