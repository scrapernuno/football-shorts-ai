from dataclasses import replace

import pytest

from factory.subtitle_generation import SubtitleGenerationError, build_subtitle_track


def timeline(*, state="composed", text="Ele recebe, acelera e marca um golo inesquecível."):
    return {
        "timeline_id": "TIMELINE-ABCDEF0123456789",
        "composition_state": state,
        "clips": [
            {
                "timeline_clip_id": "TLINECLIP-ABCDEF0123456789",
                "timeline_start_seconds": 0.0,
                "timeline_end_seconds": 4.0,
                "script_text": text,
                "role": "hook",
            }
        ],
    }


def test_generates_ordered_synchronized_subtitle_cues():
    report = build_subtitle_track(timeline=timeline(), max_words_per_cue=4)
    report.validate()
    assert report.subtitle_state == "generated"
    assert len(report.cues) == 2
    assert report.cues[0].start_seconds == 0.0
    assert report.cues[-1].end_seconds == 4.0
    assert all(cue.timeline_clip_id.startswith("TLINECLIP-") for cue in report.cues)


def test_replay_is_deterministic():
    first = build_subtitle_track(timeline=timeline())
    second = build_subtitle_track(timeline=timeline())
    assert first == second


def test_uncomposed_timeline_is_fail_closed():
    report = build_subtitle_track(timeline=timeline(state="blocked"))
    assert report.subtitle_state == "blocked"
    assert "TIMELINE_NOT_COMPOSED" in report.blockers


def test_missing_text_is_fail_closed():
    report = build_subtitle_track(timeline=timeline(text=""))
    assert report.subtitle_state == "blocked"
    assert "SUBTITLE_TEXT_MISSING" in report.blockers


def test_invalid_word_limit_is_rejected():
    with pytest.raises(SubtitleGenerationError):
        build_subtitle_track(timeline=timeline(), max_words_per_cue=0)


def test_tampering_is_detected():
    report = build_subtitle_track(timeline=timeline())
    damaged = replace(report, language="en-US")
    with pytest.raises(SubtitleGenerationError, match="evidence mismatch"):
        damaged.validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_subtitle_track(timeline=timeline())
    with pytest.raises(SubtitleGenerationError, match="operational capabilities"):
        replace(report, render_enabled=True).validate()
