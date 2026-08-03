from dataclasses import replace

import pytest

from vision.viral_moment_detection import (
    ViralMomentDetectionError,
    build_viral_moment_ranking,
)


def _reports(*, analyzed=True, low_confidence=False):
    vision = {
        "report_id": "VISION-1234567890ABCDEFGHIJ",
        "pipeline_state": "analyzed" if analyzed else "blocked",
        "scenes": [
            {"scene_id": "VSCENE-HOOK000000000001", "start_seconds": 0.0, "end_seconds": 2.0},
            {"scene_id": "VSCENE-GOAL000000000002", "start_seconds": 2.0, "end_seconds": 5.0},
            {"scene_id": "VSCENE-CELEB00000000003", "start_seconds": 5.0, "end_seconds": 8.0},
        ],
    }
    confidence = 0.45 if low_confidence else 0.94
    event = {
        "detection_state": "detected" if analyzed else "blocked",
        "events": [
            {"event_id": "FBEVENT-SHOT", "scene_id": "VSCENE-HOOK000000000001", "event_type": "shot", "confidence": confidence},
            {"event_id": "FBEVENT-GOAL", "scene_id": "VSCENE-GOAL000000000002", "event_type": "goal", "confidence": confidence},
            {"event_id": "FBEVENT-CELEB", "scene_id": "VSCENE-CELEB00000000003", "event_type": "celebration", "confidence": confidence},
        ],
    }
    emotion = {
        "analysis_state": "analyzed" if analyzed else "blocked",
        "scene_summaries": [
            {"scene_id": "VSCENE-HOOK000000000001", "summary_id": "EMO-HOOK", "emotional_peak_score": 0.78, "crowd_energy_score": 0.45, "confidence": confidence},
            {"scene_id": "VSCENE-GOAL000000000002", "summary_id": "EMO-GOAL", "emotional_peak_score": 0.99, "crowd_energy_score": 0.96, "confidence": confidence},
            {"scene_id": "VSCENE-CELEB00000000003", "summary_id": "EMO-CELEB", "emotional_peak_score": 0.95, "crowd_energy_score": 0.98, "confidence": confidence},
        ],
    }
    motion = {
        "tracking_state": "tracked" if analyzed else "blocked",
        "scene_summaries": [
            {"scene_id": "VSCENE-HOOK000000000001", "summary_id": "MOTION-HOOK", "composite_motion_score": 0.98, "confidence": confidence},
            {"scene_id": "VSCENE-GOAL000000000002", "summary_id": "MOTION-GOAL", "composite_motion_score": 0.88, "confidence": confidence},
            {"scene_id": "VSCENE-CELEB00000000003", "summary_id": "MOTION-CELEB", "composite_motion_score": 0.72, "confidence": confidence},
        ],
    }
    quality = {
        "quality_state": "analyzed" if analyzed else "blocked",
        "scene_scores": [
            {"scene_id": "VSCENE-HOOK000000000001", "score_id": "VIS-HOOK", "visual_quality_score": 0.97, "hook_visual_score": 0.99, "confidence": confidence},
            {"scene_id": "VSCENE-GOAL000000000002", "score_id": "VIS-GOAL", "visual_quality_score": 0.96, "hook_visual_score": 0.84, "confidence": confidence},
            {"scene_id": "VSCENE-CELEB00000000003", "score_id": "VIS-CELEB", "visual_quality_score": 0.91, "hook_visual_score": 0.74, "confidence": confidence},
        ],
    }
    return vision, event, emotion, motion, quality


def test_ranks_viral_moments_and_selects_hook_and_climax():
    report = build_viral_moment_ranking(
        vision_report=_reports()[0],
        event_report=_reports()[1],
        emotion_report=_reports()[2],
        motion_report=_reports()[3],
        quality_report=_reports()[4],
    )
    assert report.ranking_state == "ranked"
    assert len(report.candidates) == 3
    assert report.top_hook_moment_id is not None
    assert report.top_climax_moment_id is not None
    hook = next(item for item in report.candidates if item.moment_id == report.top_hook_moment_id)
    climax = next(item for item in report.candidates if item.moment_id == report.top_climax_moment_id)
    assert hook.scene_id == "VSCENE-HOOK000000000001"
    assert climax.scene_id == "VSCENE-GOAL000000000002"
    assert report.ranked_moment_ids[0] in {item.moment_id for item in report.candidates}


def test_score_components_are_bounded_and_auditable():
    reports = _reports()
    result = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    for item in result.candidates:
        assert item.evidence_ids
        for name in (
            "event_score", "emotion_score", "crowd_score", "motion_score",
            "visual_score", "surprise_score", "hook_score", "climax_score",
            "viral_moment_score", "confidence",
        ):
            assert 0.0 <= getattr(item, name) <= 1.0


def test_low_confidence_requires_review():
    reports = _reports(low_confidence=True)
    result = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4], minimum_confidence=0.70,
    )
    assert result.ranking_state == "review_required"
    assert "VIRAL_MOMENT_REVIEW_REQUIRED" in result.blockers


def test_blocked_upstream_is_fail_closed():
    reports = _reports(analyzed=False)
    result = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    assert result.ranking_state == "blocked"
    assert "VISION_REPORT_NOT_ANALYZED" in result.blockers


def test_replay_is_deterministic():
    reports = _reports()
    first = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    second = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_evidence_tampering_is_rejected():
    reports = _reports()
    result = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    with pytest.raises(ViralMomentDetectionError, match="evidence mismatch"):
        replace(result, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    reports = _reports()
    result = build_viral_moment_ranking(
        vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
        motion_report=reports[3], quality_report=reports[4],
    )
    for field in ("network_enabled", "acquisition_enabled", "model_training_enabled", "render_enabled", "auto_publish"):
        with pytest.raises(ViralMomentDetectionError, match="cannot enable operational capabilities"):
            replace(result, **{field: True}).validate()


def test_invalid_confidence_threshold_is_rejected():
    reports = _reports()
    with pytest.raises(ViralMomentDetectionError, match="minimum_confidence"):
        build_viral_moment_ranking(
            vision_report=reports[0], event_report=reports[1], emotion_report=reports[2],
            motion_report=reports[3], quality_report=reports[4], minimum_confidence=1.1,
        )
