from __future__ import annotations

import pytest

from video.rendering import RenderResult, build_render_request


PRODUCTION_PACKAGE = {
    "topic": "A final impossível",
    "format": "vertical_9_16",
    "resolution": "1080x1920",
    "scenes": [
        {
            "scene_id": "scene_01",
            "start_second": 0,
            "end_second": 8,
            "screen_text": "A final impossível",
            "narration": "Tudo parecia perdido.",
            "visual_prompt": "Vertical football stadium opening scene",
        },
        {
            "scene_id": "scene_02",
            "start_second": 8,
            "end_second": 16,
            "screen_text": "Até ao último minuto",
            "narration": "Mas o jogo mudou no último minuto.",
            "visual_prompt": "Vertical football comeback scene",
        },
    ],
}


def test_build_render_request_is_deterministic_and_vertical() -> None:
    request = build_render_request(
        PRODUCTION_PACKAGE,
        render_id="render-001",
        video_id="VID-000001",
    )

    assert request.width == 1080
    assert request.height == 1920
    assert request.fps == 30
    assert request.output_path == "videos/VID-000001.mp4"
    assert request.thumbnail_path == "videos/VID-000001.jpg"
    assert request.subtitles_path == "videos/VID-000001.vtt"
    assert request.duration_seconds == 16
    assert len(request.scenes) == 2


def test_render_request_rejects_unsafe_output_prefix() -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        build_render_request(
            PRODUCTION_PACKAGE,
            render_id="render-001",
            video_id="VID-000001",
            output_prefix="../outside",
        )


def test_render_request_rejects_overlapping_scenes() -> None:
    payload = {
        **PRODUCTION_PACKAGE,
        "scenes": [
            PRODUCTION_PACKAGE["scenes"][0],
            {
                **PRODUCTION_PACKAGE["scenes"][1],
                "start_second": 7,
            },
        ],
    }

    with pytest.raises(ValueError, match="must not overlap"):
        build_render_request(
            payload,
            render_id="render-001",
            video_id="VID-000001",
        )


def test_succeeded_render_result_requires_complete_integrity_evidence() -> None:
    result = RenderResult(
        render_id="render-001",
        video_id="VID-000001",
        status="succeeded",
        output_path="videos/VID-000001.mp4",
        thumbnail_path="videos/VID-000001.jpg",
        subtitles_path="videos/VID-000001.vtt",
        checksum_sha256="a" * 64,
        size_bytes=1024,
    )

    assert result.status == "succeeded"
    assert result.checksum_sha256 == "a" * 64


def test_succeeded_render_result_fails_closed_without_checksum() -> None:
    with pytest.raises(ValueError, match="checksum_sha256"):
        RenderResult(
            render_id="render-001",
            video_id="VID-000001",
            status="succeeded",
            output_path="videos/VID-000001.mp4",
            thumbnail_path="videos/VID-000001.jpg",
            subtitles_path="videos/VID-000001.vtt",
            size_bytes=1024,
        )


def test_failed_render_result_rejects_partial_outputs() -> None:
    with pytest.raises(ValueError, match="partial governed outputs"):
        RenderResult(
            render_id="render-001",
            video_id="VID-000001",
            status="failed",
            output_path="videos/partial.mp4",
            failure_reason="ffmpeg failed",
        )
