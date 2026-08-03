"""
FOOTBALL-SHORTS-AI-0058A
AI DIRECTOR STRATEGY AND VERSIONING CONTRACT

Builds deterministic editorial variants from governed 0056/0057 evidence.
No network access, acquisition, model training, extraction, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class AIDirectorStrategyError(ValueError):
    """Raised when governed AI Director evidence is invalid."""


SUPPORTED_STRATEGIES = {"fast", "emotional", "informative", "balanced"}
SUPPORTED_STATES = {"proposed", "review_required", "blocked"}
SUPPORTED_ROLES = {"hook", "development", "climax", "reaction", "resolution", "cta"}


@dataclass(frozen=True)
class DirectorSegment:
    segment_id: str
    clip_id: str
    scene_id: str
    editorial_role: str
    start_seconds: float
    end_seconds: float
    priority: int
    strategy_score: float
    rationale_codes: tuple[str, ...]

    def validate(self) -> None:
        if not self.segment_id.startswith("DIRSEG-"):
            raise AIDirectorStrategyError("invalid director segment identity")
        if not self.clip_id.startswith("VIRALCLIP-"):
            raise AIDirectorStrategyError("invalid clip identity")
        if not self.scene_id.startswith("VSCENE-"):
            raise AIDirectorStrategyError("invalid scene identity")
        if self.editorial_role not in SUPPORTED_ROLES:
            raise AIDirectorStrategyError("unsupported editorial role")
        if not 0.0 <= self.start_seconds < self.end_seconds:
            raise AIDirectorStrategyError("director segment timestamps are invalid")
        if self.priority < 1:
            raise AIDirectorStrategyError("priority must be positive")
        if not 0.0 <= self.strategy_score <= 1.0:
            raise AIDirectorStrategyError("strategy_score must be between 0 and 1")
        if tuple(sorted(set(self.rationale_codes))) != self.rationale_codes:
            raise AIDirectorStrategyError("rationale codes must be normalized")

    @property
    def duration_seconds(self) -> float:
        return round(self.end_seconds - self.start_seconds, 3)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "segment_id": self.segment_id,
            "clip_id": self.clip_id,
            "scene_id": self.scene_id,
            "editorial_role": self.editorial_role,
            "start_seconds": round(self.start_seconds, 3),
            "end_seconds": round(self.end_seconds, 3),
            "duration_seconds": self.duration_seconds,
            "priority": self.priority,
            "strategy_score": round(self.strategy_score, 4),
            "rationale_codes": list(self.rationale_codes),
        }


@dataclass(frozen=True)
class DirectorVariant:
    variant_id: str
    strategy: str
    title: str
    segments: tuple[DirectorSegment, ...]
    total_duration_seconds: float
    hook_strength_score: float
    emotional_arc_score: float
    information_density_score: float
    pacing_score: float
    predicted_retention_score: float
    render_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.variant_id.startswith("DIRVAR-"):
            raise AIDirectorStrategyError("invalid director variant identity")
        if self.strategy not in SUPPORTED_STRATEGIES:
            raise AIDirectorStrategyError("unsupported director strategy")
        if not self.title.strip():
            raise AIDirectorStrategyError("variant title is required")
        if not self.segments:
            raise AIDirectorStrategyError("variant requires segments")
        for item in self.segments:
            item.validate()
        if len({item.segment_id for item in self.segments}) != len(self.segments):
            raise AIDirectorStrategyError("segment identities must be unique")
        if abs(sum(item.duration_seconds for item in self.segments) - self.total_duration_seconds) > 0.01:
            raise AIDirectorStrategyError("variant duration is inconsistent")
        for name in (
            "hook_strength_score", "emotional_arc_score", "information_density_score",
            "pacing_score", "predicted_retention_score",
        ):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise AIDirectorStrategyError(f"{name} must be between 0 and 1")
        if self.render_allowed and self.blockers:
            raise AIDirectorStrategyError("renderable variant cannot contain blockers")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise AIDirectorStrategyError("variant blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "variant_id": self.variant_id,
            "strategy": self.strategy,
            "title": self.title,
            "segments": [item.to_dict() for item in self.segments],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "hook_strength_score": round(self.hook_strength_score, 4),
            "emotional_arc_score": round(self.emotional_arc_score, 4),
            "information_density_score": round(self.information_density_score, 4),
            "pacing_score": round(self.pacing_score, 4),
            "predicted_retention_score": round(self.predicted_retention_score, 4),
            "render_allowed": self.render_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class AIDirectorStrategyReport:
    schema: str
    director_id: str
    clip_plan_id: str
    variants: tuple[DirectorVariant, ...]
    recommended_variant_id: str | None
    director_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.ai-director-strategy.v1":
            raise AIDirectorStrategyError("unsupported AI Director schema")
        if not self.director_id.startswith("AIDIRECTOR-"):
            raise AIDirectorStrategyError("invalid AI Director identity")
        if not self.clip_plan_id.startswith("CLIPPLAN-"):
            raise AIDirectorStrategyError("invalid clip-plan identity")
        if self.director_state not in SUPPORTED_STATES:
            raise AIDirectorStrategyError("unsupported director state")
        for item in self.variants:
            item.validate()
        variant_ids = {item.variant_id for item in self.variants}
        if len(variant_ids) != len(self.variants):
            raise AIDirectorStrategyError("variant identities must be unique")
        if self.recommended_variant_id is not None and self.recommended_variant_id not in variant_ids:
            raise AIDirectorStrategyError("recommended variant is unknown")
        if self.director_state == "proposed" and (self.blockers or not self.variants):
            raise AIDirectorStrategyError("proposed report requires unblocked variants")
        if self.director_state in {"review_required", "blocked"} and not self.blockers:
            raise AIDirectorStrategyError("non-proposed report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise AIDirectorStrategyError("0058A cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise AIDirectorStrategyError("AI Director evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "director_id": self.director_id,
            "clip_plan_id": self.clip_plan_id,
            "variants": [item.to_dict() for item in self.variants],
            "recommended_variant_id": self.recommended_variant_id,
            "director_state": self.director_state,
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


def build_ai_director_strategy_report(
    *,
    clip_plan: Mapping[str, object],
    strategies: Sequence[str] = ("fast", "emotional", "informative", "balanced"),
) -> AIDirectorStrategyReport:
    clip_plan_id = _required_id(clip_plan, "plan_id", "CLIPPLAN-")
    blockers: set[str] = set()
    planning_state = str(clip_plan.get("planning_state", "blocked"))
    if planning_state == "blocked":
        blockers.add("CLIP_PLAN_BLOCKED")
    elif planning_state == "review_required":
        blockers.add("CLIP_PLAN_REVIEW_REQUIRED")

    requested = tuple(dict.fromkeys(str(item) for item in strategies))
    if not requested or any(item not in SUPPORTED_STRATEGIES for item in requested):
        raise AIDirectorStrategyError("strategies contain unsupported values")

    clips = [item for item in clip_plan.get("clips", ()) if isinstance(item, Mapping)]
    if not clips:
        blockers.add("CLIP_PLAN_EMPTY")

    variants = tuple(_build_variant(strategy, clips) for strategy in requested if clips)
    if any(not item.render_allowed for item in variants):
        blockers.add("DIRECTOR_VARIANT_RENDER_BLOCKED")

    state = "blocked" if "CLIP_PLAN_BLOCKED" in blockers or not variants else "review_required" if blockers else "proposed"
    recommended = max(
        variants,
        key=lambda item: (item.predicted_retention_score, item.hook_strength_score, item.variant_id),
        default=None,
    )
    core = {
        "schema": "football-shorts-ai.ai-director-strategy.v1",
        "clip_plan_id": clip_plan_id,
        "variants": [item.to_dict() for item in variants],
        "recommended_variant_id": None if recommended is None else recommended.variant_id,
        "director_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    director_id = f"AIDIRECTOR-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "director_id": director_id}
    result = AIDirectorStrategyReport(
        schema="football-shorts-ai.ai-director-strategy.v1",
        director_id=director_id,
        clip_plan_id=clip_plan_id,
        variants=variants,
        recommended_variant_id=core["recommended_variant_id"],
        director_state=state,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


def _build_variant(strategy: str, clips: Sequence[Mapping[str, object]]) -> DirectorVariant:
    weights = {
        "fast": {"hook": 0.35, "viral": 0.25, "confidence": 0.15, "brevity": 0.25},
        "emotional": {"hook": 0.20, "viral": 0.30, "confidence": 0.15, "brevity": 0.10, "climax": 0.25},
        "informative": {"hook": 0.15, "viral": 0.20, "confidence": 0.25, "brevity": 0.10, "development": 0.30},
        "balanced": {"hook": 0.25, "viral": 0.25, "confidence": 0.20, "brevity": 0.15, "climax": 0.15},
    }[strategy]

    scored: list[tuple[float, Mapping[str, object]]] = []
    for item in clips:
        role = str(item.get("editorial_role", "development"))
        duration = max(0.001, float(item.get("end_seconds", 0.0)) - float(item.get("start_seconds", 0.0)))
        score = (
            weights.get("hook", 0.0) * (1.0 if role == "hook" else 0.35)
            + weights.get("climax", 0.0) * (1.0 if role == "climax" else 0.25)
            + weights.get("development", 0.0) * (1.0 if role == "development" else 0.35)
            + weights["viral"] * float(item.get("viral_score", item.get("viral_moment_score", 0.0)))
            + weights["confidence"] * float(item.get("confidence", 0.0))
            + weights["brevity"] * min(1.0, 3.0 / duration)
        )
        scored.append((max(0.0, min(1.0, score)), item))

    limit = 3 if strategy == "fast" else 5
    selected = sorted(scored, key=lambda pair: (-pair[0], int(pair[1].get("priority", 999)), str(pair[1].get("clip_id", ""))))[:limit]
    role_order = {"hook": 0, "development": 1, "climax": 2, "reaction": 3, "resolution": 4, "cta": 5}
    selected.sort(key=lambda pair: (role_order.get(str(pair[1].get("editorial_role", "development")), 9), int(pair[1].get("priority", 999))))

    segments: list[DirectorSegment] = []
    render_allowed = True
    blockers: set[str] = set()
    for priority, (score, item) in enumerate(selected, 1):
        if not bool(item.get("render_allowed", False)):
            render_allowed = False
            blockers.add("CLIP_RENDER_NOT_ALLOWED")
        core = {
            "clip_id": str(item["clip_id"]),
            "scene_id": str(item["scene_id"]),
            "editorial_role": str(item.get("editorial_role", "development")),
            "start_seconds": float(item["start_seconds"]),
            "end_seconds": float(item["end_seconds"]),
            "priority": priority,
            "strategy_score": round(score, 4),
            "rationale_codes": tuple(sorted({f"STRATEGY_{strategy.upper()}", f"ROLE_{str(item.get('editorial_role', 'development')).upper()}"})),
        }
        segments.append(DirectorSegment(segment_id=f"DIRSEG-{canonical_sha256(core)[:20].upper()}", **core))

    total = round(sum(item.duration_seconds for item in segments), 3)
    hook = max((item.strategy_score for item in segments if item.editorial_role == "hook"), default=0.0)
    climax = max((item.strategy_score for item in segments if item.editorial_role == "climax"), default=0.0)
    emotional = max((climax, max((item.strategy_score for item in segments if item.editorial_role == "reaction"), default=0.0)))
    information = min(1.0, len({item.editorial_role for item in segments}) / 5.0)
    pacing = min(1.0, len(segments) / max(total / 2.5, 1.0))
    retention = max(0.0, min(1.0, 0.35 * hook + 0.25 * emotional + 0.20 * pacing + 0.20 * sum(item.strategy_score for item in segments) / len(segments)))
    title = {
        "fast": "Fast Impact Cut",
        "emotional": "Emotional Arc Cut",
        "informative": "Context and Story Cut",
        "balanced": "Balanced Director Cut",
    }[strategy]
    core = {
        "strategy": strategy,
        "title": title,
        "segments": [item.to_dict() for item in segments],
        "total_duration_seconds": total,
        "hook_strength_score": round(hook, 4),
        "emotional_arc_score": round(emotional, 4),
        "information_density_score": round(information, 4),
        "pacing_score": round(pacing, 4),
        "predicted_retention_score": round(retention, 4),
        "render_allowed": render_allowed,
        "blockers": sorted(blockers),
    }
    return DirectorVariant(
        variant_id=f"DIRVAR-{canonical_sha256(core)[:20].upper()}",
        strategy=strategy,
        title=title,
        segments=tuple(segments),
        total_duration_seconds=total,
        hook_strength_score=round(hook, 4),
        emotional_arc_score=round(emotional, 4),
        information_density_score=round(information, 4),
        pacing_score=round(pacing, 4),
        predicted_retention_score=round(retention, 4),
        render_allowed=render_allowed,
        blockers=tuple(sorted(blockers)),
    )


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_id(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise AIDirectorStrategyError(f"{key} must start with {prefix}")
    return value


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise AIDirectorStrategyError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AIDirectorStrategyError("evidence must be hexadecimal") from exc


__all__ = [
    "AIDirectorStrategyError",
    "AIDirectorStrategyReport",
    "DirectorSegment",
    "DirectorVariant",
    "build_ai_director_strategy_report",
    "canonical_sha256",
]
