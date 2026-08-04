"""FOOTBALL-SHORTS-AI-0061D — controlled render result intake.

Validates a completed 0061B render result and creates deterministic review evidence.
No publishing, network access or further rendering is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class RenderResultIntakeError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class RenderResultIntake:
    schema: str
    intake_id: str
    execution_id: str
    render_package_id: str
    output_uri: str
    output_sha256: str
    duration_seconds: float
    width: int
    height: int
    video_codec: str
    audio_codec: str
    reviewer: str
    review_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    publication_allowed: bool = False
    auto_publish: bool = False
    network_enabled: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "intake_id": self.intake_id,
            "execution_id": self.execution_id,
            "render_package_id": self.render_package_id,
            "output_uri": self.output_uri,
            "output_sha256": self.output_sha256,
            "duration_seconds": round(self.duration_seconds, 3),
            "width": self.width,
            "height": self.height,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "reviewer": self.reviewer,
            "review_state": self.review_state,
            "blockers": list(self.blockers),
            "publication_allowed": False,
            "auto_publish": False,
            "network_enabled": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.render-result-intake.v1":
            raise RenderResultIntakeError("unsupported schema")
        if not self.intake_id.startswith("RENDERINTAKE-"):
            raise RenderResultIntakeError("invalid intake identity")
        if not self.execution_id.startswith("FFMPEGEXEC-") or not self.render_package_id.startswith("RENDERPKG-"):
            raise RenderResultIntakeError("invalid upstream identity")
        if len(self.output_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.output_sha256):
            raise RenderResultIntakeError("invalid output sha256")
        if self.review_state not in {"ready_for_review", "review_required", "blocked"}:
            raise RenderResultIntakeError("unsupported review state")
        if self.review_state == "ready_for_review" and self.blockers:
            raise RenderResultIntakeError("ready result cannot have blockers")
        if self.review_state != "ready_for_review" and not self.blockers:
            raise RenderResultIntakeError("non-ready result requires blockers")
        if any((self.publication_allowed, self.auto_publish, self.network_enabled)):
            raise RenderResultIntakeError("0061D cannot enable publication or network")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise RenderResultIntakeError("evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_render_result_intake(*, result: Mapping[str, object], probe: Mapping[str, object], reviewer: str) -> RenderResultIntake:
    blockers: set[str] = set()
    execution_id = str(result.get("execution_id", ""))
    package_id = str(result.get("render_package_id", ""))
    output_uri = str(result.get("output_uri", ""))
    output_sha = str(result.get("output_sha256", "")).lower()
    if result.get("return_code") != 0:
        blockers.add("RENDER_EXECUTION_NOT_SUCCESSFUL")
    if result.get("publication_performed") is not False or result.get("network_used") is not False:
        blockers.add("PROHIBITED_OPERATION_REPORTED")
    if not output_uri:
        blockers.add("RENDER_OUTPUT_MISSING")
    if len(output_sha) != 64 or any(c not in "0123456789abcdef" for c in output_sha):
        blockers.add("RENDER_OUTPUT_SHA256_INVALID")
    duration = float(probe.get("duration_seconds", 0) or 0)
    width = int(probe.get("width", 0) or 0)
    height = int(probe.get("height", 0) or 0)
    video_codec = str(probe.get("video_codec", ""))
    audio_codec = str(probe.get("audio_codec", ""))
    if duration <= 0:
        blockers.add("RENDER_DURATION_INVALID")
    if (width, height) != (1080, 1920):
        blockers.add("RENDER_DIMENSIONS_INVALID")
    if video_codec not in {"h264", "libx264"}:
        blockers.add("RENDER_VIDEO_CODEC_INVALID")
    if audio_codec != "aac":
        blockers.add("RENDER_AUDIO_CODEC_INVALID")
    if not reviewer.strip():
        blockers.add("HUMAN_REVIEWER_REQUIRED")
    state = "ready_for_review" if not blockers else "blocked"
    core = {
        "schema": "football-shorts-ai.render-result-intake.v1",
        "execution_id": execution_id,
        "render_package_id": package_id,
        "output_uri": output_uri,
        "output_sha256": output_sha,
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "reviewer": reviewer.strip(),
        "review_state": state,
        "blockers": sorted(blockers),
        "publication_allowed": False,
        "auto_publish": False,
        "network_enabled": False,
    }
    intake_id = f"RENDERINTAKE-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "intake_id": intake_id}
    item = RenderResultIntake(
        schema=core["schema"], intake_id=intake_id, execution_id=execution_id,
        render_package_id=package_id, output_uri=output_uri, output_sha256=output_sha,
        duration_seconds=duration, width=width, height=height, video_codec=video_codec,
        audio_codec=audio_codec, reviewer=reviewer.strip(), review_state=state,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    item.validate()
    return item


__all__ = ["RenderResultIntake", "RenderResultIntakeError", "build_render_result_intake", "canonical_sha256"]
