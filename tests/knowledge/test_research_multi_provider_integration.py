from __future__ import annotations

from dataclasses import dataclass

from engines.research_engine import ResearchEngine
from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource
from knowledge.orchestration import (
    DeterministicKnowledgeOrchestrator,
    ProviderRegistration,
)


def _package(topic: str, provider: str, claim: str) -> ExternalKnowledgePackage:
    source = KnowledgeSource(
        source_id="source_001",
        provider=provider,
        title=f"Evidence from {provider}",
        source_type="official_statement",
        reliability="official",
        url=f"https://example.com/{provider}",
    )
    fact = KnowledgeFact(
        fact_id="fact_001",
        claim=claim,
        source_ids=(source.source_id,),
        verification_status="supported",
    )
    return ExternalKnowledgePackage(
        topic=topic,
        sources=(source,),
        facts=(fact,),
        provider_mode="live",
    )


@dataclass
class StaticProvider:
    provider_name: str
    claim: str
    provider_mode: str = "live"

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        return _package(topic, self.provider_name, self.claim)


def test_research_engine_preserves_orchestration_and_policy_evidence() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration(
                "official_a",
                StaticProvider("official_a", "Player joins the club"),
                1,
                role="primary",
                required=True,
            ),
            ProviderRegistration(
                "official_b",
                StaticProvider("official_b", "Player joins the club."),
                2,
                role="secondary",
            ),
        )
    )

    research = ResearchEngine(provider=orchestrator).execute(
        {"topic": "transfer story"}
    )

    assert research["research_status"] == "completed"
    assert research["provider_mode"] == "live"
    assert research["facts"] == ["Player joins the club"]
    assert len(research["sources"]) == 2

    orchestration = research["knowledge_orchestration"]
    assert [record["provider_id"] for record in orchestration["executions"]] == [
        "official_a",
        "official_b",
    ]
    assert all(
        record["status"] == "completed"
        for record in orchestration["executions"]
    )
    assert orchestration["package"] == research["knowledge"]

    policy = research["knowledge_policy"]
    assert policy["topic"] == "transfer story"
    assert len(policy["assessments"]) == 1
    assert policy["assessments"][0]["confidence"] == "high"
    assert policy["assessments"][0]["independent_source_count"] == 2
    assert policy["conflicts"] == []


def test_single_provider_keeps_contract_and_adds_policy_without_orchestration() -> None:
    provider = StaticProvider("official_single", "Club confirms the signing")

    research = ResearchEngine(provider=provider).execute(
        {"topic": "single provider story"}
    )

    assert research["facts"] == ["Club confirms the signing"]
    assert "knowledge_orchestration" not in research
    assert research["knowledge_policy"]["assessments"][0]["confidence"] == "high"


class InvalidExecuteProvider:
    provider_name = "invalid"
    provider_mode = "offline_fixture"

    def execute(self, topic: str) -> dict:
        return {"topic": topic}


def test_research_engine_rejects_invalid_execute_result() -> None:
    engine = ResearchEngine(provider=InvalidExecuteProvider())

    try:
        engine.execute({"topic": "invalid provider"})
    except TypeError as exc:
        assert "MultiProviderKnowledgeResult" in str(exc)
    else:
        raise AssertionError("invalid execute result must fail closed")
