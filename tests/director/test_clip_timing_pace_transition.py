from dataclasses import replace

import pytest

from director.clip_timing_pace_transition import (
    ClipTimingOptimizationError,
    build_clip_timing_optimization,
)


def _alignment(*, state="aligned", confidence=0.92, render_allowed=True):
    return {
        "alignment_id": "DIRALIGN-1234567890ABCDEF1234",
        "alignment_state": state,
        "beats": [
            {
                "beat_id": "DIRBEAT-00000000000000000001",
                "segment_id": "DIRSEG-00000000000000000001",
                "clip_id": "VIRALCLIP-000000000000000001",
                "narrative_role": "hook",
                "clip_start_seconds": 1.0,
                "clip_end_seconds": 4.0,
                "alignment_score": confidence,
                "confidence": confidence,
                "render_allowed": render_allowed,
            },
            {
                "beat_id": "DIRBEAT-00000000000000000002",
                "segment_id": "DIRSEG-00000000000000000002",
                "clip_id": "VIRALCLIP-000000000000000002",
                "narrative_role": "development",
                "clip_start_seconds": 5.0,
                "clip_end_seconds": 10.0,
                "alignment_score": confidence,
                "confidence": confidence,
                "render_allowed": render_allowed,
            },
            {
                "beat_id": "DIRBEAT-00000000000000000003",
                "segment_id": "DIRSEG-00000000000000000003",
                "clip_id": "VIRALCLIP-000000000000000003",
                "narrative_role": "climax",
                "clip_start_seconds": 11.0,
                "clip_end_seconds": 16.0,
                "alignment_score": confidence,
                "confidence": confidence,
                "render_allowed": render_allowed,
            },
        ],
    }


def test_fast_strategy_builds_continuous_optimized_timeline():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="fast",
    )

    report.validate()
    assert report.optimization_state == "optimized"
    assert report.blockers == ()
    assert report.strategy == "fast"
    assert len(report.timings) == 3
    assert report.timings[0].timeline_start_seconds == 0.0
    assert report.timings[1].timeline_start_seconds == report.timings[0].timeline_end_seconds
    assert report.timings[2].timeline_start_seconds == report.timings[1].timeline_end_seconds
    assert report.total_duration_seconds == report.timings[-1].timeline_end_seconds
    assert report.timings[0].playback_rate == 1.2
    assert report.timings[0].transition_in == "none"
    assert report.timings[-1].transition_out == "fade"
    assert 0.0 <= report.average_pace_score <= 1.0
    assert 0.0 <= report.predicted_retention_score <= 1.0


def test_emotional_strategy_uses_slower_climax_and_soft_transitions():
    alignment = _alignment()
    alignment["beats"][2]["narrative_role"] = "reaction"
    report = build_clip_timing_optimization(
        alignment_report=alignment,
        strategy="emotional",
    )

    reaction = report.timings[-1]
    assert reaction.playback_rate == 0.9
    assert reaction.transition_in == "crossfade"
    assert reaction.transition_out == "fade"
    assert reaction.transition_duration_seconds == 0.35


def test_informative_strategy_uses_match_cut_for_development():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="informative",
    )

    assert report.timings[1].transition_in == "match_cut"
    assert report.timings[1].playback_rate == 1.0


def test_low_confidence_requires_review():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(confidence=0.40),
        strategy="balanced",
    )

    assert report.optimization_state == "review_required"
    assert "TIMING_REVIEW_REQUIRED" in report.blockers
    assert all("TIMING_REVIEW_REQUIRED" in item.blockers for item in report.timings)


def test_render_blocked_clip_requires_review():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(render_allowed=False),
        strategy="balanced",
    )

    assert report.optimization_state == "review_required"
    assert "TIMING_REVIEW_REQUIRED" in report.blockers
    assert all("CLIP_RENDER_NOT_ALLOWED" in item.blockers for item in report.timings)


def test_blocked_alignment_remains_blocked():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(state="blocked"),
        strategy="balanced",
    )

    assert report.optimization_state == "blocked"
    assert "NARRATIVE_ALIGNMENT_BLOCKED" in report.blockers


def test_missing_beats_is_fail_closed():
    report = build_clip_timing_optimization(
        alignment_report={
            "alignment_id": "DIRALIGN-1234567890ABCDEF1234",
            "alignment_state": "aligned",
            "beats": [],
        },
        strategy="balanced",
    )

    assert report.optimization_state == "blocked"
    assert "NARRATIVE_BEATS_MISSING" in report.blockers
    assert "TIMING_EVIDENCE_MISSING" in report.blockers


def test_replay_is_deterministic():
    first = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="balanced",
    )
    second = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="balanced",
    )

    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_evidence_tampering_is_detected():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="balanced",
    )
    tampered = replace(report, predicted_retention_score=0.01)

    with pytest.raises(ClipTimingOptimizationError, match="evidence mismatch"):
        tampered.validate()


def test_invalid_strategy_is_rejected():
    with pytest.raises(ClipTimingOptimizationError, match="unsupported director strategy"):
        build_clip_timing_optimization(
            alignment_report=_alignment(),
            strategy="cinematic",
        )


def test_operational_capabilities_cannot_be_enabled():
    report = build_clip_timing_optimization(
        alignment_report=_alignment(),
        strategy="balanced",
    )
    unsafe = replace(report, render_enabled=True)

    with pytest.raises(ClipTimingOptimizationError, match="cannot enable operational capabilities"):
        unsafe.validate()
