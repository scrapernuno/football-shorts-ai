from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol, runtime_checkable

from knowledge.contracts import (
    ExternalKnowledgePackage,
    KnowledgeFact,
    KnowledgeSource,
)


ProviderRole = Literal["primary", "secondary", "fallback"]
ProviderExecutionStatus = Literal["completed", "failed", "skipped"]


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Minimum provider boundary accepted by multi-provider orchestration."""

    provider_name: str
    provider_mode: str

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        """Return governed knowledge for one normalized topic."""


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    """Governed registration metadata for one knowledge provider."""

    provider_id: str
    provider: KnowledgeProvider
    priority: int
    role: ProviderRole = "secondary"
    required: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if self.priority < 0:
            raise ValueError("priority must be zero or greater")
        if not isinstance(self.provider, KnowledgeProvider):
            raise TypeError("provider must satisfy the KnowledgeProvider protocol")


@dataclass(frozen=True, slots=True)
class ProviderExecutionRecord:
    """Immutable evidence describing one provider execution decision."""

    provider_id: str
    provider_name: str
    role: ProviderRole
    priority: int
    required: bool
    status: ProviderExecutionStatus
    source_count: int = 0
    fact_count: int = 0
    error_type: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if not self.provider_name.strip():
            raise ValueError("provider_name must not be empty")
        if self.priority < 0:
            raise ValueError("priority must be zero or greater")
        if self.source_count < 0 or self.fact_count < 0:
            raise ValueError("source_count and fact_count must be zero or greater")
        if self.status == "completed" and self.error_type is not None:
            raise ValueError("completed provider execution cannot contain error_type")
        if self.status == "failed" and not self.error_type:
            raise ValueError("failed provider execution requires error_type")


@dataclass(frozen=True, slots=True)
class MultiProviderKnowledgeResult:
    """Canonical output of governed multi-provider knowledge orchestration."""

    topic: str
    package: ExternalKnowledgePackage
    executions: tuple[ProviderExecutionRecord, ...]

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("topic must not be empty")
        if self.package.topic != self.topic:
            raise ValueError("package topic must match orchestration topic")
        if not self.executions:
            raise ValueError("at least one provider execution record is required")

        provider_ids = [record.provider_id for record in self.executions]
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("provider execution records must use unique provider_id values")

        completed = [record for record in self.executions if record.status == "completed"]
        if not completed:
            raise ValueError("at least one provider execution must complete")

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "package": self.package.to_dict(),
            "executions": [
                {
                    "provider_id": record.provider_id,
                    "provider_name": record.provider_name,
                    "role": record.role,
                    "priority": record.priority,
                    "required": record.required,
                    "status": record.status,
                    "source_count": record.source_count,
                    "fact_count": record.fact_count,
                    "error_type": record.error_type,
                }
                for record in self.executions
            ],
        }


class DeterministicKnowledgeOrchestrator:
    """Execute registered providers in a stable, fail-closed order.

    Primary and secondary providers execute first by ascending priority and then
    provider_id. Fallback providers execute only when no non-fallback provider
    completed. Required provider failure aborts orchestration immediately.
    """

    def __init__(self, registrations: tuple[ProviderRegistration, ...]) -> None:
        if not registrations:
            raise ValueError("at least one provider registration is required")

        provider_ids = [registration.provider_id for registration in registrations]
        if len(set(provider_ids)) != len(provider_ids):
            raise ValueError("provider_id values must be unique")

        self._registrations = tuple(
            sorted(registrations, key=lambda item: (item.priority, item.provider_id))
        )

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        """Provide protocol compatibility by returning only the merged package."""

        return self.execute(topic).package

    def execute(self, topic: str) -> MultiProviderKnowledgeResult:
        normalized_topic = str(topic).strip()
        if not normalized_topic:
            raise ValueError("topic must not be empty")

        executions: list[ProviderExecutionRecord] = []
        completed_packages: list[tuple[ProviderRegistration, ExternalKnowledgePackage]] = []

        non_fallback_completed = False
        for registration in self._registrations:
            if registration.role == "fallback" and non_fallback_completed:
                executions.append(self._record(registration, status="skipped"))
                continue

            try:
                package = registration.provider.fetch(normalized_topic)
                if not isinstance(package, ExternalKnowledgePackage):
                    raise TypeError("provider must return ExternalKnowledgePackage")
                if package.topic != normalized_topic:
                    raise ValueError("provider package topic does not match requested topic")
            except Exception as exc:
                executions.append(
                    self._record(
                        registration,
                        status="failed",
                        error_type=type(exc).__name__,
                    )
                )
                if registration.required:
                    raise RuntimeError(
                        f"required knowledge provider failed: {registration.provider_id}"
                    ) from exc
                continue

            completed_packages.append((registration, package))
            executions.append(
                self._record(
                    registration,
                    status="completed",
                    source_count=len(package.sources),
                    fact_count=len(package.facts),
                )
            )
            if registration.role != "fallback":
                non_fallback_completed = True

        if not completed_packages:
            raise RuntimeError("no knowledge provider completed successfully")

        merged_package = self._merge(normalized_topic, completed_packages)
        return MultiProviderKnowledgeResult(
            topic=normalized_topic,
            package=merged_package,
            executions=tuple(executions),
        )

    @staticmethod
    def _record(
        registration: ProviderRegistration,
        *,
        status: ProviderExecutionStatus,
        source_count: int = 0,
        fact_count: int = 0,
        error_type: str | None = None,
    ) -> ProviderExecutionRecord:
        return ProviderExecutionRecord(
            provider_id=registration.provider_id,
            provider_name=registration.provider.provider_name,
            role=registration.role,
            priority=registration.priority,
            required=registration.required,
            status=status,
            source_count=source_count,
            fact_count=fact_count,
            error_type=error_type,
        )

    @staticmethod
    def _merge(
        topic: str,
        packages: list[tuple[ProviderRegistration, ExternalKnowledgePackage]],
    ) -> ExternalKnowledgePackage:
        sources: list[KnowledgeSource] = []
        facts: list[KnowledgeFact] = []
        provider_modes: set[str] = set()

        for registration, package in packages:
            provider_modes.add(package.provider_mode)
            source_id_map: dict[str, str] = {}

            for source in package.sources:
                namespaced_source_id = f"{registration.provider_id}:{source.source_id}"
                source_id_map[source.source_id] = namespaced_source_id
                sources.append(replace(source, source_id=namespaced_source_id))

            for fact in package.facts:
                namespaced_fact_id = f"{registration.provider_id}:{fact.fact_id}"
                namespaced_source_ids = tuple(
                    source_id_map[source_id] for source_id in fact.source_ids
                )
                facts.append(
                    replace(
                        fact,
                        fact_id=namespaced_fact_id,
                        source_ids=namespaced_source_ids,
                    )
                )

        provider_mode = "live" if "live" in provider_modes else "offline_fixture"
        return ExternalKnowledgePackage(
            topic=topic,
            sources=tuple(sources),
            facts=tuple(facts),
            provider_mode=provider_mode,
        )
