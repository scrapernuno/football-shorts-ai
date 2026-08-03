"""
FOOTBALL-SHORTS-AI-0056D
VIRAL HOOK OPTIMIZER AND OPENING SCENE SELECTION

Ranks the hook candidates produced by 0056C and emits deterministic opening-scene
editorial evidence. This module performs no model inference, network access,
media acquisition, rendering or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from editorial.football_scene_understanding import FootballSceneUnderstandingReport
from editorial.semantic_scene_indexer import SemanticSceneIndex
from editorial.story_scene_matching import StorySceneMatchingReport


class ViralHookOptimizerError(ValueError):
    """Raised when governed hook optimization evidence is invalid."""


@dataclass(frozen=True)
class HookCandidateScore:
    scene_id: str
    rank: int
    source_match_score: float
    immediate_impact_score: float
    surprise_score: float
    motion_score: float
    emotion_score: float
    clarity_score: float
    retention_score: float
    semantic_alignment_score: float
    rights_score: float
    duration_fit_score: float
    final_hook_score: float
    render_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.scene_id.startswith("SCENE-"):
            raise ViralHookOptimizerError("invalid hook candidate scene identity")
        if self.rank < 1:
            raise ViralHookOptimizerError("hook candidate rank must be positive")
        for name, value in (
            ("source_match_score", self.source_match_score),
            ("immediate_impact_score", self.immediate_impact_score),
            ("surprise_score", self.surprise_score),
            ("motion_score", self.motion_score),
            ("emotion_score", self.emotion_score),
            ("clarity_score", self.clarity_score),
            ("retention_score", self.retention_score),
            ("semantic_alignment_score", self.semantic_alignment_score),
            ("rights_score", self.rights_score),
            ("duration_fit_score", self.duration_fit_score),
            ("final_hook_score", self.final_hook_score),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ViralHookOptimizerError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise ViralHookOptimizerError(f"{name} must be between 0 and 1")
        if self.render_allowed and self.blockers:
            raise ViralHookOptimizerError("renderable hook candidate cannot contain blockers")
        if not self.render_allowed and not self.blockers:
            raise ViralHookOptimizerError("non-renderable hook candidate requires blockers")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "scene_id": self.scene_id,
            "rank": self.rank,
            "source_match_score": self.source_match_score,
            "immediate_impact_score": self.immediate_impact_score,
            "surprise_score": self.surprise_score,
            "motion_score": self.motion_score,
            "emotion_score": self.emotion_score,
            "clarity_score": self.clarity_score,
            "retention_score": self.retention_score,
            "semantic_alignment_score": self.semantic_alignment_score,
            "rights_score": self.rights_score,
            "duration_fit_score": self.duration_fit_score,
            "final_hook_score": self.final_hook_score,
            "render_allowed": self.render_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ViralHookOptimizationReport:
    schema: str
    optimization_id: str
    story_match_report_id: str
    hook_beat_id: str
    hook_text: str
    selected_scene_id: str
    alternative_scene_ids: tuple[str, ...]
    candidates: tuple[HookCandidateScore, ...]
    opening_duration_seconds: float
    optimization_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    model_execution_enabled: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.viral-hook-optimization.v1":
            raise ViralHookOptimizerError("unsupported hook optimization schema")
        if not self.optimization_id.startswith("HOOKOPT-"):
            raise ViralHookOptimizerError("invalid hook optimization identity")
        if not self.story_match_report_id.startswith("STORYMATCH-"):
            raise ViralHookOptimizerError("invalid story matching identity")
        if not self.hook_beat_id.startswith("BEAT-"):
            raise ViralHookOptimizerError("invalid hook beat identity")
        if not self.hook_text.strip():
            raise ViralHookOptimizerError("hook text is required")
        if not self.candidates:
            raise ViralHookOptimizerError("hook optimization requires candidates")
        for expected_rank, candidate in enumerate(self.candidates, start=1):
            candidate.validate()
            if candidate.rank != expected_rank:
                raise ViralHookOptimizerError("hook candidate ranks must be contiguous")
        candidate_ids = {candidate.scene_id for candidate in self.candidates}
        if self.selected_scene_id not in candidate_ids:
            raise ViralHookOptimizerError("selected hook scene must be a candidate")
        if len(set(self.alternative_scene_ids)) != len(self.alternative_scene_ids):
            raise ViralHookOptimizerError("alternative scenes must be unique")
        if any(scene_id not in candidate_ids for scene_id in self.alternative_scene_ids):
            raise ViralHookOptimizerError("alternative hook scene is not a candidate")
        if self.selected_scene_id in self.alternative_scene_ids:
            raise ViralHookOptimizerError("selected hook scene cannot be an alternative")
        if not 0.5 <= self.opening_duration_seconds <= 5.0:
            raise ViralHookOptimizerError("opening duration must be between 0.5 and 5 seconds")
        if self.optimization_state not in {"optimized", "blocked"}:
            raise ViralHookOptimizerError("unsupported optimization state")
        selected = next(item for item in self.candidates if item.scene_id == self.selected_scene_id)
        if self.optimization_state == "optimized" and (self.blockers or not selected.render_allowed):
            raise ViralHookOptimizerError("optimized hook must select a renderable scene")
        if self.optimization_state == "blocked" and not self.blockers:
            raise ViralHookOptimizerError("blocked hook optimization requires blockers")
        if any((
            self.model_execution_enabled,
            self.network_enabled,
            self.acquisition_enabled,
            self.auto_render,
            self.auto_publish,
        )):
            raise ViralHookOptimizerError("0056D cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ViralHookOptimizerError("hook optimization evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "optimization_id": self.optimization_id,
            "story_match_report_id": self.story_match_report_id,
            "hook_beat_id": self.hook_beat_id,
            "hook_text": self.hook_text,
            "selected_scene_id": self.selected_scene_id,
            "alternative_scene_ids": list(self.alternative_scene_ids),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "opening_duration_seconds": self.opening_duration_seconds,
            "optimization_state": self.optimization_state,
            "blockers": list(self.blockers),
            "model_execution_enabled": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def optimize_viral_hook(
    *,
    matching: StorySceneMatchingReport,
    index: SemanticSceneIndex,
    understanding: FootballSceneUnderstandingReport,
    max_alternatives: int = 2,
) -> ViralHookOptimizationReport:
    """Select the strongest governed opening scene for the story hook."""

    index.validate()
    understanding.validate(index)
    matching.validate(index, understanding)
    if not 0 <= max_alternatives <= 5:
        raise ViralHookOptimizerError("max_alternatives must be between 0 and 5")

    hook_matches = [item for item in matching.matches if item.beat.role == "hook"]
    if len(hook_matches) != 1:
        raise ViralHookOptimizerError("story must contain exactly one hook beat")
    hook_match = hook_matches[0]

    scenes = {scene.scene_id: scene for scene in index.scenes}
    classifications = {item.scene_id: item for item in understanding.classifications}
    scored: list[HookCandidateScore] = []

    for source in hook_match.candidates:
        scene = scenes[source.scene_id]
        classification = classifications[source.scene_id]
        signals = scene.signals
        action_boost = 1.0 if classification.action in {"goal", "shot", "save", "celebration", "dribble"} else 0.35
        immediate = _clamp(
            0.35 * classification.hook_score
            + 0.25 * classification.viral_signal_score
            + 0.20 * signals.motion_intensity
            + 0.20 * action_boost
        )
        surprise = _clamp(
            0.55 * (1.0 if signals.emotion == "surprise" else signals.emotion_intensity)
            + 0.25 * classification.hook_score
            + 0.20 * (1.0 if classification.action in {"goal", "save", "shot"} else 0.0)
        )
        clarity = _clamp(
            0.45 * signals.visual_quality
            + 0.20 * (1.0 if signals.ball_visible else 0.0)
            + 0.20 * (1.0 if signals.face_visible else 0.0)
            + 0.15 * (1.0 if signals.shot_type in {"close_up", "medium", "wide"} else 0.5)
        )
        duration_fit = _duration_fit(scene.duration_seconds)
        final = _clamp(
            0.18 * source.total_score
            + 0.17 * immediate
            + 0.10 * surprise
            + 0.10 * signals.motion_intensity
            + 0.10 * signals.emotion_intensity
            + 0.08 * clarity
            + 0.10 * classification.retention_score
            + 0.08 * source.semantic_score
            + 0.06 * source.rights_score
            + 0.03 * duration_fit
        )
        blockers = () if scene.render_allowed else ("HOOK_SCENE_NOT_RENDERABLE",)
        scored.append(
            HookCandidateScore(
                scene_id=scene.scene_id,
                rank=1,
                source_match_score=source.total_score,
                immediate_impact_score=immediate,
                surprise_score=surprise,
                motion_score=round(float(signals.motion_intensity), 4),
                emotion_score=round(float(signals.emotion_intensity), 4),
                clarity_score=clarity,
                retention_score=classification.retention_score,
                semantic_alignment_score=source.semantic_score,
                rights_score=source.rights_score,
                duration_fit_score=duration_fit,
                final_hook_score=final,
                render_allowed=scene.render_allowed,
                blockers=blockers,
            )
        )

    scored.sort(key=lambda item: (-item.final_hook_score, -item.rights_score, -item.retention_score, item.scene_id))
    ranked = tuple(
        HookCandidateScore(**{**candidate.__dict__, "rank": rank})
        for rank, candidate in enumerate(scored, start=1)
    )
    renderable = [candidate for candidate in ranked if candidate.render_allowed]
    selected = renderable[0] if renderable else ranked[0]
    alternatives = tuple(
        candidate.scene_id
        for candidate in ranked
        if candidate.scene_id != selected.scene_id
    )[:max_alternatives]
    blockers = () if renderable else ("NO_RENDERABLE_HOOK_CANDIDATE",)
    state = "optimized" if renderable else "blocked"
    selected_scene = scenes[selected.scene_id]
    opening_duration = round(min(3.0, max(0.5, selected_scene.duration_seconds)), 3)

    core = {
        "schema": "football-shorts-ai.viral-hook-optimization.v1",
        "story_match_report_id": matching.report_id,
        "hook_beat_id": hook_match.beat.beat_id,
        "hook_text": hook_match.beat.text,
        "selected_scene_id": selected.scene_id,
        "alternative_scene_ids": list(alternatives),
        "candidates": [candidate.to_dict() for candidate in ranked],
        "opening_duration_seconds": opening_duration,
        "optimization_state": state,
        "blockers": list(blockers),
        "model_execution_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    optimization_id = f"HOOKOPT-{provisional[:20].upper()}"
    unsigned = {**core, "optimization_id": optimization_id}
    evidence = canonical_sha256(unsigned)
    result = ViralHookOptimizationReport(
        optimization_id=optimization_id,
        evidence_sha256=evidence,
        alternative_scene_ids=alternatives,
        candidates=ranked,
        blockers=blockers,
        **{
            key: value
            for key, value in unsigned.items()
            if key not in {"optimization_id", "evidence_sha256", "alternative_scene_ids", "candidates", "blockers"}
        },
    )
    result.validate()
    return result


def _duration_fit(duration_seconds: float) -> float:
    duration = float(duration_seconds)
    if 1.0 <= duration <= 3.0:
        return 1.0
    if 0.5 <= duration < 1.0:
        return round(0.7 + 0.3 * ((duration - 0.5) / 0.5), 4)
    if 3.0 < duration <= 5.0:
        return round(1.0 - 0.25 * ((duration - 3.0) / 2.0), 4)
    return 0.5


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ViralHookOptimizerError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ViralHookOptimizerError("evidence must be hexadecimal") from exc


__all__ = [
    "HookCandidateScore",
    "ViralHookOptimizationReport",
    "ViralHookOptimizerError",
    "canonical_sha256",
    "optimize_viral_hook",
]
