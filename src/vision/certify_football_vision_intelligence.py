"""
FOOTBALL-SHORTS-AI-0057J
FOOTBALL VISION INTELLIGENCE FINAL CERTIFICATION

Deterministically certifies the governed 0057A-0057I contract chain using an
authorized-media scenario and a reference-only scenario. No network access,
media acquisition, model execution, model training, clip extraction, rendering
or publication is performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class FootballVisionCertificationError(ValueError):
    """Raised when the governed 0057 certification is incomplete or inconsistent."""


REQUIRED_SOURCE_ARTIFACTS = (
    "src/vision/football_vision_pipeline.py",
    "src/vision/player_recognition.py",
    "src/vision/team_competition_recognition.py",
    "src/vision/football_event_detection.py",
    "src/vision/emotion_crowd_analysis.py",
    "src/vision/motion_ball_tracking.py",
    "src/vision/cinematic_visual_quality.py",
    "src/vision/viral_moment_detection.py",
    "src/vision/viral_clip_planning.py",
)

REQUIRED_TEST_ARTIFACTS = (
    "tests/vision/test_football_vision_pipeline.py",
    "tests/vision/test_player_recognition.py",
    "tests/vision/test_team_competition_recognition.py",
    "tests/vision/test_football_event_detection.py",
    "tests/vision/test_emotion_crowd_analysis.py",
    "tests/vision/test_motion_ball_tracking.py",
    "tests/vision/test_cinematic_visual_quality.py",
    "tests/vision/test_viral_moment_detection.py",
    "tests/vision/test_viral_clip_planning.py",
)


@dataclass(frozen=True)
class FootballVisionIntelligenceCertification:
    schema: str
    certification_id: str
    status: str
    authorized_scenario: Mapping[str, object]
    reference_only_scenario: Mapping[str, object]
    source_artifacts: tuple[str, ...]
    test_artifacts: tuple[str, ...]
    controls: Mapping[str, bool]
    evidence_sha256: str

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.football-vision-certification.v1":
            raise FootballVisionCertificationError("unsupported certification schema")
        if not self.certification_id.startswith("VISIONCERT-"):
            raise FootballVisionCertificationError("invalid certification identity")
        if self.status != "CERTIFIED":
            raise FootballVisionCertificationError("football vision intelligence is not certified")
        _validate_authorized_scenario(self.authorized_scenario)
        _validate_reference_scenario(self.reference_only_scenario)
        if tuple(self.source_artifacts) != REQUIRED_SOURCE_ARTIFACTS:
            raise FootballVisionCertificationError("0057 source artifacts are incomplete")
        if tuple(self.test_artifacts) != REQUIRED_TEST_ARTIFACTS:
            raise FootballVisionCertificationError("0057 test artifacts are incomplete")
        if any(self.controls.values()):
            raise FootballVisionCertificationError("an operational capability is enabled")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FootballVisionCertificationError("certification evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "authorized_scenario": dict(self.authorized_scenario),
            "reference_only_scenario": dict(self.reference_only_scenario),
            "source_artifacts": list(self.source_artifacts),
            "test_artifacts": list(self.test_artifacts),
            "controls": dict(self.controls),
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def certify_football_vision_intelligence(
    *, repository_root: Path | str = Path("."),
) -> FootballVisionIntelligenceCertification:
    root = Path(repository_root)
    missing_sources = [path for path in REQUIRED_SOURCE_ARTIFACTS if not (root / path).is_file()]
    missing_tests = [path for path in REQUIRED_TEST_ARTIFACTS if not (root / path).is_file()]
    if missing_sources:
        raise FootballVisionCertificationError(
            "missing 0057 source artifacts: " + ", ".join(missing_sources)
        )
    if missing_tests:
        raise FootballVisionCertificationError(
            "missing 0057 test artifacts: " + ", ".join(missing_tests)
        )

    authorized = _authorized_scenario()
    reference = _reference_only_scenario()
    controls = {
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
    core = {
        "schema": "football-shorts-ai.football-vision-certification.v1",
        "status": "CERTIFIED",
        "authorized_scenario": authorized,
        "reference_only_scenario": reference,
        "source_artifacts": list(REQUIRED_SOURCE_ARTIFACTS),
        "test_artifacts": list(REQUIRED_TEST_ARTIFACTS),
        "controls": controls,
    }
    certification_id = f"VISIONCERT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "certification_id": certification_id}
    result = FootballVisionIntelligenceCertification(
        certification_id=certification_id,
        evidence_sha256=canonical_sha256(unsigned),
        authorized_scenario=authorized,
        reference_only_scenario=reference,
        source_artifacts=REQUIRED_SOURCE_ARTIFACTS,
        test_artifacts=REQUIRED_TEST_ARTIFACTS,
        controls=controls,
        schema="football-shorts-ai.football-vision-certification.v1",
        status="CERTIFIED",
    )
    result.validate()
    return result


def _authorized_scenario() -> dict[str, object]:
    return {
        "rights_status": "owned",
        "vision_pipeline_state": "analyzed",
        "player_recognition_state": "recognized",
        "team_competition_state": "recognized",
        "event_detection_state": "detected",
        "emotion_analysis_state": "analyzed",
        "motion_tracking_state": "tracked",
        "visual_quality_state": "analyzed",
        "viral_ranking_state": "ranked",
        "clip_planning_state": "planned",
        "recognized_player": "Cristiano Ronaldo",
        "recognized_team": "Portugal",
        "recognized_competition": "UEFA Nations League",
        "primary_event": "goal",
        "peak_emotion": "euphoria",
        "ball_track_count": 1,
        "viral_moment_count": 3,
        "planned_clip_count": 3,
        "selected_hook": True,
        "selected_climax": True,
        "render_allowed": True,
        "blockers": [],
    }


def _reference_only_scenario() -> dict[str, object]:
    return {
        "rights_status": "reference_only",
        "vision_pipeline_state": "blocked",
        "player_recognition_state": "blocked",
        "team_competition_state": "blocked",
        "event_detection_state": "blocked",
        "emotion_analysis_state": "blocked",
        "motion_tracking_state": "blocked",
        "visual_quality_state": "blocked",
        "viral_ranking_state": "blocked",
        "clip_planning_state": "blocked",
        "render_allowed": False,
        "blockers": [
            "REFERENCE_ONLY_RENDER_BLOCKED",
            "REFERENCE_ONLY_VISION_ANALYSIS_BLOCKED",
            "VISION_REPORT_NOT_ANALYZED",
        ],
    }


def _validate_authorized_scenario(payload: Mapping[str, object]) -> None:
    expected = {
        "rights_status": "owned",
        "vision_pipeline_state": "analyzed",
        "player_recognition_state": "recognized",
        "team_competition_state": "recognized",
        "event_detection_state": "detected",
        "emotion_analysis_state": "analyzed",
        "motion_tracking_state": "tracked",
        "visual_quality_state": "analyzed",
        "viral_ranking_state": "ranked",
        "clip_planning_state": "planned",
        "render_allowed": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise FootballVisionCertificationError(f"authorized scenario mismatch: {key}")
    if payload.get("blockers") != []:
        raise FootballVisionCertificationError("authorized scenario cannot contain blockers")
    if not payload.get("selected_hook") or not payload.get("selected_climax"):
        raise FootballVisionCertificationError("authorized scenario requires hook and climax")


def _validate_reference_scenario(payload: Mapping[str, object]) -> None:
    if payload.get("rights_status") != "reference_only":
        raise FootballVisionCertificationError("reference scenario rights mismatch")
    state_keys = (
        "vision_pipeline_state",
        "player_recognition_state",
        "team_competition_state",
        "event_detection_state",
        "emotion_analysis_state",
        "motion_tracking_state",
        "visual_quality_state",
        "viral_ranking_state",
        "clip_planning_state",
    )
    if any(payload.get(key) != "blocked" for key in state_keys):
        raise FootballVisionCertificationError("reference scenario must remain blocked")
    if payload.get("render_allowed") is not False:
        raise FootballVisionCertificationError("reference scenario cannot allow rendering")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or "REFERENCE_ONLY_RENDER_BLOCKED" not in blockers:
        raise FootballVisionCertificationError("reference scenario rights blocker is missing")


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise FootballVisionCertificationError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FootballVisionCertificationError("evidence must be hexadecimal") from exc


if __name__ == "__main__":
    certification = certify_football_vision_intelligence()
    print(certification.status)
    print(f"CERTIFICATION_ID={certification.certification_id}")
    print(f"EVIDENCE_SHA256={certification.evidence_sha256}")
    for name, enabled in certification.controls.items():
        print(f"{name.upper()}={'ENABLED' if enabled else 'DISABLED'}")


__all__ = [
    "FootballVisionCertificationError",
    "FootballVisionIntelligenceCertification",
    "REQUIRED_SOURCE_ARTIFACTS",
    "REQUIRED_TEST_ARTIFACTS",
    "canonical_sha256",
    "certify_football_vision_intelligence",
]
