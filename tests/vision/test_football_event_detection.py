from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from vision.football_event_detection import (
    FootballEventDetectionError,
    FootballEventDetectionReport,
    build_football_event_detection_report,
)
from vision.football_vision_pipeline import (
    VisionAnalysisRequest,
    build_football_vision_report,
    canonical_sha256 as vision_sha256,
)


def _vision(rights_status: str = "owned"):
    request = VisionAnalysisRequest(
        asset_id="EXT-0057D-CERT",
        source_uri="file:///tmp/owned-match.mp4",
        source_sha256=hashlib.sha256(b"owned-match").hexdigest(),
        duration_seconds=12.0,
        rights_status=rights_status,
        sample_fps=2.0,
    )
    if rights_status == "reference_only":
        return build_football_vision_report(request=request, provider_name="fixture")

    frame_core = {
        "frame_number": 0,
        "timestamp_seconds": 1.0,
        "width": 1920,
        "height": 1080,
        "frame_sha256": hashlib.sha256(b"frame-0").hexdigest(),
    }
    frame_id = f"VFRAME-{vision_sha256(frame_core)[:20].upper()}"
    scene_core = {
        "start_seconds": 0.0,
        "end_seconds": 6.0,
        "representative_frame_id": frame_id,
        "event_ids": (),
        "motion_score": 0.92,
        "visual_quality_score": 0.95,
    }
    return build_football_vision_report(
        request=request,
        provider_name="fixture",
        frames=(frame_core,),
        scenes=(scene_core,),
    )


def _detection(vision, confidence: float = 0.96):
    return {
        "event_type": "goal",
        "start_seconds": 2.0,
        "end_seconds": 3.5,
        "confidence": confidence,
        "scene_id": vision.scenes[0].scene_id,
        "evidence_frame_ids": [vision.frames[0].frame_id],
        "actor_track_ids": ["PTRACK-CR7"],
        "team_labels": ["Portugal"],
        "competition_label": "UEFA Nations League",
        "evidence_labels": ["ball_crossed_line", "net_reaction", "score_change"],
    }


def test_detects_governed_goal_event() -> None:
    vision = _vision()
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=(_detection(vision),),
    )
    assert report.detection_state == "detected"
    assert report.detected_event_types == ("goal",)
    assert report.events[0].actor_track_ids == ("PTRACK-CR7",)
    assert report.events[0].team_labels == ("Portugal",)
    assert report.events[0].competition_label == "UEFA Nations League"
    report.validate(vision)


def test_low_confidence_requires_human_review() -> None:
    vision = _vision()
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=(_detection(vision, confidence=0.49),),
        minimum_confidence=0.70,
    )
    assert report.detection_state == "review_required"
    assert "EVENT_REVIEW_REQUIRED" in report.blockers
    assert report.events[0].review_required is True


def test_missing_event_evidence_is_blocked() -> None:
    vision = _vision()
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
    )
    assert report.detection_state == "blocked"
    assert "FOOTBALL_EVENT_EVIDENCE_MISSING" in report.blockers


def test_reference_only_vision_remains_blocked() -> None:
    vision = _vision("reference_only")
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
    )
    assert report.detection_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in report.blockers


def test_unknown_scene_or_frame_fails_closed() -> None:
    vision = _vision()
    detection = _detection(vision)
    detection["scene_id"] = "VSCENE-UNKNOWN"
    with pytest.raises(FootballEventDetectionError):
        build_football_event_detection_report(
            vision=vision,
            provider_name="fixture-event-detector",
            detections=(detection,),
        )


def test_invalid_temporal_range_and_confidence_fail() -> None:
    vision = _vision()
    for field, value in (("end_seconds", 13.0), ("confidence", 1.1)):
        detection = _detection(vision)
        detection[field] = value
        with pytest.raises(FootballEventDetectionError):
            build_football_event_detection_report(
                vision=vision,
                provider_name="fixture-event-detector",
                detections=(detection,),
            )


def test_replay_is_deterministic() -> None:
    vision = _vision()
    first = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=(_detection(vision),),
    )
    second = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=(_detection(vision),),
    )
    assert first.to_dict() == second.to_dict()
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampered_evidence_and_operational_capabilities_fail() -> None:
    vision = _vision()
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=(_detection(vision),),
    )
    with pytest.raises(FootballEventDetectionError):
        replace(report, evidence_sha256="0" * 64).validate(vision)
    for field in ("network_enabled", "acquisition_enabled", "model_training_enabled", "render_enabled", "auto_publish"):
        with pytest.raises(FootballEventDetectionError):
            replace(report, **{field: True}).validate(vision)


def test_supported_event_taxonomy_is_present() -> None:
    vision = _vision()
    detections = []
    for index, event_type in enumerate(("shot", "save", "yellow_card", "var", "celebration")):
        item = _detection(vision)
        item.update({
            "event_type": event_type,
            "start_seconds": 0.2 + index,
            "end_seconds": 0.7 + index,
            "actor_track_ids": [],
        })
        detections.append(item)
    report = build_football_event_detection_report(
        vision=vision,
        provider_name="fixture-event-detector",
        detections=detections,
    )
    assert report.detected_event_types == ("celebration", "save", "shot", "var", "yellow_card")
