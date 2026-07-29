from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Literal


VideoStatus = Literal["draft", "rendering", "ready", "failed", "published"]
VideoPlatform = Literal[
    "youtube_shorts",
    "tiktok",
    "instagram_reels",
    "facebook_reels",
]
VideoContainer = Literal["mp4", "webm"]
VideoOrientation = Literal["vertical", "square", "horizontal"]


@dataclass(frozen=True, slots=True)
class VideoFileReference:
    """Governed reference to one dashboard-served video file."""

    path: str
    container: VideoContainer
    mime_type: str
    checksum_sha256: str | None = None
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        _validate_relative_asset_path(self.path, "video path")
        expected_mime = {
            "mp4": "video/mp4",
            "webm": "video/webm",
        }[self.container]
        if self.mime_type != expected_mime:
            raise ValueError(
                f"mime_type must be {expected_mime!r} for {self.container!r}"
            )
        if self.checksum_sha256 is not None:
            normalized = self.checksum_sha256.strip().casefold()
            if len(normalized) != 64 or any(
                character not in "0123456789abcdef" for character in normalized
            ):
                raise ValueError("checksum_sha256 must contain 64 hexadecimal characters")
        if self.size_bytes is not None and self.size_bytes <= 0:
            raise ValueError("size_bytes must be greater than zero")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VideoAsset:
    """Canonical video object shared by production, publishing and dashboard layers."""

    video_id: str
    title: str
    topic: str
    status: VideoStatus
    platform: VideoPlatform
    duration_seconds: float
    width: int
    height: int
    orientation: VideoOrientation
    video_file: VideoFileReference | None = None
    thumbnail_path: str | None = None
    subtitles_path: str | None = None
    script_id: str | None = None
    storyboard_id: str | None = None
    production_package_id: str | None = None
    publishing_package_id: str | None = None
    render_engine: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.video_id.strip():
            raise ValueError("video_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.topic.strip():
            raise ValueError("topic must not be empty")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be greater than zero")

        expected_orientation = _orientation_for_dimensions(self.width, self.height)
        if self.orientation != expected_orientation:
            raise ValueError(
                "orientation does not match width and height: "
                f"expected {expected_orientation!r}"
            )

        if self.thumbnail_path is not None:
            _validate_relative_asset_path(self.thumbnail_path, "thumbnail_path")
        if self.subtitles_path is not None:
            _validate_relative_asset_path(self.subtitles_path, "subtitles_path")
            if not self.subtitles_path.casefold().endswith(".vtt"):
                raise ValueError("subtitles_path must reference a .vtt file")

        if self.status in {"ready", "published"} and self.video_file is None:
            raise ValueError(f"{self.status} video assets require video_file")
        if self.status == "failed" and not (self.failure_reason or "").strip():
            raise ValueError("failed video assets require failure_reason")
        if self.status != "failed" and self.failure_reason is not None:
            raise ValueError("failure_reason is only valid when status is failed")

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


@dataclass(frozen=True, slots=True)
class VideoLibrary:
    """Deterministic dashboard library containing uniquely identified video assets."""

    generated_at: str
    videos: tuple[VideoAsset, ...]
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.generated_at.strip():
            raise ValueError("generated_at must not be empty")
        if self.schema_version != "1.0":
            raise ValueError("unsupported video library schema_version")
        video_ids = [video.video_id for video in self.videos]
        if len(set(video_ids)) != len(video_ids):
            raise ValueError("video_id values must be unique")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "videos": [video.to_dict() for video in self.videos],
        }


def _orientation_for_dimensions(width: int, height: int) -> VideoOrientation:
    if width == height:
        return "square"
    if height > width:
        return "vertical"
    return "horizontal"


def _validate_relative_asset_path(value: str, field_name: str) -> None:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a safe relative path")
