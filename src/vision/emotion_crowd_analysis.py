"""
FOOTBALL-SHORTS-AI-0057E
EMOTION AND CROWD REACTION ANALYSIS CONTRACT

Creates deterministic, reviewable emotional and crowd-energy evidence from governed
0057A vision and 0057D event evidence. No network, acquisition, model training,
rendering or publication is performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_event_detection import FootballEventDetectionReport
from vision.football_vision_pipeline import FootballVisionReport


class EmotionCrowdAnalysisError(ValueError):
    """Raised when governed emotion or crowd evidence is invalid."""


SUPPORTED_EMOTIONS = {
    "neutral",
    "joy",
    "euphoria",
    "surprise",
    "tension",
    "frustration",
    "sadness",
    "anger",
}
SUPPORTED_STATES = {"analyzed", "review_required", "blocked"}


@dataclass(frozen=True)
class EmotionSignal:
    signal_id: str
    scene_id: str
    frame_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    emotion: str
    confidence: float
    intensity: float
    crowd_energy: float
    celebration_probability: float
    tension_probability: float
    collective_reaction_probability: float
    evidence_labels: tuple[str, ...]

    def validate(self, vision: FootballVisionReport, events: FootballEventDetectionReport) -> None:
        if not self.signal_id.startswith("EMOSIGNAL-"):
            raise EmotionCrowdAnalysisError("invalid emotion signal identity")
        scene_ids = {item.scene_id for item in vision.scenes}
        frame_ids = {item.frame_id for item in vision.frames}
        event_ids = {item.event_id for item in events.events}
        if self.scene_id not in scene_ids:
            raise EmotionCrowdAnalysisError("emotion signal references unknown scene")
        if not self.frame_ids or any(item not in frame_ids for item in self.frame_ids):
            raise EmotionCrowdAnalysisError("emotion signal requires valid frame evidence")
        if any(item not in event_ids for item in self.event_ids):
            raise EmotionCrowdAnalysisError("emotion signal references unknown event")
        if self.emotion not in SUPPORTED_EMOTIONS:
            raise EmotionCrowdAnalysisError("unsupported emotion")
        for name, value in (
            ("confidence", self.confidence),
            ("intensity", self.intensity),
            ("crowd_energy", self.crowd_energy),
            ("celebration_probability", self.celebration_probability),
            ("tension_probability", self.tension_probability),
            ("collective_reaction_probability", self.collective_reaction_probability),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                raise EmotionCrowdAnalysisError(f"{name} must be between 0 and 1")
        if tuple(sorted(set(self.evidence_labels))) != self.evidence_labels:
            raise EmotionCrowdAnalysisError("evidence labels must be normalized")

    def to_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "scene_id": self.scene_id,
            "frame_ids": list(self.frame_ids),
            "event_ids": list(self.event_ids),
            "emotion": self.emotion,
            "confidence": round(float(self.confidence), 4),
            "intensity": round(float(self.intensity), 4),
            "crowd_energy": round(float(self.crowd_energy), 4),
            "celebration_probability": round(float(self.celebration_probability), 4),
            "tension_probability": round(float(self.tension_probability), 4),
            "collective_reaction_probability": round(float(self.collective_reaction_probability), 4),
            "evidence_labels": list(self.evidence_labels),
        }


@dataclass(frozen=True)
class SceneEmotionSummary:
    scene_id: str
    dominant_emotion: str
    emotional_peak_score: float
    crowd_energy_score: float
    celebration_score: float
    tension_score: float
    confidence: float
    signal_ids: tuple[str, ...]

    def validate(self, scene_ids: set[str], signal_ids: set[str]) -> None:
        if self.scene_id not in scene_ids:
            raise EmotionCrowdAnalysisError("summary references unknown scene")
        if self.dominant_emotion not in SUPPORTED_EMOTIONS:
            raise EmotionCrowdAnalysisError("unsupported dominant emotion")
        if not self.signal_ids or any(item not in signal_ids for item in self.signal_ids):
            raise EmotionCrowdAnalysisError("summary requires valid signal references")
        for value in (
            self.emotional_peak_score,
            self.crowd_energy_score,
            self.celebration_score,
            self.tension_score,
            self.confidence,
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise EmotionCrowdAnalysisError("summary score must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "dominant_emotion": self.dominant_emotion,
            "emotional_peak_score": round(float(self.emotional_peak_score), 4),
            "crowd_energy_score": round(float(self.crowd_energy_score), 4),
            "celebration_score": round(float(self.celebration_score), 4),
            "tension_score": round(float(self.tension_score), 4),
            "confidence": round(float(self.confidence), 4),
            "signal_ids": list(self.signal_ids),
        }


@dataclass(frozen=True)
class EmotionCrowdAnalysisReport:
    schema: str
    analysis_id: str
    vision_report_id: str
    event_detection_id: str
    provider_name: str
    signals: tuple[EmotionSignal, ...]
    scene_summaries: tuple[SceneEmotionSummary, ...]
    peak_scene_id: str | None
    analysis_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport, events: FootballEventDetectionReport) -> None:
        vision.validate()
        events.validate(vision)
        if self.schema != "football-shorts-ai.emotion-crowd-analysis.v1":
            raise EmotionCrowdAnalysisError("unsupported emotion analysis schema")
        if not self.analysis_id.startswith("EMOTION-"):
            raise EmotionCrowdAnalysisError("invalid emotion analysis identity")
        if self.vision_report_id != vision.report_id or self.event_detection_id != events.detection_id:
            raise EmotionCrowdAnalysisError("upstream evidence identity mismatch")
        if not self.provider_name.strip():
            raise EmotionCrowdAnalysisError("provider_name is required")
        if self.analysis_state not in SUPPORTED_STATES:
            raise EmotionCrowdAnalysisError("unsupported analysis state")
        signal_ids = {item.signal_id for item in self.signals}
        scene_ids = {item.scene_id for item in vision.scenes}
        if len(signal_ids) != len(self.signals):
            raise EmotionCrowdAnalysisError("emotion signal identities must be unique")
        for item in self.signals:
            item.validate(vision, events)
        for item in self.scene_summaries:
            item.validate(scene_ids, signal_ids)
        expected_peak = None
        if self.scene_summaries:
            expected_peak = max(
                self.scene_summaries,
                key=lambda item: (item.emotional_peak_score, item.scene_id),
            ).scene_id
        if self.peak_scene_id != expected_peak:
            raise EmotionCrowdAnalysisError("peak scene is inconsistent")
        if self.analysis_state == "analyzed" and (self.blockers or not self.signals):
            raise EmotionCrowdAnalysisError("analyzed report requires unblocked evidence")
        if self.analysis_state in {"review_required", "blocked"} and not self.blockers:
            raise EmotionCrowdAnalysisError("non-ready analysis requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise EmotionCrowdAnalysisError("0057E cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise EmotionCrowdAnalysisError("emotion analysis evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "analysis_id": self.analysis_id,
            "vision_report_id": self.vision_report_id,
            "event_detection_id": self.event_detection_id,
            "provider_name": self.provider_name,
            "signals": [item.to_dict() for item in self.signals],
            "scene_summaries": [item.to_dict() for item in self.scene_summaries],
            "peak_scene_id": self.peak_scene_id,
            "analysis_state": self.analysis_state,
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


def build_emotion_crowd_analysis(
    *,
    vision: FootballVisionReport,
    events: FootballEventDetectionReport,
    provider_name: str,
    signals: Sequence[Mapping[str, object]] = (),
    minimum_confidence: float = 0.70,
) -> EmotionCrowdAnalysisReport:
    vision.validate()
    events.validate(vision)
    if not 0.0 <= minimum_confidence <= 1.0:
        raise EmotionCrowdAnalysisError("minimum_confidence must be between 0 and 1")
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed" or events.detection_state == "blocked":
        blockers.add("UPSTREAM_VISION_OR_EVENT_EVIDENCE_BLOCKED")
    parsed = tuple(_signal(item) for item in signals)
    if vision.pipeline_state == "analyzed" and not parsed:
        blockers.add("EMOTION_EVIDENCE_MISSING")
    if any(item.confidence < minimum_confidence for item in parsed):
        blockers.add("EMOTION_REVIEW_REQUIRED")
    summaries = _summaries(parsed)
    peak_scene_id = None
    if summaries:
        peak_scene_id = max(summaries, key=lambda item: (item.emotional_peak_score, item.scene_id)).scene_id
    if blockers:
        state = "blocked" if "UPSTREAM_VISION_OR_EVENT_EVIDENCE_BLOCKED" in blockers else "review_required"
    else:
        state = "analyzed"
    core = {
        "schema": "football-shorts-ai.emotion-crowd-analysis.v1",
        "vision_report_id": vision.report_id,
        "event_detection_id": events.detection_id,
        "provider_name": provider_name.strip(),
        "signals": [item.to_dict() for item in parsed],
        "scene_summaries": [item.to_dict() for item in summaries],
        "peak_scene_id": peak_scene_id,
        "analysis_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    analysis_id = f"EMOTION-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "analysis_id": analysis_id}
    result = EmotionCrowdAnalysisReport(
        analysis_id=analysis_id,
        evidence_sha256=canonical_sha256(unsigned),
        vision_report_id=vision.report_id,
        event_detection_id=events.detection_id,
        provider_name=provider_name.strip(),
        signals=parsed,
        scene_summaries=summaries,
        peak_scene_id=peak_scene_id,
        analysis_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.emotion-crowd-analysis.v1",
    )
    result.validate(vision, events)
    return result


def _signal(item: Mapping[str, object]) -> EmotionSignal:
    core = {
        "scene_id": str(item["scene_id"]),
        "frame_ids": tuple(str(value) for value in item.get("frame_ids", ())),
        "event_ids": tuple(str(value) for value in item.get("event_ids", ())),
        "emotion": str(item.get("emotion", "neutral")),
        "confidence": float(item.get("confidence", 0.0)),
        "intensity": float(item.get("intensity", 0.0)),
        "crowd_energy": float(item.get("crowd_energy", 0.0)),
        "celebration_probability": float(item.get("celebration_probability", 0.0)),
        "tension_probability": float(item.get("tension_probability", 0.0)),
        "collective_reaction_probability": float(item.get("collective_reaction_probability", 0.0)),
        "evidence_labels": tuple(sorted(set(
            str(value).strip().lower().replace(" ", "_")
            for value in item.get("evidence_labels", ())
            if str(value).strip()
        ))),
    }
    serializable = {**core, "frame_ids": list(core["frame_ids"]), "event_ids": list(core["event_ids"]), "evidence_labels": list(core["evidence_labels"])}
    return EmotionSignal(signal_id=f"EMOSIGNAL-{canonical_sha256(serializable)[:20].upper()}", **core)


def _summaries(signals: Sequence[EmotionSignal]) -> tuple[SceneEmotionSummary, ...]:
    grouped: dict[str, list[EmotionSignal]] = {}
    for item in signals:
        grouped.setdefault(item.scene_id, []).append(item)
    summaries: list[SceneEmotionSummary] = []
    for scene_id in sorted(grouped):
        items = grouped[scene_id]
        dominant = max(items, key=lambda item: (item.intensity * item.confidence, item.emotion))
        def avg(name: str) -> float:
            return round(sum(float(getattr(item, name)) for item in items) / len(items), 4)
        peak = round(max(item.intensity * item.confidence for item in items), 4)
        summaries.append(SceneEmotionSummary(
            scene_id=scene_id,
            dominant_emotion=dominant.emotion,
            emotional_peak_score=peak,
            crowd_energy_score=avg("crowd_energy"),
            celebration_score=avg("celebration_probability"),
            tension_score=avg("tension_probability"),
            confidence=avg("confidence"),
            signal_ids=tuple(item.signal_id for item in items),
        ))
    return tuple(summaries)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise EmotionCrowdAnalysisError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EmotionCrowdAnalysisError("evidence must be hexadecimal") from exc


__all__ = [
    "EmotionCrowdAnalysisError",
    "EmotionCrowdAnalysisReport",
    "EmotionSignal",
    "SceneEmotionSummary",
    "build_emotion_crowd_analysis",
    "canonical_sha256",
]
