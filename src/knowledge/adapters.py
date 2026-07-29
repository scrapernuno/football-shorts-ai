from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource


class KnowledgeProviderAdapter(ABC):
    """Provider-neutral boundary for external football knowledge sources."""

    provider_name: str
    provider_mode: str

    @abstractmethod
    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        """Return a validated knowledge package for the requested topic."""


class MappingKnowledgeAdapter(KnowledgeProviderAdapter):
    """Convert provider-neutral mapping payloads into governed contracts.

    This adapter performs no network access. Concrete providers may fetch data
    elsewhere and pass the resulting mapping into ``build_package``.
    """

    provider_name = "mapping"
    provider_mode = "offline_fixture"

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        raise RuntimeError(
            "MappingKnowledgeAdapter does not fetch data directly; "
            "use build_package(topic, payload)"
        )

    def build_package(
        self,
        topic: str,
        payload: Mapping[str, Any],
        *,
        provider_mode: str | None = None,
    ) -> ExternalKnowledgePackage:
        normalized_topic = str(topic).strip()
        if not normalized_topic:
            raise ValueError("topic must not be empty")

        raw_sources = payload.get("sources", [])
        raw_facts = payload.get("facts", [])

        if not isinstance(raw_sources, list):
            raise TypeError("payload sources must be a list")
        if not isinstance(raw_facts, list):
            raise TypeError("payload facts must be a list")

        sources = tuple(self._build_source(item) for item in raw_sources)
        facts = tuple(self._build_fact(item) for item in raw_facts)

        mode = provider_mode or self.provider_mode
        if mode not in {"offline_fixture", "live"}:
            raise ValueError("provider_mode must be offline_fixture or live")

        return ExternalKnowledgePackage(
            topic=normalized_topic,
            sources=sources,
            facts=facts,
            provider_mode=mode,
        )

    def _build_source(self, item: Any) -> KnowledgeSource:
        if not isinstance(item, Mapping):
            raise TypeError("each source must be a mapping")

        return KnowledgeSource(
            source_id=self._required_text(item, "source_id"),
            provider=self._optional_text(item, "provider") or self.provider_name,
            title=self._required_text(item, "title"),
            source_type=self._required_text(item, "source_type"),
            reliability=self._required_text(item, "reliability"),
            url=self._optional_text(item, "url"),
            published_at=self._optional_text(item, "published_at"),
            retrieved_at=self._optional_text(item, "retrieved_at"),
        )

    def _build_fact(self, item: Any) -> KnowledgeFact:
        if not isinstance(item, Mapping):
            raise TypeError("each fact must be a mapping")

        raw_source_ids = item.get("source_ids", [])
        if not isinstance(raw_source_ids, list):
            raise TypeError("fact source_ids must be a list")

        source_ids = tuple(str(value).strip() for value in raw_source_ids)
        if any(not value for value in source_ids):
            raise ValueError("fact source_ids must not contain empty values")

        return KnowledgeFact(
            fact_id=self._required_text(item, "fact_id"),
            claim=self._required_text(item, "claim"),
            source_ids=source_ids,
            verification_status=self._required_text(item, "verification_status"),
        )

    @staticmethod
    def _required_text(item: Mapping[str, Any], key: str) -> str:
        value = item.get(key)
        if value is None:
            raise ValueError(f"missing required field: {key}")

        text = str(value).strip()
        if not text:
            raise ValueError(f"field {key} must not be empty")
        return text

    @staticmethod
    def _optional_text(item: Mapping[str, Any], key: str) -> str | None:
        value = item.get(key)
        if value is None:
            return None

        text = str(value).strip()
        return text or None
