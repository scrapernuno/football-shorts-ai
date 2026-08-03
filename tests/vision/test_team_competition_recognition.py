from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from vision.football_vision_pipeline import VisionAnalysisRequest, build_football_vision_report
from vision.team_competition_recognition import (
    TeamCompetitionRecognitionError,
    build_team_competition_recognition_report,
)


def _vision(*, rights_status: str = "owned"):
    request = VisionAnalysisRequest(
        asset_id="EXT-0057C-TEST",
        source_uri="file:///authorized-match.mp4",
        source_sha256=hashlib.sha256(b"authorized-match").hexdigest(),
        duration_seconds=8.0,
        rights_status=rights_status,
        sample_fps=1.0,
    )
    frames = [
        {"frame_number": 0, "timestamp_seconds": 0.0, "width": 1920, "height": 1080, "frame_sha256": hashlib.sha256(b"f0").hexdigest()},
        {"frame_number": 1, "timestamp_seconds": 4.0, "width": 1920, "height": 1080, "frame_sha256": hashlib.sha256(b"f1").hexdigest()},
    ]
    provisional = build_football_vision_report(
        request=request,
        provider_name="fixture-provider",
        frames=frames if rights_status != "reference_only" else (),
        scenes=(),
    ) if rights_status == "reference_only" else None
    if provisional is not None:
        return provisional
    first_frame = "VFRAME-" + hashlib.sha256(
        b'{"frame_number":0,"frame_sha256":"' + frames[0]["frame_sha256"].encode() + b'","height":1080,"timestamp_seconds":0.0,"width":1920}'
    ).hexdigest()[:20].upper()
    second_frame = "VFRAME-" + hashlib.sha256(
        b'{"frame_number":1,"frame_sha256":"' + frames[1]["frame_sha256"].encode() + b'","height":1080,"timestamp_seconds":4.0,"width":1920}'
    ).hexdigest()[:20].upper()
    scenes = [
        {"start_seconds": 0.0, "end_seconds": 4.0, "representative_frame_id": first_frame, "event_ids": [], "motion_score": 0.6, "visual_quality_score": 0.9},
        {"start_seconds": 4.0, "end_seconds": 8.0, "representative_frame_id": second_frame, "event_ids": [], "motion_score": 0.7, "visual_quality_score": 0.92},
    ]
    return build_football_vision_report(request=request, provider_name="fixture-provider", frames=frames, scenes=scenes)


def _signals(vision):
    return [
        {
            "signal_type": "kit",
            "scene_id": vision.scenes[0].scene_id,
            "frame_id": vision.frames[0].frame_id,
            "entity_type": "national_team",
            "label": "Portugal",
            "confidence": 0.94,
            "evidence_labels": ["red_kit", "shirt_7"],
        },
        {
            "signal_type": "scoreboard",
            "scene_id": vision.scenes[1].scene_id,
            "frame_id": vision.frames[1].frame_id,
            "entity_type": "competition",
            "label": "UEFA Nations League",
            "confidence": 0.97,
            "evidence_labels": ["broadcast_graphic", "scoreboard_text"],
        },
    ]


def test_recognizes_team_and_competition() -> None:
    vision = _vision()
    report = build_team_competition_recognition_report(
        vision=vision,
        provider_name="fixture-provider",
        signals=_signals(vision),
    )
    assert report.recognition_state == "recognized"
    assert report.team_labels == ("Portugal",)
    assert report.competition_labels == ("UEFA Nations League",)
    report.validate(vision)


def test_low_confidence_requires_review() -> None:
    vision = _vision()
    signals = _signals(vision)
    signals[0]["confidence"] = 0.4
    report = build_team_competition_recognition_report(
        vision=vision,
        provider_name="fixture-provider",
        signals=signals,
        minimum_confidence=0.75,
    )
    assert report.recognition_state == "review_required"
    assert "ENTITY_REVIEW_REQUIRED" in report.blockers


def test_missing_competition_is_fail_closed() -> None:
    vision = _vision()
    report = build_team_competition_recognition_report(
        vision=vision,
        provider_name="fixture-provider",
        signals=[_signals(vision)[0]],
    )
    assert report.recognition_state == "review_required"
    assert "COMPETITION_IDENTITY_MISSING" in report.blockers


def test_reference_only_remains_blocked() -> None:
    vision = _vision(rights_status="reference_only")
    report = build_team_competition_recognition_report(
        vision=vision,
        provider_name="fixture-provider",
        signals=(),
    )
    assert report.recognition_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in report.blockers


def test_unknown_scene_reference_is_rejected() -> None:
    vision = _vision()
    signals = _signals(vision)
    signals[0]["scene_id"] = "VSCENE-UNKNOWN"
    with pytest.raises(TeamCompetitionRecognitionError):
        build_team_competition_recognition_report(
            vision=vision,
            provider_name="fixture-provider",
            signals=signals,
        )


def test_replay_is_deterministic() -> None:
    vision = _vision()
    first = build_team_competition_recognition_report(vision=vision, provider_name="fixture-provider", signals=_signals(vision))
    second = build_team_competition_recognition_report(vision=vision, provider_name="fixture-provider", signals=_signals(vision))
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_rejected() -> None:
    vision = _vision()
    report = build_team_competition_recognition_report(vision=vision, provider_name="fixture-provider", signals=_signals(vision))
    tampered = replace(report, evidence_sha256="0" * 64)
    with pytest.raises(TeamCompetitionRecognitionError):
        tampered.validate(vision)


def test_operational_capabilities_cannot_be_enabled() -> None:
    vision = _vision()
    report = build_team_competition_recognition_report(vision=vision, provider_name="fixture-provider", signals=_signals(vision))
    with pytest.raises(TeamCompetitionRecognitionError):
        replace(report, auto_publish=True).validate(vision)
