from __future__ import annotations

import pytest

from video.contracts import VideoAsset, VideoFileReference, VideoLibrary


def _file() -> VideoFileReference:
    return VideoFileReference(
        path="videos/VID-000001.mp4",
        container="mp4",
        mime_type="video/mp4",
        checksum_sha256="a" * 64,
        size_bytes=1024,
    )


def _asset(**overrides: object) -> VideoAsset:
    values: dict[str, object] = {
        "video_id": "VID-000001",
        "title": "Football short",
        "topic": "football topic",
        "status": "ready",
        "platform": "youtube_shorts",
        "duration_seconds": 43.5,
        "width": 1080,
        "height": 1920,
        "orientation": "vertical",
        "video_file": _file(),
        "thumbnail_path": "videos/VID-000001.jpg",
        "subtitles_path": "videos/VID-000001.vtt",
        "script_id": "SCRIPT-000001",
        "storyboard_id": "STORYBOARD-000001",
        "production_package_id": "PRODUCTION-000001",
        "publishing_package_id": "PUBLISHING-000001",
        "render_engine": "controlled_fixture",
        "created_at": "2026-07-29T20:00:00Z",
    }
    values.update(overrides)
    return VideoAsset(**values)  # type: ignore[arg-type]


def test_ready_video_asset_serializes_canonical_contract() -> None:
    asset = _asset()
    payload = asset.to_dict()

    assert payload["video_id"] == "VID-000001"
    assert payload["status"] == "ready"
    assert payload["orientation"] == "vertical"
    assert payload["video_file"]["path"] == "videos/VID-000001.mp4"
    assert payload["video_file"]["mime_type"] == "video/mp4"


def test_ready_and_published_assets_require_video_file() -> None:
    with pytest.raises(ValueError, match="ready video assets require video_file"):
        _asset(video_file=None)

    with pytest.raises(ValueError, match="published video assets require video_file"):
        _asset(status="published", video_file=None)


def test_failed_asset_requires_reason_and_rejects_file_path_escape() -> None:
    with pytest.raises(ValueError, match="failed video assets require failure_reason"):
        _asset(status="failed", video_file=None, failure_reason=None)

    with pytest.raises(ValueError, match="safe relative path"):
        VideoFileReference(
            path="../secret.mp4",
            container="mp4",
            mime_type="video/mp4",
        )


def test_contract_validates_container_mime_checksum_and_subtitles() -> None:
    with pytest.raises(ValueError, match="mime_type"):
        VideoFileReference(
            path="videos/video.mp4",
            container="mp4",
            mime_type="video/webm",
        )

    with pytest.raises(ValueError, match="64 hexadecimal"):
        VideoFileReference(
            path="videos/video.mp4",
            container="mp4",
            mime_type="video/mp4",
            checksum_sha256="invalid",
        )

    with pytest.raises(ValueError, match=".vtt"):
        _asset(subtitles_path="videos/VID-000001.srt")


def test_orientation_must_match_dimensions() -> None:
    with pytest.raises(ValueError, match="orientation does not match"):
        _asset(width=1920, height=1080, orientation="vertical")


def test_video_library_rejects_duplicate_ids_and_serializes_deterministically() -> None:
    first = _asset()
    second = _asset(video_id="VID-000002", status="draft", video_file=None)
    library = VideoLibrary(
        generated_at="2026-07-29T20:00:00Z",
        videos=(first, second),
    )

    payload = library.to_dict()
    assert payload["schema_version"] == "1.0"
    assert [video["video_id"] for video in payload["videos"]] == [
        "VID-000001",
        "VID-000002",
    ]

    with pytest.raises(ValueError, match="video_id values must be unique"):
        VideoLibrary(
            generated_at="2026-07-29T20:00:00Z",
            videos=(first, first),
        )
