from __future__ import annotations

from knowledge.adapters import MappingKnowledgeAdapter
from knowledge.contracts import ExternalKnowledgePackage


class OfflineFootballKnowledgeFixture:
    """Deterministic football knowledge provider for tests and certification.

    The fixture performs no network access and does not claim live accuracy. Its
    purpose is to exercise the governed knowledge contract before real provider
    activation.
    """

    provider_name = "offline_football_fixture"
    provider_mode = "offline_fixture"

    def __init__(self) -> None:
        self._adapter = MappingKnowledgeAdapter()

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        normalized_topic = str(topic).strip()
        if not normalized_topic:
            raise ValueError("topic must not be empty")

        payload = {
            "sources": [
                {
                    "source_id": "fixture_source_001",
                    "provider": self.provider_name,
                    "title": f"Controlled fixture for {normalized_topic}",
                    "source_type": "controlled_fixture",
                    "reliability": "controlled_fixture",
                    "url": None,
                    "published_at": None,
                    "retrieved_at": None,
                }
            ],
            "facts": [
                {
                    "fact_id": "fixture_fact_001",
                    "claim": f"{normalized_topic} is the selected football research topic.",
                    "source_ids": ["fixture_source_001"],
                    "verification_status": "supported",
                },
                {
                    "fact_id": "fixture_fact_002",
                    "claim": (
                        "This package is deterministic certification evidence and "
                        "must not be represented as live football reporting."
                    ),
                    "source_ids": ["fixture_source_001"],
                    "verification_status": "supported",
                },
            ],
        }

        return self._adapter.build_package(
            normalized_topic,
            payload,
            provider_mode=self.provider_mode,
        )
