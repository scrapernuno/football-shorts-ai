"""
FOOTBALL-SHORTS-AI-0056F
RETENTION, VIRAL POTENTIAL AND EDITORIAL QUALITY SCORING

Consolidates the governed evidence produced by 0056A-0056E into one deterministic,
audit-friendly editorial scorecard. It does not execute models, media operations,
rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from editorial.football_scene_understanding import FootballSceneUnderstandingReport
from editorial.semantic_scene_indexer import SemanticSceneIndex
from editorial.story_alignment_optimizer import StoryAlignmentReport
from editorial.story_scene_matching import StorySceneMatchingReport
from editorial.viral_hook_optimizer import ViralHookOptimizationReport


class EditorialQualityScoringError(ValueError):
    """Raised when governed editorial scoring evidence is invalid."""


@dataclass(frozen=True)
class EditorialQualityReport:
    schema: str
    score_id: str
    alignment_id: str
    hook_optimization_id: str
    story_match_report_id: str
    hook_strength_score: float
    semantic_alignment_score: float
    narrative_progression_score: float
    sequence_diversity_score: float
    motion_energy_score: float
    emotional_intensity_score: float
    visual_quality_score: float
    retention_potential_score: float
    rights_readiness_score: float
    viral_potential_score: float
    editorial_quality_score: float
    quality_band: str
    score_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    model_execution_enabled: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.editorial-quality-score.v1":
            raise EditorialQualityScoringError("unsupported editorial score schema")
        if not self.score_id.startswith("EDITSCORE-"):
            raise EditorialQualityScoringError("invalid editorial score identity")
        if not self.alignment_id.startswith("ALIGN-"):
            raise EditorialQualityScoringError("invalid alignment identity")
        if not self.hook_optimization_id.startswith("HOOKOPT-"):
            raise EditorialQualityScoringError("invalid hook optimization identity")
        if not self.story_match_report_id.startswith("STORYMATCH-"):
            raise EditorialQualityScoringError("invalid story matching identity")
        for name, value in self._score_items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EditorialQualityScoringError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise EditorialQualityScoringError(f"{name} must be between 0 and 1")
        if self.quality_band not in {"low", "developing", "strong", "excellent"}:
            raise EditorialQualityScoringError("unsupported quality band")
        if self.score_state not in {"scored", "blocked"}:
            raise EditorialQualityScoringError("unsupported score state")
        if self.score_state == "scored" and self.blockers:
            raise EditorialQualityScoringError("scored report cannot contain blockers")
        if self.score_state == "blocked" and not self.blockers:
            raise EditorialQualityScoringError("blocked score requires blockers")
        if any((self.model_execution_enabled, self.network_enabled, self.acquisition_enabled, self.auto_render, self.auto_publish)):
            raise EditorialQualityScoringError("0056F cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise EditorialQualityScoringError("editorial score evidence mismatch")

    def _score_items(self) -> tuple[tuple[str, float], ...]:
        return (
            ("hook_strength_score", self.hook_strength_score),
            ("semantic_alignment_score", self.semantic_alignment_score),
            ("narrative_progression_score", self.narrative_progression_score),
            ("sequence_diversity_score", self.sequence_diversity_score),
            ("motion_energy_score", self.motion_energy_score),
            ("emotional_intensity_score", self.emotional_intensity_score),
            ("visual_quality_score", self.visual_quality_score),
            ("retention_potential_score", self.retention_potential_score),
            ("rights_readiness_score", self.rights_readiness_score),
            ("viral_potential_score", self.viral_potential_score),
            ("editorial_quality_score", self.editorial_quality_score),
        )

    def _unsigned(self) -> dict[str, object]:
        payload = {
            "schema": self.schema,
            "score_id": self.score_id,
            "alignment_id": self.alignment_id,
            "hook_optimization_id": self.hook_optimization_id,
            "story_match_report_id": self.story_match_report_id,
            "quality_band": self.quality_band,
            "score_state": self.score_state,
            "blockers": list(self.blockers),
            "model_execution_enabled": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }
        payload.update({name: value for name, value in self._score_items()})
        return payload

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def score_editorial_quality(
    *,
    alignment: StoryAlignmentReport,
    hook: ViralHookOptimizationReport,
    matching: StorySceneMatchingReport,
    index: SemanticSceneIndex,
    understanding: FootballSceneUnderstandingReport,
) -> EditorialQualityReport:
    alignment.validate()
    hook.validate()
    index.validate()
    understanding.validate(index)
    matching.validate(index, understanding)
    if alignment.hook_optimization_id != hook.optimization_id:
        raise EditorialQualityScoringError("alignment and hook evidence do not match")
    if alignment.story_match_report_id != matching.report_id:
        raise EditorialQualityScoringError("alignment and story matching evidence do not match")

    scenes = {scene.scene_id: scene for scene in index.scenes}
    classes = {item.scene_id: item for item in understanding.classifications}
    selected = [scenes[item.scene_id] for item in alignment.scenes]
    selected_classes = [classes[item.scene_id] for item in alignment.scenes]

    hook_strength = next(item.final_hook_score for item in hook.candidates if item.scene_id == hook.selected_scene_id)
    semantic = alignment.average_match_score
    progression = alignment.narrative_progression_score
    diversity = alignment.sequence_diversity_score
    motion = _average(float(scene.signals.motion_intensity) for scene in selected)
    emotion = _average(float(scene.signals.emotion_intensity) for scene in selected)
    quality = _average(float(scene.signals.visual_quality) for scene in selected)
    retention = _average(float(item.retention_score) for item in selected_classes)
    rights = round(sum(1.0 for item in alignment.scenes if item.render_allowed) / len(alignment.scenes), 4)

    viral = _clamp(
        0.24 * hook_strength
        + 0.18 * retention
        + 0.14 * emotion
        + 0.12 * motion
        + 0.12 * semantic
        + 0.10 * progression
        + 0.06 * diversity
        + 0.04 * quality
    )
    editorial = _clamp(
        0.20 * semantic
        + 0.16 * progression
        + 0.12 * diversity
        + 0.16 * quality
        + 0.14 * retention
        + 0.12 * hook_strength
        + 0.10 * rights
    )
    blockers = tuple(sorted(set((*alignment.blockers, *hook.blockers, *matching.blockers))))
    state = "blocked" if blockers or rights < 1.0 else "scored"
    band = _quality_band(editorial)

    core = {
        "schema": "football-shorts-ai.editorial-quality-score.v1",
        "alignment_id": alignment.alignment_id,
        "hook_optimization_id": hook.optimization_id,
        "story_match_report_id": matching.report_id,
        "hook_strength_score": hook_strength,
        "semantic_alignment_score": semantic,
        "narrative_progression_score": progression,
        "sequence_diversity_score": diversity,
        "motion_energy_score": motion,
        "emotional_intensity_score": emotion,
        "visual_quality_score": quality,
        "retention_potential_score": retention,
        "rights_readiness_score": rights,
        "viral_potential_score": viral,
        "editorial_quality_score": editorial,
        "quality_band": band,
        "score_state": state,
        "blockers": list(blockers),
        "model_execution_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    score_id = f"EDITSCORE-{provisional[:20].upper()}"
    unsigned = {**core, "score_id": score_id}
    evidence = canonical_sha256(unsigned)
    result = EditorialQualityReport(
        score_id=score_id,
        evidence_sha256=evidence,
        blockers=tuple(blockers),
        **{key: value for key, value in unsigned.items() if key not in {"score_id", "evidence_sha256", "blockers"}},
    )
    result.validate()
    return result


def _average(values) -> float:
    materialized = tuple(float(value) for value in values)
    if not materialized:
        raise EditorialQualityScoringError("at least one score value is required")
    return round(sum(materialized) / len(materialized), 4)


def _quality_band(value: float) -> str:
    if value >= 0.85:
        return "excellent"
    if value >= 0.70:
        return "strong"
    if value >= 0.50:
        return "developing"
    return "low"


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise EditorialQualityScoringError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EditorialQualityScoringError("evidence must be hexadecimal") from exc


__all__ = [
    "EditorialQualityReport",
    "EditorialQualityScoringError",
    "canonical_sha256",
    "score_editorial_quality",
]
