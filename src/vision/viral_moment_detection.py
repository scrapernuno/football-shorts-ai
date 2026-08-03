"""
FOOTBALL-SHORTS-AI-0057H
VIRAL MOMENT DETECTION AND RANKING CONTRACT

Combines governed football-event, emotion, motion and visual-quality evidence into
reviewable viral-moment candidates. This module performs no network access, media
acquisition, model training, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ViralMomentDetectionError(ValueError):
    """Raised when governed viral-moment evidence is invalid."""


SUPPORTED_STATES = {"ranked", "review_required", "blocked"}
SUPPORTED_ROLES = {"hook", "development", "climax", "reaction", "resolution"}
EVENT_WEIGHTS = {
    "goal": 1.0,
    "penalty": 0.92,
    "red_card": 0.90,
    "save": 0.86,
    "shot": 0.82,
    "free_kick": 0.78,
    "var": 0.76,
    "celebration": 0.88,
    "crowd_reaction": 0.84,
    "dribble": 0.72,
    "trophy": 0.90,
    "replay": 0.58,
}


@dataclass(frozen=True)
class ViralMomentCandidate:
    moment_id: str
    scene_id: str
    start_seconds: float
    end_seconds: float
    primary_event_type: str
    editorial_role: str
    event_score: float
    emotion_score: float
    crowd_score: float
    motion_score: float
    visual_score: float
    surprise_score: float
    hook_score: float
    climax_score: float
    viral_moment_score: float
    confidence: float
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.moment_id.startswith("VIRALMOMENT-"):
            raise ViralMomentDetectionError("invalid viral moment identity")
        if not self.scene_id.startswith("VSCENE-"):
            raise ViralMomentDetectionError("invalid vision scene identity")
        if not 0.0 <= self.start_seconds < self.end_seconds:
            raise ViralMomentDetectionError("viral moment timestamps are invalid")
        if self.editorial_role not in SUPPORTED_ROLES:
            raise ViralMomentDetectionError("unsupported editorial role")
        for name in (
            "event_score", "emotion_score", "crowd_score", "motion_score",
            "visual_score", "surprise_score", "hook_score", "climax_score",
            "viral_moment_score", "confidence",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ViralMomentDetectionError(f"{name} must be between 0 and 1")
        if not self.evidence_ids:
            raise ViralMomentDetectionError("viral moment requires evidence")
        if tuple(sorted(set(self.evidence_ids))) != self.evidence_ids:
            raise ViralMomentDetectionError("evidence identities must be normalized")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ViralMomentDetectionError("moment blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "moment_id": self.moment_id,
            "scene_id": self.scene_id,
            "start_seconds": round(self.start_seconds, 3),
            "end_seconds": round(self.end_seconds, 3),
            "primary_event_type": self.primary_event_type,
            "editorial_role": self.editorial_role,
            "event_score": round(self.event_score, 4),
            "emotion_score": round(self.emotion_score, 4),
            "crowd_score": round(self.crowd_score, 4),
            "motion_score": round(self.motion_score, 4),
            "visual_score": round(self.visual_score, 4),
            "surprise_score": round(self.surprise_score, 4),
            "hook_score": round(self.hook_score, 4),
            "climax_score": round(self.climax_score, 4),
            "viral_moment_score": round(self.viral_moment_score, 4),
            "confidence": round(self.confidence, 4),
            "evidence_ids": list(self.evidence_ids),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ViralMomentRankingReport:
    schema: str
    ranking_id: str
    vision_report_id: str
    candidates: tuple[ViralMomentCandidate, ...]
    ranked_moment_ids: tuple[str, ...]
    top_hook_moment_id: str | None
    top_climax_moment_id: str | None
    ranking_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.viral-moment-ranking.v1":
            raise ViralMomentDetectionError("unsupported viral moment schema")
        if not self.ranking_id.startswith("VIRALRANK-"):
            raise ViralMomentDetectionError("invalid ranking identity")
        if not self.vision_report_id.startswith("VISION-"):
            raise ViralMomentDetectionError("invalid vision report identity")
        if self.ranking_state not in SUPPORTED_STATES:
            raise ViralMomentDetectionError("unsupported ranking state")
        moment_ids = {item.moment_id for item in self.candidates}
        if len(moment_ids) != len(self.candidates):
            raise ViralMomentDetectionError("moment identities must be unique")
        for item in self.candidates:
            item.validate()
        expected = tuple(
            item.moment_id for item in sorted(
                self.candidates,
                key=lambda value: (-value.viral_moment_score, -value.confidence, value.moment_id),
            )
        )
        if self.ranked_moment_ids != expected:
            raise ViralMomentDetectionError("viral moment ranking is inconsistent")
        if self.top_hook_moment_id is not None and self.top_hook_moment_id not in moment_ids:
            raise ViralMomentDetectionError("top hook moment is unknown")
        if self.top_climax_moment_id is not None and self.top_climax_moment_id not in moment_ids:
            raise ViralMomentDetectionError("top climax moment is unknown")
        if self.ranking_state == "ranked" and (self.blockers or not self.candidates):
            raise ViralMomentDetectionError("ranked report requires unblocked candidates")
        if self.ranking_state in {"review_required", "blocked"} and not self.blockers:
            raise ViralMomentDetectionError("non-ranked report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise ViralMomentDetectionError("0057H cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ViralMomentDetectionError("viral ranking evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "ranking_id": self.ranking_id,
            "vision_report_id": self.vision_report_id,
            "candidates": [item.to_dict() for item in self.candidates],
            "ranked_moment_ids": list(self.ranked_moment_ids),
            "top_hook_moment_id": self.top_hook_moment_id,
            "top_climax_moment_id": self.top_climax_moment_id,
            "ranking_state": self.ranking_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_viral_moment_ranking(
    *,
    vision_report: Mapping[str, object],
    event_report: Mapping[str, object],
    emotion_report: Mapping[str, object],
    motion_report: Mapping[str, object],
    quality_report: Mapping[str, object],
    minimum_confidence: float = 0.65,
) -> ViralMomentRankingReport:
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ViralMomentDetectionError("minimum_confidence must be between 0 and 1")
    vision_id = _required_id(vision_report, "report_id", "VISION-")
    blockers: set[str] = set()
    if vision_report.get("pipeline_state") != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    for name, report, state_key, accepted in (
        ("event", event_report, "detection_state", {"detected", "review_required"}),
        ("emotion", emotion_report, "analysis_state", {"analyzed", "review_required"}),
        ("motion", motion_report, "tracking_state", {"tracked", "review_required"}),
        ("quality", quality_report, "quality_state", {"analyzed", "review_required"}),
    ):
        state = report.get(state_key)
        if state not in accepted:
            blockers.add(f"{name.upper()}_EVIDENCE_BLOCKED")

    scenes = {str(item["scene_id"]): item for item in vision_report.get("scenes", ()) if isinstance(item, Mapping)}
    events_by_scene: dict[str, list[Mapping[str, object]]] = {}
    for item in event_report.get("events", ()):
        if isinstance(item, Mapping):
            events_by_scene.setdefault(str(item.get("scene_id", "")), []).append(item)
    emotion_by_scene = _index_by_scene(emotion_report, ("scene_summaries", "scenes"))
    motion_by_scene = _index_by_scene(motion_report, ("scene_summaries", "scenes"))
    quality_by_scene = _index_by_scene(quality_report, ("scene_scores", "scenes", "measurements"))

    candidates: list[ViralMomentCandidate] = []
    for scene_id, scene in sorted(scenes.items()):
        scene_events = events_by_scene.get(scene_id, [])
        emotion = emotion_by_scene.get(scene_id, {})
        motion = motion_by_scene.get(scene_id, {})
        quality = quality_by_scene.get(scene_id, {})
        if not scene_events and not emotion and not motion and not quality:
            continue
        primary = max(scene_events, key=lambda item: float(item.get("confidence", 0.0)), default={})
        event_type = str(primary.get("event_type", "unknown"))
        event_score = max((EVENT_WEIGHTS.get(str(item.get("event_type", "unknown")), 0.35) * float(item.get("confidence", 0.0)) for item in scene_events), default=0.25)
        emotion_score = _rate(emotion, "emotional_peak_score", "emotion_intensity", "emotional_intensity_score")
        crowd_score = _rate(emotion, "crowd_energy_score", "crowd_score", "crowd_reaction_probability")
        motion_score = _rate(motion, "composite_motion_score", "ball_motion_score", "peak_speed_score")
        visual_score = _rate(quality, "visual_quality_score", "cinematic_score", "hook_visual_score")
        surprise_score = _clamp(0.55 * event_score + 0.25 * motion_score + 0.20 * emotion_score)
        hook_score = _clamp(0.30 * event_score + 0.25 * motion_score + 0.20 * visual_score + 0.15 * surprise_score + 0.10 * emotion_score)
        climax_score = _clamp(0.35 * event_score + 0.30 * emotion_score + 0.20 * crowd_score + 0.15 * visual_score)
        role = "climax" if climax_score >= hook_score and event_type in {"goal", "save", "penalty", "red_card", "trophy"} else "hook" if hook_score >= 0.65 else "reaction" if event_type in {"celebration", "crowd_reaction"} else "development"
        confidence = _clamp(_average([float(primary.get("confidence", 0.0)) if primary else 0.5, _rate(emotion, "confidence"), _rate(motion, "confidence"), _rate(quality, "confidence")], ignore_zero=True))
        moment_blockers: set[str] = set()
        if confidence < minimum_confidence:
            moment_blockers.add("VIRAL_MOMENT_REVIEW_REQUIRED")
        viral_score = _clamp(0.24 * event_score + 0.20 * emotion_score + 0.14 * crowd_score + 0.17 * motion_score + 0.15 * visual_score + 0.10 * surprise_score)
        evidence_ids = sorted({
            str(primary.get("event_id", "")),
            str(emotion.get("summary_id", emotion.get("scene_id", ""))),
            str(motion.get("summary_id", motion.get("scene_id", ""))),
            str(quality.get("score_id", quality.get("scene_id", ""))),
        } - {""})
        core = {
            "scene_id": scene_id,
            "start_seconds": float(scene.get("start_seconds", 0.0)),
            "end_seconds": float(scene.get("end_seconds", 0.0)),
            "primary_event_type": event_type,
            "editorial_role": role,
            "event_score": round(event_score, 4),
            "emotion_score": round(emotion_score, 4),
            "crowd_score": round(crowd_score, 4),
            "motion_score": round(motion_score, 4),
            "visual_score": round(visual_score, 4),
            "surprise_score": round(surprise_score, 4),
            "hook_score": round(hook_score, 4),
            "climax_score": round(climax_score, 4),
            "viral_moment_score": round(viral_score, 4),
            "confidence": round(confidence, 4),
            "evidence_ids": tuple(evidence_ids or [scene_id]),
            "blockers": tuple(sorted(moment_blockers)),
        }
        candidates.append(ViralMomentCandidate(moment_id=f"VIRALMOMENT-{canonical_sha256(core)[:20].upper()}", **core))

    if not candidates:
        blockers.add("VIRAL_MOMENT_EVIDENCE_MISSING")
    if any(item.blockers for item in candidates):
        blockers.add("VIRAL_MOMENT_REVIEW_REQUIRED")
    state = "blocked" if "VISION_REPORT_NOT_ANALYZED" in blockers or not candidates else "review_required" if blockers else "ranked"
    ranked = tuple(item.moment_id for item in sorted(candidates, key=lambda value: (-value.viral_moment_score, -value.confidence, value.moment_id)))
    hook_candidates = [item for item in candidates if item.editorial_role == "hook"] or candidates
    climax_candidates = [item for item in candidates if item.editorial_role == "climax"] or candidates
    top_hook = max(hook_candidates, key=lambda value: (value.hook_score, value.viral_moment_score, value.moment_id), default=None)
    top_climax = max(climax_candidates, key=lambda value: (value.climax_score, value.viral_moment_score, value.moment_id), default=None)
    core = {
        "schema": "football-shorts-ai.viral-moment-ranking.v1",
        "vision_report_id": vision_id,
        "candidates": [item.to_dict() for item in candidates],
        "ranked_moment_ids": list(ranked),
        "top_hook_moment_id": None if top_hook is None else top_hook.moment_id,
        "top_climax_moment_id": None if top_climax is None else top_climax.moment_id,
        "ranking_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    ranking_id = f"VIRALRANK-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "ranking_id": ranking_id}
    result = ViralMomentRankingReport(
        ranking_id=ranking_id,
        evidence_sha256=canonical_sha256(unsigned),
        vision_report_id=vision_id,
        candidates=tuple(candidates),
        ranked_moment_ids=ranked,
        top_hook_moment_id=core["top_hook_moment_id"],
        top_climax_moment_id=core["top_climax_moment_id"],
        ranking_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.viral-moment-ranking.v1",
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _index_by_scene(report: Mapping[str, object], keys: Sequence[str]) -> dict[str, Mapping[str, object]]:
    for key in keys:
        values = report.get(key)
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            return {str(item.get("scene_id", "")): item for item in values if isinstance(item, Mapping) and item.get("scene_id")}
    return {}


def _rate(payload: Mapping[str, object], *keys: str) -> float:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _clamp(float(value))
    return 0.0


def _average(values: Sequence[float], *, ignore_zero: bool = False) -> float:
    selected = [value for value in values if not ignore_zero or value > 0]
    return sum(selected) / len(selected) if selected else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _required_id(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ViralMomentDetectionError(f"{key} must start with {prefix}")
    return value


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ViralMomentDetectionError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ViralMomentDetectionError("evidence must be hexadecimal") from exc


__all__ = [
    "ViralMomentCandidate",
    "ViralMomentDetectionError",
    "ViralMomentRankingReport",
    "build_viral_moment_ranking",
    "canonical_sha256",
]
