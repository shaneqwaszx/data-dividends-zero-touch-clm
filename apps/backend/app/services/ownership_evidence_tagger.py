"""One semantic tagger baseline. No arithmetic, legal findings or external AI."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Protocol, TypedDict

from app.domain.ownership_evidence import (
    OwnershipEvidence,
    OwnershipEvidenceTag,
    OwnershipTaggingResult,
)
from app.domain.policy import EvidenceClassifierPolicy


class _ClassMetrics(TypedDict):
    label: str
    precision: float
    recall: float
    f1: float
    support: int


class ExperimentalOwnershipModel(Protocol):
    """Unwired POC seam; composition requires separately approved runtime/evaluation."""

    def classify(self, evidence: tuple[OwnershipEvidence, ...]) -> OwnershipTaggingResult: ...


class OwnershipEvidenceTagger:
    def tag(
        self,
        evidence: tuple[OwnershipEvidence, ...],
        *,
        case_version: int,
        policy: EvidenceClassifierPolicy | None = None,
        policy_version: int | None = None,
    ) -> OwnershipTaggingResult:
        if policy is not None and (policy_version is None or policy_version < 1):
            raise ValueError("classifier policy requires a frozen version")
        tags: list[OwnershipEvidenceTag] = []
        for untrusted in evidence:
            item = OwnershipEvidence.model_validate(untrusted.model_dump())
            tag: str = "UNKNOWN"
            reason = "SEMANTIC_EVIDENCE_UNKNOWN"
            confidence = Decimal("0")
            if item.entity_identifier is None:
                reason = "EVIDENCE_ENTITY_BINDING_UNKNOWN"
            elif item.kind == "ROLE":
                role = item.raw_value.strip().upper()
                if role in {"OWNER", "PARTNER", "MEMBER"}:
                    tag, reason, confidence = f"{role}_ROLE", f"SOURCE_ROLE_{role}", Decimal("1")
                elif role == "SHAREHOLDER":
                    tag, reason, confidence = (
                        "DIRECT_ECONOMIC_INTEREST",
                        "SOURCE_ROLE_SHAREHOLDER",
                        Decimal("1"),
                    )
                else:
                    reason = "ROLE_DOES_NOT_ESTABLISH_OWNERSHIP"
            elif item.kind == "SHARE_UNITS":
                tag, reason, confidence = "SHARE_UNIT_EVIDENCE", "SHARE_UNITS_PRESENT", Decimal("1")
            elif item.kind == "CAPITAL_DENOMINATOR":
                tag, reason, confidence = (
                    "CAPITAL_DENOMINATOR_EVIDENCE",
                    "CAPITAL_UNITS_PRESENT",
                    Decimal("1"),
                )
            elif item.kind in {"DIRECT_PERCENTAGE", "ECONOMIC_INTEREST", "MEMBERSHIP_INTEREST"}:
                tag, reason, confidence = (
                    "DIRECT_ECONOMIC_INTEREST",
                    "SOURCE_INTEREST_PRESENT",
                    Decimal("1"),
                )
            elif item.kind == "CONTROL":
                tag, reason, confidence = "CONTROL_EVIDENCE", "SOURCE_CONTROL_PRESENT", Decimal("1")
            elif item.kind == "CONFLICT":
                tag, reason, confidence = (
                    "CONFLICTING_EVIDENCE",
                    "SOURCE_CONFLICT_PRESENT",
                    Decimal("1"),
                )
            parameters: dict[str, object] = {}
            if policy is not None:
                recognized = tag != "UNKNOWN"
                score = (
                    policy.kind_weight * Decimal(int(recognized))
                    + policy.binding_weight * Decimal(int(item.entity_identifier is not None))
                    + policy.confidence_weight * item.confidence
                )
                reasons = [reason]
                if recognized and score < policy.threshold:
                    tag = "INSUFFICIENT_EVIDENCE"
                    reasons.append("SEMANTIC_SCORE_BELOW_THRESHOLD")
                parameters = dict(
                    score=score,
                    threshold=policy.threshold,
                    policy_version=policy_version,
                    reason_codes=tuple(reasons),
                    rule_version="ownership-semantic-rules-v2",
                )
            tags.append(
                OwnershipEvidenceTag.model_validate(
                    dict(
                        **parameters,
                        tag=tag,
                        evidence_ids=(item.evidence_id,),
                        reason_code=reason,
                        confidence=min(confidence, item.confidence),
                        provider=item.provider,
                        environment=item.environment,
                        case_version=case_version,
                        evidence_version=item.evidence_version,
                    )
                )
            )
        return OwnershipTaggingResult(tags=tuple(tags))

    @staticmethod
    def benchmark_definitions() -> tuple[tuple[str, str, str, str, bool], ...]:
        return (
            ("ROLE", "OWNER", "OWNER_ROLE", "1", True),
            ("ROLE", "PARTNER", "PARTNER_ROLE", "1", True),
            ("ROLE", "MEMBER", "MEMBER_ROLE", "1", True),
            ("ROLE", "SHAREHOLDER", "DIRECT_ECONOMIC_INTEREST", "1", True),
            ("ROLE", "DIRECTOR", "UNKNOWN", "1", True),
            ("SHARE_UNITS", "10", "SHARE_UNIT_EVIDENCE", "1", True),
            ("CAPITAL_DENOMINATOR", "100", "CAPITAL_DENOMINATOR_EVIDENCE", "1", True),
            ("DIRECT_PERCENTAGE", "25", "DIRECT_ECONOMIC_INTEREST", "1", True),
            ("CONTROL", "SOURCE_CONTROL", "CONTROL_EVIDENCE", "1", True),
            ("CONFLICT", "SOURCE_CONFLICT", "CONFLICTING_EVIDENCE", "1", True),
            ("UNKNOWN", "UNKNOWN", "UNKNOWN", "1", True),
            ("ROLE", "OWNER", "UNKNOWN", "1", False),
            ("SHARE_UNITS", "10", "SHARE_UNIT_EVIDENCE", "0.20", True),
            ("ROLE", "PARTNER", "PARTNER_ROLE", "0.40", True),
        )

    def benchmark_evidence(self) -> tuple[OwnershipEvidence, ...]:
        definitions = self.benchmark_definitions()
        return tuple(
            OwnershipEvidence.model_validate(
                dict(
                    evidence_id=f"benchmark-{i}",
                    entity_identifier="202400001A" if bound else None,
                    party_id=f"synthetic-party-{i}",
                    kind=kind,
                    raw_value=raw,
                    source_operation="SYNTHETIC_BENCHMARK",
                    provider="BENCHMARK",
                    environment="LOCAL",
                    retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                    confidence=Decimal(confidence),
                    evidence_version=1,
                )
            )
            for i, (kind, raw, _, confidence, bound) in enumerate(definitions)
        )

    def benchmark(
        self, policy: EvidenceClassifierPolicy, *, policy_version: int
    ) -> dict[str, object]:
        """Reproducible synthetic semantic benchmark; not a trained-model evaluation."""
        definitions = self.benchmark_definitions()
        evidence = self.benchmark_evidence()
        expected = tuple(row[2] for row in definitions)
        predicted = tuple(
            t.tag
            for t in self.tag(
                evidence, case_version=0, policy=policy, policy_version=policy_version
            ).tags
        )
        labels = sorted(set(expected) | set(predicted))
        confusion = {
            actual: {
                guess: sum(
                    a == actual and b == guess for a, b in zip(expected, predicted, strict=True)
                )
                for guess in labels
            }
            for actual in labels
        }
        classes: list[_ClassMetrics] = []
        for label in labels:
            tp = confusion[label][label]
            support = sum(confusion[label].values())
            predicted_count = sum(confusion[a][label] for a in labels)
            precision = tp / predicted_count if predicted_count else 0.0
            recall = tp / support if support else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            classes.append(
                _ClassMetrics(
                    label=label, precision=precision, recall=recall, f1=f1, support=support
                )
            )
        correct = sum(a == b for a, b in zip(expected, predicted, strict=True))
        count = len(expected)
        identity = sha256(
            json.dumps(
                [item.model_dump(mode="json") for item in evidence],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return dict(
            label="Parameterized deterministic evidence classifier",
            benchmark_id="SYNTHETIC_SEMANTIC_V1",
            benchmark_hash=identity,
            rule_version="ownership-semantic-rules-v2",
            policy_version=policy_version,
            scope=(
                "14 labelled synthetic semantic examples; no trained-model or legal accuracy claim"
            ),
            classes=classes,
            confusion_matrix=confusion,
            support=count,
            exact_accuracy=correct / count,
            macro=dict(
                precision=sum(row["precision"] for row in classes) / len(classes),
                recall=sum(row["recall"] for row in classes) / len(classes),
                f1=sum(row["f1"] for row in classes) / len(classes),
            ),
            micro=dict(precision=correct / count, recall=correct / count, f1=correct / count),
            predictions=list(predicted),
        )
