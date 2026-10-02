"""Typed policy catalogue mutation, reset, and per-case snapshot owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock

from pydantic import ValidationError

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
    GOLDTIER_ACCOUNT_ENTITY_TYPE_POC_VALUE,
    GOLDTIER_BOOKING_ENTITY_ID,
    GOLDTIER_BOOKING_ENTITY_POC_VALUE,
    GOLDTIER_CLIENT_SEGMENT_ID,
    GOLDTIER_CLIENT_SEGMENT_VALUES,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
    GOLDTIER_KYC_CUSTOMER_TYPE_ID,
    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
    GOLDTIER_POLICY_ID,
    GOLDTIER_POLICY_POC_VALUE,
    GOLDTIER_PRODUCT_TYPE_ID,
    GOLDTIER_REGISTRATION_TYPE_ID,
    GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
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
    EvidenceClassifierPolicy,
    GoldTierTargetPolicySnapshot,
    IntegerPolicyValue,
    IntelligencePolicySnapshot,
    PolicyAuditEvent,
    PolicyAuthority,
    PolicyCatalogue,
    PolicyClassification,
    PolicyEnforcement,
    PolicyProposal,
    PolicyRule,
    PolicyValue,
    PolicyValueType,
    PolicyVersionRecord,
    RegistryPolicySnapshot,
    StringListPolicyValue,
    StringPolicyValue,
)
from app.services.admin_repository import (
    AdministrationAuditCapacityError,
    AdministrationConflictError,
    PolicyRepository,
    new_event_id,
)
from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger


class PolicyForbiddenError(Exception):
    pass


class PolicyNotFoundError(Exception):
    pass


class PolicyValidationError(Exception):
    pass


CASE_BOUND_GOLDTIER_POLICY_IDS = frozenset(
    {GOLDTIER_KYC_CUSTOMER_TYPE_ID, GOLDTIER_CLIENT_SEGMENT_ID}
)


class PolicyManagementService:
    def __init__(
        self,
        repository: PolicyRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._lock = RLock()
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
        legacy_count = next(
            (
                count
                for count in (29, 21, 8)
                if current_ids[:count] == required_ids[:count]
                and all(
                    rule.enforcement == PolicyEnforcement.DISPLAY_SHOWCASE_ONLY
                    and rule.policy_id not in required_ids
                    for rule in current.rules[count:]
                )
            ),
            None,
        )
        if legacy_count is None or len(current.audit_events) >= MAX_POLICY_AUDIT_EVENTS:
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
            metadata={"added_rule_count": len(defaults.rules) - legacy_count},
        )
        candidate = PolicyCatalogue(
            catalogue_id=current.catalogue_id,
            version=next_version,
            active_version=next_version,
            active_effective_at=now,
            rules=(
                *current.rules[:legacy_count],
                *defaults.rules[legacy_count:],
                *current.rules[legacy_count:],
            ),
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

    def create_showcase(self, *args: object, **kwargs: object) -> PolicyCatalogue:
        """Retired direct mutation route; arbitrary rules have no runtime consumer."""
        raise PolicyForbiddenError

    def update(self, *args: object, **kwargs: object) -> PolicyCatalogue:
        raise PolicyForbiddenError

    def reset_one(self, *args: object, **kwargs: object) -> PolicyCatalogue:
        raise PolicyForbiddenError

    def reset_all(self, *args: object, **kwargs: object) -> PolicyCatalogue:
        raise PolicyForbiddenError

    def _authorized_actor(
        self,
        actor: AuthenticatedActor,
        reauthorize: Callable[[], AuthenticatedActor] | None,
        capability: Capability,
    ) -> AuthenticatedActor:
        current = reauthorize() if reauthorize is not None else actor
        if (
            current.profile.user_id != actor.profile.user_id
            or capability not in ROLE_CAPABILITIES[current.profile.role]
        ):
            raise PolicyForbiddenError
        return current

    def _proposed_rules(
        self,
        current: PolicyCatalogue,
        source: tuple[PolicyRule, ...],
        changes: dict[str, PolicyValue],
        reset_ids: tuple[str, ...],
        actor: AuthenticatedActor,
    ) -> tuple[PolicyRule, ...]:
        if len(changes) > 64 or len(reset_ids) > 64 or len(set(reset_ids)) != len(reset_ids):
            raise PolicyValidationError
        ids = set(changes) | set(reset_ids)
        if set(changes) & set(reset_ids) or not ids:
            raise PolicyValidationError
        by_id = {rule.policy_id: rule for rule in current.rules}
        if any(
            key not in by_id
            or by_id[key].enforcement != PolicyEnforcement.RUNTIME_ENFORCED
            or key in GOLDTIER_TARGET_POLICY_IDS
            for key in ids
        ):
            raise PolicyValidationError
        now = self._clock()
        try:
            rules = tuple(
                PolicyRule.model_validate(
                    rule.model_copy(
                        update={
                            "value": by_id[rule.policy_id].default_value
                            if rule.policy_id in reset_ids
                            else changes.get(rule.policy_id, rule.value),
                            "version": by_id[rule.policy_id].version + 1,
                            "updated_at": now,
                            "updated_by": actor.profile.user_id,
                        }
                    ).model_dump()
                )
                if rule.policy_id in ids
                else rule
                for rule in source
            )
        except (ValidationError, ValueError, TypeError):
            raise PolicyValidationError from None
        return rules

    def create_proposal(
        self,
        actor: AuthenticatedActor,
        *,
        expected_catalogue_version: int,
        changes: dict[str, PolicyValue],
        reason: str,
        reset_ids: tuple[str, ...] = (),
        reauthorize: Callable[[], AuthenticatedActor] | None = None,
    ) -> PolicyCatalogue:
        with self._lock:
            actor = self._authorized_actor(actor, reauthorize, Capability.POLICY_MUTATE)
            current = self._expected(expected_catalogue_version)
            if len(current.proposals) >= 64:
                raise AdministrationAuditCapacityError
            now = self._clock()
            try:
                proposal = PolicyProposal(
                    proposal_id=new_event_id(),
                    base_active_version=current.active_version,
                    proposer_id=actor.profile.user_id,
                    reason=reason,
                    created_at=now,
                    updated_at=now,
                    rules=self._proposed_rules(current, current.rules, changes, reset_ids, actor),
                )
            except (ValidationError, ValueError, TypeError):
                raise PolicyValidationError from None
            return self._persist(
                current,
                actor,
                "POLICY_PROPOSAL_CREATED",
                proposal.proposal_id,
                proposals=(*current.proposals, proposal),
            )

    def edit_proposal(
        self,
        actor: AuthenticatedActor,
        proposal_id: str,
        *,
        expected_catalogue_version: int,
        expected_proposal_version: int,
        changes: dict[str, PolicyValue],
        reason: str,
        reset_ids: tuple[str, ...] = (),
        reauthorize: Callable[[], AuthenticatedActor] | None = None,
    ) -> PolicyCatalogue:
        with self._lock:
            actor = self._authorized_actor(actor, reauthorize, Capability.POLICY_MUTATE)
            current = self._expected(expected_catalogue_version)
            proposal = self._proposal(current, proposal_id, expected_proposal_version, "DRAFT")
            if proposal.proposer_id != actor.profile.user_id:
                raise PolicyForbiddenError
            try:
                updated = PolicyProposal.model_validate(
                    proposal.model_copy(
                        update={
                            "rules": self._proposed_rules(
                                current, proposal.rules, changes, reset_ids, actor
                            ),
                            "reason": reason,
                            "updated_at": self._clock(),
                            "version": proposal.version + 1,
                        }
                    ).model_dump()
                )
            except (ValidationError, ValueError, TypeError):
                raise PolicyValidationError from None
            return self._persist(
                current,
                actor,
                "POLICY_PROPOSAL_EDITED",
                proposal_id,
                proposals=tuple(
                    updated if p.proposal_id == proposal_id else p for p in current.proposals
                ),
            )

    def submit_proposal(
        self,
        actor: AuthenticatedActor,
        proposal_id: str,
        *,
        expected_catalogue_version: int,
        expected_proposal_version: int,
        reauthorize: Callable[[], AuthenticatedActor] | None = None,
    ) -> PolicyCatalogue:
        with self._lock:
            actor = self._authorized_actor(actor, reauthorize, Capability.POLICY_MUTATE)
            current = self._expected(expected_catalogue_version)
            proposal = self._proposal(current, proposal_id, expected_proposal_version, "DRAFT")
            if proposal.proposer_id != actor.profile.user_id:
                raise PolicyForbiddenError
            self._validate_runtime(current.model_copy(update={"rules": proposal.rules}))
            updated = proposal.model_copy(
                update={
                    "status": "PENDING_APPROVAL",
                    "version": proposal.version + 1,
                    "updated_at": self._clock(),
                }
            )
            return self._persist(
                current,
                actor,
                "POLICY_PROPOSAL_SUBMITTED",
                proposal_id,
                proposals=tuple(
                    updated if p.proposal_id == proposal_id else p for p in current.proposals
                ),
            )

    def decide_proposal(
        self,
        actor: AuthenticatedActor,
        proposal_id: str,
        *,
        approve: bool,
        expected_catalogue_version: int,
        expected_proposal_version: int,
        reason: str,
        reauthorize: Callable[[], AuthenticatedActor] | None = None,
    ) -> PolicyCatalogue:
        with self._lock:
            actor = self._authorized_actor(actor, reauthorize, Capability.POLICY_APPROVE)
            current = self._expected(expected_catalogue_version)
            proposal = self._proposal(
                current, proposal_id, expected_proposal_version, "PENDING_APPROVAL"
            )
            if proposal.proposer_id == actor.profile.user_id:
                raise PolicyForbiddenError
            if approve and len(current.superseded_versions) >= 64:
                raise AdministrationAuditCapacityError
            self._validate_runtime(current.model_copy(update={"rules": proposal.rules}))
            now = self._clock()
            next_active = current.version + 1
            try:
                updated = PolicyProposal.model_validate(
                    proposal.model_copy(
                        update={
                            "status": "APPROVED" if approve else "REJECTED",
                            "version": proposal.version + 1,
                            "updated_at": now,
                            "decided_at": now,
                            "decided_by": actor.profile.user_id,
                            "decision_reason": reason,
                            "activated_version": next_active if approve else None,
                        }
                    ).model_dump()
                )
            except (ValidationError, ValueError, TypeError):
                raise PolicyValidationError from None
            values: dict[str, object] = {
                "proposals": tuple(
                    updated if p.proposal_id == proposal_id else p for p in current.proposals
                )
            }
            if approve:
                values.update(
                    rules=proposal.rules,
                    active_version=next_active,
                    active_origin="APPROVED",
                    active_effective_at=now,
                    superseded_versions=(
                        *current.superseded_versions,
                        PolicyVersionRecord(
                            version=current.active_version, rules=current.rules, superseded_at=now
                        ),
                    ),
                )
            return self._persist(
                current,
                actor,
                "POLICY_PROPOSAL_APPROVED" if approve else "POLICY_PROPOSAL_REJECTED",
                proposal_id,
                **values,
            )

    def classifier_benchmark(self) -> dict[str, object]:
        from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger

        with self._lock:
            current = self.catalogue()
            return OwnershipEvidenceTagger().benchmark(
                self._classifier_snapshot(current), policy_version=current.active_version
            )

    def proposal_impact(self, proposal_id: str) -> dict[str, object]:
        """Read-only synthetic fixtures, without any case/provider mutation path."""
        with self._lock:
            current = self.catalogue()
            proposal = next((p for p in current.proposals if p.proposal_id == proposal_id), None)
            if proposal is None:
                raise PolicyNotFoundError
            proposed = current.model_copy(update={"rules": proposal.rules})
            self._validate_runtime(proposed)
            tagger = OwnershipEvidenceTagger()
            before = tagger.benchmark(
                self._classifier_snapshot(current), policy_version=current.active_version
            )
            after = tagger.benchmark(
                self._classifier_snapshot(proposed), policy_version=current.version + 1
            )

            def runtime(catalogue: PolicyCatalogue) -> dict[str, object]:
                registry = self._registry_snapshot(catalogue)
                document = self._runtime_decimal(catalogue, IDP_POLICY_ID)
                ownership = self._runtime_decimal(catalogue, UBO_POLICY_ID)
                return dict(
                    registry_freshness_seconds=registry.freshness_seconds,
                    not_found_ttl_seconds=registry.negative_seconds,
                    document_auto_confirm=[
                        confidence >= document
                        for confidence in (Decimal("0.84"), Decimal("0.85"), Decimal("0.90"))
                    ],
                    ownership_numeric_candidates=[
                        percent >= ownership
                        for percent in (Decimal("24.999999"), Decimal("25"), Decimal("30"))
                    ],
                )

            changes = [
                dict(
                    policy_id=rule.policy_id,
                    current=base.value.model_dump(mode="json"),
                    default=base.default_value.model_dump(mode="json"),
                    proposed=rule.value.model_dump(mode="json"),
                )
                for rule in proposal.rules
                if (base := current.rule(rule.policy_id)) is not None and rule.value != base.value
            ]
            return dict(
                proposal_id=proposal_id,
                base_active_version=proposal.base_active_version,
                current_active_version=current.active_version,
                stale=proposal.base_active_version != current.active_version,
                label="Read-only synthetic policy impact; no real case or provider mutation",
                changes=changes,
                before=dict(classifier=before, runtime=runtime(current)),
                after=dict(classifier=after, runtime=runtime(proposed)),
            )

    def _expected(self, version: int) -> PolicyCatalogue:
        current = self.catalogue()
        if current.version != version:
            raise AdministrationConflictError
        return current

    @staticmethod
    def _proposal(
        current: PolicyCatalogue, proposal_id: str, version: int, status: str
    ) -> PolicyProposal:
        proposal = next((p for p in current.proposals if p.proposal_id == proposal_id), None)
        if proposal is None:
            raise PolicyNotFoundError
        if (
            proposal.version != version
            or proposal.status != status
            or proposal.base_active_version != current.active_version
        ):
            raise AdministrationConflictError
        return proposal

    def _persist(
        self,
        current: PolicyCatalogue,
        actor: AuthenticatedActor,
        action: str,
        target: str,
        **changes: object,
    ) -> PolicyCatalogue:
        if len(current.audit_events) >= MAX_POLICY_AUDIT_EVENTS:
            raise AdministrationAuditCapacityError
        now = self._clock()
        version = current.version + 1
        event = PolicyAuditEvent.model_validate(
            dict(
                event_id=new_event_id(),
                action=action,
                actor_user_id=actor.profile.user_id,
                target_id=target,
                timestamp=now,
                resulting_version=version,
                metadata={"active_version": changes.get("active_version", current.active_version)},
            )
        )
        candidate = PolicyCatalogue.model_validate(
            current.model_copy(
                update={
                    **changes,
                    "catalogue_schema_version": 2,
                    "version": version,
                    "updated_at": now,
                    "updated_by": actor.profile.user_id,
                    "audit_events": (*current.audit_events, event),
                }
            ).model_dump()
        )
        return self._repository.update(candidate, expected_version=current.version)

    def _validate_runtime(self, catalogue: PolicyCatalogue) -> None:
        try:
            self._intelligence_snapshot(catalogue)
            self._goldtier_target_snapshot(catalogue)
            self._registry_snapshot(catalogue)
            self._classifier_snapshot(catalogue)
        except (ValidationError, ValueError, TypeError):
            raise PolicyValidationError from None

    @classmethod
    def _registry_snapshot(cls, catalogue: PolicyCatalogue) -> RegistryPolicySnapshot:
        return RegistryPolicySnapshot(
            freshness_seconds=cls._runtime_integer(catalogue, "REGISTRY_FRESHNESS_DAYS") * 86400,
            negative_seconds=cls._runtime_integer(catalogue, "REGISTRY_NOT_FOUND_TTL_SECONDS"),
        )

    @classmethod
    def _classifier_snapshot(cls, catalogue: PolicyCatalogue) -> EvidenceClassifierPolicy:
        return EvidenceClassifierPolicy(
            kind_weight=cls._runtime_decimal(catalogue, "EVIDENCE_KIND_WEIGHT"),
            binding_weight=cls._runtime_decimal(catalogue, "EVIDENCE_BINDING_WEIGHT"),
            confidence_weight=cls._runtime_decimal(catalogue, "EVIDENCE_CONFIDENCE_WEIGHT"),
            threshold=cls._runtime_decimal(catalogue, "EVIDENCE_CLASSIFICATION_THRESHOLD"),
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
            snapshot_label=f"GLOBAL_POLICY_CATALOGUE_V{catalogue.active_version}",
            catalogue_version=catalogue.active_version,
            policy_identity=catalogue.active_identity,
            registry=self._registry_snapshot(catalogue),
            evidence_classifier=self._classifier_snapshot(catalogue),
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
                ubo_advisory_likely_threshold=decimal_values[UBO_ADVISORY_LIKELY_THRESHOLD_ID],
                ubo_advisory_unlikely_threshold=decimal_values[UBO_ADVISORY_UNLIKELY_THRESHOLD_ID],
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
        *,
        default_value: str = "TBD_SPONSOR",
        default_authority: PolicyAuthority = PolicyAuthority.TBD_SPONSOR,
        classifications: tuple[PolicyClassification, ...] = (pending,),
        allowed_values: tuple[str, ...] = (),
    ) -> PolicyRule:
        typed = StringPolicyValue(value=default_value)
        return PolicyRule(
            policy_id=policy_id,
            category="GoldTier target preparation",
            name=name,
            description=description,
            value=typed,
            value_type=PolicyValueType.STRING,
            default_value=typed,
            allowed_values=allowed_values,
            classifications=classifications,
            authority=default_authority,
            default_authority=default_authority,
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

    rules: tuple[PolicyRule, ...] = (
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
            "Sponsor-confirmed default aggregated ownership >=25% threshold (D-062); "
            "legal/control and production policy remain unresolved.",
            "25.000000",
            "0",
            "100",
            classifications=(project, derived),
        ),
        fixed(
            "OWNERSHIP_UBO_COMPARATOR",
            "Ownership",
            "UBO comparator",
            "Sponsor-confirmed inclusive comparator (D-062) for the bounded POC threshold.",
            StringPolicyValue(value="GREATER_THAN_OR_EQUAL_TO"),
            (derived,),
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
            "Case-selected XPI Shell customer type from the corrected OpenAPI vocabulary.",
            allowed_values=("TBD_SPONSOR", *GOLDTIER_KYC_CUSTOMER_TYPE_VALUES),
        ),
        target_rule(
            GOLDTIER_CLIENT_SEGMENT_ID,
            "GoldTier client segment",
            "Case-selected XPI Shell client segment from the corrected OpenAPI vocabulary.",
            allowed_values=("TBD_SPONSOR", *GOLDTIER_CLIENT_SEGMENT_VALUES),
        ),
        target_rule(
            GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
            "GoldTier customer external system",
            (
                "Sponsor-documented sandbox source-system label; independent of "
                "SG registration identity."
            ),
            default_value=GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,
            default_authority=PolicyAuthority.SPONSOR_DOCUMENTED,
            classifications=(project, pending),
            allowed_values=(GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE,),
        ),
        target_rule(
            GOLDTIER_REGISTRATION_TYPE_ID,
            "GoldTier registration type",
            "User-authorized Singapore mapping to the sponsor-documented ACRA registration type.",
            default_value=GOLDTIER_REGISTRATION_TYPE_POC_VALUE,
            default_authority=PolicyAuthority.USER_AUTHORIZED_POC,
            classifications=(project, pending),
            allowed_values=(GOLDTIER_REGISTRATION_TYPE_POC_VALUE,),
        ),
        target_rule(
            GOLDTIER_POLICY_ID,
            "GoldTier policy",
            "Sponsor-documented Singapore XPI customer policy.",
            default_value=GOLDTIER_POLICY_POC_VALUE,
            default_authority=PolicyAuthority.SPONSOR_DOCUMENTED,
            classifications=(project, pending),
            allowed_values=(GOLDTIER_POLICY_POC_VALUE,),
        ),
        target_rule(
            GOLDTIER_BOOKING_ENTITY_ID,
            "GoldTier booking entity",
            "User-authorized bounded POC selection from the sponsor booking-entity vocabulary.",
            default_value=GOLDTIER_BOOKING_ENTITY_POC_VALUE,
            default_authority=PolicyAuthority.USER_AUTHORIZED_POC,
            classifications=(project, pending),
            allowed_values=(GOLDTIER_BOOKING_ENTITY_POC_VALUE,),
        ),
        target_rule(
            GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
            "GoldTier account entity type",
            "Optional XPI sandbox field; an unconfirmed placeholder is emitted as empty.",
            default_value=GOLDTIER_ACCOUNT_ENTITY_TYPE_POC_VALUE,
            default_authority=PolicyAuthority.PROJECT_DEFINED_PROVISIONAL,
            classifications=(project, pending),
        ),
        target_rule(
            GOLDTIER_PRODUCT_TYPE_ID,
            "GoldTier product type",
            "Optional XPI sandbox field; the unconfirmed default is emitted as empty.",
        ),
    )
    rules = (
        *rules,
        integer_rule(
            "REGISTRY_FRESHNESS_DAYS",
            "Registry & External Data",
            "Registry evidence freshness",
            "Approved elapsed-day reuse window for normalized Mock registry evidence.",
            90,
            1,
            365,
        ),
        integer_rule(
            "REGISTRY_NOT_FOUND_TTL_SECONDS",
            "Registry & External Data",
            "Definitive not-found cache TTL",
            "Only definitive missing entities use this cache; uncertain failures do not.",
            600,
            1,
            3600,
        ),
        decimal_rule(
            "EVIDENCE_KIND_WEIGHT",
            "Ownership Evidence Classification",
            "Recognized evidence contribution",
            "Deterministic semantic score contribution for recognized evidence kinds.",
            "0.50",
            "0",
            "1",
        ),
        decimal_rule(
            "EVIDENCE_BINDING_WEIGHT",
            "Ownership Evidence Classification",
            "Identity binding contribution",
            "Deterministic semantic score contribution for an explicit entity binding.",
            "0.25",
            "0",
            "1",
        ),
        decimal_rule(
            "EVIDENCE_CONFIDENCE_WEIGHT",
            "Ownership Evidence Classification",
            "Source confidence contribution",
            "Deterministic semantic score contribution from bounded source confidence.",
            "0.25",
            "0",
            "1",
        ),
        decimal_rule(
            "EVIDENCE_CLASSIFICATION_THRESHOLD",
            "Ownership Evidence Classification",
            "Semantic classification threshold",
            "Inclusive deterministic semantic score threshold; never a legal ownership decision.",
            "0.50",
            "0",
            "1",
        ),
    )
    return PolicyCatalogue(
        version=1,
        active_effective_at=now,
        rules=rules,
        created_at=now,
        updated_at=now,
        updated_by="system-bootstrap",
    )
