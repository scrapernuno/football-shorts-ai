from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from video.rendering import RenderRequest, RenderResult

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class FfmpegRuntimeConfig:
    ffmpeg_binary: str = "ffmpeg"
    workspace: Path = Path("dashboard")
    font_file: Path | None = None
    background_color: str = "0x07111f"
    text_color: str = "white"
    font_size: int = 68
    timeout_seconds: int = 180

    def __post_init__(self) -> None:
        if not self.ffmpeg_binary.strip():
            raise ValueError("ffmpeg_binary must not be empty")
        if self.font_size <= 0:
            raise ValueError("font_size must be greater than zero")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")


class FfmpegRenderRuntime:
    """Concrete deterministic renderer backed by FFmpeg.

    The runtime creates a vertical video from the governed scene timeline. It does
    not fetch remote assets and never uses shell=True. All output paths remain
    confined to the configured workspace.
    """

    def __init__(
        self,
        config: FfmpegRuntimeConfig | None = None,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config or FfmpegRuntimeConfig()
        self._runner = runner or self._run_command

    def render(self, request: RenderRequest) -> RenderResult:
        try:
            output = self._resolve_output(request.output_path)
            thumbnail = self._resolve_output(request.thumbnail_path)
            subtitles = self._resolve_output(request.subtitles_path)
            for path in (output, thumbnail, subtitles):
                path.parent.mkdir(parents=True, exist_ok=True)

            self._emit_vtt(request, subtitles)
            self._runner(self.build_video_command(request, output, subtitles))
            self._runner(self.build_thumbnail_command(output, thumbnail))

            if not output.is_file() or output.stat().st_size <= 0:
                raise RuntimeError("FFmpeg did not materialize a non-empty video file")
            if not thumbnail.is_file() or thumbnail.stat().st_size <= 0:
                raise RuntimeError("FFmpeg did not materialize a non-empty thumbnail")
            if not subtitles.is_file() or subtitles.stat().st_size <= 0:
                raise RuntimeError("subtitle emission did not materialize a non-empty VTT file")

            return RenderResult(
                render_id=request.render_id,
                video_id=request.video_id,
                status="succeeded",
                output_path=request.output_path,
                thumbnail_path=request.thumbnail_path,
                subtitles_path=request.subtitles_path,
                checksum_sha256=_sha256(output),
                size_bytes=output.stat().st_size,
            )
        except Exception as exc:  # fail closed: no partial governed outputs exposed
            return RenderResult(
                render_id=request.render_id,
                video_id=request.video_id,
                status="failed",
                failure_reason=f"{type(exc).__name__}: {exc}",
            )

    def build_video_command(
        self,
        request: RenderRequest,
        output: Path,
        subtitles: Path,
    ) -> tuple[str, ...]:
        filters = [
            f"scale={request.width}:{request.height}",
            "format=yuv420p",
        ]
        filters.extend(self._drawtext_filter(scene, request) for scene in request.scenes)
        filters.append(f"subtitles={_escape_filter_path(subtitles)}")

        codec_args: tuple[str, ...]
        if request.container == "mp4":
            codec_args = ("-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart")
        else:
            codec_args = ("-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0")

        return (
            self.config.ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={self.config.background_color}:s={request.width}x{request.height}:r={request.fps}:d={request.duration_seconds}",
            "-vf",
            ",".join(filters),
            "-an",
            "-r",
            str(request.fps),
            *codec_args,
            str(output),
        )

    def build_thumbnail_command(self, video: Path, thumbnail: Path) -> tuple[str, ...]:
        return (
            self.config.ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "0.5",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(thumbnail),
        )

    def _drawtext_filter(self, scene, request: RenderRequest) -> str:
        text = _escape_drawtext(scene.screen_text)
        font = ""
        if self.config.font_file is not None:
            font = f"fontfile={_escape_filter_path(self.config.font_file)}:"
        start = _format_time(scene.start_second)
        end = _format_time(scene.end_second)
        return (
            "drawtext="
            f"{font}text='{text}':"
            f"fontcolor={self.config.text_color}:fontsize={self.config.font_size}:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            "box=1:boxcolor=black@0.58:boxborderw=28:"
            f"enable='between(t,{start},{end})'"
        )

    def _emit_vtt(self, request: RenderRequest, path: Path) -> None:
        lines = ["WEBVTT", ""]
        for scene in request.scenes:
            lines.extend(
                (
                    f"{_vtt_time(scene.start_second)} --> {_vtt_time(scene.end_second)}",
                    scene.narration.strip(),
                    "",
                )
            )
        path.write_text("\n".join(lines), encoding="utf-8")

    def _resolve_output(self, relative_path: str) -> Path:
        root = self.config.workspace.resolve()
        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("render output escaped the configured workspace")
        return candidate

    def _run_command(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_time(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _vtt_time(value: float) -> str:
    milliseconds = max(0, round(value * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _escape_drawtext(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def _escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
