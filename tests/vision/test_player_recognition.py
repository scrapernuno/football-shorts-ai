from __future__ import annotations

import dataclasses
import hashlib

import pytest

from vision.football_vision_pipeline import (
    VisionAnalysisRequest,
    build_football_vision_report,
    canonical_sha256 as vision_sha256,
)
from vision.player_recognition import (
    PlayerRecognitionError,
    build_player_recognition_report,
    canonical_sha256,
)


def _vision(*, rights_status: str = "owned"):
    request = VisionAnalysisRequest(
        asset_id="EXT-PLAYER-001",
        source_uri="file:///authorized/match.mp4",
        source_sha256=hashlib.sha256(b"authorized-match").hexdigest(),
        duration_seconds=8.0,
        rights_status=rights_status,
        sample_fps=2.0,
    )
    frame_material = [
        {"frame_number": 0, "timestamp_seconds": 0.5, "width": 1920, "height": 1080, "frame_sha256": "1" * 64},
        {"frame_number": 1, "timestamp_seconds": 2.5, "width": 1920, "height": 1080, "frame_sha256": "2" * 64},
        {"frame_number": 2, "timestamp_seconds": 5.5, "width": 1920, "height": 1080, "frame_sha256": "3" * 64},
    ]
    frame_ids = [
        f"VFRAME-{vision_sha256({key: value for key, value in item.items()})[:20].upper()}"
        for item in frame_material
    ]
    events = [
        {
            "event_type": "shot",
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "confidence": 0.95,
            "labels": ["player close-up"],
            "evidence_frame_ids": [frame_ids[0]],
        }
    ]
    event_core = {
        "event_type": "shot",
        "start_seconds": 0.0,
        "end_seconds": 2.0,
        "confidence": 0.95,
        "labels": ("player_close-up",),
        "evidence_frame_ids": (frame_ids[0],),
    }
    event_id = f"VEVENT-{vision_sha256(event_core)[:20].upper()}"
    scene_material = [
        {
            "start_seconds": 0.0,
            "end_seconds": 4.0,
            "representative_frame_id": frame_ids[0],
            "event_ids": [event_id],
            "motion_score": 0.8,
            "visual_quality_score": 0.9,
        },
        {
            "start_seconds": 4.0,
            "end_seconds": 8.0,
            "representative_frame_id": frame_ids[2],
            "event_ids": [],
            "motion_score": 0.7,
            "visual_quality_score": 0.88,
        },
    ]
    report = build_football_vision_report(
        request=request,
        provider_name="deterministic-fixture",
        frames=frame_material,
        events=events,
        scenes=scene_material,
    )
    return report


def _detections(vision):
    first_scene, second_scene = vision.scenes
    first_frame, second_frame, third_frame = vision.frames
    return [
        {
            "track_id": "PTRACK-CR7",
            "frame_id": first_frame.frame_id,
            "scene_id": first_scene.scene_id,
            "timestamp_seconds": 0.5,
            "role": "player",
            "detection_confidence": 0.99,
            "identity_label": "Cristiano Ronaldo",
            "identity_confidence": 0.96,
            "team_label": "Portugal",
            "shirt_number": 7,
            "bounding_box": {"x": 0.30, "y": 0.10, "width": 0.25, "height": 0.80},
            "evidence_labels": ["face", "shirt number", "team kit"],
        },
        {
            "track_id": "PTRACK-CR7",
            "frame_id": second_frame.frame_id,
            "scene_id": first_scene.scene_id,
            "timestamp_seconds": 2.5,
            "role": "player",
            "detection_confidence": 0.98,
            "identity_label": "Cristiano Ronaldo",
            "identity_confidence": 0.94,
            "team_label": "Portugal",
            "shirt_number": 7,
            "bounding_box": {"x": 0.32, "y": 0.11, "width": 0.24, "height": 0.79},
            "evidence_labels": ["face", "shirt number"],
        },
        {
            "track_id": "PTRACK-REF-1",
            "frame_id": third_frame.frame_id,
            "scene_id": second_scene.scene_id,
            "timestamp_seconds": 5.5,
            "role": "referee",
            "detection_confidence": 0.91,
            "identity_label": None,
            "identity_confidence": 0.0,
            "team_label": None,
            "shirt_number": None,
            "bounding_box": {"x": 0.70, "y": 0.15, "width": 0.15, "height": 0.75},
            "evidence_labels": ["referee kit"],
        },
    ]


def test_builds_recognized_tracks_from_authorized_vision_evidence() -> None:
    vision = _vision()
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=_detections(vision),
    )

    assert report.recognition_state == "recognized"
    assert report.blockers == ()
    assert len(report.observations) == 3
    assert len(report.tracks) == 2
    assert report.recognized_identity_labels == ("Cristiano Ronaldo",)
    cr7 = next(item for item in report.tracks if item.track_id == "PTRACK-CR7")
    assert cr7.role == "player"
    assert cr7.team_label == "Portugal"
    assert cr7.identity_confidence == 0.96
    assert len(cr7.observation_ids) == 2
    report.validate(vision)


def test_anonymous_role_detection_is_valid_without_identity_confidence() -> None:
    vision = _vision()
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=[_detections(vision)[2]],
    )

    assert report.recognition_state == "recognized"
    assert report.recognized_identity_labels == ()
    assert report.tracks[0].identity_label is None
    assert report.tracks[0].identity_confidence == 0.0


def test_low_confidence_identity_requires_human_review() -> None:
    vision = _vision()
    detections = _detections(vision)
    detections[0] = {**detections[0], "identity_confidence": 0.60}
    detections[1] = {**detections[1], "identity_confidence": 0.62}
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=detections,
        minimum_identity_confidence=0.75,
    )

    assert report.recognition_state == "review_required"
    assert report.blockers == ("IDENTITY_REVIEW_REQUIRED",)


def test_reference_only_vision_remains_blocked() -> None:
    vision = _vision(rights_status="reference_only")
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=(),
    )

    assert report.recognition_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in report.blockers
    assert report.observations == ()
    assert report.tracks == ()


def test_missing_player_evidence_is_fail_closed() -> None:
    vision = _vision()
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=(),
    )

    assert report.recognition_state == "review_required"
    assert report.blockers == ("PLAYER_EVIDENCE_MISSING",)


def test_rejects_invalid_bounding_box_and_unknown_references() -> None:
    vision = _vision()
    invalid_box = _detections(vision)[0]
    invalid_box = {**invalid_box, "bounding_box": {"x": 0.9, "y": 0.1, "width": 0.2, "height": 0.8}}
    with pytest.raises(PlayerRecognitionError, match="exceeds frame bounds"):
        build_player_recognition_report(
            vision=vision,
            provider_name="fixture-player-provider",
            detections=[invalid_box],
        )

    unknown = {**_detections(vision)[0], "frame_id": "VFRAME-UNKNOWN"}
    with pytest.raises(PlayerRecognitionError, match="unknown vision evidence"):
        build_player_recognition_report(
            vision=vision,
            provider_name="fixture-player-provider",
            detections=[unknown],
        )


def test_replay_and_identity_are_deterministic() -> None:
    vision = _vision()
    first = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=_detections(vision),
    )
    second = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=_detections(vision),
    )

    assert first.recognition_id == second.recognition_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_detects_evidence_tampering_and_forbidden_capabilities() -> None:
    vision = _vision()
    report = build_player_recognition_report(
        vision=vision,
        provider_name="fixture-player-provider",
        detections=_detections(vision),
    )

    forged_hash = dataclasses.replace(report, evidence_sha256="0" * 64)
    with pytest.raises(PlayerRecognitionError, match="evidence mismatch"):
        forged_hash.validate(vision)

    forged_capability = dataclasses.replace(report, biometric_enrolment_enabled=True)
    with pytest.raises(PlayerRecognitionError, match="operational capabilities"):
        forged_capability.validate(vision)
