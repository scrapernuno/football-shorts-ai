from __future__ import annotations

from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource
from knowledge.policy import evaluate_knowledge_policy


def _source(
    source_id: str,
    provider: str,
    reliability: str,
) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        provider=provider,
        title=f"Evidence {source_id}",
        source_type="official_statement" if reliability == "official" else "article",
        reliability=reliability,
    )


def test_policy_scores_high_confidence_from_independent_strong_sources() -> None:
    package = ExternalKnowledgePackage(
        topic="transfer topic",
        sources=(
            _source("official", "club", "official"),
            _source("primary", "league", "primary"),
        ),
        facts=(
            KnowledgeFact(
                fact_id="fact_transfer",
                claim="The player joined the club",
                source_ids=("official", "primary"),
                verification_status="supported",
            ),
        ),
        provider_mode="live",
    )

    result = evaluate_knowledge_policy(package)
    assessment = result.assessments[0]

    assert assessment.confidence == "high"
    assert assessment.score == 10
    assert assessment.independent_source_count == 2
    assert assessment.strongest_reliability == "official"
    assert result.conflicts == ()


def test_policy_scores_low_confidence_for_unverified_unsupported_claim() -> None:
    package = ExternalKnowledgePackage(
        topic="rumour topic",
        sources=(_source("rumour", "unknown_blog", "unverified"),),
        facts=(
            KnowledgeFact(
                fact_id="fact_rumour",
                claim="A transfer may happen",
                source_ids=("rumour",),
                verification_status="unsupported",
            ),
        ),
        provider_mode="live",
    )

    assessment = evaluate_knowledge_policy(package).assessments[0]

    assert assessment.confidence == "low"
    assert assessment.score == 1
    assert assessment.independent_source_count == 1


def test_policy_detects_only_explicit_opposing_polarity() -> None:
    package = ExternalKnowledgePackage(
        topic="manager topic",
        sources=(
            _source("source_a", "provider_a", "reputable_secondary"),
            _source("source_b", "provider_b", "reputable_secondary"),
            _source("source_c", "provider_c", "reputable_secondary"),
        ),
        facts=(
            KnowledgeFact(
                fact_id="positive",
                claim="The manager will leave the club",
                source_ids=("source_a",),
                verification_status="supported",
            ),
            KnowledgeFact(
                fact_id="negative",
                claim="The manager will not leave the club",
                source_ids=("source_b",),
                verification_status="supported",
            ),
            KnowledgeFact(
                fact_id="different",
                claim="The manager spoke after training",
                source_ids=("source_c",),
                verification_status="supported",
            ),
        ),
        provider_mode="live",
    )

    result = evaluate_knowledge_policy(package)

    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.conflict_id == "conflict_001"
    assert conflict.fact_ids == ("negative", "positive")
    assert conflict.status == "potential_conflict"


def test_policy_output_is_deterministic_and_serializable() -> None:
    package = ExternalKnowledgePackage(
        topic="fixture topic",
        sources=(_source("fixture", "fixture_provider", "controlled_fixture"),),
        facts=(
            KnowledgeFact(
                fact_id="fixture_fact",
                claim="Fixture claim",
                source_ids=("fixture",),
                verification_status="supported",
            ),
        ),
    )

    first = evaluate_knowledge_policy(package).to_dict()
    second = evaluate_knowledge_policy(package).to_dict()

    assert first == second
    assert first["topic"] == "fixture topic"
    assert first["assessments"][0]["confidence"] == "medium"
