"""
FOOTBALL-SHORTS-AI-0058C
AI DIRECTOR CLIP TIMING, PACE AND TRANSITION OPTIMIZATION CONTRACT

Creates deterministic timing and transition proposals from governed 0058B narrative
alignment evidence. It performs no network access, media acquisition, extraction,
model training, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ClipTimingOptimizationError(ValueError):
    """Raised when governed timing or transition evidence is invalid."""


SUPPORTED_STATES = {"optimized", "review_required", "blocked"}
SUPPORTED_STRATEGIES = {"fast", "emotional", "informative", "balanced"}
SUPPORTED_TRANSITIONS = {"none", "cut", "match_cut", "crossfade", "fade", "dip_to_black"}


@dataclass(frozen=True)
class OptimizedClipTiming:
    timing_id: str
    beat_id: str
    segment_id: str
    clip_id: str
    editorial_role: str
    source_start_seconds: float
    source_end_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    playback_rate: float
    transition_in: str
    transition_out: str
    transition_duration_seconds: float
    pace_score: float
    retention_score: float
    confidence: float
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.timing_id.startswith("DIRTIMING-"):
            raise ClipTimingOptimizationError("invalid timing identity")
        if not self.beat_id.startswith("DIRBEAT-"):
            raise ClipTimingOptimizationError("invalid beat identity")
        if not self.segment_id.startswith("DIRSEG-"):
            raise ClipTimingOptimizationError("invalid segment identity")
        if not self.clip_id.startswith("VIRALCLIP-"):
            raise ClipTimingOptimizationError("invalid clip identity")
        if not 0.0 <= self.source_start_seconds < self.source_end_seconds:
            raise ClipTimingOptimizationError("source timing is invalid")
        if not 0.0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise ClipTimingOptimizationError("timeline timing is invalid")
        if not 0.75 <= self.playback_rate <= 1.35:
            raise ClipTimingOptimizationError("playback rate is outside governed limits")
        if self.transition_in not in SUPPORTED_TRANSITIONS or self.transition_out not in SUPPORTED_TRANSITIONS:
            raise ClipTimingOptimizationError("unsupported transition")
        if not 0.0 <= self.transition_duration_seconds <= 1.0:
            raise ClipTimingOptimizationError("transition duration is outside governed limits")
        for name in ("pace_score", "retention_score", "confidence"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ClipTimingOptimizationError(f"{name} must be between 0 and 1")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ClipTimingOptimizationError("timing blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "timing_id": self.timing_id,
            "beat_id": self.beat_id,
            "segment_id": self.segment_id,
            "clip_id": self.clip_id,
            "editorial_role": self.editorial_role,
            "source_start_seconds": round(self.source_start_seconds, 3),
            "source_end_seconds": round(self.source_end_seconds, 3),
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "playback_rate": round(self.playback_rate, 4),
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "transition_duration_seconds": round(self.transition_duration_seconds, 3),
            "pace_score": round(self.pace_score, 4),
            "retention_score": round(self.retention_score, 4),
            "confidence": round(self.confidence, 4),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ClipTimingOptimizationReport:
    schema: str
    optimization_id: str
    alignment_id: str
    strategy: str
    timings: tuple[OptimizedClipTiming, ...]
    total_duration_seconds: float
    average_pace_score: float
    predicted_retention_score: float
    optimization_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.clip-timing-optimization.v1":
            raise ClipTimingOptimizationError("unsupported optimization schema")
        if not self.optimization_id.startswith("DIROPT-"):
            raise ClipTimingOptimizationError("invalid optimization identity")
        if not self.alignment_id.startswith("DIRALIGN-"):
            raise ClipTimingOptimizationError("invalid alignment identity")
        if self.strategy not in SUPPORTED_STRATEGIES:
            raise ClipTimingOptimizationError("unsupported director strategy")
        if self.optimization_state not in SUPPORTED_STATES:
            raise ClipTimingOptimizationError("unsupported optimization state")
        timing_ids = {item.timing_id for item in self.timings}
        if len(timing_ids) != len(self.timings):
            raise ClipTimingOptimizationError("timing identities must be unique")
        previous_end = 0.0
        for index, item in enumerate(self.timings):
            item.validate()
            if index == 0 and item.timeline_start_seconds != 0.0:
                raise ClipTimingOptimizationError("timeline must start at zero")
            if abs(item.timeline_start_seconds - previous_end) > 0.001:
                raise ClipTimingOptimizationError("timeline must be continuous")
            previous_end = item.timeline_end_seconds
        expected_duration = 0.0 if not self.timings else self.timings[-1].timeline_end_seconds
        if abs(self.total_duration_seconds - expected_duration) > 0.001:
            raise ClipTimingOptimizationError("total duration is inconsistent")
        for name in ("average_pace_score", "predicted_retention_score"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ClipTimingOptimizationError(f"{name} must be between 0 and 1")
        if self.optimization_state == "optimized" and (self.blockers or not self.timings):
            raise ClipTimingOptimizationError("optimized report requires unblocked timings")
        if self.optimization_state in {"review_required", "blocked"} and not self.blockers:
            raise ClipTimingOptimizationError("non-optimized report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise ClipTimingOptimizationError("0058C cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ClipTimingOptimizationError("optimization evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "optimization_id": self.optimization_id,
            "alignment_id": self.alignment_id,
            "strategy": self.strategy,
            "timings": [item.to_dict() for item in self.timings],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "average_pace_score": round(self.average_pace_score, 4),
            "predicted_retention_score": round(self.predicted_retention_score, 4),
            "optimization_state": self.optimization_state,
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


def build_clip_timing_optimization(
    *,
    alignment_report: Mapping[str, object],
    strategy: str,
    minimum_confidence: float = 0.65,
) -> ClipTimingOptimizationReport:
    if strategy not in SUPPORTED_STRATEGIES:
        raise ClipTimingOptimizationError("unsupported director strategy")
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ClipTimingOptimizationError("minimum_confidence must be between 0 and 1")
    alignment_id = _required_id(alignment_report, "alignment_id", "DIRALIGN-")
    blockers: set[str] = set()
    alignment_state = alignment_report.get("alignment_state")
    if alignment_state == "blocked":
        blockers.add("NARRATIVE_ALIGNMENT_BLOCKED")
    elif alignment_state == "review_required":
        blockers.add("NARRATIVE_ALIGNMENT_REVIEW_REQUIRED")

    beats = alignment_report.get("beats", ())
    if not isinstance(beats, Sequence) or isinstance(beats, (str, bytes)) or not beats:
        blockers.add("NARRATIVE_BEATS_MISSING")
        beats = ()

    timings: list[OptimizedClipTiming] = []
    cursor = 0.0
    for index, raw in enumerate(beats):
        if not isinstance(raw, Mapping):
            raise ClipTimingOptimizationError("beat must be an object")
        source_start = float(raw.get("clip_start_seconds", raw.get("source_start_seconds", 0.0)))
        source_end = float(raw.get("clip_end_seconds", raw.get("source_end_seconds", 0.0)))
        if source_end <= source_start:
            raise ClipTimingOptimizationError("beat source duration is invalid")
        role = str(raw.get("narrative_role", raw.get("editorial_role", "development")))
        confidence = _clamp(float(raw.get("confidence", raw.get("alignment_score", 0.0))))
        playback_rate = _playback_rate(strategy, role)
        source_duration = source_end - source_start
        target_duration = _target_duration(strategy, role, source_duration) / playback_rate
        transition_in, transition_out, transition_duration = _transitions(strategy, role, index, len(beats))
        item_blockers: set[str] = set()
        if confidence < minimum_confidence:
            item_blockers.add("TIMING_REVIEW_REQUIRED")
        if raw.get("render_allowed") is False:
            item_blockers.add("CLIP_RENDER_NOT_ALLOWED")
        pace = _pace_score(strategy, target_duration, role)
        retention = _clamp(0.45 * pace + 0.35 * confidence + 0.20 * (1.0 if role in {"hook", "climax"} else 0.72))
        core = {
            "beat_id": str(raw.get("beat_id", "")),
            "segment_id": str(raw.get("segment_id", "")),
            "clip_id": str(raw.get("clip_id", "")),
            "editorial_role": role,
            "source_start_seconds": source_start,
            "source_end_seconds": source_end,
            "timeline_start_seconds": round(cursor, 3),
            "timeline_end_seconds": round(cursor + target_duration, 3),
            "playback_rate": playback_rate,
            "transition_in": transition_in,
            "transition_out": transition_out,
            "transition_duration_seconds": transition_duration,
            "pace_score": round(pace, 4),
            "retention_score": round(retention, 4),
            "confidence": round(confidence, 4),
            "blockers": tuple(sorted(item_blockers)),
        }
        timings.append(OptimizedClipTiming(timing_id=f"DIRTIMING-{canonical_sha256(core)[:20].upper()}", **core))
        cursor = core["timeline_end_seconds"]

    if any(item.blockers for item in timings):
        blockers.add("TIMING_REVIEW_REQUIRED")
    if not timings:
        blockers.add("TIMING_EVIDENCE_MISSING")
    state = "blocked" if "NARRATIVE_ALIGNMENT_BLOCKED" in blockers or not timings else "review_required" if blockers else "optimized"
    average_pace = _average([item.pace_score for item in timings])
    retention = _average([item.retention_score for item in timings])
    core = {
        "schema": "football-shorts-ai.clip-timing-optimization.v1",
        "alignment_id": alignment_id,
        "strategy": strategy,
        "timings": [item.to_dict() for item in timings],
        "total_duration_seconds": round(cursor, 3),
        "average_pace_score": round(average_pace, 4),
        "predicted_retention_score": round(retention, 4),
        "optimization_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    optimization_id = f"DIROPT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "optimization_id": optimization_id}
    report = ClipTimingOptimizationReport(
        schema=core["schema"],
        optimization_id=optimization_id,
        alignment_id=alignment_id,
        strategy=strategy,
        timings=tuple(timings),
        total_duration_seconds=core["total_duration_seconds"],
        average_pace_score=core["average_pace_score"],
        predicted_retention_score=core["predicted_retention_score"],
        optimization_state=state,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    report.validate()
    return report


def _playback_rate(strategy: str, role: str) -> float:
    base = {"fast": 1.15, "emotional": 0.95, "informative": 1.0, "balanced": 1.05}[strategy]
    if role == "hook" and strategy == "fast":
        return 1.2
    if role in {"climax", "reaction"} and strategy == "emotional":
        return 0.9
    return base


def _target_duration(strategy: str, role: str, source_duration: float) -> float:
    caps = {
        "fast": {"hook": 1.8, "development": 2.4, "climax": 2.8, "reaction": 1.8, "resolution": 1.6},
        "emotional": {"hook": 2.4, "development": 3.6, "climax": 4.2, "reaction": 3.2, "resolution": 2.4},
        "informative": {"hook": 2.5, "development": 4.5, "climax": 3.8, "reaction": 2.5, "resolution": 3.0},
        "balanced": {"hook": 2.2, "development": 3.4, "climax": 3.6, "reaction": 2.4, "resolution": 2.2},
    }
    return max(0.5, min(source_duration, caps[strategy].get(role, 3.0)))


def _transitions(strategy: str, role: str, index: int, total: int) -> tuple[str, str, float]:
    transition_in = "none" if index == 0 else "cut"
    transition_out = "fade" if index == total - 1 else "cut"
    duration = 0.0
    if strategy == "emotional" and role in {"reaction", "resolution"}:
        transition_in = "crossfade" if index else "none"
        transition_out = "fade" if index == total - 1 else "crossfade"
        duration = 0.35
    elif strategy == "informative" and role == "development":
        transition_in = "match_cut" if index else "none"
    elif role == "climax":
        transition_in = "cut"
        transition_out = "cut" if index < total - 1 else "fade"
    return transition_in, transition_out, duration


def _pace_score(strategy: str, duration: float, role: str) -> float:
    ideal = {"fast": 1.9, "emotional": 3.2, "informative": 3.8, "balanced": 2.8}[strategy]
    role_bonus = 0.08 if role in {"hook", "climax"} else 0.0
    return _clamp(1.0 - abs(duration - ideal) / max(ideal, 0.1) + role_bonus)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _average(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _required_id(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ClipTimingOptimizationError(f"{key} must start with {prefix}")
    return value


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ClipTimingOptimizationError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ClipTimingOptimizationError("evidence must be hexadecimal") from exc


__all__ = [
    "ClipTimingOptimizationError",
    "ClipTimingOptimizationReport",
    "OptimizedClipTiming",
    "build_clip_timing_optimization",
    "canonical_sha256",
]
