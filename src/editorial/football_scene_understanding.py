"""
FOOTBALL-SHORTS-AI-0056B
FOOTBALL SCENE UNDERSTANDING AND EDITORIAL SIGNAL CLASSIFICATION

Derives deterministic football and editorial classifications from 0056A scene
signals. This module does not perform computer-vision inference, network access,
media acquisition, rendering or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from editorial.semantic_scene_indexer import SemanticScene, SemanticSceneIndex


class FootballSceneUnderstandingError(ValueError):
    """Raised when governed scene classification evidence is invalid."""


SUPPORTED_ACTIONS = {
    "unknown",
    "build_up",
    "pass",
    "dribble",
    "shot",
    "goal",
    "save",
    "celebration",
    "crowd_reaction",
    "coach_reaction",
    "replay",
    "trophy",
    "interview",
}

SUPPORTED_EDITORIAL_ROLES = {
    "context",
    "hook",
    "development",
    "climax",
    "reaction",
    "resolution",
    "cta_support",
}


@dataclass(frozen=True)
class EditorialSignalClassification:
    schema: str
    classification_id: str
    scene_id: str
    action: str
    editorial_role: str
    semantic_strength: float
    motion_strength: float
    emotion_strength: float
    crowd_strength: float
    hook_score: float
    climax_score: float
    retention_score: float
    quality_score: float
    viral_signal_score: float
    labels: tuple[str, ...]
    blockers: tuple[str, ...]
    evidence_sha256: str
    inference_executed: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_match: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self, scene: SemanticScene) -> None:
        scene.validate()
        if self.schema != "football-shorts-ai.football-scene-classification.v1":
            raise FootballSceneUnderstandingError("unsupported classification schema")
        if not self.classification_id.startswith("SCENECLS-"):
            raise FootballSceneUnderstandingError("classification_id must start with SCENECLS-")
        if self.scene_id != scene.scene_id:
            raise FootballSceneUnderstandingError("scene identity mismatch")
        if self.action not in SUPPORTED_ACTIONS:
            raise FootballSceneUnderstandingError("unsupported football action")
        if self.editorial_role not in SUPPORTED_EDITORIAL_ROLES:
            raise FootballSceneUnderstandingError("unsupported editorial role")
        for name, value in (
            ("semantic_strength", self.semantic_strength),
            ("motion_strength", self.motion_strength),
            ("emotion_strength", self.emotion_strength),
            ("crowd_strength", self.crowd_strength),
            ("hook_score", self.hook_score),
            ("climax_score", self.climax_score),
            ("retention_score", self.retention_score),
            ("quality_score", self.quality_score),
            ("viral_signal_score", self.viral_signal_score),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FootballSceneUnderstandingError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise FootballSceneUnderstandingError(f"{name} must be between 0 and 1")
        if tuple(sorted(set(self.labels))) != self.labels:
            raise FootballSceneUnderstandingError("labels must be normalized, unique and sorted")
        if self.blockers and scene.render_allowed:
            raise FootballSceneUnderstandingError("renderable scene cannot contain rights blockers")
        if not self.blockers and not scene.render_allowed:
            raise FootballSceneUnderstandingError("non-renderable scene requires blockers")
        if any((
            self.inference_executed,
            self.network_enabled,
            self.acquisition_enabled,
            self.auto_match,
            self.auto_render,
            self.auto_publish,
        )):
            raise FootballSceneUnderstandingError("0056B cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FootballSceneUnderstandingError("classification evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "classification_id": self.classification_id,
            "scene_id": self.scene_id,
            "action": self.action,
            "editorial_role": self.editorial_role,
            "semantic_strength": self.semantic_strength,
            "motion_strength": self.motion_strength,
            "emotion_strength": self.emotion_strength,
            "crowd_strength": self.crowd_strength,
            "hook_score": self.hook_score,
            "climax_score": self.climax_score,
            "retention_score": self.retention_score,
            "quality_score": self.quality_score,
            "viral_signal_score": self.viral_signal_score,
            "labels": list(self.labels),
            "blockers": list(self.blockers),
            "inference_executed": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "auto_match": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


@dataclass(frozen=True)
class FootballSceneUnderstandingReport:
    schema: str
    report_id: str
    index_id: str
    classifications: tuple[EditorialSignalClassification, ...]
    top_hook_scene_id: str
    top_climax_scene_id: str
    report_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    inference_executed: bool = False
    auto_match: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self, index: SemanticSceneIndex) -> None:
        index.validate()
        if self.schema != "football-shorts-ai.football-scene-understanding.v1":
            raise FootballSceneUnderstandingError("unsupported understanding schema")
        if not self.report_id.startswith("SCENEUNDERSTANDING-"):
            raise FootballSceneUnderstandingError("invalid report identity")
        if self.index_id != index.index_id:
            raise FootballSceneUnderstandingError("scene index identity mismatch")
        if len(self.classifications) != len(index.scenes):
            raise FootballSceneUnderstandingError("every scene requires one classification")
        for scene, classification in zip(index.scenes, self.classifications, strict=True):
            classification.validate(scene)
        ids = {item.scene_id for item in self.classifications}
        if self.top_hook_scene_id not in ids or self.top_climax_scene_id not in ids:
            raise FootballSceneUnderstandingError("top scene identity is invalid")
        if self.report_state not in {"classified", "blocked"}:
            raise FootballSceneUnderstandingError("unsupported report state")
        if self.report_state == "classified" and self.blockers:
            raise FootballSceneUnderstandingError("classified report cannot contain blockers")
        if self.report_state == "blocked" and not self.blockers:
            raise FootballSceneUnderstandingError("blocked report requires blockers")
        if any((self.inference_executed, self.auto_match, self.auto_render, self.auto_publish)):
            raise FootballSceneUnderstandingError("automatic execution is forbidden")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FootballSceneUnderstandingError("report evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "report_id": self.report_id,
            "index_id": self.index_id,
            "classifications": [item.to_dict() for item in self.classifications],
            "top_hook_scene_id": self.top_hook_scene_id,
            "top_climax_scene_id": self.top_climax_scene_id,
            "report_state": self.report_state,
            "blockers": list(self.blockers),
            "inference_executed": False,
            "auto_match": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def classify_scene(scene: SemanticScene) -> EditorialSignalClassification:
    scene.validate()
    signals = scene.signals
    action = _action(signals.scene_type)
    role = _editorial_role(action, signals.hook_potential, signals.climax_potential)
    semantic_strength = _semantic_strength(scene)
    motion = round(float(signals.motion_intensity), 4)
    emotion = round(float(signals.emotion_intensity), 4)
    crowd = round(float(signals.crowd_reaction), 4)
    hook = _clamp(
        0.40 * float(signals.hook_potential)
        + 0.20 * motion
        + 0.20 * emotion
        + 0.10 * crowd
        + 0.10 * (1.0 if action in {"goal", "shot", "save", "celebration"} else 0.0)
    )
    climax = _clamp(
        0.45 * float(signals.climax_potential)
        + 0.20 * emotion
        + 0.15 * crowd
        + 0.10 * motion
        + 0.10 * (1.0 if action in {"goal", "save", "celebration", "trophy"} else 0.0)
    )
    retention = _clamp(0.30 * hook + 0.25 * climax + 0.20 * motion + 0.15 * emotion + 0.10 * semantic_strength)
    quality = round(float(signals.visual_quality), 4)
    viral = _clamp(0.30 * retention + 0.25 * hook + 0.20 * climax + 0.15 * quality + 0.10 * crowd)
    labels = tuple(sorted(set((action, role, signals.emotion, signals.shot_type, *signals.semantic_tags))))
    blockers = () if scene.render_allowed else ("SCENE_NOT_RENDERABLE",)

    core = {
        "schema": "football-shorts-ai.football-scene-classification.v1",
        "scene_id": scene.scene_id,
        "action": action,
        "editorial_role": role,
        "semantic_strength": semantic_strength,
        "motion_strength": motion,
        "emotion_strength": emotion,
        "crowd_strength": crowd,
        "hook_score": hook,
        "climax_score": climax,
        "retention_score": retention,
        "quality_score": quality,
        "viral_signal_score": viral,
        "labels": list(labels),
        "blockers": list(blockers),
        "inference_executed": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "auto_match": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    classification_id = f"SCENECLS-{provisional[:20].upper()}"
    unsigned = {**core, "classification_id": classification_id}
    evidence = canonical_sha256(unsigned)
    result = EditorialSignalClassification(
        classification_id=classification_id,
        evidence_sha256=evidence,
        labels=labels,
        blockers=blockers,
        **{k: v for k, v in unsigned.items() if k not in {"classification_id", "evidence_sha256", "labels", "blockers"}},
    )
    result.validate(scene)
    return result


def build_football_scene_understanding(index: SemanticSceneIndex) -> FootballSceneUnderstandingReport:
    index.validate()
    classifications = tuple(classify_scene(scene) for scene in index.scenes)
    top_hook = max(classifications, key=lambda item: (item.hook_score, item.viral_signal_score, item.scene_id))
    top_climax = max(classifications, key=lambda item: (item.climax_score, item.viral_signal_score, item.scene_id))
    blockers = tuple(sorted(set(index.blockers)))
    state = "blocked" if blockers else "classified"
    core = {
        "schema": "football-shorts-ai.football-scene-understanding.v1",
        "index_id": index.index_id,
        "classifications": [item.to_dict() for item in classifications],
        "top_hook_scene_id": top_hook.scene_id,
        "top_climax_scene_id": top_climax.scene_id,
        "report_state": state,
        "blockers": list(blockers),
        "inference_executed": False,
        "auto_match": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    report_id = f"SCENEUNDERSTANDING-{provisional[:20].upper()}"
    unsigned = {**core, "report_id": report_id}
    evidence = canonical_sha256(unsigned)
    result = FootballSceneUnderstandingReport(
        report_id=report_id,
        evidence_sha256=evidence,
        classifications=classifications,
        blockers=blockers,
        **{k: v for k, v in unsigned.items() if k not in {"report_id", "evidence_sha256", "classifications", "blockers"}},
    )
    result.validate(index)
    return result


def _action(scene_type: str) -> str:
    mapping = {
        "crowd": "crowd_reaction",
        "coach": "coach_reaction",
    }
    value = mapping.get(scene_type, scene_type)
    return value if value in SUPPORTED_ACTIONS else "unknown"


def _editorial_role(action: str, hook: float, climax: float) -> str:
    if hook >= 0.75 and hook >= climax:
        return "hook"
    if climax >= 0.75:
        return "climax"
    if action in {"celebration", "crowd_reaction", "coach_reaction"}:
        return "reaction"
    if action in {"goal", "save", "trophy"}:
        return "resolution"
    if action in {"pass", "dribble", "shot", "build_up"}:
        return "development"
    return "context"


def _semantic_strength(scene: SemanticScene) -> float:
    signals = scene.signals
    components = [
        1.0 if signals.scene_type != "unknown" else 0.0,
        1.0 if signals.players else 0.0,
        1.0 if signals.teams else 0.0,
        1.0 if signals.competition else 0.0,
        min(1.0, len(signals.semantic_tags) / 5.0),
        1.0 if signals.ball_visible else 0.0,
    ]
    return round(sum(components) / len(components), 4)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise FootballSceneUnderstandingError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FootballSceneUnderstandingError("evidence must be hexadecimal") from exc


__all__ = [
    "EditorialSignalClassification",
    "FootballSceneUnderstandingError",
    "FootballSceneUnderstandingReport",
    "SUPPORTED_ACTIONS",
    "SUPPORTED_EDITORIAL_ROLES",
    "build_football_scene_understanding",
    "canonical_sha256",
    "classify_scene",
]
