"""
FOOTBALL-SHORTS-AI-0057B
PLAYER DETECTION AND RECOGNITION EVIDENCE CONTRACT

Creates deterministic, reviewable person detections and identity hypotheses from
0057A vision evidence. It performs no network access, media acquisition, external
model execution, biometric enrolment, model training, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_vision_pipeline import FootballVisionReport


class PlayerRecognitionError(ValueError):
    """Raised when governed player-recognition evidence is invalid."""


SUPPORTED_ROLES = {"player", "goalkeeper", "referee", "coach", "staff", "unknown"}
SUPPORTED_STATES = {"recognized", "review_required", "blocked"}


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def validate(self) -> None:
        for name, value in (("x", self.x), ("y", self.y), ("width", self.width), ("height", self.height)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PlayerRecognitionError(f"bounding box {name} must be numeric")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise PlayerRecognitionError("bounding box origin must be normalized")
        if not 0.0 < self.width <= 1.0 or not 0.0 < self.height <= 1.0:
            raise PlayerRecognitionError("bounding box size must be normalized and positive")
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise PlayerRecognitionError("bounding box exceeds frame bounds")

    def to_dict(self) -> dict[str, float]:
        self.validate()
        return {name: round(float(getattr(self, name)), 6) for name in ("x", "y", "width", "height")}


@dataclass(frozen=True)
class PersonObservation:
    observation_id: str
    track_id: str
    frame_id: str
    scene_id: str
    timestamp_seconds: float
    role: str
    detection_confidence: float
    identity_label: str | None
    identity_confidence: float
    team_label: str | None
    shirt_number: int | None
    bounding_box: BoundingBox
    evidence_labels: tuple[str, ...]

    def validate(self, report: FootballVisionReport) -> None:
        if not self.observation_id.startswith("PERSONOBS-"):
            raise PlayerRecognitionError("invalid person observation identity")
        if not self.track_id.startswith("PTRACK-"):
            raise PlayerRecognitionError("invalid person track identity")
        frame_ids = {item.frame_id for item in report.frames}
        scene_ids = {item.scene_id for item in report.scenes}
        if self.frame_id not in frame_ids or self.scene_id not in scene_ids:
            raise PlayerRecognitionError("person observation references unknown vision evidence")
        if not 0.0 <= self.timestamp_seconds <= report.request.duration_seconds:
            raise PlayerRecognitionError("person observation timestamp is invalid")
        if self.role not in SUPPORTED_ROLES:
            raise PlayerRecognitionError("unsupported person role")
        for name, value in (("detection_confidence", self.detection_confidence), ("identity_confidence", self.identity_confidence)):
            if not 0.0 <= value <= 1.0:
                raise PlayerRecognitionError(f"{name} must be between 0 and 1")
        if self.identity_label is None and self.identity_confidence != 0.0:
            raise PlayerRecognitionError("anonymous observation cannot have identity confidence")
        if self.identity_label is not None and not self.identity_label.strip():
            raise PlayerRecognitionError("identity label cannot be blank")
        if self.team_label is not None and not self.team_label.strip():
            raise PlayerRecognitionError("team label cannot be blank")
        if self.shirt_number is not None and not 0 <= self.shirt_number <= 99:
            raise PlayerRecognitionError("shirt number must be between 0 and 99")
        if tuple(sorted(set(self.evidence_labels))) != self.evidence_labels:
            raise PlayerRecognitionError("evidence labels must be normalized")
        self.bounding_box.validate()

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "track_id": self.track_id,
            "frame_id": self.frame_id,
            "scene_id": self.scene_id,
            "timestamp_seconds": round(float(self.timestamp_seconds), 3),
            "role": self.role,
            "detection_confidence": round(float(self.detection_confidence), 4),
            "identity_label": self.identity_label,
            "identity_confidence": round(float(self.identity_confidence), 4),
            "team_label": self.team_label,
            "shirt_number": self.shirt_number,
            "bounding_box": self.bounding_box.to_dict(),
            "evidence_labels": list(self.evidence_labels),
        }


@dataclass(frozen=True)
class PlayerTrack:
    track_id: str
    role: str
    identity_label: str | None
    identity_confidence: float
    team_label: str | None
    observation_ids: tuple[str, ...]
    first_seen_seconds: float
    last_seen_seconds: float

    def validate(self, observation_ids: set[str]) -> None:
        if not self.track_id.startswith("PTRACK-"):
            raise PlayerRecognitionError("invalid player track identity")
        if self.role not in SUPPORTED_ROLES:
            raise PlayerRecognitionError("unsupported track role")
        if not self.observation_ids or any(item not in observation_ids for item in self.observation_ids):
            raise PlayerRecognitionError("track must reference valid observations")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise PlayerRecognitionError("track observations must be unique")
        if not 0.0 <= self.identity_confidence <= 1.0:
            raise PlayerRecognitionError("track identity confidence must be between 0 and 1")
        if self.identity_label is None and self.identity_confidence != 0.0:
            raise PlayerRecognitionError("anonymous track cannot have identity confidence")
        if self.last_seen_seconds < self.first_seen_seconds:
            raise PlayerRecognitionError("track temporal range is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "role": self.role,
            "identity_label": self.identity_label,
            "identity_confidence": round(float(self.identity_confidence), 4),
            "team_label": self.team_label,
            "observation_ids": list(self.observation_ids),
            "first_seen_seconds": round(float(self.first_seen_seconds), 3),
            "last_seen_seconds": round(float(self.last_seen_seconds), 3),
        }


@dataclass(frozen=True)
class PlayerRecognitionReport:
    schema: str
    recognition_id: str
    vision_report_id: str
    provider_name: str
    observations: tuple[PersonObservation, ...]
    tracks: tuple[PlayerTrack, ...]
    recognized_identity_labels: tuple[str, ...]
    recognition_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    biometric_enrolment_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport) -> None:
        vision.validate()
        if self.schema != "football-shorts-ai.player-recognition-report.v1":
            raise PlayerRecognitionError("unsupported player recognition schema")
        if not self.recognition_id.startswith("PLAYERREC-"):
            raise PlayerRecognitionError("invalid player recognition identity")
        if self.vision_report_id != vision.report_id:
            raise PlayerRecognitionError("vision report identity mismatch")
        if not self.provider_name.strip():
            raise PlayerRecognitionError("provider_name is required")
        if self.recognition_state not in SUPPORTED_STATES:
            raise PlayerRecognitionError("unsupported recognition state")
        observation_ids = {item.observation_id for item in self.observations}
        track_ids = {item.track_id for item in self.tracks}
        if len(observation_ids) != len(self.observations) or len(track_ids) != len(self.tracks):
            raise PlayerRecognitionError("observation and track identities must be unique")
        for observation in self.observations:
            observation.validate(vision)
            if observation.track_id not in track_ids:
                raise PlayerRecognitionError("observation references unknown track")
        for track in self.tracks:
            track.validate(observation_ids)
            linked = [item for item in self.observations if item.track_id == track.track_id]
            if tuple(item.observation_id for item in linked) != track.observation_ids:
                raise PlayerRecognitionError("track observation sequence is inconsistent")
        expected_labels = tuple(sorted({item.identity_label for item in self.tracks if item.identity_label}))
        if self.recognized_identity_labels != expected_labels:
            raise PlayerRecognitionError("recognized identity labels are inconsistent")
        if self.recognition_state == "recognized" and (self.blockers or not self.tracks):
            raise PlayerRecognitionError("recognized report requires unblocked tracks")
        if self.recognition_state == "review_required" and not self.blockers:
            raise PlayerRecognitionError("review-required report needs blockers")
        if self.recognition_state == "blocked" and not self.blockers:
            raise PlayerRecognitionError("blocked report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.biometric_enrolment_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise PlayerRecognitionError("0057B cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise PlayerRecognitionError("player recognition evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "recognition_id": self.recognition_id,
            "vision_report_id": self.vision_report_id,
            "provider_name": self.provider_name,
            "observations": [item.to_dict() for item in self.observations],
            "tracks": [item.to_dict() for item in self.tracks],
            "recognized_identity_labels": list(self.recognized_identity_labels),
            "recognition_state": self.recognition_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "biometric_enrolment_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_player_recognition_report(
    *,
    vision: FootballVisionReport,
    provider_name: str,
    detections: Sequence[Mapping[str, object]] = (),
    minimum_identity_confidence: float = 0.75,
) -> PlayerRecognitionReport:
    vision.validate()
    if not 0.0 <= minimum_identity_confidence <= 1.0:
        raise PlayerRecognitionError("minimum_identity_confidence must be between 0 and 1")
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    observations = tuple(_observation(item) for item in detections)
    tracks = _tracks(observations)
    if vision.pipeline_state == "analyzed" and not observations:
        blockers.add("PLAYER_EVIDENCE_MISSING")
    if any(item.identity_label and item.identity_confidence < minimum_identity_confidence for item in observations):
        blockers.add("IDENTITY_REVIEW_REQUIRED")
    if blockers:
        # Missing recognition evidence on an otherwise analyzed asset
        # requires human review; only an upstream-blocked vision report
        # blocks the recognition contract completely.
        state = "blocked" if vision.pipeline_state != "analyzed" else "review_required"
    else:
        state = "recognized"
    labels = tuple(sorted({item.identity_label for item in tracks if item.identity_label}))
    core = {
        "schema": "football-shorts-ai.player-recognition-report.v1",
        "vision_report_id": vision.report_id,
        "provider_name": provider_name.strip(),
        "observations": [item.to_dict() for item in observations],
        "tracks": [item.to_dict() for item in tracks],
        "recognized_identity_labels": list(labels),
        "recognition_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "biometric_enrolment_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    recognition_id = f"PLAYERREC-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "recognition_id": recognition_id}
    result = PlayerRecognitionReport(
        recognition_id=recognition_id,
        evidence_sha256=canonical_sha256(unsigned),
        vision_report_id=vision.report_id,
        provider_name=provider_name.strip(),
        observations=observations,
        tracks=tracks,
        recognized_identity_labels=labels,
        recognition_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.player-recognition-report.v1",
    )
    result.validate(vision)
    return result


def _observation(item: Mapping[str, object]) -> PersonObservation:
    identity = item.get("identity_label")
    identity_label = str(identity).strip() if identity is not None and str(identity).strip() else None
    team = item.get("team_label")
    team_label = str(team).strip() if team is not None and str(team).strip() else None
    box_data = item.get("bounding_box", {})
    if not isinstance(box_data, Mapping):
        raise PlayerRecognitionError("bounding_box must be an object")
    box = BoundingBox(*(float(box_data[key]) for key in ("x", "y", "width", "height")))
    core = {
        "track_id": str(item["track_id"]),
        "frame_id": str(item["frame_id"]),
        "scene_id": str(item["scene_id"]),
        "timestamp_seconds": float(item["timestamp_seconds"]),
        "role": str(item.get("role", "unknown")),
        "detection_confidence": float(item.get("detection_confidence", 0.0)),
        "identity_label": identity_label,
        "identity_confidence": float(item.get("identity_confidence", 0.0)),
        "team_label": team_label,
        "shirt_number": None if item.get("shirt_number") is None else int(item["shirt_number"]),
        "bounding_box": box,
        "evidence_labels": tuple(sorted(set(str(value).strip().lower().replace(" ", "_") for value in item.get("evidence_labels", ()) if str(value).strip()))),
    }
    serializable = {**core, "bounding_box": box.to_dict(), "evidence_labels": list(core["evidence_labels"])}
    return PersonObservation(observation_id=f"PERSONOBS-{canonical_sha256(serializable)[:20].upper()}", **core)


def _tracks(observations: Sequence[PersonObservation]) -> tuple[PlayerTrack, ...]:
    grouped: dict[str, list[PersonObservation]] = {}
    for item in observations:
        grouped.setdefault(item.track_id, []).append(item)
    tracks: list[PlayerTrack] = []
    for track_id in sorted(grouped):
        items = sorted(grouped[track_id], key=lambda value: (value.timestamp_seconds, value.observation_id))
        identified = [item for item in items if item.identity_label]
        best = max(identified, key=lambda value: (value.identity_confidence, value.identity_label or ""), default=None)
        role = max(items, key=lambda value: (value.detection_confidence, value.role)).role
        team_labels = [item.team_label for item in items if item.team_label]
        team = max(set(team_labels), key=lambda value: (team_labels.count(value), value)) if team_labels else None
        tracks.append(PlayerTrack(
            track_id=track_id,
            role=role,
            identity_label=None if best is None else best.identity_label,
            identity_confidence=0.0 if best is None else round(best.identity_confidence, 4),
            team_label=team,
            observation_ids=tuple(item.observation_id for item in items),
            first_seen_seconds=items[0].timestamp_seconds,
            last_seen_seconds=items[-1].timestamp_seconds,
        ))
    return tuple(tracks)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise PlayerRecognitionError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise PlayerRecognitionError("evidence must be hexadecimal") from exc


__all__ = [
    "BoundingBox",
    "PersonObservation",
    "PlayerRecognitionError",
    "PlayerRecognitionReport",
    "PlayerTrack",
    "build_player_recognition_report",
    "canonical_sha256",
]
