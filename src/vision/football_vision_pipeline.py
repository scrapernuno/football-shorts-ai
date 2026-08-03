"""
FOOTBALL-SHORTS-AI-0057A
FOOTBALL COMPUTER VISION PIPELINE CONTRACT

Provider-neutral, deterministic contracts for local/authorized video analysis.
This module does not download media, call networks, execute external models,
render video, train models or publish content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


class FootballVisionPipelineError(ValueError):
    """Raised when governed vision evidence is invalid."""


SUPPORTED_RIGHTS = {"owned", "licensed", "reference_only"}
SUPPORTED_PIPELINE_STATES = {"planned", "analyzed", "blocked"}
SUPPORTED_EVENT_TYPES = {
    "unknown",
    "build_up",
    "pass",
    "dribble",
    "shot",
    "goal",
    "save",
    "celebration",
    "crowd_reaction",
    "replay",
    "card",
    "var",
    "trophy",
}


class VisionProvider(Protocol):
    provider_name: str

    def analyze(self, request: "VisionAnalysisRequest") -> Mapping[str, object]: ...


@dataclass(frozen=True)
class VisionAnalysisRequest:
    asset_id: str
    source_uri: str
    source_sha256: str
    duration_seconds: float
    rights_status: str
    sample_fps: float = 2.0

    def validate(self) -> None:
        if not self.asset_id.startswith("EXT-"):
            raise FootballVisionPipelineError("asset_id must start with EXT-")
        if not self.source_uri.strip():
            raise FootballVisionPipelineError("source_uri is required")
        _validate_sha256(self.source_sha256)
        if self.duration_seconds <= 0 or self.duration_seconds > 21600:
            raise FootballVisionPipelineError("duration_seconds is outside governed limits")
        if self.rights_status not in SUPPORTED_RIGHTS:
            raise FootballVisionPipelineError("unsupported rights_status")
        if not 0.1 <= self.sample_fps <= 30.0:
            raise FootballVisionPipelineError("sample_fps must be between 0.1 and 30")

    @property
    def analysis_allowed(self) -> bool:
        return self.rights_status in {"owned", "licensed"}

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "asset_id": self.asset_id,
            "source_uri": self.source_uri,
            "source_sha256": self.source_sha256,
            "duration_seconds": round(float(self.duration_seconds), 3),
            "rights_status": self.rights_status,
            "sample_fps": round(float(self.sample_fps), 3),
            "analysis_allowed": self.analysis_allowed,
        }


@dataclass(frozen=True)
class VisionFrame:
    frame_id: str
    frame_number: int
    timestamp_seconds: float
    width: int
    height: int
    frame_sha256: str

    def validate(self, request: VisionAnalysisRequest) -> None:
        if not self.frame_id.startswith("VFRAME-"):
            raise FootballVisionPipelineError("invalid frame identity")
        if self.frame_number < 0:
            raise FootballVisionPipelineError("frame_number must be non-negative")
        if not 0 <= self.timestamp_seconds <= request.duration_seconds:
            raise FootballVisionPipelineError("frame timestamp is outside asset duration")
        if self.width < 1 or self.height < 1:
            raise FootballVisionPipelineError("frame dimensions must be positive")
        _validate_sha256(self.frame_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "frame_number": self.frame_number,
            "timestamp_seconds": round(float(self.timestamp_seconds), 3),
            "width": self.width,
            "height": self.height,
            "frame_sha256": self.frame_sha256,
        }


@dataclass(frozen=True)
class VisionEvent:
    event_id: str
    event_type: str
    start_seconds: float
    end_seconds: float
    confidence: float
    labels: tuple[str, ...]
    evidence_frame_ids: tuple[str, ...]

    def validate(self, request: VisionAnalysisRequest, frame_ids: set[str]) -> None:
        if not self.event_id.startswith("VEVENT-"):
            raise FootballVisionPipelineError("invalid event identity")
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise FootballVisionPipelineError("unsupported event type")
        if not 0 <= self.start_seconds < self.end_seconds <= request.duration_seconds:
            raise FootballVisionPipelineError("event timestamps are invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise FootballVisionPipelineError("event confidence must be between 0 and 1")
        if tuple(sorted(set(self.labels))) != self.labels:
            raise FootballVisionPipelineError("event labels must be normalized")
        if not self.evidence_frame_ids or any(item not in frame_ids for item in self.evidence_frame_ids):
            raise FootballVisionPipelineError("event must reference valid evidence frames")

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "confidence": round(float(self.confidence), 4),
            "labels": list(self.labels),
            "evidence_frame_ids": list(self.evidence_frame_ids),
        }


@dataclass(frozen=True)
class VisionScene:
    scene_id: str
    start_seconds: float
    end_seconds: float
    representative_frame_id: str
    event_ids: tuple[str, ...]
    motion_score: float
    visual_quality_score: float

    def validate(self, request: VisionAnalysisRequest, frame_ids: set[str], event_ids: set[str]) -> None:
        if not self.scene_id.startswith("VSCENE-"):
            raise FootballVisionPipelineError("invalid scene identity")
        if not 0 <= self.start_seconds < self.end_seconds <= request.duration_seconds:
            raise FootballVisionPipelineError("scene timestamps are invalid")
        if self.representative_frame_id not in frame_ids:
            raise FootballVisionPipelineError("scene representative frame is invalid")
        if any(item not in event_ids for item in self.event_ids):
            raise FootballVisionPipelineError("scene references invalid events")
        for value in (self.motion_score, self.visual_quality_score):
            if not 0.0 <= value <= 1.0:
                raise FootballVisionPipelineError("scene score must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "representative_frame_id": self.representative_frame_id,
            "event_ids": list(self.event_ids),
            "motion_score": round(float(self.motion_score), 4),
            "visual_quality_score": round(float(self.visual_quality_score), 4),
        }


@dataclass(frozen=True)
class FootballVisionReport:
    schema: str
    report_id: str
    request: VisionAnalysisRequest
    provider_name: str
    frames: tuple[VisionFrame, ...]
    events: tuple[VisionEvent, ...]
    scenes: tuple[VisionScene, ...]
    pipeline_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        self.request.validate()
        if self.schema != "football-shorts-ai.football-vision-report.v1":
            raise FootballVisionPipelineError("unsupported vision report schema")
        if not self.report_id.startswith("VISION-"):
            raise FootballVisionPipelineError("invalid vision report identity")
        if not self.provider_name.strip():
            raise FootballVisionPipelineError("provider_name is required")
        if self.pipeline_state not in SUPPORTED_PIPELINE_STATES:
            raise FootballVisionPipelineError("unsupported pipeline state")
        if self.pipeline_state == "analyzed" and (self.blockers or not self.request.analysis_allowed):
            raise FootballVisionPipelineError("analyzed report cannot contain blockers")
        if self.pipeline_state == "blocked" and not self.blockers:
            raise FootballVisionPipelineError("blocked report requires blockers")
        frame_ids = {item.frame_id for item in self.frames}
        event_ids = {item.event_id for item in self.events}
        if len(frame_ids) != len(self.frames) or len(event_ids) != len(self.events):
            raise FootballVisionPipelineError("frame and event identities must be unique")
        for frame in self.frames:
            frame.validate(self.request)
        for event in self.events:
            event.validate(self.request, frame_ids)
        cursor = 0.0
        for scene in self.scenes:
            scene.validate(self.request, frame_ids, event_ids)
            if scene.start_seconds < cursor:
                raise FootballVisionPipelineError("vision scenes cannot overlap")
            cursor = scene.end_seconds
        if self.pipeline_state == "analyzed" and (not self.frames or not self.scenes):
            raise FootballVisionPipelineError("analyzed report requires frames and scenes")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise FootballVisionPipelineError("0057A cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FootballVisionPipelineError("vision report evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "report_id": self.report_id,
            "request": self.request.to_dict(),
            "provider_name": self.provider_name,
            "frames": [item.to_dict() for item in self.frames],
            "events": [item.to_dict() for item in self.events],
            "scenes": [item.to_dict() for item in self.scenes],
            "pipeline_state": self.pipeline_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_football_vision_report(
    *,
    request: VisionAnalysisRequest,
    provider_name: str,
    frames: Sequence[Mapping[str, object]] = (),
    events: Sequence[Mapping[str, object]] = (),
    scenes: Sequence[Mapping[str, object]] = (),
) -> FootballVisionReport:
    request.validate()
    blockers: list[str] = []
    if not request.analysis_allowed:
        blockers.append("REFERENCE_ONLY_VISION_ANALYSIS_BLOCKED")
    parsed_frames = tuple(_frame(item) for item in frames)
    parsed_events = tuple(_event(item) for item in events)
    parsed_scenes = tuple(_scene(item) for item in scenes)
    if request.analysis_allowed and (not parsed_frames or not parsed_scenes):
        blockers.append("VISION_EVIDENCE_INCOMPLETE")
    state = "blocked" if blockers else "analyzed"
    core = {
        "schema": "football-shorts-ai.football-vision-report.v1",
        "request": request.to_dict(),
        "provider_name": provider_name.strip(),
        "frames": [item.to_dict() for item in parsed_frames],
        "events": [item.to_dict() for item in parsed_events],
        "scenes": [item.to_dict() for item in parsed_scenes],
        "pipeline_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    report_id = f"VISION-{provisional[:20].upper()}"
    unsigned = {**core, "report_id": report_id}
    report = FootballVisionReport(
        report_id=report_id,
        evidence_sha256=canonical_sha256(unsigned),
        request=request,
        provider_name=provider_name.strip(),
        frames=parsed_frames,
        events=parsed_events,
        scenes=parsed_scenes,
        pipeline_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.football-vision-report.v1",
    )
    report.validate()
    return report


def _frame(item: Mapping[str, object]) -> VisionFrame:
    core = {
        "frame_number": int(item["frame_number"]),
        "timestamp_seconds": float(item["timestamp_seconds"]),
        "width": int(item["width"]),
        "height": int(item["height"]),
        "frame_sha256": str(item["frame_sha256"]),
    }
    return VisionFrame(frame_id=f"VFRAME-{canonical_sha256(core)[:20].upper()}", **core)


def _event(item: Mapping[str, object]) -> VisionEvent:
    core = {
        "event_type": str(item.get("event_type", "unknown")),
        "start_seconds": float(item["start_seconds"]),
        "end_seconds": float(item["end_seconds"]),
        "confidence": float(item.get("confidence", 0.0)),
        "labels": tuple(sorted(set(str(value).strip().lower().replace(" ", "_") for value in item.get("labels", ()) if str(value).strip()))),
        "evidence_frame_ids": tuple(str(value) for value in item.get("evidence_frame_ids", ())),
    }
    return VisionEvent(event_id=f"VEVENT-{canonical_sha256(core)[:20].upper()}", **core)


def _scene(item: Mapping[str, object]) -> VisionScene:
    core = {
        "start_seconds": float(item["start_seconds"]),
        "end_seconds": float(item["end_seconds"]),
        "representative_frame_id": str(item["representative_frame_id"]),
        "event_ids": tuple(str(value) for value in item.get("event_ids", ())),
        "motion_score": float(item.get("motion_score", 0.0)),
        "visual_quality_score": float(item.get("visual_quality_score", 0.0)),
    }
    return VisionScene(scene_id=f"VSCENE-{canonical_sha256(core)[:20].upper()}", **core)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise FootballVisionPipelineError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FootballVisionPipelineError("evidence must be hexadecimal") from exc


__all__ = [
    "FootballVisionPipelineError",
    "FootballVisionReport",
    "VisionAnalysisRequest",
    "VisionEvent",
    "VisionFrame",
    "VisionProvider",
    "VisionScene",
    "build_football_vision_report",
    "canonical_sha256",
]
