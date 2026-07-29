from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from knowledge.contracts import ExternalKnowledgePackage


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
