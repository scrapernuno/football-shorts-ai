from __future__ import annotations

from knowledge.contracts import ExternalKnowledgePackage
from knowledge.fixtures import OfflineFootballKnowledgeFixture


class ResearchEngine:
    """Build the research package from a governed knowledge provider.

    The default provider is deterministic and offline. A live provider can be
    injected later without changing the Production Brain orchestration contract.
    """

    def __init__(self, provider: object | None = None) -> None:
        self._provider = provider or OfflineFootballKnowledgeFixture()

    def execute(self, context: dict) -> dict:
        topic = str(context["topic"]).strip()
        if not topic:
            raise ValueError("topic must not be empty")

        package = self._provider.fetch(topic)
        if not isinstance(package, ExternalKnowledgePackage):
            raise TypeError(
                "knowledge provider must return ExternalKnowledgePackage"
            )

        knowledge = package.to_dict()
        fact_claims = [fact["claim"] for fact in knowledge["facts"]]

        return {
            "topic": topic,
            "entities": [],
            # Preserve the existing Story Engine contract: facts remain strings.
            "facts": fact_claims,
            "story_angles": [
                "evidence-led explainer angle",
                "player or club context angle",
                "football fan debate angle",
            ],
            "sources": knowledge["sources"],
            "knowledge": knowledge,
            "provider_mode": knowledge["provider_mode"],
            "research_status": "completed",
        }
