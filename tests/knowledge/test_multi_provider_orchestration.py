from __future__ import annotations

from dataclasses import dataclass

import pytest

from knowledge.contracts import (
    ExternalKnowledgePackage,
    KnowledgeFact,
    KnowledgeSource,
)
from knowledge.orchestration import (
    DeterministicKnowledgeOrchestrator,
    ProviderRegistration,
)


def _package(topic: str, provider: str, mode: str = "offline_fixture") -> ExternalKnowledgePackage:
    source = KnowledgeSource(
        source_id="source_001",
        provider=provider,
        title=f"Evidence from {provider}",
        source_type="controlled_fixture",
        reliability="controlled_fixture",
    )
    fact = KnowledgeFact(
        fact_id="fact_001",
        claim=f"Claim from {provider}",
        source_ids=(source.source_id,),
        verification_status="supported",
    )
    return ExternalKnowledgePackage(
        topic=topic,
        sources=(source,),
        facts=(fact,),
        provider_mode=mode,
    )


@dataclass
class StaticProvider:
    provider_name: str
    provider_mode: str = "offline_fixture"

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        return _package(topic, self.provider_name, self.provider_mode)


@dataclass
class FailingProvider:
    provider_name: str
    provider_mode: str = "offline_fixture"

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        raise LookupError(f"no evidence for {topic}")


def test_orchestrator_executes_in_stable_priority_order_and_namespaces_ids() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration("secondary_b", StaticProvider("provider_b"), 20),
            ProviderRegistration("primary_a", StaticProvider("provider_a"), 10, role="primary"),
        )
    )

    result = orchestrator.execute("football topic")

    assert [record.provider_id for record in result.executions] == [
        "primary_a",
        "secondary_b",
    ]
    assert [record.status for record in result.executions] == ["completed", "completed"]
    assert [source.source_id for source in result.package.sources] == [
        "primary_a:source_001",
        "secondary_b:source_001",
    ]
    assert [fact.fact_id for fact in result.package.facts] == [
        "primary_a:fact_001",
        "secondary_b:fact_001",
    ]
    assert result.package.facts[0].source_ids == ("primary_a:source_001",)


def test_optional_failure_is_recorded_and_other_provider_completes() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration("optional", FailingProvider("broken"), 1),
            ProviderRegistration("healthy", StaticProvider("healthy"), 2),
        )
    )

    result = orchestrator.execute("football topic")

    assert result.executions[0].status == "failed"
    assert result.executions[0].error_type == "LookupError"
    assert result.executions[1].status == "completed"
    assert len(result.package.sources) == 1


def test_required_failure_aborts_fail_closed() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration(
                "required",
                FailingProvider("broken"),
                1,
                role="primary",
                required=True,
            ),
            ProviderRegistration("healthy", StaticProvider("healthy"), 2),
        )
    )

    with pytest.raises(RuntimeError, match="required knowledge provider failed"):
        orchestrator.execute("football topic")


def test_fallback_runs_only_when_non_fallback_did_not_complete() -> None:
    fallback = ProviderRegistration(
        "fallback",
        StaticProvider("fallback_provider"),
        100,
        role="fallback",
    )

    successful = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration("primary", StaticProvider("primary_provider"), 1, role="primary"),
            fallback,
        )
    ).execute("football topic")
    assert [record.status for record in successful.executions] == ["completed", "skipped"]

    recovered = DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration("primary", FailingProvider("broken"), 1, role="primary"),
            fallback,
        )
    ).execute("football topic")
    assert [record.status for record in recovered.executions] == ["failed", "completed"]
    assert recovered.package.sources[0].source_id == "fallback:source_001"


def test_orchestrator_rejects_invalid_registration_sets_and_empty_topic() -> None:
    provider = StaticProvider("provider")

    with pytest.raises(ValueError, match="at least one provider registration"):
        DeterministicKnowledgeOrchestrator(())

    with pytest.raises(ValueError, match="provider_id values must be unique"):
        DeterministicKnowledgeOrchestrator(
            (
                ProviderRegistration("duplicate", provider, 1),
                ProviderRegistration("duplicate", provider, 2),
            )
        )

    orchestrator = DeterministicKnowledgeOrchestrator(
        (ProviderRegistration("provider", provider, 1),)
    )
    with pytest.raises(ValueError, match="topic must not be empty"):
        orchestrator.execute("   ")


def test_fetch_protocol_returns_merged_package() -> None:
    orchestrator = DeterministicKnowledgeOrchestrator(
        (ProviderRegistration("provider", StaticProvider("provider"), 1),)
    )

    package = orchestrator.fetch("football topic")

    assert isinstance(package, ExternalKnowledgePackage)
    assert package.topic == "football topic"
    assert package.sources[0].source_id == "provider:source_001"
