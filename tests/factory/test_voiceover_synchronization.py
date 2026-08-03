from dataclasses import replace

import pytest

from factory.voiceover_synchronization import (
    VoiceoverSynchronizationError,
    build_voiceover_track,
)


def _timeline(state="composed"):
    return {
        "timeline_id": "TIMELINE-0123456789ABCDEF0123",
        "composition_state": state,
        "clips": [
            {
                "timeline_clip_id": "TLINECLIP-HOOK000000000001",
                "timeline_start_seconds": 0.0,
                "timeline_end_seconds": 2.5,
                "script_text": "Este momento mudou o jogo.",
                "role": "hook",
            },
            {
                "timeline_clip_id": "TLINECLIP-GOAL000000000002",
                "timeline_start_seconds": 2.5,
                "timeline_end_seconds": 6.0,
                "script_text": "E então surgiu o golo decisivo.",
                "role": "climax",
            },
        ],
    }


def _assets(rights="owned"):
    return [
        {
            "timeline_clip_id": "TLINECLIP-HOOK000000000001",
            "audio_uri": "media/voice/hook.mp3",
            "rights_status": rights,
            "audio_start_seconds": 0.0,
            "audio_end_seconds": 2.5,
        },
        {
            "timeline_clip_id": "TLINECLIP-GOAL000000000002",
            "audio_uri": "media/voice/climax.mp3",
            "rights_status": rights,
            "audio_start_seconds": 0.0,
            "audio_end_seconds": 3.5,
        },
    ]


def test_builds_synchronized_track_for_authorized_audio():
    track = build_voiceover_track(timeline=_timeline(), audio_assets=_assets())
    track.validate()
    assert track.synchronization_state == "synchronized"
    assert track.blockers == ()
    assert len(track.cues) == 2
    assert all(cue.audio_allowed for cue in track.cues)
    assert track.cues[0].timeline_end_seconds == 2.5


def test_missing_audio_requires_review():
    track = build_voiceover_track(timeline=_timeline(), audio_assets=())
    assert track.synchronization_state == "review_required"
    assert "VOICEOVER_REVIEW_REQUIRED" in track.blockers
    assert all("VOICEOVER_AUDIO_MISSING" in cue.blockers for cue in track.cues)


def test_reference_only_audio_is_not_authorized():
    track = build_voiceover_track(timeline=_timeline(), audio_assets=_assets("reference_only"))
    assert track.synchronization_state == "review_required"
    assert all(not cue.audio_allowed for cue in track.cues)
    assert all("VOICEOVER_AUDIO_NOT_AUTHORIZED" in cue.blockers for cue in track.cues)


def test_blocked_timeline_stays_blocked():
    track = build_voiceover_track(timeline=_timeline("blocked"), audio_assets=_assets())
    assert track.synchronization_state == "blocked"
    assert "TIMELINE_NOT_COMPOSED" in track.blockers


def test_replay_is_deterministic():
    first = build_voiceover_track(timeline=_timeline(), audio_assets=_assets())
    second = build_voiceover_track(timeline=_timeline(), audio_assets=_assets())
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampering_is_detected():
    track = build_voiceover_track(timeline=_timeline(), audio_assets=_assets())
    with pytest.raises(VoiceoverSynchronizationError, match="evidence mismatch"):
        replace(track, voice_style="tampered").validate()


def test_operational_capabilities_cannot_be_enabled():
    track = build_voiceover_track(timeline=_timeline(), audio_assets=_assets())
    with pytest.raises(VoiceoverSynchronizationError, match="operational capabilities"):
        replace(track, synthesis_enabled=True).validate()
