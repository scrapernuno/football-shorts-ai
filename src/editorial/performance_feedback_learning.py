"""
FOOTBALL-SHORTS-AI-0056I
PERFORMANCE FEEDBACK AND EDITORIAL LEARNING CONTRACT

Associates observed publication metrics with governed editorial decisions and emits
reviewable learning evidence. It does not fetch analytics, mutate scoring weights,
execute models, render media or publish content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence


class PerformanceFeedbackLearningError(ValueError):
    """Raised when performance feedback evidence is invalid or unsafe."""


SUPPORTED_PLATFORMS = {"youtube", "tiktok", "instagram", "other"}
SUPPORTED_LEARNING_STATES = {"insufficient_data", "review_ready", "blocked"}


@dataclass(frozen=True)
class PublishedShortMetrics:
    platform: str
    publication_id: str
    measured_at: str
    views: int
    likes: int
    comments: int
    shares: int
    average_view_duration_seconds: float
    video_duration_seconds: float
    retention_3s: float
    retention_10s: float
    completion_rate: float
    impressions: int | None = None
    click_through_rate: float | None = None

    def validate(self) -> None:
        if self.platform not in SUPPORTED_PLATFORMS:
            raise PerformanceFeedbackLearningError("unsupported analytics platform")
        if not self.publication_id.strip():
            raise PerformanceFeedbackLearningError("publication_id is required")
        _validate_utc_timestamp(self.measured_at)
        for name, value in (
            ("views", self.views),
            ("likes", self.likes),
            ("comments", self.comments),
            ("shares", self.shares),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PerformanceFeedbackLearningError(f"{name} must be a non-negative integer")
        if self.impressions is not None and (
            isinstance(self.impressions, bool)
            or not isinstance(self.impressions, int)
            or self.impressions < 0
        ):
            raise PerformanceFeedbackLearningError("impressions must be a non-negative integer")
        for name, value in (
            ("average_view_duration_seconds", self.average_view_duration_seconds),
            ("video_duration_seconds", self.video_duration_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise PerformanceFeedbackLearningError(f"{name} must be positive")
        if self.average_view_duration_seconds > self.video_duration_seconds * 5:
            raise PerformanceFeedbackLearningError("average view duration is implausible")
        for name, value in (
            ("retention_3s", self.retention_3s),
            ("retention_10s", self.retention_10s),
            ("completion_rate", self.completion_rate),
        ):
            _validate_rate(name, value)
        if self.click_through_rate is not None:
            _validate_rate("click_through_rate", self.click_through_rate)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "platform": self.platform,
            "publication_id": self.publication_id,
            "measured_at": self.measured_at,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "average_view_duration_seconds": round(float(self.average_view_duration_seconds), 4),
            "video_duration_seconds": round(float(self.video_duration_seconds), 4),
            "retention_3s": round(float(self.retention_3s), 4),
            "retention_10s": round(float(self.retention_10s), 4),
            "completion_rate": round(float(self.completion_rate), 4),
            "impressions": self.impressions,
            "click_through_rate": (
                None if self.click_through_rate is None else round(float(self.click_through_rate), 4)
            ),
        }


@dataclass(frozen=True)
class EditorialOutcomeSignal:
    signal_name: str
    observed_score: float
    interpretation: str

    def validate(self) -> None:
        if not self.signal_name.strip():
            raise PerformanceFeedbackLearningError("signal_name is required")
        _validate_rate("observed_score", self.observed_score)
        if self.interpretation not in {"weak", "mixed", "strong"}:
            raise PerformanceFeedbackLearningError("unsupported signal interpretation")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "signal_name": self.signal_name,
            "observed_score": round(float(self.observed_score), 4),
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True)
class EditorialLearningReport:
    schema: str
    learning_id: str
    timeline_id: str
    editorial_score_id: str
    publication_id: str
    metrics: PublishedShortMetrics
    outcome_signals: tuple[EditorialOutcomeSignal, ...]
    observed_retention_score: float
    observed_engagement_score: float
    observed_shareability_score: float
    prediction_error: float
    recommendations: tuple[str, ...]
    learning_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    analytics_fetch_enabled: bool = False
    weight_update_enabled: bool = False
    model_training_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.editorial-learning.v1":
            raise PerformanceFeedbackLearningError("unsupported editorial learning schema")
        if not self.learning_id.startswith("LEARN-"):
            raise PerformanceFeedbackLearningError("invalid learning identity")
        if not self.timeline_id.startswith(("AUTOTIMELINE-", "TIMELINE-")):
            raise PerformanceFeedbackLearningError("invalid timeline identity")
        if not self.editorial_score_id.startswith("EDITSCORE-"):
            raise PerformanceFeedbackLearningError("invalid editorial score identity")
        if self.publication_id != self.metrics.publication_id:
            raise PerformanceFeedbackLearningError("publication identity mismatch")
        self.metrics.validate()
        if not self.outcome_signals:
            raise PerformanceFeedbackLearningError("outcome signals are required")
        for signal in self.outcome_signals:
            signal.validate()
        for name, value in (
            ("observed_retention_score", self.observed_retention_score),
            ("observed_engagement_score", self.observed_engagement_score),
            ("observed_shareability_score", self.observed_shareability_score),
        ):
            _validate_rate(name, value)
        if isinstance(self.prediction_error, bool) or not isinstance(self.prediction_error, (int, float)):
            raise PerformanceFeedbackLearningError("prediction_error must be numeric")
        if not -1.0 <= float(self.prediction_error) <= 1.0:
            raise PerformanceFeedbackLearningError("prediction_error must be between -1 and 1")
        if tuple(sorted(set(self.recommendations))) != self.recommendations:
            raise PerformanceFeedbackLearningError("recommendations must be normalized")
        if self.learning_state not in SUPPORTED_LEARNING_STATES:
            raise PerformanceFeedbackLearningError("unsupported learning state")
        if self.learning_state == "review_ready" and self.blockers:
            raise PerformanceFeedbackLearningError("review-ready learning cannot contain blockers")
        if self.learning_state in {"blocked", "insufficient_data"} and not self.blockers:
            raise PerformanceFeedbackLearningError("non-ready learning requires blockers")
        if any((
            self.analytics_fetch_enabled,
            self.weight_update_enabled,
            self.model_training_enabled,
            self.auto_render,
            self.auto_publish,
        )):
            raise PerformanceFeedbackLearningError("0056I cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise PerformanceFeedbackLearningError("learning evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "learning_id": self.learning_id,
            "timeline_id": self.timeline_id,
            "editorial_score_id": self.editorial_score_id,
            "publication_id": self.publication_id,
            "metrics": self.metrics.to_dict(),
            "outcome_signals": [signal.to_dict() for signal in self.outcome_signals],
            "observed_retention_score": self.observed_retention_score,
            "observed_engagement_score": self.observed_engagement_score,
            "observed_shareability_score": self.observed_shareability_score,
            "prediction_error": self.prediction_error,
            "recommendations": list(self.recommendations),
            "learning_state": self.learning_state,
            "blockers": list(self.blockers),
            "analytics_fetch_enabled": False,
            "weight_update_enabled": False,
            "model_training_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_editorial_learning_report(
    *,
    timeline: Mapping[str, object],
    editorial_score: Mapping[str, object],
    metrics: PublishedShortMetrics,
    minimum_views: int = 100,
) -> EditorialLearningReport:
    """Create deterministic post-publication learning evidence for human review."""

    metrics.validate()
    if isinstance(minimum_views, bool) or not isinstance(minimum_views, int) or minimum_views < 1:
        raise PerformanceFeedbackLearningError("minimum_views must be a positive integer")
    timeline_id = _required_text(timeline, "timeline_id")
    score_id = _required_text(editorial_score, "score_id")
    if not timeline_id.startswith(("AUTOTIMELINE-", "TIMELINE-")):
        raise PerformanceFeedbackLearningError("invalid timeline identity")
    if not score_id.startswith("EDITSCORE-"):
        raise PerformanceFeedbackLearningError("invalid editorial score identity")
    predicted_retention = _required_rate(editorial_score, "retention_potential_score")

    avg_watch_ratio = min(1.0, metrics.average_view_duration_seconds / metrics.video_duration_seconds)
    observed_retention = _clamp(
        0.35 * metrics.retention_3s
        + 0.25 * metrics.retention_10s
        + 0.25 * metrics.completion_rate
        + 0.15 * avg_watch_ratio
    )
    engagement_denominator = max(1, metrics.views)
    engagement_rate = min(
        1.0,
        (metrics.likes + 2 * metrics.comments + 3 * metrics.shares) / engagement_denominator,
    )
    shareability = min(1.0, metrics.shares / engagement_denominator * 20.0)
    observed_engagement = _clamp(engagement_rate)
    observed_shareability = _clamp(shareability)
    prediction_error = round(observed_retention - predicted_retention, 4)

    signals = (
        _signal("hook_retention", metrics.retention_3s),
        _signal("mid_story_retention", metrics.retention_10s),
        _signal("completion", metrics.completion_rate),
        _signal("engagement", observed_engagement),
        _signal("shareability", observed_shareability),
    )
    blockers: list[str] = []
    if metrics.views < minimum_views:
        blockers.append("INSUFFICIENT_VIEWS")
    recommendations = _recommendations(
        metrics=metrics,
        observed_retention=observed_retention,
        observed_engagement=observed_engagement,
        observed_shareability=observed_shareability,
        prediction_error=prediction_error,
    )
    state = "insufficient_data" if blockers else "review_ready"

    core = {
        "schema": "football-shorts-ai.editorial-learning.v1",
        "timeline_id": timeline_id,
        "editorial_score_id": score_id,
        "publication_id": metrics.publication_id,
        "metrics": metrics.to_dict(),
        "outcome_signals": [signal.to_dict() for signal in signals],
        "observed_retention_score": observed_retention,
        "observed_engagement_score": observed_engagement,
        "observed_shareability_score": observed_shareability,
        "prediction_error": prediction_error,
        "recommendations": list(recommendations),
        "learning_state": state,
        "blockers": blockers,
        "analytics_fetch_enabled": False,
        "weight_update_enabled": False,
        "model_training_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    learning_id = f"LEARN-{provisional[:20].upper()}"
    unsigned = {**core, "learning_id": learning_id}
    evidence = canonical_sha256(unsigned)
    result = EditorialLearningReport(
        learning_id=learning_id,
        evidence_sha256=evidence,
        metrics=metrics,
        outcome_signals=signals,
        recommendations=recommendations,
        blockers=tuple(blockers),
        **{
            key: value
            for key, value in unsigned.items()
            if key not in {"learning_id", "evidence_sha256", "metrics", "outcome_signals", "recommendations", "blockers"}
        },
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _recommendations(
    *,
    metrics: PublishedShortMetrics,
    observed_retention: float,
    observed_engagement: float,
    observed_shareability: float,
    prediction_error: float,
) -> tuple[str, ...]:
    values: set[str] = set()
    if metrics.retention_3s < 0.70:
        values.add("STRENGTHEN_OPENING_HOOK")
    if metrics.retention_10s < 0.45:
        values.add("ACCELERATE_STORY_PROGRESSION")
    if metrics.completion_rate < 0.35:
        values.add("SHORTEN_OR_TIGHTEN_TIMELINE")
    if observed_engagement < 0.04:
        values.add("IMPROVE_COMMENT_PROMPT_OR_EMOTIONAL_PAYOFF")
    if observed_shareability < 0.03:
        values.add("INCREASE_SURPRISE_OR_SHARE_VALUE")
    if prediction_error < -0.15:
        values.add("REVIEW_RETENTION_SCORING_CALIBRATION")
    if observed_retention >= 0.75 and metrics.completion_rate >= 0.60:
        values.add("PRESERVE_CURRENT_STORY_PATTERN")
    return tuple(sorted(values))


def _signal(name: str, value: float) -> EditorialOutcomeSignal:
    score = _clamp(value)
    interpretation = "strong" if score >= 0.70 else "mixed" if score >= 0.40 else "weak"
    return EditorialOutcomeSignal(name, score, interpretation)


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PerformanceFeedbackLearningError(f"{key} is required")
    return value.strip()


def _required_rate(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    _validate_rate(key, value)
    return round(float(value), 4)


def _validate_rate(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PerformanceFeedbackLearningError(f"{name} must be numeric")
    if not 0.0 <= float(value) <= 1.0:
        raise PerformanceFeedbackLearningError(f"{name} must be between 0 and 1")


def _validate_utc_timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PerformanceFeedbackLearningError("measured_at is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PerformanceFeedbackLearningError("measured_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise PerformanceFeedbackLearningError("measured_at must use UTC")


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise PerformanceFeedbackLearningError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise PerformanceFeedbackLearningError("evidence must be hexadecimal") from exc


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


__all__ = [
    "EditorialLearningReport",
    "EditorialOutcomeSignal",
    "PerformanceFeedbackLearningError",
    "PublishedShortMetrics",
    "SUPPORTED_LEARNING_STATES",
    "SUPPORTED_PLATFORMS",
    "build_editorial_learning_report",
    "canonical_sha256",
]
