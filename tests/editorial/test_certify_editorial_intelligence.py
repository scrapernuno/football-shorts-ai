from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from editorial.certify_editorial_intelligence import (
    EditorialIntelligenceCertificationError,
    canonical_sha256,
    certify_editorial_intelligence,
)


def test_certifies_complete_owned_and_reference_scenarios() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))

    assert result.status == "CERTIFIED"
    assert result.certification_id.startswith("EDITORIALCERT-")
    assert result.owned_scenario["scene_index_state"] == "indexed"
    assert result.owned_scenario["matching_state"] == "matched"
    assert result.owned_scenario["hook_state"] == "optimized"
    assert result.owned_scenario["alignment_state"] == "aligned"
    assert result.owned_scenario["score_state"] == "scored"
    assert result.owned_scenario["timeline_state"] == "ready_for_review"
    assert result.owned_scenario["learning_state"] == "review_ready"
    assert result.reference_scenario["scene_index_state"] == "blocked"
    assert result.reference_scenario["matching_state"] == "blocked"
    assert result.reference_scenario["hook_state"] == "blocked"
    assert result.reference_scenario["alignment_state"] == "blocked"
    assert result.reference_scenario["score_state"] == "blocked"
    assert result.reference_scenario["timeline_state"] == "blocked"


def test_certifies_editorial_review_dashboard_artifacts() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))

    assert set(result.dashboard_artifacts) == {
        "dashboard/editorial-review.html",
        "dashboard/assets/editorial-review.css",
        "dashboard/assets/editorial-review.js",
    }


def test_all_operational_capabilities_remain_disabled() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))

    assert result.controls
    assert all(value is False for value in result.controls.values())
    assert result.controls["network_enabled"] is False
    assert result.controls["model_execution_enabled"] is False
    assert result.controls["acquisition_enabled"] is False
    assert result.controls["analytics_fetch_enabled"] is False
    assert result.controls["weight_update_enabled"] is False
    assert result.controls["model_training_enabled"] is False
    assert result.controls["render_enabled"] is False
    assert result.controls["auto_render"] is False
    assert result.controls["auto_publish"] is False


def test_certification_replay_is_deterministic() -> None:
    first = certify_editorial_intelligence(repository_root=Path("."))
    second = certify_editorial_intelligence(repository_root=Path("."))

    assert first.certification_id == second.certification_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_owned_scenario_exposes_editorial_and_viral_scores() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))

    assert 0.0 <= result.owned_scenario["editorial_quality_score"] <= 1.0
    assert 0.0 <= result.owned_scenario["viral_potential_score"] <= 1.0
    assert result.owned_scenario["scene_count"] == 3
    assert result.owned_scenario["timeline_scene_count"] == 3
    assert result.owned_scenario["blockers"] == []
    assert result.reference_scenario["blockers"]


def test_missing_dashboard_artifacts_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(EditorialIntelligenceCertificationError, match="dashboard artifacts"):
        certify_editorial_intelligence(repository_root=tmp_path)


def test_certification_controls_cannot_be_forged() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))
    forged = dataclasses.replace(
        result,
        controls={**result.controls, "auto_publish": True},
    )

    with pytest.raises(EditorialIntelligenceCertificationError, match="capability is enabled"):
        forged.validate()


def test_certification_evidence_detects_tampering() -> None:
    result = certify_editorial_intelligence(repository_root=Path("."))
    forged = dataclasses.replace(result, status="BLOCKED")

    with pytest.raises(EditorialIntelligenceCertificationError, match="not certified"):
        forged.validate()
