from dataclasses import replace

import pytest

from factory.motion_graphics_overlay import (
    MotionGraphicsError,
    build_motion_graphics_track,
)


def timeline(state="composed"):
    return {
        "timeline_id": "TIMELINE-ABCDEF1234567890ABCD",
        "composition_state": state,
        "total_duration_seconds": 30.0,
    }


def cues():
    return (
        {
            "kind": "scoreboard",
            "timeline_start_seconds": 0,
            "timeline_end_seconds": 8,
            "primary_text": "POR 1–0 ESP",
            "secondary_text": "67:42",
            "position": "top_left",
            "animation_in": "slide_left",
            "animation_out": "fade",
            "emphasis_score": 0.7,
        },
        {
            "kind": "event",
            "timeline_start_seconds": 8,
            "timeline_end_seconds": 12,
            "primary_text": "GOLO!",
            "secondary_text": "Portugal",
            "position": "center",
            "animation_in": "scale",
            "animation_out": "fade",
            "emphasis_score": 1.0,
        },
    )


def test_composes_authorized_motion_graphics_track():
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=cues())
    track.validate()
    assert track.graphics_state == "composed"
    assert track.blockers == ()
    assert len(track.cues) == 2
    assert all(cue.overlay_allowed for cue in track.cues)
    assert track.graphics_id.startswith("MOTIONGFX-")


def test_missing_cues_is_fail_closed():
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=())
    assert track.graphics_state == "blocked"
    assert "MOTION_GRAPHICS_CUES_MISSING" in track.blockers


def test_uncomposed_timeline_is_blocked():
    track = build_motion_graphics_track(timeline=timeline("blocked"), cue_inputs=cues())
    assert track.graphics_state == "blocked"
    assert "TIMELINE_NOT_COMPOSED" in track.blockers


def test_missing_text_requires_review():
    raw = dict(cues()[0])
    raw["primary_text"] = ""
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=(raw,))
    assert track.graphics_state == "review_required"
    assert "MOTION_GRAPHICS_REVIEW_REQUIRED" in track.blockers
    assert "OVERLAY_TEXT_MISSING" in track.cues[0].blockers


def test_overlay_outside_timeline_requires_review():
    raw = dict(cues()[0])
    raw["timeline_end_seconds"] = 31
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=(raw,))
    assert track.graphics_state == "review_required"
    assert "OVERLAY_OUTSIDE_TIMELINE" in track.cues[0].blockers


def test_replay_is_deterministic():
    first = build_motion_graphics_track(timeline=timeline(), cue_inputs=cues())
    second = build_motion_graphics_track(timeline=timeline(), cue_inputs=cues())
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampering_is_detected():
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=cues())
    with pytest.raises(MotionGraphicsError, match="evidence mismatch"):
        replace(track, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    track = build_motion_graphics_track(timeline=timeline(), cue_inputs=cues())
    with pytest.raises(MotionGraphicsError, match="cannot enable"):
        replace(track, render_enabled=True).validate()
