from __future__ import annotations

import json
import tempfile
from pathlib import Path

from production_brain import brain


EXPECTED_PACKAGES = {
    "research_package.json": "research_status",
    "story_package.json": "story_status",
    "production_package.json": "production_status",
    "publishing_package.json": "publishing_status",
}


def _certify_research_evidence(research: dict) -> None:
    if research.get("research_status") != "completed":
        raise SystemExit("CERTIFICATION_FAILED: research package incomplete")

    if research.get("provider_mode") != "offline_fixture":
        raise SystemExit("CERTIFICATION_FAILED: unexpected provider mode")

    knowledge = research.get("knowledge")
    if not isinstance(knowledge, dict):
        raise SystemExit("CERTIFICATION_FAILED: knowledge package missing")

    if knowledge.get("provider_mode") != "offline_fixture":
        raise SystemExit("CERTIFICATION_FAILED: knowledge package is not deterministic")

    sources = knowledge.get("sources")
    facts = knowledge.get("facts")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("CERTIFICATION_FAILED: governed sources missing")
    if not isinstance(facts, list) or not facts:
        raise SystemExit("CERTIFICATION_FAILED: governed facts missing")

    source_ids = {source.get("source_id") for source in sources if isinstance(source, dict)}
    if None in source_ids or len(source_ids) != len(sources):
        raise SystemExit("CERTIFICATION_FAILED: invalid or duplicate source identifiers")

    for fact in facts:
        if not isinstance(fact, dict):
            raise SystemExit("CERTIFICATION_FAILED: invalid governed fact")
        if fact.get("verification_status") != "supported":
            raise SystemExit("CERTIFICATION_FAILED: unsupported governed fact")
        fact_source_ids = fact.get("source_ids")
        if not isinstance(fact_source_ids, list) or not fact_source_ids:
            raise SystemExit("CERTIFICATION_FAILED: fact evidence references missing")
        if not set(fact_source_ids).issubset(source_ids):
            raise SystemExit("CERTIFICATION_FAILED: fact references unknown source")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0042a5-") as tmp:
        output_dir = Path(tmp) / "output"
        original_output = brain.OUTPUT
        brain.OUTPUT = output_dir

        try:
            result = brain.execute("football external knowledge certification demo")
        finally:
            brain.OUTPUT = original_output

        if result.get("status") != "COMPLETED":
            raise SystemExit("CERTIFICATION_FAILED: pipeline did not complete")

        persisted_packages: dict[str, dict] = {}
        for package_name, status_key in EXPECTED_PACKAGES.items():
            package_path = output_dir / package_name
            if not package_path.is_file():
                raise SystemExit(
                    f"CERTIFICATION_FAILED: missing package {package_name}"
                )

            payload = json.loads(package_path.read_text(encoding="utf-8"))
            if payload.get(status_key) != "completed":
                raise SystemExit(
                    f"CERTIFICATION_FAILED: invalid status in {package_name}"
                )
            persisted_packages[package_name] = payload

        research = result.get("research", {})
        _certify_research_evidence(research)

        if persisted_packages["research_package.json"] != research:
            raise SystemExit("CERTIFICATION_FAILED: persisted research evidence drift")

        publishing = result.get("publishing", {})
        if publishing.get("publishing_status") != "completed":
            raise SystemExit("CERTIFICATION_FAILED: publishing package incomplete")

        print("FOOTBALL-SHORTS-AI-0042A.5: CERTIFIED")
        print("PIPELINE_STATUS: COMPLETED")
        print("PACKAGES_GENERATED: 4")
        print("KNOWLEDGE_PROVIDER_MODE: OFFLINE_FIXTURE")
        print("GOVERNED_SOURCES: PRESENT")
        print("SUPPORTED_FACT_EVIDENCE: PRESENT")
        print("EXTERNAL_API_ACCESS: NOT EXECUTED")
        print("REAL_PUBLICATION: NOT EXECUTED")
        print("NEXT_AUTHORISED_STEP: LIVE_PROVIDER_ACTIVATION_DESIGN")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
