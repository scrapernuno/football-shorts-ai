from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from video.ffmpeg_runtime import FfmpegRenderRuntime, FfmpegRuntimeConfig
from video.library_promotion import load_video_library, promote_render_result
from video.rendering import build_render_request


def _fake_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    output = Path(command[-1])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}:
        output.write_bytes(b"football-shorts-ai-0045f-thumbnail")
    else:
        output.write_bytes(b"football-shorts-ai-0045f-video")
    return subprocess.CompletedProcess(list(command), 0, "", "")


def _production_package() -> dict:
    return {
        "production_package_id": "PRODUCTION-CERT-0045F",
        "topic": "governed_rendering_pipeline",
        "format": "vertical_9_16",
        "resolution": "1080x1920",
        "scenes": [
            {
                "scene_id": "scene_01",
                "start_second": 0,
                "end_second": 4,
                "screen_text": "The opening moment",
                "narration": "The opening moment set the match in motion.",
                "visual_prompt": "Vertical football stadium opening, editorial style",
            },
            {
                "scene_id": "scene_02",
                "start_second": 4,
                "end_second": 8,
                "screen_text": "The decisive finish",
                "narration": "The decisive finish completed the story.",
                "visual_prompt": "Vertical football goal celebration, cinematic editorial style",
            },
        ],
    }


def _library_payload() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-07-30T08:00:00+00:00",
        "videos": [
            {
                "video_id": "VID-CERT-0045F",
                "title": "Final rendering pipeline certification",
                "topic": "governed_rendering_pipeline",
                "status": "draft",
                "platform": "youtube_shorts",
                "duration_seconds": 8.0,
                "width": 1080,
                "height": 1920,
                "orientation": "vertical",
                "video_file": None,
                "thumbnail_path": None,
                "subtitles_path": None,
                "script_id": "SCRIPT-CERT-0045F",
                "storyboard_id": "STORYBOARD-CERT-0045F",
                "production_package_id": "PRODUCTION-CERT-0045F",
                "publishing_package_id": "PUBLISHING-CERT-0045F",
                "render_engine": None,
                "created_at": "2026-07-30T08:00:00+00:00",
                "updated_at": "2026-07-30T08:00:00+00:00",
                "failure_reason": None,
            }
        ],
    }


def certify() -> dict[str, str | int]:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0045f-") as temp_dir:
        root = Path(temp_dir)
        workspace = root / "dashboard"
        library_path = workspace / "data" / "video_library.json"
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(json.dumps(_library_payload(), indent=2), encoding="utf-8")

        request = build_render_request(
            _production_package(),
            render_id="RENDER-CERT-0045F",
            video_id="VID-CERT-0045F",
        )
        runtime = FfmpegRenderRuntime(
            FfmpegRuntimeConfig(workspace=workspace),
            runner=_fake_runner,
        )
        result = runtime.render(request)
        if result.status != "succeeded":
            raise RuntimeError(f"integrated render failed: {result.failure_reason}")

        fixed_now = datetime(2026, 7, 30, 9, 30, tzinfo=timezone.utc)
        promoted = promote_render_result(
            library_path,
            request,
            result,
            clock=lambda: fixed_now,
        )
        reloaded = load_video_library(library_path)
        if promoted != reloaded:
            raise RuntimeError("persisted video library does not match promoted library")

        asset = reloaded.videos[0]
        video = workspace / request.output_path
        thumbnail = workspace / request.thumbnail_path
        subtitles = workspace / request.subtitles_path

        if asset.status != "ready":
            raise RuntimeError("final asset was not promoted to ready")
        if asset.video_file is None:
            raise RuntimeError("final asset video evidence is missing")
        if asset.video_file.checksum_sha256 != result.checksum_sha256:
            raise RuntimeError("final asset checksum does not match render result")
        if asset.video_file.size_bytes != result.size_bytes:
            raise RuntimeError("final asset size does not match render result")
        if not all(path.is_file() and path.stat().st_size > 0 for path in (video, thumbnail, subtitles)):
            raise RuntimeError("one or more final render outputs are missing")
        if asset.thumbnail_path != request.thumbnail_path:
            raise RuntimeError("thumbnail path was not promoted")
        if asset.subtitles_path != request.subtitles_path:
            raise RuntimeError("subtitle path was not promoted")
        if asset.render_engine != "ffmpeg":
            raise RuntimeError("render engine attribution is missing")
        if list(library_path.parent.glob(f".{library_path.name}.*.tmp")):
            raise RuntimeError("temporary library files remain after atomic promotion")

        return {
            "artifact": "FOOTBALL-SHORTS-AI-0045F",
            "status": "PASS",
            "production_to_request": "PASS",
            "request_to_runtime": "PASS",
            "video_output": "PASS",
            "subtitle_output": "PASS",
            "thumbnail_output": "PASS",
            "checksum_binding": "PASS",
            "atomic_library_promotion": "PASS",
            "dashboard_asset_ready": "PASS",
            "scene_count": len(request.scenes),
            "video_count": len(reloaded.videos),
        }


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0045F")
    print("FINAL GOVERNED VIDEO RENDERING CERTIFICATION")
    print("=" * 72)
    for key, value in certify().items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
