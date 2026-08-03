from dataclasses import replace

import pytest

from factory.music_ambience_sfx_mixing import AudioMixError, build_audio_mix_track


def timeline(state="composed"):
    return {"timeline_id": "TIMELINE-ABCDEF0123456789", "composition_state": state}


def cue(kind="music", rights="owned", uri="media/music.mp3"):
    return {
        "kind": kind,
        "audio_uri": uri,
        "timeline_start_seconds": 0,
        "timeline_end_seconds": 12,
        "audio_start_seconds": 0,
        "audio_end_seconds": 12,
        "gain_db": -14,
        "fade_in_seconds": 0.5,
        "fade_out_seconds": 0.8,
        "loop": False,
        "duck_under_voiceover_db": -8,
        "rights_status": rights,
    }


def test_builds_authorized_music_ambience_and_sfx_mix():
    report = build_audio_mix_track(
        timeline=timeline(),
        cue_inputs=(cue("music"), cue("ambience", uri="media/crowd.mp3"), cue("sfx", uri="media/impact.wav")),
    )
    report.validate()
    assert report.mix_state == "mixed"
    assert len(report.cues) == 3
    assert all(item.audio_allowed for item in report.cues)


def test_reference_only_audio_requires_review():
    report = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(rights="reference_only"),))
    assert report.mix_state == "review_required"
    assert "AUDIO_MIX_REVIEW_REQUIRED" in report.blockers
    assert report.cues[0].audio_allowed is False


def test_missing_source_requires_review():
    report = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(uri=""),))
    assert report.mix_state == "review_required"
    assert "AUDIO_SOURCE_MISSING" in report.cues[0].blockers


def test_blocked_timeline_is_fail_closed():
    report = build_audio_mix_track(timeline=timeline("blocked"), cue_inputs=(cue(),))
    assert report.mix_state == "blocked"
    assert "TIMELINE_NOT_COMPOSED" in report.blockers


def test_empty_mix_is_blocked():
    report = build_audio_mix_track(timeline=timeline(), cue_inputs=())
    assert report.mix_state == "blocked"
    assert "AUDIO_MIX_CUES_MISSING" in report.blockers


def test_replay_is_deterministic():
    a = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(),))
    b = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(),))
    assert a == b


def test_evidence_tampering_is_detected():
    report = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(),))
    with pytest.raises(AudioMixError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_audio_mix_track(timeline=timeline(), cue_inputs=(cue(),))
    with pytest.raises(AudioMixError, match="operational capabilities"):
        replace(report, render_enabled=True).validate()
