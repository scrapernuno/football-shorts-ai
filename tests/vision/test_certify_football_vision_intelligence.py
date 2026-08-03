from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from vision.certify_football_vision_intelligence import (
    FootballVisionCertificationError,
    REQUIRED_SOURCE_ARTIFACTS,
    REQUIRED_TEST_ARTIFACTS,
    certify_football_vision_intelligence,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_0057j_certifies_complete_authorized_and_reference_only_chain() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)

    assert result.status == "CERTIFIED"
    assert result.certification_id.startswith("VISIONCERT-")
    assert len(result.evidence_sha256) == 64

    owned = result.authorized_scenario
    assert owned["rights_status"] == "owned"
    assert owned["vision_pipeline_state"] == "analyzed"
    assert owned["player_recognition_state"] == "recognized"
    assert owned["team_competition_state"] == "recognized"
    assert owned["event_detection_state"] == "detected"
    assert owned["emotion_analysis_state"] == "analyzed"
    assert owned["motion_tracking_state"] == "tracked"
    assert owned["visual_quality_state"] == "analyzed"
    assert owned["viral_ranking_state"] == "ranked"
    assert owned["clip_planning_state"] == "planned"
    assert owned["render_allowed"] is True
    assert owned["selected_hook"] is True
    assert owned["selected_climax"] is True
    assert owned["blockers"] == []

    reference = result.reference_only_scenario
    assert reference["rights_status"] == "reference_only"
    assert reference["render_allowed"] is False
    assert reference["clip_planning_state"] == "blocked"
    assert "REFERENCE_ONLY_RENDER_BLOCKED" in reference["blockers"]


def test_0057j_certifies_exact_source_and_test_inventory() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)

    assert result.source_artifacts == REQUIRED_SOURCE_ARTIFACTS
    assert result.test_artifacts == REQUIRED_TEST_ARTIFACTS
    assert len(result.source_artifacts) == 9
    assert len(result.test_artifacts) == 9
    assert all((REPOSITORY_ROOT / path).is_file() for path in result.source_artifacts)
    assert all((REPOSITORY_ROOT / path).is_file() for path in result.test_artifacts)


def test_0057j_replay_is_deterministic() -> None:
    first = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)
    second = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)

    assert first.to_dict() == second.to_dict()
    assert first.certification_id == second.certification_id
    assert first.evidence_sha256 == second.evidence_sha256


def test_0057j_all_operational_capabilities_remain_disabled() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)

    assert result.controls
    assert not any(result.controls.values())
    assert result.controls == {
        "network_enabled": False,
        "acquisition_enabled": False,
        "external_model_execution_enabled": False,
        "biometric_enrolment_enabled": False,
        "model_training_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }


def test_0057j_fails_closed_when_source_artifact_is_missing(tmp_path: Path) -> None:
    for path in REQUIRED_SOURCE_ARTIFACTS[1:]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")
    for path in REQUIRED_TEST_ARTIFACTS:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")

    with pytest.raises(FootballVisionCertificationError, match="missing 0057 source artifacts"):
        certify_football_vision_intelligence(repository_root=tmp_path)


def test_0057j_fails_closed_when_test_artifact_is_missing(tmp_path: Path) -> None:
    for path in REQUIRED_SOURCE_ARTIFACTS:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")
    for path in REQUIRED_TEST_ARTIFACTS[1:]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")

    with pytest.raises(FootballVisionCertificationError, match="missing 0057 test artifacts"):
        certify_football_vision_intelligence(repository_root=tmp_path)


def test_0057j_rejects_evidence_tampering() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)
    tampered = replace(result, evidence_sha256="0" * 64)

    with pytest.raises(FootballVisionCertificationError, match="evidence mismatch"):
        tampered.validate()


def test_0057j_rejects_enabled_operational_capability() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)
    controls = dict(result.controls)
    controls["render_enabled"] = True
    tampered = replace(result, controls=controls)

    with pytest.raises(FootballVisionCertificationError, match="operational capability"):
        tampered.validate()


def test_0057j_rejects_reference_only_render_permission() -> None:
    result = certify_football_vision_intelligence(repository_root=REPOSITORY_ROOT)
    reference = dict(result.reference_only_scenario)
    reference["render_allowed"] = True
    tampered = replace(result, reference_only_scenario=reference)

    with pytest.raises(FootballVisionCertificationError, match="cannot allow rendering"):
        tampered.validate()
