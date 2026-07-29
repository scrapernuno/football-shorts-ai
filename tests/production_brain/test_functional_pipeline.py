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

    expected = {
        "research_package.json",
        "story_package.json",
        "production_package.json",
        "publishing_package.json",
    }
    assert {path.name for path in (tmp_path / "output").iterdir()} == expected

    for package_name in expected:
        payload = json.loads(
            (tmp_path / "output" / package_name).read_text(encoding="utf-8")
        )
        assert isinstance(payload, dict)
