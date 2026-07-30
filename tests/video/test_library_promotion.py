from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from video.library_promotion import (
    VideoLibraryPromotionError,
    load_video_library,
    promote_render_result,
)
from video.rendering import RenderRequest, RenderResult, RenderScene


def _library_payload() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-07-29T21:00:00+01:00",
        "videos": [
            {
                "video_id": "VID-000001",
                "title": "Governed football short",
                "topic": "football_short_demo",
                "status": "draft",
                "platform": "youtube_shorts",
                "duration_seconds": 8.0,
                "width": 1080,
                "height": 1920,
                "orientation": "vertical",
                "video_file": None,
                "thumbnail_path": None,
                "subtitles_path": None,
                "script_id": "SCRIPT-000001",
                "storyboard_id": "STORYBOARD-000001",
                "production_package_id": "PRODUCTION-000001",
                "publishing_package_id": "PUBLISHING-000001",
                "render_engine": None,
                "created_at": "2026-07-29T21:00:00+01:00",
                "updated_at": "2026-07-29T21:00:00+01:00",
                "failure_reason": None,
            }
        ],
    }


def _request() -> RenderRequest:
    return RenderRequest(
        render_id="RENDER-000001",
        video_id="VID-000001",
        topic="football_short_demo",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path="videos/VID-000001.mp4",
        thumbnail_path="videos/VID-000001.jpg",
        subtitles_path="videos/VID-000001.vtt",
        scenes=(
            RenderScene(
                scene_id="scene_01",
                start_second=0,
                end_second=8,
                screen_text="Football history",
                narration="Football history in eight seconds.",
                visual_prompt="Vertical football editorial visual",
            ),
        ),
    )


def _success() -> RenderResult:
    return RenderResult(
        render_id="RENDER-000001",
        video_id="VID-000001",
        status="succeeded",
        output_path="videos/VID-000001.mp4",
        thumbnail_path="videos/VID-000001.jpg",
        subtitles_path="videos/VID-000001.vtt",
        checksum_sha256="a" * 64,
        size_bytes=2048,
    )


def test_successful_render_is_atomically_promoted(tmp_path: Path) -> None:
    library_path = tmp_path / "video_library.json"
    library_path.write_text(json.dumps(_library_payload()), encoding="utf-8")
    fixed_now = datetime(2026, 7, 30, 8, 30, tzinfo=timezone.utc)

    promoted = promote_render_result(
        library_path,
        _request(),
        _success(),
        clock=lambda: fixed_now,
    )

    assert promoted.generated_at == fixed_now.isoformat()
    asset = promoted.videos[0]
    assert asset.status == "ready"
    assert asset.render_engine == "ffmpeg"
    assert asset.video_file is not None
    assert asset.video_file.path == "videos/VID-000001.mp4"
    assert asset.video_file.mime_type == "video/mp4"
    assert asset.video_file.checksum_sha256 == "a" * 64
    assert asset.video_file.size_bytes == 2048
    assert asset.thumbnail_path == "videos/VID-000001.jpg"
    assert asset.subtitles_path == "videos/VID-000001.vtt"

    reloaded = load_video_library(library_path)
    assert reloaded == promoted
    assert not list(tmp_path.glob(".video_library.json.*.tmp"))


def test_failed_render_never_mutates_library(tmp_path: Path) -> None:
    library_path = tmp_path / "video_library.json"
    original = json.dumps(_library_payload(), indent=2)
    library_path.write_text(original, encoding="utf-8")
    failed = RenderResult(
        render_id="RENDER-000001",
        video_id="VID-000001",
        status="failed",
        failure_reason="controlled failure",
    )

    with pytest.raises(VideoLibraryPromotionError, match="only succeeded"):
        promote_render_result(library_path, _request(), failed)

    assert library_path.read_text(encoding="utf-8") == original


def test_identity_mismatch_never_mutates_library(tmp_path: Path) -> None:
    library_path = tmp_path / "video_library.json"
    original = json.dumps(_library_payload())
    library_path.write_text(original, encoding="utf-8")
    mismatch = RenderResult(
        render_id="RENDER-OTHER",
        video_id="VID-000001",
        status="succeeded",
        output_path="videos/VID-000001.mp4",
        thumbnail_path="videos/VID-000001.jpg",
        subtitles_path="videos/VID-000001.vtt",
        checksum_sha256="b" * 64,
        size_bytes=1024,
    )

    with pytest.raises(VideoLibraryPromotionError, match="identity"):
        promote_render_result(library_path, _request(), mismatch)

    assert library_path.read_text(encoding="utf-8") == original


def test_unregistered_video_is_rejected(tmp_path: Path) -> None:
    library_path = tmp_path / "video_library.json"
    library_path.write_text(json.dumps(_library_payload()), encoding="utf-8")
    request = RenderRequest(
        render_id="RENDER-000002",
        video_id="VID-999999",
        topic="unknown",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path="videos/VID-999999.mp4",
        thumbnail_path="videos/VID-999999.jpg",
        subtitles_path="videos/VID-999999.vtt",
        scenes=(
            RenderScene(
                scene_id="scene_01",
                start_second=0,
                end_second=8,
                screen_text="Unknown",
                narration="Unknown",
                visual_prompt="Unknown visual",
            ),
        ),
    )
    result = RenderResult(
        render_id=request.render_id,
        video_id=request.video_id,
        status="succeeded",
        output_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        checksum_sha256="c" * 64,
        size_bytes=1024,
    )

    with pytest.raises(VideoLibraryPromotionError, match="not registered"):
        promote_render_result(library_path, request, result)
