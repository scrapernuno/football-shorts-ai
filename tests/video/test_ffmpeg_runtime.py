from __future__ import annotations

import subprocess
from pathlib import Path

from video.ffmpeg_runtime import FfmpegRenderRuntime, FfmpegRuntimeConfig
from video.rendering import RenderRequest, RenderScene


def request() -> RenderRequest:
    return RenderRequest(
        render_id="RENDER-0001",
        video_id="VID-0001",
        topic="Football test",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path="videos/VID-0001.mp4",
        thumbnail_path="videos/VID-0001.jpg",
        subtitles_path="videos/VID-0001.vtt",
        scenes=(
            RenderScene(
                scene_id="scene_01",
                start_second=0,
                end_second=4,
                screen_text="Opening: goal!",
                narration="Opening goal.",
                visual_prompt="Vertical football opening",
            ),
            RenderScene(
                scene_id="scene_02",
                start_second=4,
                end_second=8,
                screen_text="Final scene",
                narration="Final scene narration.",
                visual_prompt="Vertical football ending",
            ),
        ),
    )


def test_build_video_command_is_deterministic_and_shell_free(tmp_path: Path) -> None:
    runtime = FfmpegRenderRuntime(FfmpegRuntimeConfig(workspace=tmp_path))
    render_request = request()
    output = tmp_path / render_request.output_path
    subtitles = tmp_path / render_request.subtitles_path

    first = runtime.build_video_command(render_request, output, subtitles)
    second = runtime.build_video_command(render_request, output, subtitles)

    assert first == second
    assert first[0] == "ffmpeg"
    assert "lavfi" in first
    assert "libx264" in first
    assert "subtitles=" in first[first.index("-vf") + 1]
    assert "between(t,0,4)" in first[first.index("-vf") + 1]
    assert isinstance(first, tuple)


def test_render_materializes_governed_evidence_with_injected_runner(tmp_path: Path) -> None:
    commands: list[tuple[str, ...]] = []

    def runner(command):
        normalized = tuple(command)
        commands.append(normalized)
        target = Path(normalized[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"rendered-evidence")
        return subprocess.CompletedProcess(normalized, 0, "", "")

    runtime = FfmpegRenderRuntime(
        FfmpegRuntimeConfig(workspace=tmp_path),
        runner=runner,
    )
    result = runtime.render(request())

    assert result.status == "succeeded"
    assert result.output_path == "videos/VID-0001.mp4"
    assert result.thumbnail_path == "videos/VID-0001.jpg"
    assert result.subtitles_path == "videos/VID-0001.vtt"
    assert result.size_bytes == len(b"rendered-evidence")
    assert result.checksum_sha256 is not None
    assert len(result.checksum_sha256) == 64
    assert len(commands) == 2

    vtt = (tmp_path / "videos/VID-0001.vtt").read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:04.000" in vtt
    assert "Opening goal." in vtt


def test_render_fails_closed_without_exposing_partial_outputs(tmp_path: Path) -> None:
    def runner(command):
        raise subprocess.CalledProcessError(1, command, stderr="ffmpeg failed")

    runtime = FfmpegRenderRuntime(
        FfmpegRuntimeConfig(workspace=tmp_path),
        runner=runner,
    )
    result = runtime.render(request())

    assert result.status == "failed"
    assert result.failure_reason is not None
    assert "CalledProcessError" in result.failure_reason
    assert result.output_path is None
    assert result.thumbnail_path is None
    assert result.subtitles_path is None
    assert result.checksum_sha256 is None
    assert result.size_bytes is None


def test_thumbnail_command_is_governed(tmp_path: Path) -> None:
    runtime = FfmpegRenderRuntime(FfmpegRuntimeConfig(workspace=tmp_path))
    command = runtime.build_thumbnail_command(
        tmp_path / "videos/video.mp4",
        tmp_path / "videos/video.jpg",
    )

    assert command[:4] == ("ffmpeg", "-hide_banner", "-loglevel", "error")
    assert "-frames:v" in command
    assert command[-1].endswith("video.jpg")
