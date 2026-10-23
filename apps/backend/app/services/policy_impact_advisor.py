"""Pure prospective projection beneath PolicyManagementService; no durable state."""

import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from typing import cast

from app.domain.models import RegistryFreshnessPolicy
from app.domain.policy import (
    IDP_POLICY_ID,
    UBO_POLICY_ID,
    DecimalPolicyValue,
    EvidenceClassifierPolicy,
    IntegerPolicyValue,
    PolicyCatalogue,
    RegistryPolicySnapshot,
)
from app.domain.policy_impact import (
    ClassifierBenchmarkImpact,
    CountDelta,
    ImpactChange,
    ImpactScenario,
    Materiality,
    PolicyAdvisorImpact,
    PolicyImpactResponse,
    PolicyImpactSide,
    PolicyRuntimeImpact,
    ScenarioOutcome,
    Stage,
    UnknownImpact,
)
from app.services.document_processing import document_semantic_assessment
from app.services.ownership_analysis import (
    aggregate_ownership_paths,
    build_ownership_candidates,
    build_ownership_graph,
    calculate_ownership_paths,
    validate_ownership_graph,
)
from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger
from app.services.policy_impact_fixtures import (
    DOCUMENT_CONFIDENCES,
    FIXTURE_EPSILON,
    FIXTURE_NOW,
    NEGATIVE_AGES_SECONDS,
    OWNERSHIP_PERCENTAGES,
    REGISTRY_AGES_DAYS,
    document_fixture,
    ownership_fixture,
    synthetic_entity,
)
from app.services.registry_acquisition import (
    registry_cache_window_is_fresh,
    registry_negative_cache_is_fresh,
)

MAX_SCENARIOS = 64
MAX_OUTPUT_BYTES = 262144
CLASSIFIER_IDS = (
    "EVIDENCE_KIND_WEIGHT",
    "EVIDENCE_BINDING_WEIGHT",
    "EVIDENCE_CONFIDENCE_WEIGHT",
    "EVIDENCE_CLASSIFICATION_THRESHOLD",
)
UNKNOWN_CONCEPTS = (
    "Ready-for-Approval",
    "Production ACRA load",
    "Legal UBO determination",
    "Sanctions/PEP",
    "Production case volume",
    "GoldTier approval",
    "Production retry behavior",
)


@dataclass(frozen=True)
class ImpactPolicy:
    catalogue: PolicyCatalogue
    registry: RegistryPolicySnapshot
    classifier: EvidenceClassifierPolicy
    document: Decimal
    ownership: Decimal
    version: int


def _document(confidence: Decimal, variant: str, policy: ImpactPolicy) -> ScenarioOutcome:
    assessment = document_semantic_assessment(
        record=document_fixture(confidence, variant),
        current_entity=synthetic_entity(),
        confidence_threshold=float(policy.document),
    )
    return ScenarioOutcome(
        label="AUTO_CONFIRMED" if assessment.eligible else "REVIEW_REQUIRED",
        value=str(confidence),
        threshold=str(policy.document),
        reason_codes=tuple(b.value for b in assessment.blockers) or ("DOCUMENT_SEMANTIC_MATCH",),
        automatic=assessment.eligible,
        review_required=not assessment.eligible,
    )


def _ownership(kind: str, percent: Decimal, party_id: str, policy: ImpactPolicy) -> ScenarioOutcome:
    if policy.ownership <= 0:
        return ScenarioOutcome(
            label="NOT_ASSESSED",
            threshold=str(policy.ownership),
            reason_codes=("OWNERSHIP_ENGINE_THRESHOLD_UNSUPPORTED",),
        )
    graph = build_ownership_graph(ownership_fixture(kind, percent))
    validate_ownership_graph(graph)
    calculation = calculate_ownership_paths(
        graph,
        max_depth=4,
        max_paths_per_candidate=16,
        max_total_paths=32,
    )
    candidates = build_ownership_candidates(
        graph,
        calculation,
        aggregate_ownership_paths(calculation),
        threshold_percent=policy.ownership,
    )
    candidate = next(c for c in candidates if c.party.party_id == party_id)
    return ScenarioOutcome(
        label=candidate.classification.value,
        value=str(candidate.aggregated_ownership_percent),
        threshold=str(candidate.threshold_percent),
        reason_codes=tuple(i.code.value for i in calculation.issues)
        or (candidate.threshold_result.value,),
        provisional_candidate=candidate.classification.value == "PROVISIONAL_UBO_CANDIDATE",
        review_required=candidate.classification.value == "REVIEW_REQUIRED",
    )


def _window(age: int, negative: bool, policy: ImpactPolicy) -> ScenarioOutcome:
    anchor = FIXTURE_NOW - timedelta(seconds=age)
    if negative:
        fresh = registry_negative_cache_is_fresh(
            anchor, FIXTURE_NOW, policy.registry.negative_seconds
        )
        label = "NEGATIVE_CACHE_HIT" if fresh else "NEGATIVE_CACHE_EXPIRED"
        threshold = policy.registry.negative_seconds
    else:
        freshness = RegistryFreshnessPolicy(
            policy_id="MOCK_ACRA_APPROVED_POLICY",
            version=policy.version,
            duration_seconds=policy.registry.freshness_seconds,
        )
        fresh = registry_cache_window_is_fresh(freshness.expires_at(anchor), FIXTURE_NOW)
        label = "REUSE_FRESH" if fresh else "REFRESH_REQUIRED"
        threshold = policy.registry.freshness_seconds
    return ScenarioOutcome(
        label=label,
        value=str(age),
        threshold=str(threshold),
        reason_codes=("EVALUATION_NOW_LT_EXPIRES_AT" if fresh else "CACHE_WINDOW_EXPIRED",),
        cache_reuse=fresh,
    )


def _count(rows: list[ImpactScenario], flag: str) -> CountDelta:
    def side(which: str) -> int | None:
        values = [getattr(getattr(row, which), flag) for row in rows]
        return None if any(value is None for value in values) else sum(bool(v) for v in values)

    before, after = side("before"), side("after")
    return CountDelta(
        before=before,
        after=after,
        delta=None if before is None or after is None else after - before,
    )


def _reuse_direction(before: int, after: int) -> str:
    return (
        "MORE_RESTRICTIVE_REUSE"
        if after < before
        else "LESS_RESTRICTIVE_REUSE"
        if after > before
        else "NO_OBSERVED_CHANGE"
    )


def _direction(delta: int | None, more: str, less: str) -> str:
    return (
        "NOT_ASSESSED"
        if delta is None
        else more
        if delta > 0
        else less
        if delta < 0
        else "NO_OBSERVED_CHANGE"
    )


def _severity(rows: list[ImpactScenario]) -> tuple[Materiality, tuple[str, ...]]:
    if any(r.before.label == "NOT_ASSESSED" or r.after.label == "NOT_ASSESSED" for r in rows):
        return "NOT_ASSESSED", ("IMPACT_NOT_ASSESSED", "OWNERSHIP_ENGINE_THRESHOLD_UNSUPPORTED")
    transitions = [r for r in rows if r.before.label != r.after.label]
    if transitions:
        stage = transitions[0].stage
        if stage == "DOCUMENT":
            return "HIGH", ("DOCUMENT_FIXTURE_CROSSES_AUTO_CONFIRM_THRESHOLD",)
        if stage == "OWNERSHIP":
            return "HIGH", ("OWNERSHIP_FIXTURE_CROSSES_UBO_THRESHOLD",)
        if stage == "CLASSIFIER":
            return "MODERATE", ("CLASSIFIER_LABEL_CHANGED",)
        if any(r.fixture_id.startswith("REGISTRY_") for r in transitions):
            reason = (
                "REGISTRY_FIXTURE_BECOMES_STALE"
                if any(r.before.cache_reuse and not r.after.cache_reuse for r in transitions)
                else "REGISTRY_FIXTURE_BECOMES_REUSABLE"
            )
            return "HIGH", (reason,)
        return "MODERATE", (
            "NEGATIVE_CACHE_WINDOW_CONTRACTS"
            if any(r.before.cache_reuse and not r.after.cache_reuse for r in transitions)
            else "NEGATIVE_CACHE_WINDOW_EXPANDS",
        )
    if any(r.before.score != r.after.score for r in rows):
        return "LOW", ("CLASSIFIER_SCORE_CHANGED_NO_LABEL_CHANGE",)
    return "NO_OBSERVED_CHANGE", ("NO_OBSERVED_FIXTURE_TRANSITION",)


class PolicyImpactAdvisor:
    """Evaluate the same bounded inputs under each policy using existing evaluators."""

    @staticmethod
    def evaluate(
        *,
        before: ImpactPolicy,
        after: ImpactPolicy,
        current: PolicyCatalogue,
        proposal_id: str,
        proposal_version: int,
        stale: bool,
        after_is_activated: bool,
    ) -> PolicyImpactResponse:
        rows: list[ImpactScenario] = []
        inputs: list[dict[str, object]] = []

        def add(
            fixture_id: str,
            stage: Stage,
            effect: str,
            left: ScenarioOutcome,
            right: ScenarioOutcome,
            definition: dict[str, object],
        ) -> None:
            if len(rows) >= MAX_SCENARIOS:
                raise ValueError("policy impact fixture limit")
            rows.append(
                ImpactScenario.model_validate(
                    dict(
                        fixture_id=fixture_id,
                        stage=stage,
                        effect=effect,
                        before=left,
                        after=right,
                    )
                )
            )
            inputs.append(dict(fixture_id=fixture_id, **definition))

        documents = [
            (f"DOCUMENT_CONFIDENCE_{v}", Decimal(v), "MATCH") for v in DOCUMENT_CONFIDENCES
        ]
        for name, policy in (("BASE", before), ("PROPOSED", after)):
            for suffix, delta in (
                ("BELOW", -FIXTURE_EPSILON),
                ("AT", Decimal(0)),
                ("ABOVE", FIXTURE_EPSILON),
            ):
                confidence = policy.document + delta
                if 0 <= confidence <= 1:
                    documents.append((f"DOCUMENT_{name}_{suffix}", confidence, "MATCH"))
        documents.extend(
            (f"DOCUMENT_{variant}", Decimal("0.97"), variant)
            for variant in ("MISSING", "CONFLICT", "TEXT_UNAVAILABLE", "SUPERSEDED")
        )
        for identity, confidence, variant in documents:
            add(
                identity,
                "DOCUMENT",
                "AUTOMATIC_REVIEW",
                _document(confidence, variant, before),
                _document(confidence, variant, after),
                dict(
                    document=document_fixture(confidence, variant).model_dump(mode="json"),
                    entity=synthetic_entity().model_dump(mode="json"),
                ),
            )

        windows = [(f"REGISTRY_AGE_{age}_DAYS", age * 86400, False) for age in REGISTRY_AGES_DAYS]
        windows.extend((f"NEGATIVE_AGE_{age}_SECONDS", age, True) for age in NEGATIVE_AGES_SECONDS)
        for name, policy in (("BASE", before), ("PROPOSED", after)):
            for prefix, duration, negative in (
                ("REGISTRY", policy.registry.freshness_seconds, False),
                ("NEGATIVE", policy.registry.negative_seconds, True),
            ):
                windows.extend(
                    (f"{prefix}_{name}_EXPIRY{suffix}", duration + delta, negative)
                    for suffix, delta in (("_BELOW", -1), ("", 0), ("_ABOVE", 1))
                )
        for identity, age, negative in windows:
            add(
                identity,
                "REGISTRY",
                "CACHE_ONLY",
                _window(age, negative, before),
                _window(age, negative, after),
                dict(age_seconds=age, definitive_not_found=negative),
            )

        ownerships = [
            (f"OWNERSHIP_DIRECT_{v}", "DIRECT", Decimal(v), "person") for v in OWNERSHIP_PERCENTAGES
        ]
        for name, policy in (("BASE", before), ("PROPOSED", after)):
            for suffix, delta in (
                ("BELOW", -FIXTURE_EPSILON),
                ("AT", Decimal(0)),
                ("ABOVE", FIXTURE_EPSILON),
            ):
                percent = policy.ownership + delta
                if 0 < percent <= 100:
                    ownerships.append((f"OWNERSHIP_{name}_{suffix}", "DIRECT", percent, "person"))
        ownerships.extend(
            (
                ("OWNERSHIP_MULTIPATH", "MULTIPATH", Decimal("27"), "person"),
                ("OWNERSHIP_INCOMPLETE", "INCOMPLETE", Decimal("27"), "person"),
                ("OWNERSHIP_DECLARATION_60", "DECLARATION_60_40", Decimal("60"), "person"),
                ("OWNERSHIP_DECLARATION_40", "DECLARATION_60_40", Decimal("40"), "person-b"),
            )
        )
        for identity, kind, percent, party in ownerships:
            add(
                identity,
                "OWNERSHIP",
                "PROVISIONAL_CANDIDATE",
                _ownership(kind, percent, party, before),
                _ownership(kind, percent, party, after),
                dict(source=ownership_fixture(kind, percent).model_dump(mode="json"), party=party),
            )

        tagger = OwnershipEvidenceTagger()
        evidence = tagger.benchmark_evidence()
        tags_before = tagger.tag(
            evidence, case_version=0, policy=before.classifier, policy_version=before.version
        ).tags
        tags_after = tagger.tag(
            evidence, case_version=0, policy=after.classifier, policy_version=after.version
        ).tags
        for i, (left, right) in enumerate(zip(tags_before, tags_after, strict=True)):

            def outcome(tag: object) -> ScenarioOutcome:
                # Validate the existing tag projection rather than recalculate its score.
                from app.domain.ownership_evidence import OwnershipEvidenceTag

                assert isinstance(tag, OwnershipEvidenceTag)
                return ScenarioOutcome(
                    label=tag.tag,
                    score=str(tag.score),
                    threshold=str(tag.threshold),
                    reason_codes=tag.reason_codes,
                )

            add(
                f"CLASSIFIER_BENCHMARK_{i:02d}",
                "CLASSIFIER",
                "ADVISORY",
                outcome(left),
                outcome(right),
                evidence[i].model_dump(mode="json"),
            )
        benchmark_before = tagger.benchmark(before.classifier, policy_version=before.version)
        benchmark_after = tagger.benchmark(after.classifier, policy_version=after.version)
        changes: list[ImpactChange] = []
        unknowns = [
            UnknownImpact(
                concept=c, limitation="No authoritative synthetic evaluator in this comparison."
            )
            for c in UNKNOWN_CONCEPTS
        ]
        for rule in after.catalogue.rules:
            base = before.catalogue.rule(rule.policy_id)
            active = current.rule(rule.policy_id)
            if base is None or active is None:
                raise ValueError("policy impact rule identity")
            if base.value == rule.value:
                continue
            identity = rule.policy_id
            if identity == IDP_POLICY_ID:
                selected = [r for r in rows if r.stage == "DOCUMENT"]
            elif identity == UBO_POLICY_ID:
                selected = [r for r in rows if r.stage == "OWNERSHIP"]
            elif identity in CLASSIFIER_IDS:
                selected = [r for r in rows if r.stage == "CLASSIFIER"]
            elif identity in ("REGISTRY_FRESHNESS_DAYS", "REGISTRY_NOT_FOUND_TTL_SECONDS"):
                prefix = "REGISTRY_" if identity == "REGISTRY_FRESHNESS_DAYS" else "NEGATIVE_"
                selected = [r for r in rows if r.fixture_id.startswith(prefix)]
            else:
                selected = []
            materiality, reasons = (
                _severity(selected) if selected else ("NOT_ASSESSED", ("IMPACT_NOT_ASSESSED",))
            )
            stage: Stage = (
                selected[0].stage
                if selected
                else "READINESS"
                if identity.startswith("MOCK_RISK")
                else "OWNERSHIP"
                if identity.startswith("OWNERSHIP_")
                else "INTELLIGENCE"
            )
            coupled = (
                CLASSIFIER_IDS
                if identity in CLASSIFIER_IDS
                else tuple(
                    r.policy_id
                    for r in after.catalogue.rules
                    if (
                        identity.startswith("ENTITY_RESOLUTION_")
                        and r.policy_id.startswith("ENTITY_RESOLUTION_")
                    )
                    or (
                        identity.startswith("UBO_ADVISORY_")
                        and r.policy_id.startswith("UBO_ADVISORY_")
                    )
                    or (identity.startswith("MOCK_RISK_") and r.policy_id.startswith("MOCK_RISK_"))
                )
            )
            direction = "VALUE_CHANGE"
            if isinstance(base.value, (DecimalPolicyValue, IntegerPolicyValue)) and isinstance(
                rule.value, (DecimalPolicyValue, IntegerPolicyValue)
            ):
                base_number = Decimal(str(base.value.value))
                proposed_number = Decimal(str(rule.value.value))
                direction = (
                    "INCREASE"
                    if proposed_number > base_number
                    else "DECREASE"
                    if proposed_number < base_number
                    else "VALUE_CHANGE"
                )
            limitations = [
                "Controlled synthetic inputs only; no production or compliance forecast."
            ]
            if materiality == "NOT_ASSESSED":
                limitations.append(
                    "No supported authoritative evaluation for this changed parameter."
                )
                unknowns.append(UnknownImpact(concept=rule.name, limitation=limitations[-1]))
            changes.append(
                ImpactChange.model_validate(
                    dict(
                        policy_id=identity,
                        name=rule.name,
                        current=active.value,
                        base=base.value,
                        default=base.default_value,
                        proposed=rule.value,
                        direction=direction,
                        stages=(stage,),
                        assessment="NOT_ASSESSED" if materiality == "NOT_ASSESSED" else "ASSESSED",
                        materiality=materiality,
                        effect=selected[0].effect
                        if selected and materiality != "NOT_ASSESSED"
                        else "NOT_ASSESSED",
                        scenario_ids=tuple(r.fixture_id for r in selected),
                        coupled_policy_ids=tuple(i for i in coupled if i != identity),
                        reason_codes=reasons,
                        limitations=tuple(limitations),
                    )
                )
            )
        groups = {
            stage: [r for r in rows if r.stage == stage] for stage in ("DOCUMENT", "OWNERSHIP")
        }
        counts = {
            "automatic_document_confirmations": _count(groups["DOCUMENT"], "automatic"),
            "document_review_required": _count(groups["DOCUMENT"], "review_required"),
            "provisional_ubo_candidates": _count(groups["OWNERSHIP"], "provisional_candidate"),
            "ownership_review_required": _count(groups["OWNERSHIP"], "review_required"),
            "registry_cache_reuse": _count(
                [r for r in rows if r.fixture_id.startswith("REGISTRY_")], "cache_reuse"
            ),
            "negative_cache_reuse": _count(
                [r for r in rows if r.fixture_id.startswith("NEGATIVE_")], "cache_reuse"
            ),
        }
        metric_delta: dict[str, float] = {}
        for group in ("macro", "micro"):
            left_metrics = cast(dict[str, float], benchmark_before[group])
            right_metrics = cast(dict[str, float], benchmark_after[group])
            for metric in ("precision", "recall", "f1"):
                metric_delta[f"{group}_{metric}"] = right_metrics[metric] - left_metrics[metric]
        rank: dict[Materiality, int] = {
            "NO_OBSERVED_CHANGE": 0,
            "LOW": 1,
            "MODERATE": 2,
            "HIGH": 3,
            "NOT_ASSESSED": -1,
        }
        known = [c.materiality for c in changes if c.materiality != "NOT_ASSESSED"]
        materiality = (
            max(known, key=rank.__getitem__)
            if known
            else ("NOT_ASSESSED" if changes else "NO_OBSERVED_CHANGE")
        )
        reasons = tuple(sorted({reason for change in changes for reason in change.reason_codes}))
        if stale:
            reasons += ("STALE_PROPOSAL_BASE",)
        fixture_hash = sha256(
            json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        def runtime(policy: ImpactPolicy, which: str) -> PolicyRuntimeImpact:
            by_id = {r.fixture_id: getattr(r, which) for r in rows}
            return PolicyRuntimeImpact(
                registry_freshness_seconds=policy.registry.freshness_seconds,
                not_found_ttl_seconds=policy.registry.negative_seconds,
                document_auto_confirm=tuple(
                    bool(by_id[f"DOCUMENT_CONFIDENCE_{v}"].automatic)
                    for v in ("0.84", "0.85", "0.90")
                ),
                ownership_numeric_candidates=tuple(
                    by_id[f"OWNERSHIP_DIRECT_{v}"].provisional_candidate
                    for v in ("24.999999", "25", "30")
                ),
            )

        identity = sha256(
            json.dumps(
                dict(
                    base_version=before.version,
                    fixture_hash=fixture_hash,
                    base=[r.value.model_dump(mode="json") for r in before.catalogue.rules],
                    proposed=[r.value.model_dump(mode="json") for r in after.catalogue.rules],
                ),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        advisor = PolicyAdvisorImpact.model_validate(
            dict(
                fixture_set_hash=fixture_hash,
                materiality=materiality,
                reason_codes=reasons,
                scenarios=tuple(rows),
                automation_delta=counts,
                automation_direction=_direction(
                    counts["automatic_document_confirmations"].delta,
                    "MORE_AUTOMATIC",
                    "LESS_AUTOMATIC",
                ),
                review_direction=_direction(
                    counts["document_review_required"].delta, "MORE_REVIEW", "LESS_REVIEW"
                ),
                registry_reuse_direction=_reuse_direction(
                    before.registry.freshness_seconds, after.registry.freshness_seconds
                ),
                negative_reuse_direction=_reuse_direction(
                    before.registry.negative_seconds, after.registry.negative_seconds
                ),
                classifier_metric_delta=metric_delta,
                unknown_impacts=tuple(unknowns),
                limits=dict(
                    changed_rules=64,
                    synthetic_fixtures=64,
                    classifier_cases=14,
                    output_bytes=MAX_OUTPUT_BYTES,
                ),
            )
        )
        response = PolicyImpactResponse(
            proposal_id=proposal_id,
            proposal_version=proposal_version,
            catalogue_version=current.version,
            base_active_version=before.version,
            current_active_version=current.active_version,
            stale=stale,
            comparison_basis="RETAINED_PROPOSAL_BASE" if stale else "ACTIVE_PROPOSAL_BASE",
            comparison_identity=identity,
            label="Read-only synthetic policy impact; no real case or provider mutation",
            changes=tuple(changes),
            before=PolicyImpactSide(
                policy_version_context="RETAINED_BASE" if stale else "ACTIVE_BASE",
                classifier=ClassifierBenchmarkImpact.model_validate(benchmark_before),
                runtime=runtime(before, "before"),
            ),
            after=PolicyImpactSide(
                policy_version_context="ACTIVATED_PROPOSAL"
                if after_is_activated
                else "PROSPECTIVE_UNRESERVED",
                classifier=ClassifierBenchmarkImpact.model_validate(benchmark_after),
                runtime=runtime(after, "after"),
            ),
            advisor=advisor,
        )
        if len(response.model_dump_json().encode()) > MAX_OUTPUT_BYTES:
            raise ValueError("policy impact output limit")
        return response
