from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

from video.ffmpeg_runtime import FfmpegRenderRuntime, FfmpegRuntimeConfig
from video.rendering import RenderRequest, RenderScene


def _fake_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    output = Path(command[-1])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}:
        output.write_bytes(b"governed-thumbnail-evidence")
    else:
        output.write_bytes(b"governed-video-evidence")
    return subprocess.CompletedProcess(list(command), 0, "", "")


def _request() -> RenderRequest:
    return RenderRequest(
        render_id="render-cert-0045d",
        video_id="video-cert-0045d",
        topic="Governed football short",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path="videos/video-cert-0045d.mp4",
        thumbnail_path="videos/video-cert-0045d.jpg",
        subtitles_path="videos/video-cert-0045d.vtt",
        scenes=(
            RenderScene(
                scene_id="scene_01",
                start_second=0,
                end_second=4,
                screen_text="The decisive moment",
                narration="The decisive moment changed the match.",
                visual_prompt="Vertical football editorial visual, stadium atmosphere",
            ),
            RenderScene(
                scene_id="scene_02",
                start_second=4,
                end_second=8,
                screen_text="History was made",
                narration="History was made in eight unforgettable seconds.",
                visual_prompt="Vertical football celebration, cinematic lighting",
            ),
        ),
    )


def certify() -> dict[str, str | int]:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0045d-") as temp_dir:
        workspace = Path(temp_dir)
        runtime = FfmpegRenderRuntime(
            FfmpegRuntimeConfig(workspace=workspace),
            runner=_fake_runner,
        )
        request = _request()
        result = runtime.render(request)

        if result.status != "succeeded":
            raise RuntimeError(f"controlled render failed: {result.failure_reason}")

        video = workspace / request.output_path
        thumbnail = workspace / request.thumbnail_path
        subtitles = workspace / request.subtitles_path

        if not video.is_file() or video.stat().st_size <= 0:
            raise RuntimeError("non-empty video evidence missing")
        if not thumbnail.is_file() or thumbnail.stat().st_size <= 0:
            raise RuntimeError("non-empty thumbnail evidence missing")
        if not subtitles.is_file() or subtitles.stat().st_size <= 0:
            raise RuntimeError("non-empty subtitle evidence missing")

        vtt = subtitles.read_text(encoding="utf-8")
        required_vtt = (
            "WEBVTT",
            "00:00:00.000 --> 00:00:04.000",
            "The decisive moment changed the match.",
            "00:00:04.000 --> 00:00:08.000",
            "History was made in eight unforgettable seconds.",
        )
        missing = [marker for marker in required_vtt if marker not in vtt]
        if missing:
            raise RuntimeError(f"subtitle evidence missing markers: {missing}")

        expected_checksum = hashlib.sha256(video.read_bytes()).hexdigest()
        if result.checksum_sha256 != expected_checksum:
            raise RuntimeError("video checksum evidence mismatch")
        if result.size_bytes != video.stat().st_size:
            raise RuntimeError("video size evidence mismatch")

        thumbnail_command = runtime.build_thumbnail_command(video, thumbnail)
        if "-frames:v" not in thumbnail_command or "1" not in thumbnail_command:
            raise RuntimeError("thumbnail command does not enforce a single frame")

        return {
            "artifact": "FOOTBALL-SHORTS-AI-0045D",
            "status": "PASS",
            "video_output": "PASS",
            "subtitle_vtt": "PASS",
            "thumbnail_output": "PASS",
            "checksum_capture": "PASS",
            "size_capture": "PASS",
            "fail_closed_contract": "PASS",
            "scene_count": len(request.scenes),
        }


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0045D")
    print("GOVERNED SUBTITLE AND THUMBNAIL OUTPUT CERTIFICATION")
    print("=" * 72)
    for key, value in certify().items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
