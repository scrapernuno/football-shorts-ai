from __future__ import annotations

import json
from pathlib import Path

from production_brain import brain


def test_functional_pipeline_generates_all_packages(tmp_path: Path) -> None:
    original_output = brain.OUTPUT
    brain.OUTPUT = tmp_path / "output"

    try:
        result = brain.execute("Cristiano Ronaldo recordes")
    finally:
        brain.OUTPUT = original_output

    assert result["status"] == "COMPLETED"
    assert result["research"]["research_status"] == "completed"
    assert result["story"]["story_status"] == "completed"
    assert result["production"]["production_status"] == "completed"
    assert result["publishing"]["publishing_status"] == "completed"

    research = result["research"]
    assert research["provider_mode"] == "offline_fixture"
    assert research["facts"]
    assert research["sources"]

    knowledge = research["knowledge"]
    assert knowledge["provider_mode"] == "offline_fixture"
    assert knowledge["topic"] == "Cristiano Ronaldo recordes"
    assert knowledge["sources"]
    assert knowledge["facts"]

    source_ids = {source["source_id"] for source in knowledge["sources"]}
    assert len(source_ids) == len(knowledge["sources"])

    for fact in knowledge["facts"]:
        assert fact["verification_status"] == "supported"
        assert fact["source_ids"]
        assert set(fact["source_ids"]).issubset(source_ids)

    expected = {
        "research_package.json",
        "story_package.json",
        "production_package.json",
        "publishing_package.json",
    }
    assert {path.name for path in (tmp_path / "output").iterdir()} == expected

    packages: dict[str, dict] = {}
    for package_name in expected:
        payload = json.loads(
            (tmp_path / "output" / package_name).read_text(encoding="utf-8")
        )
        assert isinstance(payload, dict)
        packages[package_name] = payload

    persisted_research = packages["research_package.json"]
    assert persisted_research["knowledge"] == knowledge
    assert persisted_research["provider_mode"] == "offline_fixture"
