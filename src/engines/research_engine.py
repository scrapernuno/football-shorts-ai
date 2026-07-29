from __future__ import annotations

from knowledge.contracts import ExternalKnowledgePackage
from knowledge.fixtures import OfflineFootballKnowledgeFixture
from knowledge.orchestration import MultiProviderKnowledgeResult
from knowledge.policy import evaluate_knowledge_policy


class ResearchEngine:
    """Build the research package from governed knowledge evidence.

    Single providers remain fully compatible through ``fetch``. Governed
    multi-provider orchestrators can expose ``execute`` so their immutable
    execution evidence is preserved in the research package.
    """

    def __init__(self, provider: object | None = None) -> None:
        self._provider = provider or OfflineFootballKnowledgeFixture()

    def execute(self, context: dict) -> dict:
        topic = str(context["topic"]).strip()
        if not topic:
            raise ValueError("topic must not be empty")

        package, orchestration = self._resolve_knowledge(topic)
        knowledge = package.to_dict()
        policy = evaluate_knowledge_policy(package).to_dict()
        fact_claims = [fact["claim"] for fact in knowledge["facts"]]

        result = {
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
            "knowledge_policy": policy,
            "provider_mode": knowledge["provider_mode"],
            "research_status": "completed",
        }
        if orchestration is not None:
            result["knowledge_orchestration"] = orchestration.to_dict()
        return result

    def _resolve_knowledge(
        self,
        topic: str,
    ) -> tuple[ExternalKnowledgePackage, MultiProviderKnowledgeResult | None]:
        execute = getattr(self._provider, "execute", None)
        if callable(execute):
            candidate = execute(topic)
            if isinstance(candidate, MultiProviderKnowledgeResult):
                return candidate.package, candidate
            if isinstance(candidate, ExternalKnowledgePackage):
                return candidate, None
            raise TypeError(
                "knowledge provider execute() must return "
                "MultiProviderKnowledgeResult or ExternalKnowledgePackage"
            )

        fetch = getattr(self._provider, "fetch", None)
        if not callable(fetch):
            raise TypeError("knowledge provider must expose fetch() or execute()")

        package = fetch(topic)
        if not isinstance(package, ExternalKnowledgePackage):
            raise TypeError(
                "knowledge provider must return ExternalKnowledgePackage"
            )
        return package, None
