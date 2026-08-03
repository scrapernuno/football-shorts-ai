"""
FOOTBALL-SHORTS-AI-0056A
SEMANTIC SCENE INDEXER AND EDITORIAL METADATA CONTRACT

Creates deterministic scene-level editorial evidence for videos already present in
the governed library. This module performs no network access, media acquisition,
computer-vision inference, rendering or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


class SemanticSceneIndexError(ValueError):
    """Raised when scene evidence is malformed or operationally unsafe."""


SUPPORTED_SCENE_TYPES = {
    "unknown",
    "build_up",
    "pass",
    "dribble",
    "shot",
    "goal",
    "save",
    "celebration",
    "crowd",
    "coach",
    "replay",
    "trophy",
    "interview",
}

SUPPORTED_SHOT_TYPES = {
    "unknown",
    "wide",
    "medium",
    "close_up",
    "aerial",
    "scoreboard",
    "replay",
}

SUPPORTED_EMOTIONS = {
    "unknown",
    "neutral",
    "anticipation",
    "surprise",
    "joy",
    "tension",
    "disappointment",
    "celebration",
}


@dataclass(frozen=True)
class SceneSignals:
    scene_type: str = "unknown"
    shot_type: str = "unknown"
    emotion: str = "unknown"
    players: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()
    competition: str | None = None
    semantic_tags: tuple[str, ...] = ()
    ball_visible: bool = False
    face_visible: bool = False
    scoreboard_visible: bool = False
    replay: bool = False
    slow_motion: bool = False
    crowd_reaction: float = 0.0
    motion_intensity: float = 0.0
    visual_quality: float = 0.0
    emotion_intensity: float = 0.0
    hook_potential: float = 0.0
    climax_potential: float = 0.0

    def validate(self) -> None:
        if self.scene_type not in SUPPORTED_SCENE_TYPES:
            raise SemanticSceneIndexError("unsupported scene_type")
        if self.shot_type not in SUPPORTED_SHOT_TYPES:
            raise SemanticSceneIndexError("unsupported shot_type")
        if self.emotion not in SUPPORTED_EMOTIONS:
            raise SemanticSceneIndexError("unsupported emotion")
        for name, value in (
            ("crowd_reaction", self.crowd_reaction),
            ("motion_intensity", self.motion_intensity),
            ("visual_quality", self.visual_quality),
            ("emotion_intensity", self.emotion_intensity),
            ("hook_potential", self.hook_potential),
            ("climax_potential", self.climax_potential),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SemanticSceneIndexError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise SemanticSceneIndexError(f"{name} must be between 0 and 1")
        _validate_terms(self.players, "players")
        _validate_terms(self.teams, "teams")
        _validate_terms(self.semantic_tags, "semantic_tags")
        if self.competition is not None and not self.competition.strip():
            raise SemanticSceneIndexError("competition cannot be blank")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "scene_type": self.scene_type,
            "shot_type": self.shot_type,
            "emotion": self.emotion,
            "players": list(self.players),
            "teams": list(self.teams),
            "competition": self.competition,
            "semantic_tags": list(self.semantic_tags),
            "ball_visible": self.ball_visible,
            "face_visible": self.face_visible,
            "scoreboard_visible": self.scoreboard_visible,
            "replay": self.replay,
            "slow_motion": self.slow_motion,
            "crowd_reaction": round(float(self.crowd_reaction), 4),
            "motion_intensity": round(float(self.motion_intensity), 4),
            "visual_quality": round(float(self.visual_quality), 4),
            "emotion_intensity": round(float(self.emotion_intensity), 4),
            "hook_potential": round(float(self.hook_potential), 4),
            "climax_potential": round(float(self.climax_potential), 4),
        }


@dataclass(frozen=True)
class SemanticScene:
    schema: str
    scene_id: str
    asset_id: str
    provider: str
    provider_asset_id: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    signals: SceneSignals
    rights_status: str
    preview_allowed: bool
    render_allowed: bool
    source_evidence_sha256: str
    evidence_sha256: str
    inference_executed: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.semantic-scene.v1":
            raise SemanticSceneIndexError("unsupported scene schema")
        if not self.scene_id.startswith("SCENE-"):
            raise SemanticSceneIndexError("scene_id must start with SCENE-")
        if not self.asset_id.startswith("EXT-"):
            raise SemanticSceneIndexError("asset_id must start with EXT-")
        if not self.provider.strip() or not self.provider_asset_id.strip():
            raise SemanticSceneIndexError("provider identity is required")
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise SemanticSceneIndexError("scene timestamps are invalid")
        expected_duration = round(self.end_seconds - self.start_seconds, 3)
        if round(self.duration_seconds, 3) != expected_duration:
            raise SemanticSceneIndexError("scene duration is inconsistent")
        if self.duration_seconds > 30:
            raise SemanticSceneIndexError("scene duration exceeds 30 seconds")
        self.signals.validate()
        if self.rights_status == "reference_only" and self.render_allowed:
            raise SemanticSceneIndexError("reference-only scenes cannot be renderable")
        if not self.preview_allowed:
            raise SemanticSceneIndexError("indexed scenes must remain previewable")
        for value in (self.source_evidence_sha256, self.evidence_sha256):
            _validate_sha256(value)
        if any(
            (
                self.inference_executed,
                self.network_enabled,
                self.acquisition_enabled,
                self.render_enabled,
                self.auto_publish,
            )
        ):
            raise SemanticSceneIndexError("0056A cannot execute operational capabilities")
        expected = canonical_sha256(self._unsigned())
        if expected != self.evidence_sha256:
            raise SemanticSceneIndexError("scene evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "provider_asset_id": self.provider_asset_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "signals": self.signals.to_dict(),
            "rights_status": self.rights_status,
            "preview_allowed": self.preview_allowed,
            "render_allowed": self.render_allowed,
            "source_evidence_sha256": self.source_evidence_sha256,
            "inference_executed": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


@dataclass(frozen=True)
class SemanticSceneIndex:
    schema: str
    index_id: str
    asset_id: str
    source_evidence_sha256: str
    scenes: tuple[SemanticScene, ...]
    total_duration_seconds: float
    index_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    inference_executed: bool = False
    auto_match: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.semantic-scene-index.v1":
            raise SemanticSceneIndexError("unsupported scene index schema")
        if not self.index_id.startswith("SCENEIDX-"):
            raise SemanticSceneIndexError("index_id must start with SCENEIDX-")
        if not self.asset_id.startswith("EXT-"):
            raise SemanticSceneIndexError("invalid asset identity")
        if not self.scenes:
            raise SemanticSceneIndexError("scene index requires at least one scene")
        previous_end = -1.0
        for expected_order, scene in enumerate(self.scenes, start=1):
            scene.validate()
            if scene.asset_id != self.asset_id:
                raise SemanticSceneIndexError("scene asset identity mismatch")
            if scene.start_seconds < previous_end:
                raise SemanticSceneIndexError("scenes cannot overlap")
            if not scene.scene_id.endswith(f"-{expected_order:04d}"):
                raise SemanticSceneIndexError("scene order suffix is inconsistent")
            previous_end = scene.end_seconds
        expected_total = round(max(scene.end_seconds for scene in self.scenes), 3)
        if round(self.total_duration_seconds, 3) != expected_total:
            raise SemanticSceneIndexError("index duration is inconsistent")
        if self.index_state not in {"indexed", "blocked"}:
            raise SemanticSceneIndexError("unsupported index state")
        if self.index_state == "indexed" and self.blockers:
            raise SemanticSceneIndexError("indexed result cannot contain blockers")
        if self.index_state == "blocked" and not self.blockers:
            raise SemanticSceneIndexError("blocked result requires blockers")
        _validate_sha256(self.source_evidence_sha256)
        _validate_sha256(self.evidence_sha256)
        if self.inference_executed or self.auto_match or self.auto_render or self.auto_publish:
            raise SemanticSceneIndexError("automatic execution is forbidden in 0056A")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise SemanticSceneIndexError("index evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "index_id": self.index_id,
            "asset_id": self.asset_id,
            "source_evidence_sha256": self.source_evidence_sha256,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "total_duration_seconds": self.total_duration_seconds,
            "index_state": self.index_state,
            "blockers": list(self.blockers),
            "inference_executed": False,
            "auto_match": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_semantic_scene_index(
    *,
    asset: Mapping[str, object],
    segments: Sequence[Mapping[str, object]],
) -> SemanticSceneIndex:
    """Build deterministic scene evidence from externally supplied segment metadata."""

    asset_id = _required_text(asset, "asset_id")
    provider = _required_text(asset, "provider")
    provider_asset_id = _required_text(asset, "provider_asset_id")
    source_evidence = _required_text(asset, "evidence_sha256")
    rights_status = _required_text(asset, "rights_status")
    preview_allowed = bool(asset.get("preview_allowed", False))
    render_allowed = bool(asset.get("render_allowed", False))
    _validate_sha256(source_evidence)
    if not segments:
        raise SemanticSceneIndexError("segments are required")

    scenes: list[SemanticScene] = []
    for order, segment in enumerate(segments, start=1):
        start = _required_number(segment, "start_seconds")
        end = _required_number(segment, "end_seconds")
        signals = SceneSignals(
            scene_type=str(segment.get("scene_type", "unknown")),
            shot_type=str(segment.get("shot_type", "unknown")),
            emotion=str(segment.get("emotion", "unknown")),
            players=_normalized_terms(segment.get("players")),
            teams=_normalized_terms(segment.get("teams")),
            competition=_optional_text(segment.get("competition")),
            semantic_tags=_normalized_terms(segment.get("semantic_tags")),
            ball_visible=bool(segment.get("ball_visible", False)),
            face_visible=bool(segment.get("face_visible", False)),
            scoreboard_visible=bool(segment.get("scoreboard_visible", False)),
            replay=bool(segment.get("replay", False)),
            slow_motion=bool(segment.get("slow_motion", False)),
            crowd_reaction=_score(segment.get("crowd_reaction", 0.0)),
            motion_intensity=_score(segment.get("motion_intensity", 0.0)),
            visual_quality=_score(segment.get("visual_quality", 0.0)),
            emotion_intensity=_score(segment.get("emotion_intensity", 0.0)),
            hook_potential=_score(segment.get("hook_potential", 0.0)),
            climax_potential=_score(segment.get("climax_potential", 0.0)),
        )
        scene_id = f"SCENE-{asset_id.removeprefix('EXT-')}-{order:04d}"
        unsigned = {
            "schema": "football-shorts-ai.semantic-scene.v1",
            "scene_id": scene_id,
            "asset_id": asset_id,
            "provider": provider,
            "provider_asset_id": provider_asset_id,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(end - start, 3),
            "signals": signals.to_dict(),
            "rights_status": rights_status,
            "preview_allowed": preview_allowed,
            "render_allowed": render_allowed,
            "source_evidence_sha256": source_evidence,
            "inference_executed": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }
        evidence = canonical_sha256(unsigned)
        scene = SemanticScene(evidence_sha256=evidence, signals=signals, **{k: v for k, v in unsigned.items() if k != "signals"})
        scene.validate()
        scenes.append(scene)

    blockers: list[str] = []
    if rights_status == "reference_only":
        blockers.append("REFERENCE_ONLY_SCENES_NOT_RENDERABLE")
    state = "blocked" if blockers else "indexed"
    index_core = {
        "schema": "football-shorts-ai.semantic-scene-index.v1",
        "asset_id": asset_id,
        "source_evidence_sha256": source_evidence,
        "scenes": [scene.to_dict() for scene in scenes],
        "total_duration_seconds": round(max(scene.end_seconds for scene in scenes), 3),
        "index_state": state,
        "blockers": sorted(set(blockers)),
        "inference_executed": False,
        "auto_match": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(index_core)
    index_id = f"SCENEIDX-{provisional[:20].upper()}"
    unsigned = {**index_core, "index_id": index_id}
    evidence = canonical_sha256(unsigned)
    result = SemanticSceneIndex(
        index_id=index_id,
        evidence_sha256=evidence,
        scenes=tuple(scenes),
        blockers=tuple(unsigned["blockers"]),
        **{k: v for k, v in unsigned.items() if k not in {"index_id", "evidence_sha256", "scenes", "blockers"}},
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SemanticSceneIndexError(f"{key} is required")
    return value.strip()


def _required_number(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticSceneIndexError(f"{key} must be numeric")
    return float(value)


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SemanticSceneIndexError("scene scores must be numeric")
    return round(float(value), 4)


def _normalized_terms(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        raise SemanticSceneIndexError("scene terms must be an array")
    normalized = tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
    return normalized


def _validate_terms(values: tuple[str, ...], name: str) -> None:
    if tuple(sorted(set(values))) != values:
        raise SemanticSceneIndexError(f"{name} must be sorted and unique")


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise SemanticSceneIndexError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SemanticSceneIndexError("evidence must be hexadecimal") from exc


__all__ = [
    "SceneSignals",
    "SemanticScene",
    "SemanticSceneIndex",
    "SemanticSceneIndexError",
    "build_semantic_scene_index",
    "canonical_sha256",
]
