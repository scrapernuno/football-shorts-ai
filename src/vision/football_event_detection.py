"""
FOOTBALL-SHORTS-AI-0057D
FOOTBALL EVENT DETECTION AND TEMPORAL EVIDENCE CONTRACT

Consolidates deterministic football-event evidence from 0057A vision reports and
optional 0057B/0057C context. This module performs no network access, acquisition,
external model execution, training, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_vision_pipeline import FootballVisionReport


class FootballEventDetectionError(ValueError):
    """Raised when governed event evidence is invalid."""


SUPPORTED_EVENTS = {
    "build_up", "pass", "dribble", "cross", "shot", "goal", "save",
    "penalty", "free_kick", "corner", "offside", "foul", "yellow_card",
    "red_card", "var", "celebration", "crowd_reaction", "replay", "trophy",
}
SUPPORTED_STATES = {"detected", "review_required", "blocked"}


@dataclass(frozen=True)
class FootballEventEvidence:
    event_id: str
    event_type: str
    start_seconds: float
    end_seconds: float
    confidence: float
    scene_id: str
    evidence_frame_ids: tuple[str, ...]
    actor_track_ids: tuple[str, ...]
    team_labels: tuple[str, ...]
    competition_label: str | None
    evidence_labels: tuple[str, ...]
    review_required: bool

    def validate(self, vision: FootballVisionReport) -> None:
        if not self.event_id.startswith("FBEVENT-"):
            raise FootballEventDetectionError("invalid football event identity")
        if self.event_type not in SUPPORTED_EVENTS:
            raise FootballEventDetectionError("unsupported football event type")
        if not 0.0 <= self.start_seconds < self.end_seconds <= vision.request.duration_seconds:
            raise FootballEventDetectionError("football event timestamps are invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise FootballEventDetectionError("event confidence must be between 0 and 1")
        scene_ids = {scene.scene_id for scene in vision.scenes}
        frame_ids = {frame.frame_id for frame in vision.frames}
        if self.scene_id not in scene_ids:
            raise FootballEventDetectionError("event references unknown scene")
        if not self.evidence_frame_ids or any(item not in frame_ids for item in self.evidence_frame_ids):
            raise FootballEventDetectionError("event must reference valid frames")
        for values, name in ((self.actor_track_ids, "actor tracks"), (self.team_labels, "team labels"), (self.evidence_labels, "evidence labels")):
            if tuple(sorted(set(values))) != values:
                raise FootballEventDetectionError(f"{name} must be normalized")
        if self.competition_label is not None and not self.competition_label.strip():
            raise FootballEventDetectionError("competition label cannot be blank")

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "start_seconds": round(float(self.start_seconds), 3),
            "end_seconds": round(float(self.end_seconds), 3),
            "confidence": round(float(self.confidence), 4),
            "scene_id": self.scene_id,
            "evidence_frame_ids": list(self.evidence_frame_ids),
            "actor_track_ids": list(self.actor_track_ids),
            "team_labels": list(self.team_labels),
            "competition_label": self.competition_label,
            "evidence_labels": list(self.evidence_labels),
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class FootballEventDetectionReport:
    schema: str
    detection_id: str
    vision_report_id: str
    provider_name: str
    events: tuple[FootballEventEvidence, ...]
    detected_event_types: tuple[str, ...]
    detection_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport) -> None:
        vision.validate()
        if self.schema != "football-shorts-ai.football-event-detection.v1":
            raise FootballEventDetectionError("unsupported event detection schema")
        if not self.detection_id.startswith("EVENTDET-"):
            raise FootballEventDetectionError("invalid event detection identity")
        if self.vision_report_id != vision.report_id:
            raise FootballEventDetectionError("vision report identity mismatch")
        if not self.provider_name.strip():
            raise FootballEventDetectionError("provider_name is required")
        if self.detection_state not in SUPPORTED_STATES:
            raise FootballEventDetectionError("unsupported detection state")
        event_ids = {event.event_id for event in self.events}
        if len(event_ids) != len(self.events):
            raise FootballEventDetectionError("event identities must be unique")
        for event in self.events:
            event.validate(vision)
        expected_types = tuple(sorted({event.event_type for event in self.events}))
        if self.detected_event_types != expected_types:
            raise FootballEventDetectionError("detected event types are inconsistent")
        if self.detection_state == "detected" and (self.blockers or not self.events):
            raise FootballEventDetectionError("detected report requires unblocked evidence")
        if self.detection_state in {"review_required", "blocked"} and not self.blockers:
            raise FootballEventDetectionError("non-ready report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise FootballEventDetectionError("0057D cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FootballEventDetectionError("event detection evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "detection_id": self.detection_id,
            "vision_report_id": self.vision_report_id,
            "provider_name": self.provider_name,
            "events": [event.to_dict() for event in self.events],
            "detected_event_types": list(self.detected_event_types),
            "detection_state": self.detection_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_football_event_detection_report(
    *,
    vision: FootballVisionReport,
    provider_name: str,
    detections: Sequence[Mapping[str, object]] = (),
    minimum_confidence: float = 0.70,
) -> FootballEventDetectionReport:
    vision.validate()
    if not 0.0 <= minimum_confidence <= 1.0:
        raise FootballEventDetectionError("minimum_confidence must be between 0 and 1")
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    events = tuple(_event(item, minimum_confidence) for item in detections)
    if vision.pipeline_state == "analyzed" and not events:
        blockers.add("FOOTBALL_EVENT_EVIDENCE_MISSING")
    if any(event.review_required for event in events):
        blockers.add("EVENT_REVIEW_REQUIRED")
    state = "blocked" if vision.pipeline_state != "analyzed" or not events else "review_required" if blockers else "detected"
    types = tuple(sorted({event.event_type for event in events}))
    core = {
        "schema": "football-shorts-ai.football-event-detection.v1",
        "vision_report_id": vision.report_id,
        "provider_name": provider_name.strip(),
        "events": [event.to_dict() for event in events],
        "detected_event_types": list(types),
        "detection_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    detection_id = f"EVENTDET-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "detection_id": detection_id}
    report = FootballEventDetectionReport(
        schema="football-shorts-ai.football-event-detection.v1",
        detection_id=detection_id,
        vision_report_id=vision.report_id,
        provider_name=provider_name.strip(),
        events=events,
        detected_event_types=types,
        detection_state=state,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    report.validate(vision)
    return report


def _event(item: Mapping[str, object], minimum_confidence: float) -> FootballEventEvidence:
    competition = item.get("competition_label")
    competition_label = str(competition).strip() if competition is not None and str(competition).strip() else None
    confidence = float(item.get("confidence", 0.0))
    core = {
        "event_type": str(item["event_type"]).strip().lower(),
        "start_seconds": float(item["start_seconds"]),
        "end_seconds": float(item["end_seconds"]),
        "confidence": confidence,
        "scene_id": str(item["scene_id"]),
        "evidence_frame_ids": _normalized(item.get("evidence_frame_ids", ())),
        "actor_track_ids": _normalized(item.get("actor_track_ids", ())),
        "team_labels": _normalized(item.get("team_labels", ())),
        "competition_label": competition_label,
        "evidence_labels": _normalized(item.get("evidence_labels", ())),
        "review_required": confidence < minimum_confidence,
    }
    return FootballEventEvidence(event_id=f"FBEVENT-{canonical_sha256(core)[:20].upper()}", **core)


def _normalized(values: object) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise FootballEventDetectionError("evidence collection must be a sequence")
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise FootballEventDetectionError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FootballEventDetectionError("evidence must be hexadecimal") from exc


__all__ = [
    "FootballEventDetectionError",
    "FootballEventDetectionReport",
    "FootballEventEvidence",
    "build_football_event_detection_report",
    "canonical_sha256",
]
