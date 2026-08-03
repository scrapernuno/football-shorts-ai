from dataclasses import replace

import pytest

from factory.final_render_package import (
    FinalRenderPackageError,
    build_final_render_package,
)


def _timeline():
    return {
        "timeline_id": "TIMELINE-0060I000000000001",
        "composition_state": "composed",
        "total_duration_seconds": 31.5,
    }


def _preview():
    return {
        "preview_state": "preview_ready",
        "source_uri": "dashboard/media/authorized-match.mp4",
        "rights_status": "owned",
    }


def test_builds_vertical_mp4_render_package_ready_for_authorization():
    package = build_final_render_package(timeline=_timeline(), preview=_preview())

    assert package.package_state == "ready_for_authorization"
    assert package.blockers == ()
    assert package.output_format == "mp4"
    assert (package.width, package.height) == (1080, 1920)
    assert package.video_codec == "libx264"
    assert package.audio_codec == "aac"
    assert package.ffmpeg_design.execution_enabled is False
    assert package.ffmpeg_design.command_preview.startswith("ffmpeg -hide_banner")
    assert package.ffmpeg_design.output_uri.endswith(".mp4")
    package.validate()


def test_optional_governed_layers_are_recorded():
    package = build_final_render_package(
        timeline=_timeline(),
        preview=_preview(),
        subtitle={"subtitle_state": "generated", "source_uri": "artifacts/subtitles.vtt", "rights_status": "not_applicable"},
        voiceover={"synchronization_state": "synchronized", "source_uri": "artifacts/voice.wav", "rights_status": "owned"},
        audio_mix={"mix_state": "mixed", "source_uri": "artifacts/mix.wav", "rights_status": "licensed"},
        graphics={"graphics_state": "composed", "source_uri": "artifacts/graphics.json", "rights_status": "not_applicable"},
        thumbnail={"composition_state": "composed", "source_uri": "artifacts/thumb.jpg", "rights_status": "owned"},
    )

    assert package.package_state == "ready_for_authorization"
    assert {item.kind for item in package.inputs} == {"video", "subtitle", "voiceover", "music", "graphics", "thumbnail"}
    assert all(item.authorized for item in package.inputs)


def test_blocks_when_timeline_is_not_composed():
    package = build_final_render_package(
        timeline={"timeline_id": "TIMELINE-0060I000000000001", "composition_state": "blocked", "total_duration_seconds": 31.5},
        preview=_preview(),
    )
    assert package.package_state == "blocked"
    assert "TIMELINE_NOT_COMPOSED" in package.blockers


def test_blocks_when_preview_is_not_ready():
    package = build_final_render_package(
        timeline=_timeline(),
        preview={"preview_state": "blocked", "source_uri": "", "rights_status": "owned"},
    )
    assert package.package_state == "blocked"
    assert "PREVIEW_NOT_READY" in package.blockers
    assert "VIDEO_SOURCE_MISSING" in package.blockers


def test_reference_only_video_is_fail_closed():
    package = build_final_render_package(
        timeline=_timeline(),
        preview={"preview_state": "preview_ready", "source_uri": "media/reference.mp4", "rights_status": "reference_only"},
    )
    assert package.package_state == "review_required"
    video = next(item for item in package.inputs if item.kind == "video")
    assert video.authorized is False
    assert "VIDEO_NOT_AUTHORIZED" in video.blockers


def test_replay_is_deterministic():
    first = build_final_render_package(timeline=_timeline(), preview=_preview())
    second = build_final_render_package(timeline=_timeline(), preview=_preview())
    assert first.to_dict() == second.to_dict()
    assert first.evidence_sha256 == second.evidence_sha256


def test_evidence_tampering_is_detected():
    package = build_final_render_package(timeline=_timeline(), preview=_preview())
    with pytest.raises(FinalRenderPackageError, match="evidence mismatch"):
        replace(package, duration_seconds=99).validate()


def test_ffmpeg_execution_cannot_be_enabled():
    package = build_final_render_package(timeline=_timeline(), preview=_preview())
    with pytest.raises(FinalRenderPackageError, match="cannot enable"):
        replace(package, ffmpeg_execution_enabled=True).validate()


def test_render_and_publish_capabilities_remain_disabled():
    package = build_final_render_package(timeline=_timeline(), preview=_preview())
    assert package.network_enabled is False
    assert package.acquisition_enabled is False
    assert package.extraction_enabled is False
    assert package.render_enabled is False
    assert package.ffmpeg_execution_enabled is False
    assert package.auto_publish is False


def test_rejects_unsupported_fps():
    with pytest.raises(FinalRenderPackageError, match="frame rate"):
        build_final_render_package(timeline=_timeline(), preview=_preview(), fps=29)
