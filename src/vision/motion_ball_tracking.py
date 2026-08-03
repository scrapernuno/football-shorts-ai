"""
FOOTBALL-SHORTS-AI-0057F
MOTION AND BALL TRACKING EVIDENCE CONTRACT

Creates deterministic, reviewable ball observations, trajectories and scene motion
summaries from governed 0057A vision evidence. It performs no network access,
media acquisition, external model execution, training, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_vision_pipeline import FootballVisionReport


class MotionBallTrackingError(ValueError):
    """Raised when governed motion or ball-tracking evidence is invalid."""


SUPPORTED_STATES = {"tracked", "review_required", "blocked"}
SUPPORTED_DIRECTIONS = {"stationary", "left", "right", "up", "down", "diagonal", "unknown"}


@dataclass(frozen=True)
class NormalizedPoint:
    x: float
    y: float

    def validate(self) -> None:
        for name, value in (("x", self.x), ("y", self.y)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise MotionBallTrackingError(f"point {name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise MotionBallTrackingError(f"point {name} must be normalized")

    def to_dict(self) -> dict[str, float]:
        self.validate()
        return {"x": round(float(self.x), 6), "y": round(float(self.y), 6)}


@dataclass(frozen=True)
class BallObservation:
    observation_id: str
    track_id: str
    frame_id: str
    scene_id: str
    timestamp_seconds: float
    center: NormalizedPoint
    radius_normalized: float
    confidence: float
    occluded: bool

    def validate(self, vision: FootballVisionReport) -> None:
        if not self.observation_id.startswith("BALLOBS-"):
            raise MotionBallTrackingError("invalid ball observation identity")
        if not self.track_id.startswith("BALLTRACK-"):
            raise MotionBallTrackingError("invalid ball track identity")
        if self.frame_id not in {item.frame_id for item in vision.frames}:
            raise MotionBallTrackingError("ball observation references unknown frame")
        if self.scene_id not in {item.scene_id for item in vision.scenes}:
            raise MotionBallTrackingError("ball observation references unknown scene")
        if not 0.0 <= self.timestamp_seconds <= vision.request.duration_seconds:
            raise MotionBallTrackingError("ball observation timestamp is invalid")
        self.center.validate()
        if not 0.0 < self.radius_normalized <= 0.25:
            raise MotionBallTrackingError("ball radius is outside governed limits")
        if not 0.0 <= self.confidence <= 1.0:
            raise MotionBallTrackingError("ball confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "track_id": self.track_id,
            "frame_id": self.frame_id,
            "scene_id": self.scene_id,
            "timestamp_seconds": round(float(self.timestamp_seconds), 3),
            "center": self.center.to_dict(),
            "radius_normalized": round(float(self.radius_normalized), 6),
            "confidence": round(float(self.confidence), 4),
            "occluded": bool(self.occluded),
        }


@dataclass(frozen=True)
class BallTrack:
    track_id: str
    observation_ids: tuple[str, ...]
    first_seen_seconds: float
    last_seen_seconds: float
    path_length_normalized: float
    average_speed_normalized_per_second: float
    peak_speed_normalized_per_second: float
    acceleration_score: float
    dominant_direction: str
    continuity_score: float

    def validate(self, observation_ids: set[str]) -> None:
        if not self.track_id.startswith("BALLTRACK-"):
            raise MotionBallTrackingError("invalid ball track identity")
        if len(self.observation_ids) < 2:
            raise MotionBallTrackingError("ball track requires at least two observations")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise MotionBallTrackingError("ball track observations must be unique")
        if any(item not in observation_ids for item in self.observation_ids):
            raise MotionBallTrackingError("ball track references unknown observations")
        if self.last_seen_seconds <= self.first_seen_seconds:
            raise MotionBallTrackingError("ball track temporal range is invalid")
        for name, value in (
            ("path_length_normalized", self.path_length_normalized),
            ("average_speed_normalized_per_second", self.average_speed_normalized_per_second),
            ("peak_speed_normalized_per_second", self.peak_speed_normalized_per_second),
        ):
            if value < 0:
                raise MotionBallTrackingError(f"{name} must be non-negative")
        for name, value in (("acceleration_score", self.acceleration_score), ("continuity_score", self.continuity_score)):
            if not 0.0 <= value <= 1.0:
                raise MotionBallTrackingError(f"{name} must be between 0 and 1")
        if self.dominant_direction not in SUPPORTED_DIRECTIONS:
            raise MotionBallTrackingError("unsupported dominant direction")

    def to_dict(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "observation_ids": list(self.observation_ids),
            "first_seen_seconds": round(float(self.first_seen_seconds), 3),
            "last_seen_seconds": round(float(self.last_seen_seconds), 3),
            "path_length_normalized": round(float(self.path_length_normalized), 6),
            "average_speed_normalized_per_second": round(float(self.average_speed_normalized_per_second), 6),
            "peak_speed_normalized_per_second": round(float(self.peak_speed_normalized_per_second), 6),
            "acceleration_score": round(float(self.acceleration_score), 4),
            "dominant_direction": self.dominant_direction,
            "continuity_score": round(float(self.continuity_score), 4),
        }


@dataclass(frozen=True)
class SceneMotionSummary:
    scene_id: str
    ball_track_ids: tuple[str, ...]
    camera_motion_score: float
    subject_motion_score: float
    ball_motion_score: float
    composite_motion_score: float
    peak_speed_score: float

    def validate(self, scene_ids: set[str], track_ids: set[str]) -> None:
        if self.scene_id not in scene_ids:
            raise MotionBallTrackingError("scene motion summary references unknown scene")
        if any(item not in track_ids for item in self.ball_track_ids):
            raise MotionBallTrackingError("scene motion summary references unknown ball track")
        for value in (
            self.camera_motion_score,
            self.subject_motion_score,
            self.ball_motion_score,
            self.composite_motion_score,
            self.peak_speed_score,
        ):
            if not 0.0 <= value <= 1.0:
                raise MotionBallTrackingError("scene motion score must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "ball_track_ids": list(self.ball_track_ids),
            "camera_motion_score": round(float(self.camera_motion_score), 4),
            "subject_motion_score": round(float(self.subject_motion_score), 4),
            "ball_motion_score": round(float(self.ball_motion_score), 4),
            "composite_motion_score": round(float(self.composite_motion_score), 4),
            "peak_speed_score": round(float(self.peak_speed_score), 4),
        }


@dataclass(frozen=True)
class MotionBallTrackingReport:
    schema: str
    tracking_id: str
    vision_report_id: str
    provider_name: str
    observations: tuple[BallObservation, ...]
    tracks: tuple[BallTrack, ...]
    scene_summaries: tuple[SceneMotionSummary, ...]
    peak_motion_scene_id: str | None
    tracking_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport) -> None:
        vision.validate()
        if self.schema != "football-shorts-ai.motion-ball-tracking-report.v1":
            raise MotionBallTrackingError("unsupported motion tracking schema")
        if not self.tracking_id.startswith("MOTIONTRACK-"):
            raise MotionBallTrackingError("invalid motion tracking identity")
        if self.vision_report_id != vision.report_id:
            raise MotionBallTrackingError("vision report identity mismatch")
        if not self.provider_name.strip():
            raise MotionBallTrackingError("provider_name is required")
        if self.tracking_state not in SUPPORTED_STATES:
            raise MotionBallTrackingError("unsupported tracking state")
        observation_ids = {item.observation_id for item in self.observations}
        track_ids = {item.track_id for item in self.tracks}
        scene_ids = {item.scene_id for item in vision.scenes}
        if len(observation_ids) != len(self.observations) or len(track_ids) != len(self.tracks):
            raise MotionBallTrackingError("tracking identities must be unique")
        for item in self.observations:
            item.validate(vision)
            if item.track_id not in track_ids:
                raise MotionBallTrackingError("observation references unknown ball track")
        for item in self.tracks:
            item.validate(observation_ids)
        for item in self.scene_summaries:
            item.validate(scene_ids, track_ids)
        if self.peak_motion_scene_id is not None and self.peak_motion_scene_id not in scene_ids:
            raise MotionBallTrackingError("peak motion scene is invalid")
        if self.tracking_state == "tracked" and (self.blockers or not self.tracks):
            raise MotionBallTrackingError("tracked report requires unblocked tracks")
        if self.tracking_state in {"review_required", "blocked"} and not self.blockers:
            raise MotionBallTrackingError("non-tracked report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise MotionBallTrackingError("0057F cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise MotionBallTrackingError("motion tracking evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "tracking_id": self.tracking_id,
            "vision_report_id": self.vision_report_id,
            "provider_name": self.provider_name,
            "observations": [item.to_dict() for item in self.observations],
            "tracks": [item.to_dict() for item in self.tracks],
            "scene_summaries": [item.to_dict() for item in self.scene_summaries],
            "peak_motion_scene_id": self.peak_motion_scene_id,
            "tracking_state": self.tracking_state,
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


def build_motion_ball_tracking_report(
    *,
    vision: FootballVisionReport,
    provider_name: str,
    detections: Sequence[Mapping[str, object]] = (),
    scene_motion: Sequence[Mapping[str, object]] = (),
    minimum_confidence: float = 0.65,
) -> MotionBallTrackingReport:
    vision.validate()
    if not 0.0 <= minimum_confidence <= 1.0:
        raise MotionBallTrackingError("minimum_confidence must be between 0 and 1")
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    observations = tuple(_observation(item) for item in detections)
    tracks = _tracks(observations)
    if vision.pipeline_state == "analyzed" and not tracks:
        blockers.add("BALL_TRACKING_EVIDENCE_MISSING")
    if any(item.confidence < minimum_confidence for item in observations):
        blockers.add("BALL_TRACK_REVIEW_REQUIRED")
    summaries = _summaries(vision, tracks, scene_motion)
    peak = max(summaries, key=lambda item: (item.composite_motion_score, item.scene_id), default=None)
    if blockers:
        state = "blocked" if vision.pipeline_state != "analyzed" or not tracks else "review_required"
    else:
        state = "tracked"
    core = {
        "schema": "football-shorts-ai.motion-ball-tracking-report.v1",
        "vision_report_id": vision.report_id,
        "provider_name": provider_name.strip(),
        "observations": [item.to_dict() for item in observations],
        "tracks": [item.to_dict() for item in tracks],
        "scene_summaries": [item.to_dict() for item in summaries],
        "peak_motion_scene_id": None if peak is None else peak.scene_id,
        "tracking_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    tracking_id = f"MOTIONTRACK-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "tracking_id": tracking_id}
    result = MotionBallTrackingReport(
        tracking_id=tracking_id,
        evidence_sha256=canonical_sha256(unsigned),
        vision_report_id=vision.report_id,
        provider_name=provider_name.strip(),
        observations=observations,
        tracks=tracks,
        scene_summaries=summaries,
        peak_motion_scene_id=None if peak is None else peak.scene_id,
        tracking_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.motion-ball-tracking-report.v1",
    )
    result.validate(vision)
    return result


def _observation(item: Mapping[str, object]) -> BallObservation:
    center_data = item.get("center", {})
    if not isinstance(center_data, Mapping):
        raise MotionBallTrackingError("center must be an object")
    center = NormalizedPoint(float(center_data["x"]), float(center_data["y"]))
    core = {
        "track_id": str(item["track_id"]),
        "frame_id": str(item["frame_id"]),
        "scene_id": str(item["scene_id"]),
        "timestamp_seconds": float(item["timestamp_seconds"]),
        "center": center,
        "radius_normalized": float(item.get("radius_normalized", 0.01)),
        "confidence": float(item.get("confidence", 0.0)),
        "occluded": bool(item.get("occluded", False)),
    }
    serializable = {**core, "center": center.to_dict()}
    return BallObservation(observation_id=f"BALLOBS-{canonical_sha256(serializable)[:20].upper()}", **core)


def _tracks(observations: Sequence[BallObservation]) -> tuple[BallTrack, ...]:
    grouped: dict[str, list[BallObservation]] = {}
    for item in observations:
        grouped.setdefault(item.track_id, []).append(item)
    result: list[BallTrack] = []
    for track_id in sorted(grouped):
        items = sorted(grouped[track_id], key=lambda value: (value.timestamp_seconds, value.observation_id))
        if len(items) < 2:
            continue
        distances: list[float] = []
        speeds: list[float] = []
        for previous, current in zip(items, items[1:]):
            dt = current.timestamp_seconds - previous.timestamp_seconds
            if dt <= 0:
                raise MotionBallTrackingError("ball observations must have increasing timestamps")
            distance = math.dist((previous.center.x, previous.center.y), (current.center.x, current.center.y))
            distances.append(distance)
            speeds.append(distance / dt)
        path = sum(distances)
        average = sum(speeds) / len(speeds)
        peak = max(speeds)
        acceleration = 0.0 if len(speeds) < 2 else min(1.0, max(abs(b - a) for a, b in zip(speeds, speeds[1:])) / max(peak, 1e-9))
        visible = sum(1 for item in items if not item.occluded)
        continuity = visible / len(items)
        direction = _direction(items[0].center, items[-1].center)
        result.append(BallTrack(
            track_id=track_id,
            observation_ids=tuple(item.observation_id for item in items),
            first_seen_seconds=items[0].timestamp_seconds,
            last_seen_seconds=items[-1].timestamp_seconds,
            path_length_normalized=round(path, 6),
            average_speed_normalized_per_second=round(average, 6),
            peak_speed_normalized_per_second=round(peak, 6),
            acceleration_score=round(acceleration, 4),
            dominant_direction=direction,
            continuity_score=round(continuity, 4),
        ))
    return tuple(result)


def _summaries(
    vision: FootballVisionReport,
    tracks: Sequence[BallTrack],
    source: Sequence[Mapping[str, object]],
) -> tuple[SceneMotionSummary, ...]:
    source_by_scene = {str(item["scene_id"]): item for item in source}
    observations_by_track: dict[str, list[BallObservation]] = {}
    # observation lookup is not required for evidence linkage; scene assignments come from source data.
    result: list[SceneMotionSummary] = []
    for scene in vision.scenes:
        data = source_by_scene.get(scene.scene_id, {})
        track_ids = tuple(sorted(set(str(value) for value in data.get("ball_track_ids", ()))))
        linked = [item for item in tracks if item.track_id in track_ids]
        ball_motion = min(1.0, max((item.average_speed_normalized_per_second for item in linked), default=0.0))
        peak_speed = min(1.0, max((item.peak_speed_normalized_per_second for item in linked), default=0.0))
        camera = float(data.get("camera_motion_score", scene.motion_score))
        subject = float(data.get("subject_motion_score", scene.motion_score))
        composite = round(0.30 * camera + 0.30 * subject + 0.25 * ball_motion + 0.15 * peak_speed, 4)
        result.append(SceneMotionSummary(
            scene_id=scene.scene_id,
            ball_track_ids=track_ids,
            camera_motion_score=round(camera, 4),
            subject_motion_score=round(subject, 4),
            ball_motion_score=round(ball_motion, 4),
            composite_motion_score=composite,
            peak_speed_score=round(peak_speed, 4),
        ))
    return tuple(result)


def _direction(first: NormalizedPoint, last: NormalizedPoint) -> str:
    dx = last.x - first.x
    dy = last.y - first.y
    if abs(dx) < 0.02 and abs(dy) < 0.02:
        return "stationary"
    if abs(dx) > abs(dy) * 1.5:
        return "right" if dx > 0 else "left"
    if abs(dy) > abs(dx) * 1.5:
        return "down" if dy > 0 else "up"
    return "diagonal"


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=lambda value: value.to_dict()).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise MotionBallTrackingError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MotionBallTrackingError("evidence must be hexadecimal") from exc


__all__ = [
    "BallObservation",
    "BallTrack",
    "MotionBallTrackingError",
    "MotionBallTrackingReport",
    "NormalizedPoint",
    "SceneMotionSummary",
    "build_motion_ball_tracking_report",
    "canonical_sha256",
]
