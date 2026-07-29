from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


SourceType = Literal[
    "article",
    "api",
    "rss",
    "official_statement",
    "statistics",
    "controlled_fixture",
]

ReliabilityLevel = Literal[
    "official",
    "primary",
    "reputable_secondary",
    "unverified",
    "controlled_fixture",
]

VerificationStatus = Literal[
    "supported",
    "partially_supported",
    "unsupported",
]


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    source_id: str
    provider: str
    title: str
    source_type: SourceType
    reliability: ReliabilityLevel
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KnowledgeFact:
    fact_id: str
    claim: str
    source_ids: tuple[str, ...]
    verification_status: VerificationStatus

    def __post_init__(self) -> None:
        if not self.fact_id.strip():
            raise ValueError("fact_id must not be empty")
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if self.verification_status == "supported" and not self.source_ids:
            raise ValueError("supported facts require at least one source_id")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must not contain duplicates")

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["source_ids"] = list(self.source_ids)
        return payload


@dataclass(frozen=True, slots=True)
class ExternalKnowledgePackage:
    topic: str
    sources: tuple[KnowledgeSource, ...]
    facts: tuple[KnowledgeFact, ...]
    provider_mode: Literal["offline_fixture", "live"] = "offline_fixture"

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("topic must not be empty")

        source_ids = [source.source_id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_id values must be unique")

        available_sources = set(source_ids)
        for fact in self.facts:
            missing = set(fact.source_ids) - available_sources
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(
                    f"fact {fact.fact_id} references unknown sources: {missing_list}"
                )

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "provider_mode": self.provider_mode,
            "sources": [source.to_dict() for source in self.sources],
            "facts": [fact.to_dict() for fact in self.facts],
        }
