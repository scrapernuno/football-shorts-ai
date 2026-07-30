from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Literal, Protocol

RenderJobStatus = Literal["planned", "running", "succeeded", "failed"]
RenderOutputContainer = Literal["mp4", "webm"]


@dataclass(frozen=True, slots=True)
class RenderScene:
    scene_id: str
    start_second: float
    end_second: float
    screen_text: str
    narration: str
    visual_prompt: str

    def __post_init__(self) -> None:
        if not self.scene_id.strip():
            raise ValueError("scene_id must not be empty")
        if self.start_second < 0:
            raise ValueError("start_second must not be negative")
        if self.end_second <= self.start_second:
            raise ValueError("end_second must be greater than start_second")
        if not self.screen_text.strip():
            raise ValueError("screen_text must not be empty")
        if not self.narration.strip():
            raise ValueError("narration must not be empty")
        if not self.visual_prompt.strip():
            raise ValueError("visual_prompt must not be empty")


@dataclass(frozen=True, slots=True)
class RenderRequest:
    render_id: str
    video_id: str
    topic: str
    width: int
    height: int
    fps: int
    container: RenderOutputContainer
    output_path: str
    thumbnail_path: str
    subtitles_path: str
    scenes: tuple[RenderScene, ...]

    def __post_init__(self) -> None:
        if not self.render_id.strip():
            raise ValueError("render_id must not be empty")
        if not self.video_id.strip():
            raise ValueError("video_id must not be empty")
        if not self.topic.strip():
            raise ValueError("topic must not be empty")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be greater than zero")
        if self.height <= self.width:
            raise ValueError("governed shorts rendering requires vertical dimensions")
        if self.fps <= 0:
            raise ValueError("fps must be greater than zero")
        if not self.scenes:
            raise ValueError("at least one render scene is required")
        _validate_relative_path(self.output_path, "output_path")
        _validate_relative_path(self.thumbnail_path, "thumbnail_path")
        _validate_relative_path(self.subtitles_path, "subtitles_path")
        if not self.output_path.casefold().endswith(f".{self.container}"):
            raise ValueError("output_path extension must match container")
        if not self.thumbnail_path.casefold().endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise ValueError("thumbnail_path must reference a supported image")
        if not self.subtitles_path.casefold().endswith(".vtt"):
            raise ValueError("subtitles_path must reference a .vtt file")
        ordered = tuple(sorted(self.scenes, key=lambda scene: scene.start_second))
        if ordered != self.scenes:
            raise ValueError("scenes must be ordered by start_second")
        for previous, current in zip(self.scenes, self.scenes[1:]):
            if current.start_second < previous.end_second:
                raise ValueError("render scenes must not overlap")

    @property
    def duration_seconds(self) -> float:
        return self.scenes[-1].end_second

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RenderResult:
    render_id: str
    video_id: str
    status: RenderJobStatus
    output_path: str | None = None
    thumbnail_path: str | None = None
    subtitles_path: str | None = None
    checksum_sha256: str | None = None
    size_bytes: int | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.render_id.strip() or not self.video_id.strip():
            raise ValueError("render_id and video_id must not be empty")
        if self.status == "succeeded":
            required = (self.output_path, self.thumbnail_path, self.subtitles_path)
            if not all(isinstance(value, str) and value.strip() for value in required):
                raise ValueError("succeeded render results require all output paths")
            _validate_relative_path(self.output_path or "", "output_path")
            _validate_relative_path(self.thumbnail_path or "", "thumbnail_path")
            _validate_relative_path(self.subtitles_path or "", "subtitles_path")
            if self.checksum_sha256 is None:
                raise ValueError("succeeded render results require checksum_sha256")
            normalized = self.checksum_sha256.strip().casefold()
            if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
                raise ValueError("checksum_sha256 must contain 64 hexadecimal characters")
            if self.size_bytes is None or self.size_bytes <= 0:
                raise ValueError("succeeded render results require positive size_bytes")
            if self.failure_reason is not None:
                raise ValueError("succeeded render results must not include failure_reason")
        elif self.status == "failed":
            if not (self.failure_reason or "").strip():
                raise ValueError("failed render results require failure_reason")
            if any(value is not None for value in (self.output_path, self.thumbnail_path, self.subtitles_path, self.checksum_sha256, self.size_bytes)):
                raise ValueError("failed render results must not expose partial governed outputs")
        else:
            if self.failure_reason is not None:
                raise ValueError("failure_reason is only valid for failed render results")

    def to_dict(self) -> dict:
        return asdict(self)


class VideoRenderRuntime(Protocol):
    def render(self, request: RenderRequest) -> RenderResult:
        """Materialize one governed video render request."""


def build_render_request(
    production_package: dict,
    *,
    render_id: str,
    video_id: str,
    output_prefix: str = "videos",
    fps: int = 30,
    container: RenderOutputContainer = "mp4",
) -> RenderRequest:
    topic = str(production_package.get("topic", "")).strip()
    scenes_payload = production_package.get("scenes")
    if not isinstance(scenes_payload, list):
        raise ValueError("production package scenes must be a list")

    scenes = tuple(
        RenderScene(
            scene_id=str(scene.get("scene_id", "")),
            start_second=float(scene.get("start_second", 0)),
            end_second=float(scene.get("end_second", 0)),
            screen_text=str(scene.get("screen_text", "")),
            narration=str(scene.get("narration", "")),
            visual_prompt=str(scene.get("visual_prompt", "")),
        )
        for scene in scenes_payload
        if isinstance(scene, dict)
    )
    if len(scenes) != len(scenes_payload):
        raise ValueError("every production scene must be an object")

    prefix = output_prefix.strip("/")
    _validate_relative_path(prefix, "output_prefix")
    return RenderRequest(
        render_id=render_id,
        video_id=video_id,
        topic=topic,
        width=1080,
        height=1920,
        fps=fps,
        container=container,
        output_path=f"{prefix}/{video_id}.{container}",
        thumbnail_path=f"{prefix}/{video_id}.jpg",
        subtitles_path=f"{prefix}/{video_id}.vtt",
        scenes=scenes,
    )


def _validate_relative_path(value: str, field_name: str) -> None:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a safe relative path")
