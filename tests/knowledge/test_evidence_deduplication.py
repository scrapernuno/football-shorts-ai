from __future__ import annotations

from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource
from knowledge.deduplication import canonical_source_key, deduplicate_package
from knowledge.orchestration import DeterministicKnowledgeOrchestrator, ProviderRegistration


class DuplicateProvider:
    provider_mode = "live"

    def __init__(self, provider_name: str, url: str, claim: str) -> None:
        self.provider_name = provider_name
        self._url = url
        self._claim = claim

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        source = KnowledgeSource(
            source_id="source_001",
            provider=self.provider_name,
            title="Transfer report",
            source_type="rss",
            reliability="reputable_secondary",
            url=self._url,
        )
        fact = KnowledgeFact(
            fact_id="fact_001",
            claim=self._claim,
            source_ids=(source.source_id,),
            verification_status="supported",
        )
        return ExternalKnowledgePackage(
            topic=topic,
            sources=(source,),
            facts=(fact,),
            provider_mode="live",
        )


def test_source_url_tracking_parameters_are_ignored() -> None:
    first = KnowledgeSource(
        source_id="a",
        provider="provider_a",
        title="Report",
        source_type="rss",
        reliability="reputable_secondary",
        url="https://example.com/report/?id=7&utm_source=rss",
    )
    second = KnowledgeSource(
        source_id="b",
        provider="provider_b",
        title="Different title",
        source_type="article",
        reliability="reputable_secondary",
        url="https://EXAMPLE.com/report?id=7&fbclid=tracking",
    )

    assert canonical_source_key(first) == canonical_source_key(second)


def test_duplicate_sources_and_claims_collapse_deterministically() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration(
                "primary",
                DuplicateProvider(
                    "provider_a",
                    "https://example.com/story?utm_source=feed",
                    "Player joins the club!",
                ),
                10,
                role="primary",
            ),
            ProviderRegistration(
                "secondary",
                DuplicateProvider(
                    "provider_b",
                    "https://example.com/story/",
                    "  player joins the club  ",
                ),
                20,
            ),
        )
    )

    result = orchestrator.execute("transfer topic")

    assert len(result.package.sources) == 1
    assert result.package.sources[0].source_id == "primary:source_001"
    assert len(result.package.facts) == 1
    assert result.package.facts[0].fact_id == "primary:fact_001"
    assert result.package.facts[0].source_ids == ("primary:source_001",)
    assert [record.source_count for record in result.executions] == [1, 1]


def test_same_claim_from_distinct_sources_preserves_both_evidence_links() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration(
                "primary",
                DuplicateProvider(
                    "provider_a",
                    "https://example.com/source-a",
                    "The final was postponed",
                ),
                1,
            ),
            ProviderRegistration(
                "secondary",
                DuplicateProvider(
                    "provider_b",
                    "https://example.org/source-b",
                    "the final was postponed.",
                ),
                2,
            ),
        )
    )

    package = orchestrator.fetch("final topic")

    assert len(package.sources) == 2
    assert len(package.facts) == 1
    assert package.facts[0].source_ids == (
        "primary:source_001",
        "secondary:source_001",
    )


def test_metadata_only_sources_deduplicate_conservatively() -> None:
    source_a = KnowledgeSource(
        source_id="a",
        provider="Official Club",
        title="Match Statement",
        source_type="official_statement",
        reliability="official",
    )
    source_b = KnowledgeSource(
        source_id="b",
        provider=" official club ",
        title="MATCH statement",
        source_type="official_statement",
        reliability="official",
    )
    package = ExternalKnowledgePackage(
        topic="match",
        sources=(source_a, source_b),
        facts=(
            KnowledgeFact("f1", "Statement published", ("a",), "supported"),
            KnowledgeFact("f2", "Another fact", ("b",), "supported"),
        ),
    )

    deduplicated = deduplicate_package(package)

    assert [source.source_id for source in deduplicated.sources] == ["a"]
    assert deduplicated.facts[0].source_ids == ("a",)
    assert deduplicated.facts[1].source_ids == ("a",)
