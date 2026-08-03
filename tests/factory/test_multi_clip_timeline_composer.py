from dataclasses import replace

import pytest

from factory.multi_clip_timeline_composer import (
    TimelineComposerError,
    compose_multi_clip_timeline,
)


def _manifest(*, ready=True, second_allowed=True):
    return {
        "manifest_id": "PREVIEW-0060A-DEMO",
        "preview_state": "preview_ready" if ready else "blocked",
        "blockers": [] if ready else ["FACTORY_HANDOVER_NOT_READY"],
        "segments": [
            {
                "segment_id": "PREVIEWSEG-HOOK",
                "clip_id": "VIRALCLIP-HOOK",
                "role": "hook",
                "source_uri": "media/authorized-match.mp4",
                "source_start_seconds": 10.0,
                "source_end_seconds": 14.0,
                "playback_rate": 1.0,
                "transition": "cut",
                "script_text": "O momento que mudou o jogo.",
                "preview_allowed": True,
                "blockers": [],
            },
            {
                "segment_id": "PREVIEWSEG-CLIMAX",
                "clip_id": "VIRALCLIP-CLIMAX",
                "role": "climax",
                "source_uri": "media/authorized-match.mp4",
                "source_start_seconds": 30.0,
                "source_end_seconds": 36.0,
                "playback_rate": 1.5,
                "transition": "crossfade",
                "script_text": "E então surgiu o golo.",
                "preview_allowed": second_allowed,
                "blockers": [],
            },
        ],
    }


def test_composes_continuous_multi_clip_timeline():
    report = compose_multi_clip_timeline(_manifest())
    report.validate()

    assert report.timeline_state == "composed"
    assert report.blockers == ()
    assert len(report.clips) == 2
    assert report.clips[0].timeline_start_seconds == 0.0
    assert report.clips[0].timeline_end_seconds == 4.0
    assert report.clips[1].timeline_start_seconds == 4.0
    assert report.clips[1].timeline_end_seconds == 8.0
    assert report.total_duration_seconds == 8.0
    assert report.clips[1].transition == "crossfade"


def test_playback_rate_changes_timeline_duration():
    report = compose_multi_clip_timeline(_manifest())
    assert report.clips[1].source_end_seconds - report.clips[1].source_start_seconds == 6.0
    assert report.clips[1].timeline_end_seconds - report.clips[1].timeline_start_seconds == 4.0


def test_non_ready_manifest_is_fail_closed():
    report = compose_multi_clip_timeline(_manifest(ready=False))
    assert report.timeline_state == "review_required"
    assert "PREVIEW_MANIFEST_NOT_READY" in report.blockers
    assert report.render_enabled is False
    assert report.auto_publish is False


def test_disallowed_clip_requires_review():
    report = compose_multi_clip_timeline(_manifest(second_allowed=False))
    assert report.timeline_state == "review_required"
    assert "CLIP_PREVIEW_NOT_ALLOWED" in report.blockers
    assert report.clips[1].preview_allowed is False


def test_missing_source_is_fail_closed():
    manifest = _manifest()
    manifest["segments"][0]["source_uri"] = ""
    report = compose_multi_clip_timeline(manifest)
    assert report.timeline_state == "review_required"
    assert "CLIP_SOURCE_MISSING" in report.blockers


def test_empty_manifest_is_blocked():
    report = compose_multi_clip_timeline({
        "manifest_id": "PREVIEW-EMPTY",
        "preview_state": "preview_ready",
        "segments": [],
    })
    assert report.timeline_state == "blocked"
    assert "PREVIEW_SEGMENTS_MISSING" in report.blockers


def test_replay_is_deterministic():
    first = compose_multi_clip_timeline(_manifest())
    second = compose_multi_clip_timeline(_manifest())
    assert first.timeline_id == second.timeline_id
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_detected():
    report = compose_multi_clip_timeline(_manifest())
    tampered = replace(report, total_duration_seconds=99.0)
    with pytest.raises(TimelineComposerError, match="duration mismatch|evidence mismatch"):
        tampered.validate()


def test_operational_capabilities_cannot_be_enabled():
    report = compose_multi_clip_timeline(_manifest())
    with pytest.raises(TimelineComposerError, match="operational capabilities"):
        replace(report, render_enabled=True).validate()
