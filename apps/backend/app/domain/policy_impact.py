"""Bounded ephemeral policy-impact projection; never a persisted policy aggregate."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.policy import PolicyValue

Materiality = Literal["NO_OBSERVED_CHANGE", "LOW", "MODERATE", "HIGH", "NOT_ASSESSED"]
Stage = Literal["REGISTRY", "DOCUMENT", "OWNERSHIP", "CLASSIFIER", "INTELLIGENCE", "READINESS"]
Text = Annotated[str, Field(max_length=240)]
Code = Annotated[str, Field(min_length=1, max_length=80)]


class ImpactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScenarioOutcome(ImpactModel):
    label: Code
    value: Annotated[str | None, Field(max_length=64)] = None
    score: Annotated[str | None, Field(max_length=32)] = None
    threshold: Annotated[str | None, Field(max_length=32)] = None
    reason_codes: Annotated[tuple[Code, ...], Field(max_length=16)] = ()
    automatic: bool | None = None
    review_required: bool | None = None
    provisional_candidate: bool | None = None
    cache_reuse: bool | None = None


class ImpactScenario(ImpactModel):
    fixture_id: Code
    stage: Stage
    effect: Literal["AUTOMATIC_REVIEW", "PROVISIONAL_CANDIDATE", "CACHE_ONLY", "ADVISORY"]
    before: ScenarioOutcome
    after: ScenarioOutcome


class ImpactChange(ImpactModel):
    policy_id: Code
    name: Annotated[str, Field(max_length=80)]
    current: PolicyValue
    base: PolicyValue
    default: PolicyValue
    proposed: PolicyValue
    direction: Literal["INCREASE", "DECREASE", "VALUE_CHANGE"]
    stages: Annotated[tuple[Stage, ...], Field(max_length=4)]
    assessment: Literal["ASSESSED", "NOT_ASSESSED"]
    materiality: Materiality
    effect: Literal[
        "AUTOMATIC_REVIEW", "PROVISIONAL_CANDIDATE", "CACHE_ONLY", "ADVISORY", "NOT_ASSESSED"
    ]
    scenario_ids: Annotated[tuple[Code, ...], Field(max_length=64)]
    coupled_policy_ids: Annotated[tuple[Code, ...], Field(max_length=16)] = ()
    reason_codes: Annotated[tuple[Code, ...], Field(max_length=16)]
    limitations: Annotated[tuple[Text, ...], Field(max_length=8)]


class CountDelta(ImpactModel):
    before: Annotated[int | None, Field(ge=0, le=64)]
    after: Annotated[int | None, Field(ge=0, le=64)]
    delta: Annotated[int | None, Field(ge=-64, le=64)]


class UnknownImpact(ImpactModel):
    concept: Text
    status: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
    reason_code: Literal["IMPACT_NOT_ASSESSED"] = "IMPACT_NOT_ASSESSED"
    limitation: Text


class PolicyAdvisorImpact(ImpactModel):
    fixture_set_id: Literal["SYNTHETIC_POLICY_IMPACT_V1"] = "SYNTHETIC_POLICY_IMPACT_V1"
    fixture_set_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    scope: Literal["Synthetic impact fixtures only — not production volume forecasting."] = (
        "Synthetic impact fixtures only — not production volume forecasting."
    )
    classifier_scope: Literal[
        "Deterministic classifier benchmark on synthetic fixtures — "
        "not trained ML model performance."
    ] = (
        "Deterministic classifier benchmark on synthetic fixtures — "
        "not trained ML model performance."
    )
    materiality: Materiality
    reason_codes: Annotated[tuple[Code, ...], Field(max_length=16)]
    scenarios: Annotated[tuple[ImpactScenario, ...], Field(max_length=64)]
    automation_delta: Annotated[dict[Code, CountDelta], Field(max_length=8)]
    automation_direction: Literal[
        "MORE_AUTOMATIC", "LESS_AUTOMATIC", "NO_OBSERVED_CHANGE", "NOT_ASSESSED"
    ]
    review_direction: Literal["MORE_REVIEW", "LESS_REVIEW", "NO_OBSERVED_CHANGE", "NOT_ASSESSED"]
    registry_reuse_direction: Literal[
        "MORE_RESTRICTIVE_REUSE", "LESS_RESTRICTIVE_REUSE", "NO_OBSERVED_CHANGE"
    ]
    negative_reuse_direction: Literal[
        "MORE_RESTRICTIVE_REUSE", "LESS_RESTRICTIVE_REUSE", "NO_OBSERVED_CHANGE"
    ]
    classifier_metric_delta: Annotated[dict[Code, float], Field(max_length=8)]
    unknown_impacts: Annotated[tuple[UnknownImpact, ...], Field(max_length=24)]
    limits: dict[str, int]


class PolicyRuntimeImpact(ImpactModel):
    registry_freshness_seconds: int
    not_found_ttl_seconds: int
    document_auto_confirm: Annotated[tuple[bool, ...], Field(min_length=3, max_length=3)]
    ownership_numeric_candidates: Annotated[
        tuple[bool | None, ...], Field(min_length=3, max_length=3)
    ]


class BenchmarkMetrics(ImpactModel):
    precision: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    recall: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    f1: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class BenchmarkClass(BenchmarkMetrics):
    label: Code
    support: Annotated[int, Field(ge=0, le=14)]


class ClassifierBenchmarkImpact(ImpactModel):
    label: Text
    benchmark_id: Code
    benchmark_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    rule_version: Code
    policy_version: Annotated[int, Field(ge=1)]
    scope: Text
    classes: Annotated[tuple[BenchmarkClass, ...], Field(max_length=16)]
    confusion_matrix: Annotated[
        dict[Code, Annotated[dict[Code, Annotated[int, Field(ge=0, le=14)]], Field(max_length=16)]],
        Field(max_length=16),
    ]
    support: Literal[14]
    exact_accuracy: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    macro: BenchmarkMetrics
    micro: BenchmarkMetrics
    predictions: Annotated[tuple[Code, ...], Field(min_length=14, max_length=14)]


class PolicyImpactSide(ImpactModel):
    policy_version_context: Literal[
        "ACTIVE_BASE", "RETAINED_BASE", "PROSPECTIVE_UNRESERVED", "ACTIVATED_PROPOSAL"
    ]
    classifier: ClassifierBenchmarkImpact
    runtime: PolicyRuntimeImpact


class PolicyImpactResponse(ImpactModel):
    proposal_id: Code
    proposal_version: Annotated[int, Field(ge=1)]
    catalogue_version: Annotated[int, Field(ge=1)]
    base_active_version: Annotated[int, Field(ge=1)]
    current_active_version: Annotated[int, Field(ge=1)]
    stale: bool
    comparison_basis: Literal["ACTIVE_PROPOSAL_BASE", "RETAINED_PROPOSAL_BASE"]
    comparison_identity: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    label: Text
    changes: Annotated[tuple[ImpactChange, ...], Field(max_length=64)]
    before: PolicyImpactSide
    after: PolicyImpactSide
    advisor: PolicyAdvisorImpact
