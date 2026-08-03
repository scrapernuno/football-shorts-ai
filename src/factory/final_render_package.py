"""FOOTBALL-SHORTS-AI-0060I — deterministic final render package design.

The module builds a governed render manifest and an inert FFmpeg command plan.
It never executes FFmpeg, reads media, downloads assets, renders or publishes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class FinalRenderPackageError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RenderInput:
    input_id: str
    kind: str
    source_uri: str
    rights_status: str
    required: bool
    authorized: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.input_id.startswith("RENDERINPUT-"):
            raise FinalRenderPackageError("invalid render input identity")
        if self.kind not in {"video", "subtitle", "voiceover", "music", "ambience", "sfx", "graphics", "thumbnail"}:
            raise FinalRenderPackageError("unsupported render input kind")
        if self.rights_status not in {"owned", "licensed", "reference_only", "not_applicable"}:
            raise FinalRenderPackageError("unsupported rights status")
        if self.rights_status == "reference_only" and self.authorized:
            raise FinalRenderPackageError("reference-only input cannot be authorized")
        if self.authorized and (not self.source_uri or self.blockers):
            raise FinalRenderPackageError("authorized input must be complete and unblocked")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise FinalRenderPackageError("blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "input_id": self.input_id,
            "kind": self.kind,
            "source_uri": self.source_uri,
            "rights_status": self.rights_status,
            "required": self.required,
            "authorized": self.authorized,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FFmpegExecutionDesign:
    executable: str
    arguments: tuple[str, ...]
    output_uri: str
    command_preview: str
    execution_enabled: bool = False

    def validate(self) -> None:
        if self.executable != "ffmpeg":
            raise FinalRenderPackageError("only ffmpeg design is supported")
        if not self.arguments or not self.output_uri:
            raise FinalRenderPackageError("incomplete ffmpeg design")
        if self.execution_enabled:
            raise FinalRenderPackageError("0060I cannot enable ffmpeg execution")
        expected = " ".join((self.executable, *self.arguments))
        if self.command_preview != expected:
            raise FinalRenderPackageError("ffmpeg command preview mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "executable": self.executable,
            "arguments": list(self.arguments),
            "output_uri": self.output_uri,
            "command_preview": self.command_preview,
            "execution_enabled": False,
        }


@dataclass(frozen=True)
class FinalRenderPackage:
    schema: str
    render_package_id: str
    timeline_id: str
    output_format: str
    width: int
    height: int
    fps: int
    video_codec: str
    audio_codec: str
    duration_seconds: float
    inputs: tuple[RenderInput, ...]
    ffmpeg_design: FFmpegExecutionDesign
    package_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    ffmpeg_execution_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "render_package_id": self.render_package_id,
            "timeline_id": self.timeline_id,
            "output_format": self.output_format,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "duration_seconds": round(self.duration_seconds, 3),
            "inputs": [item.to_dict() for item in self.inputs],
            "ffmpeg_design": self.ffmpeg_design.to_dict(),
            "package_state": self.package_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "ffmpeg_execution_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.final-render-package.v1":
            raise FinalRenderPackageError("unsupported render package schema")
        if not self.render_package_id.startswith("RENDERPKG-") or not self.timeline_id.startswith("TIMELINE-"):
            raise FinalRenderPackageError("invalid render package identity")
        if self.output_format != "mp4" or (self.width, self.height) != (1080, 1920):
            raise FinalRenderPackageError("0060I output must be vertical 1080x1920 MP4")
        if self.fps not in {25, 30, 50, 60}:
            raise FinalRenderPackageError("unsupported frame rate")
        if self.video_codec != "libx264" or self.audio_codec != "aac":
            raise FinalRenderPackageError("unsupported codecs")
        if self.duration_seconds <= 0:
            raise FinalRenderPackageError("invalid render duration")
        for item in self.inputs:
            item.validate()
        self.ffmpeg_design.validate()
        if self.package_state not in {"ready_for_authorization", "review_required", "blocked"}:
            raise FinalRenderPackageError("unsupported package state")
        if self.package_state == "ready_for_authorization":
            if self.blockers or not self.inputs or any(item.required and not item.authorized for item in self.inputs):
                raise FinalRenderPackageError("ready package requires authorized required inputs")
        elif not self.blockers:
            raise FinalRenderPackageError("non-ready package requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.ffmpeg_execution_enabled, self.auto_publish)):
            raise FinalRenderPackageError("0060I cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FinalRenderPackageError("render package evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def _make_input(kind: str, payload: Mapping[str, object], *, required: bool) -> RenderInput:
    uri = str(payload.get("source_uri") or payload.get("output_uri") or payload.get("track_uri") or "")
    rights = str(payload.get("rights_status", "not_applicable"))
    state = str(payload.get("state") or payload.get("preview_state") or payload.get("subtitle_state") or payload.get("synchronization_state") or payload.get("mix_state") or payload.get("graphics_state") or payload.get("composition_state") or "")
    accepted_states = {
        "video": {"preview_ready", "composed"},
        "subtitle": {"generated"},
        "voiceover": {"synchronized"},
        "music": {"mixed"}, "ambience": {"mixed"}, "sfx": {"mixed"},
        "graphics": {"composed"}, "thumbnail": {"composed"},
    }[kind]
    blockers: set[str] = set()
    if required and not uri:
        blockers.add(f"{kind.upper()}_SOURCE_MISSING")
    if rights == "reference_only":
        blockers.add(f"{kind.upper()}_NOT_AUTHORIZED")
    if required and state not in accepted_states:
        blockers.add(f"{kind.upper()}_NOT_READY")
    authorized = not blockers and bool(uri)
    core = {"kind": kind, "source_uri": uri, "rights_status": rights, "required": required, "authorized": authorized, "blockers": sorted(blockers)}
    return RenderInput(input_id=f"RENDERINPUT-{canonical_sha256(core)[:20].upper()}", kind=kind, source_uri=uri, rights_status=rights, required=required, authorized=authorized, blockers=tuple(sorted(blockers)))


def build_final_render_package(
    *,
    timeline: Mapping[str, object],
    preview: Mapping[str, object],
    subtitle: Mapping[str, object] | None = None,
    voiceover: Mapping[str, object] | None = None,
    audio_mix: Mapping[str, object] | None = None,
    graphics: Mapping[str, object] | None = None,
    thumbnail: Mapping[str, object] | None = None,
    fps: int = 30,
    output_uri: str = "artifacts/final/football-short.mp4",
) -> FinalRenderPackage:
    timeline_id = str(timeline.get("timeline_id", ""))
    duration = float(timeline.get("total_duration_seconds", 0) or 0)
    blockers: set[str] = set()
    if not timeline_id.startswith("TIMELINE-") or timeline.get("composition_state") != "composed":
        blockers.add("TIMELINE_NOT_COMPOSED")
    if preview.get("preview_state") != "preview_ready":
        blockers.add("PREVIEW_NOT_READY")

    inputs = [
        _make_input("video", preview, required=True),
        _make_input("subtitle", subtitle or {}, required=False),
        _make_input("voiceover", voiceover or {}, required=False),
        _make_input("music", audio_mix or {}, required=False),
        _make_input("graphics", graphics or {}, required=False),
        _make_input("thumbnail", thumbnail or {}, required=False),
    ]
    for item in inputs:
        if item.required and item.blockers:
            blockers.update(item.blockers)

    args = (
        "-hide_banner", "-nostdin", "-y", "-i", inputs[0].source_uri or "MISSING_VIDEO_INPUT",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output_uri,
    )
    design = FFmpegExecutionDesign(executable="ffmpeg", arguments=args, output_uri=output_uri, command_preview=" ".join(("ffmpeg", *args)))
    state = "blocked" if "TIMELINE_NOT_COMPOSED" in blockers or "PREVIEW_NOT_READY" in blockers else "review_required" if blockers else "ready_for_authorization"
    core = {
        "schema": "football-shorts-ai.final-render-package.v1",
        "timeline_id": timeline_id,
        "output_format": "mp4", "width": 1080, "height": 1920, "fps": fps,
        "video_codec": "libx264", "audio_codec": "aac", "duration_seconds": round(duration, 3),
        "inputs": [item.to_dict() for item in inputs], "ffmpeg_design": design.to_dict(),
        "package_state": state, "blockers": sorted(blockers),
        "network_enabled": False, "acquisition_enabled": False, "extraction_enabled": False,
        "render_enabled": False, "ffmpeg_execution_enabled": False, "auto_publish": False,
    }
    package_id = f"RENDERPKG-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "render_package_id": package_id}
    package = FinalRenderPackage(
        schema=core["schema"], render_package_id=package_id, timeline_id=timeline_id,
        output_format="mp4", width=1080, height=1920, fps=fps, video_codec="libx264", audio_codec="aac",
        duration_seconds=duration, inputs=tuple(inputs), ffmpeg_design=design,
        package_state=state, blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    package.validate()
    return package


__all__ = [
    "FFmpegExecutionDesign", "FinalRenderPackage", "FinalRenderPackageError", "RenderInput",
    "build_final_render_package", "canonical_sha256",
]
