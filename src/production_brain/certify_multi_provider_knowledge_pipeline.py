from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from knowledge.contracts import (
    ExternalKnowledgePackage,
    KnowledgeFact,
    KnowledgeSource,
)
from knowledge.orchestration import (
    DeterministicKnowledgeOrchestrator,
    ProviderRegistration,
)
from production_brain import brain


TOPIC = "football multi-provider knowledge certification demo"


@dataclass(frozen=True, slots=True)
class CertificationProvider:
    provider_name: str
    provider_mode: str
    source_title: str
    source_url: str

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        source = KnowledgeSource(
            source_id="source_001",
            provider=self.provider_name,
            title=self.source_title,
            source_type="official_statement",
            reliability="official",
            url=self.source_url,
        )
        fact = KnowledgeFact(
            fact_id="fact_001",
            claim="The club confirmed the player signing.",
            source_ids=(source.source_id,),
            verification_status="supported",
        )
        return ExternalKnowledgePackage(
            topic=topic,
            sources=(source,),
            facts=(fact,),
            provider_mode=self.provider_mode,
        )


def _build_orchestrator() -> DeterministicKnowledgeOrchestrator:
    return DeterministicKnowledgeOrchestrator(
        (
            ProviderRegistration(
                provider_id="official_primary",
                provider=CertificationProvider(
                    provider_name="official_primary_provider",
                    provider_mode="offline_fixture",
                    source_title="Official club announcement",
                    source_url="https://club.example/signing?utm_source=certification",
                ),
                priority=10,
                role="primary",
                required=True,
            ),
            ProviderRegistration(
                provider_id="official_secondary",
                provider=CertificationProvider(
                    provider_name="official_secondary_provider",
                    provider_mode="offline_fixture",
                    source_title="Official league registration",
                    source_url="https://league.example/registration",
                ),
                priority=20,
                role="secondary",
            ),
        )
    )


def _certify_research(research: dict) -> None:
    if research.get("research_status") != "completed":
        raise SystemExit("CERTIFICATION_FAILED: research did not complete")

    knowledge = research.get("knowledge")
    policy = research.get("knowledge_policy")
    orchestration = research.get("knowledge_orchestration")

    if not isinstance(knowledge, dict):
        raise SystemExit("CERTIFICATION_FAILED: knowledge package missing")
    if not isinstance(policy, dict):
        raise SystemExit("CERTIFICATION_FAILED: knowledge policy missing")
    if not isinstance(orchestration, dict):
        raise SystemExit("CERTIFICATION_FAILED: orchestration evidence missing")

    sources = knowledge.get("sources")
    facts = knowledge.get("facts")
    executions = orchestration.get("executions")
    assessments = policy.get("assessments")

    if not isinstance(sources, list) or len(sources) != 2:
        raise SystemExit("CERTIFICATION_FAILED: independent sources were not preserved")
    if not isinstance(facts, list) or len(facts) != 1:
        raise SystemExit("CERTIFICATION_FAILED: equivalent facts were not deduplicated")
    if not isinstance(executions, list) or len(executions) != 2:
        raise SystemExit("CERTIFICATION_FAILED: provider execution evidence incomplete")
    if any(record.get("status") != "completed" for record in executions):
        raise SystemExit("CERTIFICATION_FAILED: provider execution did not complete")

    source_ids = facts[0].get("source_ids")
    if not isinstance(source_ids, list) or len(source_ids) != 2:
        raise SystemExit("CERTIFICATION_FAILED: merged fact lost independent evidence")

    if not isinstance(assessments, list) or len(assessments) != 1:
        raise SystemExit("CERTIFICATION_FAILED: confidence assessment missing")
    assessment = assessments[0]
    if assessment.get("confidence") != "high":
        raise SystemExit("CERTIFICATION_FAILED: expected high-confidence assessment")
    if assessment.get("independent_source_count") != 2:
        raise SystemExit("CERTIFICATION_FAILED: independent provider count drift")

    if policy.get("conflicts") != []:
        raise SystemExit("CERTIFICATION_FAILED: false conflict detected")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0043f-") as tmp:
        output_dir = Path(tmp) / "output"
        original_output = brain.OUTPUT
        brain.OUTPUT = output_dir

        try:
            result = brain.execute(
                TOPIC,
                knowledge_provider=_build_orchestrator(),
            )
        finally:
            brain.OUTPUT = original_output

        if result.get("status") != "COMPLETED":
            raise SystemExit("CERTIFICATION_FAILED: production brain did not complete")

        research = result.get("research")
        if not isinstance(research, dict):
            raise SystemExit("CERTIFICATION_FAILED: research result missing")
        _certify_research(research)

        persisted_path = output_dir / "research_package.json"
        if not persisted_path.is_file():
            raise SystemExit("CERTIFICATION_FAILED: research package was not persisted")
        persisted = json.loads(persisted_path.read_text(encoding="utf-8"))
        if persisted != research:
            raise SystemExit("CERTIFICATION_FAILED: persisted research package drift")

        for package_name in (
            "story_package.json",
            "production_package.json",
            "publishing_package.json",
        ):
            if not (output_dir / package_name).is_file():
                raise SystemExit(
                    f"CERTIFICATION_FAILED: downstream package missing: {package_name}"
                )

        print("FOOTBALL-SHORTS-AI-0043F: CERTIFIED")
        print("PIPELINE_STATUS: COMPLETED")
        print("PROVIDERS_COMPLETED: 2")
        print("DEDUPLICATED_FACTS: 1")
        print("INDEPENDENT_SOURCES: 2")
        print("CONFIDENCE_LEVEL: HIGH")
        print("CONFLICT_STATUS: CLEAR")
        print("NETWORK_ACCESS: NOT EXECUTED")
        print("REAL_PUBLICATION: NOT EXECUTED")
        print("NEXT_AUTHORISED_STEP: GOVERNED_MULTI_PROVIDER_RUNTIME_CONFIGURATION")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
