from dataclasses import replace
import hashlib

import pytest

from vision.cinematic_visual_quality import (
    CinematicVisualQualityError,
    build_cinematic_visual_quality_report,
)
from vision.football_vision_pipeline import VisionAnalysisRequest, build_football_vision_report


def _vision(rights_status="owned"):
    request = VisionAnalysisRequest(
        asset_id="EXT-VISQUAL-001",
        source_uri="file:///tmp/owned.mp4",
        source_sha256=hashlib.sha256(b"owned").hexdigest(),
        duration_seconds=8.0,
        rights_status=rights_status,
        sample_fps=2.0,
    )
    if rights_status == "reference_only":
        return build_football_vision_report(request=request, provider_name="fixture")
    frames = [
        {"frame_number": 0, "timestamp_seconds": 1.0, "width": 1920, "height": 1080, "frame_sha256": hashlib.sha256(b"f1").hexdigest()},
        {"frame_number": 1, "timestamp_seconds": 5.0, "width": 1920, "height": 1080, "frame_sha256": hashlib.sha256(b"f2").hexdigest()},
    ]
    temp = build_football_vision_report(request=request, provider_name="fixture", frames=frames, scenes=[
        {"start_seconds": 0.0, "end_seconds": 4.0, "representative_frame_id": "VFRAME-PLACEHOLDER", "event_ids": [], "motion_score": 0.8, "visual_quality_score": 0.9}
    ]) if False else None
    frame_ids = []
    from vision.football_vision_pipeline import canonical_sha256
    for item in frames:
        core = {
            "frame_number": int(item["frame_number"]),
            "timestamp_seconds": float(item["timestamp_seconds"]),
            "width": int(item["width"]),
            "height": int(item["height"]),
            "frame_sha256": str(item["frame_sha256"]),
        }
        frame_ids.append(f"VFRAME-{canonical_sha256(core)[:20].upper()}")
    scenes = [
        {"start_seconds": 0.0, "end_seconds": 4.0, "representative_frame_id": frame_ids[0], "event_ids": [], "motion_score": 0.8, "visual_quality_score": 0.9},
        {"start_seconds": 4.0, "end_seconds": 8.0, "representative_frame_id": frame_ids[1], "event_ids": [], "motion_score": 0.6, "visual_quality_score": 0.8},
    ]
    return build_football_vision_report(request=request, provider_name="fixture", frames=frames, scenes=scenes)


def _measurements(vision, low_confidence=False):
    return [
        {
            "scene_id": vision.scenes[0].scene_id,
            "sharpness_score": 0.96,
            "stability_score": 0.90,
            "exposure_score": 0.92,
            "contrast_score": 0.88,
            "framing_score": 0.95,
            "scoreboard_legibility_score": 0.70,
            "subject_visibility_score": 0.97,
            "ball_visibility_score": 0.94,
            "vertical_crop_score": 0.93,
            "confidence": 0.60 if low_confidence else 0.95,
            "evidence_frame_ids": [vision.frames[0].frame_id],
        },
        {
            "scene_id": vision.scenes[1].scene_id,
            "sharpness_score": 0.72,
            "stability_score": 0.70,
            "exposure_score": 0.75,
            "contrast_score": 0.68,
            "framing_score": 0.74,
            "scoreboard_legibility_score": 0.80,
            "subject_visibility_score": 0.78,
            "ball_visibility_score": 0.60,
            "vertical_crop_score": 0.69,
            "confidence": 0.90,
            "evidence_frame_ids": [vision.frames[1].frame_id],
        },
    ]


def test_builds_analyzed_visual_quality_report():
    vision = _vision()
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision))
    assert report.quality_state == "analyzed"
    assert report.best_visual_scene_id == vision.scenes[0].scene_id
    assert report.best_hook_visual_scene_id == vision.scenes[0].scene_id
    assert report.average_visual_quality_score > 0.7
    report.validate(vision)


def test_low_confidence_requires_review():
    vision = _vision()
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision, True))
    assert report.quality_state == "review_required"
    assert "VISUAL_QUALITY_REVIEW_REQUIRED" in report.blockers


def test_missing_measurements_are_blocked():
    vision = _vision()
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture")
    assert report.quality_state == "blocked"
    assert "VISUAL_QUALITY_EVIDENCE_MISSING" in report.blockers


def test_reference_only_stays_blocked():
    vision = _vision("reference_only")
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture")
    assert report.quality_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in report.blockers


def test_invalid_score_fails_closed():
    vision = _vision()
    values = _measurements(vision)
    values[0]["sharpness_score"] = 1.2
    with pytest.raises(CinematicVisualQualityError):
        build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=values)


def test_unknown_frame_fails_closed():
    vision = _vision()
    values = _measurements(vision)
    values[0]["evidence_frame_ids"] = ["VFRAME-UNKNOWN"]
    with pytest.raises(CinematicVisualQualityError):
        build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=values)


def test_replay_is_deterministic():
    vision = _vision()
    first = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision))
    second = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision))
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampered_evidence_is_rejected():
    vision = _vision()
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision))
    with pytest.raises(CinematicVisualQualityError):
        replace(report, evidence_sha256="0" * 64).validate(vision)


def test_operational_capabilities_cannot_be_enabled():
    vision = _vision()
    report = build_cinematic_visual_quality_report(vision=vision, provider_name="fixture", measurements=_measurements(vision))
    with pytest.raises(CinematicVisualQualityError):
        replace(report, render_enabled=True).validate(vision)
