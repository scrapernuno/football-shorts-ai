"""
FOOTBALL-SHORTS-AI-0058D
AI DIRECTOR VIRAL PERFORMANCE PREDICTION AND VARIANT RANKING CONTRACT

Deterministically compares governed AI Director variants. No network access,
training, rendering, extraction, acquisition, or publication is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ViralPerformancePredictionError(ValueError):
    pass


SUPPORTED_STATES = {"ranked", "review_required", "blocked"}


@dataclass(frozen=True)
class VariantPrediction:
    prediction_id: str
    variant_id: str
    strategy: str
    hook_score: float
    retention_score: float
    pace_score: float
    emotion_score: float
    clarity_score: float
    rights_score: float
    viral_score: float
    confidence: float
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.prediction_id.startswith("DIRPRED-"):
            raise ViralPerformancePredictionError("invalid prediction identity")
        if not self.variant_id.startswith("DIRVAR-"):
            raise ViralPerformancePredictionError("invalid variant identity")
        if not self.strategy.strip():
            raise ViralPerformancePredictionError("strategy is required")
        for name in ("hook_score", "retention_score", "pace_score", "emotion_score", "clarity_score", "rights_score", "viral_score", "confidence"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ViralPerformancePredictionError(f"{name} must be between 0 and 1")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ViralPerformancePredictionError("prediction blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "prediction_id": self.prediction_id,
            "variant_id": self.variant_id,
            "strategy": self.strategy,
            "hook_score": round(self.hook_score, 4),
            "retention_score": round(self.retention_score, 4),
            "pace_score": round(self.pace_score, 4),
            "emotion_score": round(self.emotion_score, 4),
            "clarity_score": round(self.clarity_score, 4),
            "rights_score": round(self.rights_score, 4),
            "viral_score": round(self.viral_score, 4),
            "confidence": round(self.confidence, 4),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class VariantRankingReport:
    schema: str
    ranking_id: str
    predictions: tuple[VariantPrediction, ...]
    ranked_variant_ids: tuple[str, ...]
    recommended_variant_id: str | None
    ranking_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.director-variant-ranking.v1":
            raise ViralPerformancePredictionError("unsupported ranking schema")
        if not self.ranking_id.startswith("DIRRANK-"):
            raise ViralPerformancePredictionError("invalid ranking identity")
        if self.ranking_state not in SUPPORTED_STATES:
            raise ViralPerformancePredictionError("unsupported ranking state")
        ids = {item.variant_id for item in self.predictions}
        if len(ids) != len(self.predictions):
            raise ViralPerformancePredictionError("variant identities must be unique")
        for item in self.predictions:
            item.validate()
        expected = tuple(item.variant_id for item in sorted(self.predictions, key=lambda value: (-value.viral_score, -value.confidence, value.variant_id)))
        if self.ranked_variant_ids != expected:
            raise ViralPerformancePredictionError("variant ranking is inconsistent")
        if self.recommended_variant_id is not None and self.recommended_variant_id not in ids:
            raise ViralPerformancePredictionError("recommended variant is unknown")
        if self.ranking_state == "ranked" and (self.blockers or not self.predictions):
            raise ViralPerformancePredictionError("ranked report requires unblocked predictions")
        if self.ranking_state in {"review_required", "blocked"} and not self.blockers:
            raise ViralPerformancePredictionError("non-ranked report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise ViralPerformancePredictionError("0058D cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ViralPerformancePredictionError("ranking evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "ranking_id": self.ranking_id,
            "predictions": [item.to_dict() for item in self.predictions],
            "ranked_variant_ids": list(self.ranked_variant_ids),
            "recommended_variant_id": self.recommended_variant_id,
            "ranking_state": self.ranking_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_variant_ranking(*, variants: Sequence[Mapping[str, object]], minimum_confidence: float = 0.65) -> VariantRankingReport:
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ViralPerformancePredictionError("minimum_confidence must be between 0 and 1")
    blockers: set[str] = set()
    predictions: list[VariantPrediction] = []
    if not variants:
        blockers.add("DIRECTOR_VARIANTS_MISSING")
    for row in variants:
        variant_id = str(row.get("variant_id", ""))
        if not variant_id.startswith("DIRVAR-"):
            raise ViralPerformancePredictionError("variant_id must start with DIRVAR-")
        strategy = str(row.get("strategy", "")).strip()
        hook = _rate(row, "hook_strength_score", "hook_score")
        retention = _rate(row, "predicted_retention_score", "retention_score")
        pace = _rate(row, "pace_score")
        emotion = _rate(row, "emotional_arc_score", "emotion_score")
        clarity = _rate(row, "information_density_score", "clarity_score")
        render_allowed = bool(row.get("render_allowed", False))
        rights = 1.0 if render_allowed else 0.0
        confidence = _rate(row, "confidence", default=0.75)
        item_blockers: set[str] = set()
        if confidence < minimum_confidence:
            item_blockers.add("VARIANT_PREDICTION_REVIEW_REQUIRED")
        if not render_allowed:
            item_blockers.add("VARIANT_RENDER_NOT_ALLOWED")
        viral = _clamp(0.24 * hook + 0.25 * retention + 0.16 * pace + 0.16 * emotion + 0.11 * clarity + 0.08 * rights)
        core = {
            "variant_id": variant_id,
            "strategy": strategy,
            "hook_score": round(hook, 4),
            "retention_score": round(retention, 4),
            "pace_score": round(pace, 4),
            "emotion_score": round(emotion, 4),
            "clarity_score": round(clarity, 4),
            "rights_score": round(rights, 4),
            "viral_score": round(viral, 4),
            "confidence": round(confidence, 4),
            "blockers": tuple(sorted(item_blockers)),
        }
        predictions.append(VariantPrediction(prediction_id=f"DIRPRED-{canonical_sha256(core)[:20].upper()}", **core))
    if any(item.blockers for item in predictions):
        blockers.add("VARIANT_REVIEW_REQUIRED")
    ranked = tuple(item.variant_id for item in sorted(predictions, key=lambda value: (-value.viral_score, -value.confidence, value.variant_id)))
    eligible = [item for item in predictions if not item.blockers]
    recommended = max(eligible, key=lambda value: (value.viral_score, value.confidence, value.variant_id), default=None)
    state = "blocked" if not predictions else "review_required" if blockers else "ranked"
    core = {
        "schema": "football-shorts-ai.director-variant-ranking.v1",
        "predictions": [item.to_dict() for item in predictions],
        "ranked_variant_ids": list(ranked),
        "recommended_variant_id": None if recommended is None else recommended.variant_id,
        "ranking_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    ranking_id = f"DIRRANK-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "ranking_id": ranking_id}
    report = VariantRankingReport(
        schema=core["schema"], ranking_id=ranking_id, predictions=tuple(predictions),
        ranked_variant_ids=ranked, recommended_variant_id=core["recommended_variant_id"],
        ranking_state=state, blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    report.validate()
    return report


def _rate(payload: Mapping[str, object], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _clamp(float(value))
    return _clamp(default)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ViralPerformancePredictionError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ViralPerformancePredictionError("evidence must be hexadecimal") from exc


__all__ = ["VariantPrediction", "VariantRankingReport", "ViralPerformancePredictionError", "build_variant_ranking", "canonical_sha256"]
