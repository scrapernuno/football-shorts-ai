from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource
from knowledge.deduplication import canonical_fact_key


ConfidenceLevel = Literal["low", "medium", "high"]
ConflictStatus = Literal["clear", "potential_conflict"]

_NEGATION = re.compile(
    r"\b(?:not|no|never|denies|denied|rejects|rejected|false|without)\b",
    flags=re.IGNORECASE,
)

_RELIABILITY_SCORE = {
    "unverified": 0,
    "controlled_fixture": 1,
    "reputable_secondary": 2,
    "primary": 3,
    "official": 4,
}

_VERIFICATION_SCORE = {
    "unsupported": 0,
    "partially_supported": 1,
    "supported": 2,
}


@dataclass(frozen=True, slots=True)
class FactConfidenceAssessment:
    fact_id: str
    confidence: ConfidenceLevel
    score: int
    independent_source_count: int
    strongest_reliability: str
    verification_status: str

    def __post_init__(self) -> None:
        if not self.fact_id.strip():
            raise ValueError("fact_id must not be empty")
        if self.score < 0:
            raise ValueError("score must be zero or greater")
        if self.independent_source_count < 0:
            raise ValueError("independent_source_count must be zero or greater")

    def to_dict(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "confidence": self.confidence,
            "score": self.score,
            "independent_source_count": self.independent_source_count,
            "strongest_reliability": self.strongest_reliability,
            "verification_status": self.verification_status,
        }


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    conflict_id: str
    fact_ids: tuple[str, str]
    status: ConflictStatus
    reason: str

    def __post_init__(self) -> None:
        if not self.conflict_id.strip():
            raise ValueError("conflict_id must not be empty")
        if len(self.fact_ids) != 2 or self.fact_ids[0] == self.fact_ids[1]:
            raise ValueError("conflict records require two distinct fact_ids")
        if not self.reason.strip():
            raise ValueError("conflict reason must not be empty")

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "fact_ids": list(self.fact_ids),
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class KnowledgePolicyResult:
    topic: str
    assessments: tuple[FactConfidenceAssessment, ...]
    conflicts: tuple[ConflictRecord, ...]

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("topic must not be empty")
        fact_ids = [assessment.fact_id for assessment in self.assessments]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("fact assessments must use unique fact_id values")

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "assessments": [assessment.to_dict() for assessment in self.assessments],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


def evaluate_knowledge_policy(package: ExternalKnowledgePackage) -> KnowledgePolicyResult:
    """Score governed facts and flag only conservative, deterministic conflicts.

    Confidence is derived exclusively from verification status, source reliability and
    the number of independent providers. Conflict detection is intentionally narrow:
    claims must reduce to the same lexical subject after negation terms are removed,
    and exactly one claim must contain an explicit negation marker.
    """

    sources_by_id = {source.source_id: source for source in package.sources}
    assessments = tuple(
        _assess_fact(fact, sources_by_id)
        for fact in package.facts
    )
    conflicts = _detect_conflicts(package.facts)
    return KnowledgePolicyResult(
        topic=package.topic,
        assessments=assessments,
        conflicts=conflicts,
    )


def _assess_fact(
    fact: KnowledgeFact,
    sources_by_id: dict[str, KnowledgeSource],
) -> FactConfidenceAssessment:
    evidence = [sources_by_id[source_id] for source_id in fact.source_ids]
    provider_count = len({source.provider for source in evidence})
    strongest = max(
        (source.reliability for source in evidence),
        key=lambda reliability: _RELIABILITY_SCORE[reliability],
        default="unverified",
    )

    score = (
        _VERIFICATION_SCORE[fact.verification_status] * 2
        + _RELIABILITY_SCORE[strongest]
        + min(provider_count, 3)
    )
    if score >= 8:
        confidence: ConfidenceLevel = "high"
    elif score >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    return FactConfidenceAssessment(
        fact_id=fact.fact_id,
        confidence=confidence,
        score=score,
        independent_source_count=provider_count,
        strongest_reliability=strongest,
        verification_status=fact.verification_status,
    )


def _detect_conflicts(facts: tuple[KnowledgeFact, ...]) -> tuple[ConflictRecord, ...]:
    grouped: dict[str, list[tuple[KnowledgeFact, bool]]] = {}
    for fact in facts:
        has_negation = bool(_NEGATION.search(fact.claim))
        subject = canonical_fact_key(
            KnowledgeFact(
                fact_id=fact.fact_id,
                claim=_NEGATION.sub(" ", fact.claim),
                source_ids=fact.source_ids,
                verification_status=fact.verification_status,
            )
        )
        if subject:
            grouped.setdefault(subject, []).append((fact, has_negation))

    conflicts: list[ConflictRecord] = []
    sequence = 1
    for subject in sorted(grouped):
        entries = grouped[subject]
        positive = [fact for fact, negated in entries if not negated]
        negative = [fact for fact, negated in entries if negated]
        for positive_fact in positive:
            for negative_fact in negative:
                fact_ids = tuple(sorted((positive_fact.fact_id, negative_fact.fact_id)))
                conflicts.append(
                    ConflictRecord(
                        conflict_id=f"conflict_{sequence:03d}",
                        fact_ids=fact_ids,
                        status="potential_conflict",
                        reason="same normalized subject contains opposing explicit polarity",
                    )
                )
                sequence += 1

    return tuple(conflicts)
