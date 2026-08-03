from dataclasses import replace
import hashlib

import pytest

from vision.football_vision_pipeline import (
    VisionAnalysisRequest,
    build_football_vision_report,
    canonical_sha256 as vision_sha256,
)
from vision.motion_ball_tracking import (
    MotionBallTrackingError,
    build_motion_ball_tracking_report,
)


def _vision(*, rights_status="owned"):
    request = VisionAnalysisRequest(
        asset_id="EXT-MOTION-001",
        source_uri="file:///authorized/match.mp4",
        source_sha256=hashlib.sha256(b"authorized-match").hexdigest(),
        duration_seconds=6.0,
        rights_status=rights_status,
        sample_fps=2.0,
    )
    if rights_status == "reference_only":
        return build_football_vision_report(
            request=request,
            provider_name="deterministic-test-provider",
        )

    frame_rows = [
        {
            "frame_number": 0,
            "timestamp_seconds": 0.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-0").hexdigest(),
        },
        {
            "frame_number": 1,
            "timestamp_seconds": 1.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-1").hexdigest(),
        },
        {
            "frame_number": 2,
            "timestamp_seconds": 2.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-2").hexdigest(),
        },
    ]
    frame_ids = []
    for row in frame_rows:
        frame_ids.append(f"VFRAME-{vision_sha256(row)[:20].upper()}")

    scenes = [
        {
            "start_seconds": 0.0,
            "end_seconds": 3.0,
            "representative_frame_id": frame_ids[1],
            "event_ids": [],
            "motion_score": 0.72,
            "visual_quality_score": 0.91,
        }
    ]
    return build_football_vision_report(
        request=request,
        provider_name="deterministic-test-provider",
        frames=frame_rows,
        scenes=scenes,
    )


def _detections(vision, *, confidence=0.95):
    scene_id = vision.scenes[0].scene_id
    points = ((0.10, 0.50), (0.45, 0.40), (0.90, 0.20))
    return [
        {
            "track_id": "BALLTRACK-MAIN",
            "frame_id": frame.frame_id,
            "scene_id": scene_id,
            "timestamp_seconds": frame.timestamp_seconds,
            "center": {"x": point[0], "y": point[1]},
            "radius_normalized": 0.012,
            "confidence": confidence,
            "occluded": False,
        }
        for frame, point in zip(vision.frames, points)
    ]


def _report(*, confidence=0.95):
    vision = _vision()
    report = build_motion_ball_tracking_report(
        vision=vision,
        provider_name="deterministic-ball-provider",
        detections=_detections(vision, confidence=confidence),
        scene_motion=[
            {
                "scene_id": vision.scenes[0].scene_id,
                "ball_track_ids": ["BALLTRACK-MAIN"],
                "camera_motion_score": 0.70,
                "subject_motion_score": 0.82,
            }
        ],
    )
    return vision, report


def test_tracks_ball_path_speed_direction_and_peak_scene():
    vision, report = _report()

    report.validate(vision)
    assert report.tracking_state == "tracked"
    assert report.blockers == ()
    assert report.peak_motion_scene_id == vision.scenes[0].scene_id
    assert len(report.observations) == 3
    assert len(report.tracks) == 1

    track = report.tracks[0]
    assert track.track_id == "BALLTRACK-MAIN"
    assert track.path_length_normalized > 0
    assert track.average_speed_normalized_per_second > 0
    assert track.peak_speed_normalized_per_second >= track.average_speed_normalized_per_second
    assert track.dominant_direction == "diagonal"
    assert track.continuity_score == 1.0

    summary = report.scene_summaries[0]
    assert 0.0 <= summary.composite_motion_score <= 1.0
    assert summary.ball_track_ids == ("BALLTRACK-MAIN",)


def test_low_confidence_requires_human_review():
    vision, report = _report(confidence=0.40)

    report.validate(vision)
    assert report.tracking_state == "review_required"
    assert "BALL_TRACK_REVIEW_REQUIRED" in report.blockers


def test_missing_ball_evidence_is_blocked():
    vision = _vision()
    report = build_motion_ball_tracking_report(
        vision=vision,
        provider_name="deterministic-ball-provider",
    )

    assert report.tracking_state == "blocked"
    assert "BALL_TRACKING_EVIDENCE_MISSING" in report.blockers


def test_reference_only_vision_remains_blocked():
    vision = _vision(rights_status="reference_only")
    report = build_motion_ball_tracking_report(
        vision=vision,
        provider_name="deterministic-ball-provider",
    )

    assert report.tracking_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in report.blockers


def test_invalid_normalized_position_fails_closed():
    vision = _vision()
    detections = _detections(vision)
    detections[0]["center"] = {"x": 1.2, "y": 0.5}

    with pytest.raises(MotionBallTrackingError, match="normalized"):
        build_motion_ball_tracking_report(
            vision=vision,
            provider_name="deterministic-ball-provider",
            detections=detections,
        )


def test_unknown_frame_reference_fails_closed():
    vision = _vision()
    detections = _detections(vision)
    detections[0]["frame_id"] = "VFRAME-UNKNOWN"

    with pytest.raises(MotionBallTrackingError, match="unknown frame"):
        build_motion_ball_tracking_report(
            vision=vision,
            provider_name="deterministic-ball-provider",
            detections=detections,
        )


def test_replay_is_deterministic():
    vision = _vision()
    kwargs = {
        "vision": vision,
        "provider_name": "deterministic-ball-provider",
        "detections": _detections(vision),
        "scene_motion": [
            {
                "scene_id": vision.scenes[0].scene_id,
                "ball_track_ids": ["BALLTRACK-MAIN"],
                "camera_motion_score": 0.70,
                "subject_motion_score": 0.82,
            }
        ],
    }

    first = build_motion_ball_tracking_report(**kwargs)
    second = build_motion_ball_tracking_report(**kwargs)
    assert first.tracking_id == second.tracking_id
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_detected():
    vision, report = _report()
    tampered = replace(report, evidence_sha256="0" * 64)

    with pytest.raises(MotionBallTrackingError, match="evidence mismatch"):
        tampered.validate(vision)


def test_operational_capabilities_cannot_be_enabled():
    vision, report = _report()

    for field in (
        "network_enabled",
        "acquisition_enabled",
        "model_training_enabled",
        "render_enabled",
        "auto_publish",
    ):
        with pytest.raises(MotionBallTrackingError, match="cannot enable"):
            replace(report, **{field: True}).validate(vision)
