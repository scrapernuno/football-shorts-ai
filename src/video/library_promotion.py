from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from video.contracts import VideoAsset, VideoFileReference, VideoLibrary
from video.rendering import RenderRequest, RenderResult

Clock = Callable[[], datetime]


class VideoLibraryPromotionError(RuntimeError):
    """Raised when a rendered asset cannot be safely promoted."""


def promote_render_result(
    library_path: Path,
    request: RenderRequest,
    result: RenderResult,
    *,
    render_engine: str = "ffmpeg",
    clock: Clock | None = None,
) -> VideoLibrary:
    """Atomically promote one successful render into the governed video library.

    The existing library remains untouched unless the complete replacement payload
    validates and the temporary file is durably written. Failed or incomplete render
    results are rejected before any filesystem mutation.
    """

    if result.status != "succeeded":
        raise VideoLibraryPromotionError("only succeeded render results may be promoted")
    if result.video_id != request.video_id or result.render_id != request.render_id:
        raise VideoLibraryPromotionError("render result identity does not match request")

    required_paths = (
        result.output_path,
        result.thumbnail_path,
        result.subtitles_path,
    )
    expected_paths = (
        request.output_path,
        request.thumbnail_path,
        request.subtitles_path,
    )
    if required_paths != expected_paths:
        raise VideoLibraryPromotionError("render output paths do not match request")
    if result.checksum_sha256 is None or result.size_bytes is None:
        raise VideoLibraryPromotionError("render evidence is incomplete")

    library = load_video_library(library_path)
    now = (clock or _utc_now)().isoformat()

    matched = False
    promoted_assets: list[VideoAsset] = []
    for asset in library.videos:
        if asset.video_id != request.video_id:
            promoted_assets.append(asset)
            continue

        matched = True
        if asset.status == "published":
            raise VideoLibraryPromotionError("published video assets cannot be replaced")
        if asset.width != request.width or asset.height != request.height:
            raise VideoLibraryPromotionError("render dimensions do not match video asset")
        if abs(asset.duration_seconds - request.duration_seconds) > 0.001:
            raise VideoLibraryPromotionError("render duration does not match video asset")

        mime_type = "video/mp4" if request.container == "mp4" else "video/webm"
        promoted_assets.append(
            replace(
                asset,
                status="ready",
                video_file=VideoFileReference(
                    path=result.output_path or "",
                    container=request.container,
                    mime_type=mime_type,
                    checksum_sha256=result.checksum_sha256,
                    size_bytes=result.size_bytes,
                ),
                thumbnail_path=result.thumbnail_path,
                subtitles_path=result.subtitles_path,
                render_engine=render_engine,
                updated_at=now,
                failure_reason=None,
            )
        )

    if not matched:
        raise VideoLibraryPromotionError(
            f"video_id {request.video_id!r} is not registered in the governed library"
        )

    promoted = VideoLibrary(
        generated_at=now,
        videos=tuple(promoted_assets),
        schema_version=library.schema_version,
    )
    _atomic_write_json(library_path, promoted.to_dict())
    return promoted


def load_video_library(path: Path) -> VideoLibrary:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoLibraryPromotionError(f"unable to read video library: {exc}") from exc

    if not isinstance(payload, dict):
        raise VideoLibraryPromotionError("video library root must be an object")
    videos_payload = payload.get("videos")
    if not isinstance(videos_payload, list):
        raise VideoLibraryPromotionError("video library videos must be a list")

    try:
        videos = tuple(_video_asset_from_dict(item) for item in videos_payload)
        return VideoLibrary(
            generated_at=str(payload.get("generated_at", "")),
            videos=videos,
            schema_version=str(payload.get("schema_version", "")),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise VideoLibraryPromotionError(f"invalid video library: {exc}") from exc


def _video_asset_from_dict(payload: object) -> VideoAsset:
    if not isinstance(payload, dict):
        raise TypeError("each video library entry must be an object")

    video_file_payload = payload.get("video_file")
    video_file = None
    if video_file_payload is not None:
        if not isinstance(video_file_payload, dict):
            raise TypeError("video_file must be an object or null")
        video_file = VideoFileReference(
            path=str(video_file_payload["path"]),
            container=video_file_payload["container"],
            mime_type=str(video_file_payload["mime_type"]),
            checksum_sha256=video_file_payload.get("checksum_sha256"),
            size_bytes=video_file_payload.get("size_bytes"),
        )

    return VideoAsset(
        video_id=str(payload["video_id"]),
        title=str(payload["title"]),
        topic=str(payload["topic"]),
        status=payload["status"],
        platform=payload["platform"],
        duration_seconds=float(payload["duration_seconds"]),
        width=int(payload["width"]),
        height=int(payload["height"]),
        orientation=payload["orientation"],
        video_file=video_file,
        thumbnail_path=payload.get("thumbnail_path"),
        subtitles_path=payload.get("subtitles_path"),
        script_id=payload.get("script_id"),
        storyboard_id=payload.get("storyboard_id"),
        production_package_id=payload.get("production_package_id"),
        publishing_package_id=payload.get("publishing_package_id"),
        render_engine=payload.get("render_engine"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        failure_reason=payload.get("failure_reason"),
    )


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
