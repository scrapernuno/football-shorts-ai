from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video.contracts import VideoAsset, VideoFileReference, VideoLibrary


ROOT = Path(__file__).resolve().parents[2]
VIDEO_LIBRARY_FILE = ROOT / "dashboard" / "data" / "video_library.json"


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _load_video_file(value: Any) -> VideoFileReference | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("video_file must be an object or null")
    return VideoFileReference(
        path=str(value.get("path", "")),
        container=value.get("container"),
        mime_type=str(value.get("mime_type", "")),
        checksum_sha256=_optional_text(value.get("checksum_sha256")),
        size_bytes=value.get("size_bytes"),
    )


def _load_video(value: Any) -> VideoAsset:
    if not isinstance(value, dict):
        raise ValueError("each videos item must be an object")
    return VideoAsset(
        video_id=str(value.get("video_id", "")),
        title=str(value.get("title", "")),
        topic=str(value.get("topic", "")),
        status=value.get("status"),
        platform=value.get("platform"),
        duration_seconds=float(value.get("duration_seconds", 0)),
        width=int(value.get("width", 0)),
        height=int(value.get("height", 0)),
        orientation=value.get("orientation"),
        video_file=_load_video_file(value.get("video_file")),
        thumbnail_path=_optional_text(value.get("thumbnail_path")),
        subtitles_path=_optional_text(value.get("subtitles_path")),
        script_id=_optional_text(value.get("script_id")),
        storyboard_id=_optional_text(value.get("storyboard_id")),
        production_package_id=_optional_text(value.get("production_package_id")),
        publishing_package_id=_optional_text(value.get("publishing_package_id")),
        render_engine=_optional_text(value.get("render_engine")),
        created_at=_optional_text(value.get("created_at")),
        updated_at=_optional_text(value.get("updated_at")),
        failure_reason=_optional_text(value.get("failure_reason")),
    )


def load_video_library(path: Path = VIDEO_LIBRARY_FILE) -> VideoLibrary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("video library root must be an object")
    videos = payload.get("videos")
    if not isinstance(videos, list):
        raise ValueError("videos must be a list")
    return VideoLibrary(
        generated_at=str(payload.get("generated_at", "")),
        schema_version=str(payload.get("schema_version", "")),
        videos=tuple(_load_video(item) for item in videos),
    )


def main() -> int:
    library = load_video_library()
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0044C")
    print("GOVERNED DASHBOARD VIDEO LIBRARY CERTIFICATION")
    print("=" * 72)
    print(f"VIDEO_LIBRARY_FILE={VIDEO_LIBRARY_FILE}")
    print(f"SCHEMA_VERSION={library.schema_version}")
    print(f"VIDEO_COUNT={len(library.videos)}")
    print(f"VIDEO_IDS={','.join(video.video_id for video in library.videos)}")
    print("STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
