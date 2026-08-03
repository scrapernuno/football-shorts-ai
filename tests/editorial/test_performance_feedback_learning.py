from __future__ import annotations

import dataclasses

import pytest

from editorial.performance_feedback_learning import (
    PerformanceFeedbackLearningError,
    PublishedShortMetrics,
    build_editorial_learning_report,
    canonical_sha256,
)


def _timeline() -> dict[str, object]:
    return {
        "timeline_id": "AUTOTIMELINE-ABCDEF1234567890ABCD",
    }


def _score(*, predicted_retention: float = 0.72) -> dict[str, object]:
    return {
        "score_id": "EDITSCORE-ABCDEF1234567890ABCD",
        "retention_potential_score": predicted_retention,
    }


def _metrics(*, views: int = 12000) -> PublishedShortMetrics:
    return PublishedShortMetrics(
        platform="youtube",
        publication_id="YT-SHORT-001",
        measured_at="2026-08-03T13:30:00Z",
        views=views,
        likes=840,
        comments=96,
        shares=144,
        average_view_duration_seconds=19.5,
        video_duration_seconds=24.0,
        retention_3s=0.86,
        retention_10s=0.71,
        completion_rate=0.64,
        impressions=55000,
        click_through_rate=0.083,
    )


def test_builds_review_ready_learning_evidence() -> None:
    result = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(),
        metrics=_metrics(),
    )

    assert result.learning_state == "review_ready"
    assert result.blockers == ()
    assert result.learning_id.startswith("LEARN-")
    assert result.timeline_id.startswith("AUTOTIMELINE-")
    assert result.editorial_score_id.startswith("EDITSCORE-")
    assert result.observed_retention_score > 0.70
    assert result.observed_engagement_score > 0
    assert result.observed_shareability_score > 0
    assert len(result.outcome_signals) == 5
    assert "PRESERVE_CURRENT_STORY_PATTERN" in result.recommendations


def test_scores_are_auditable_and_prediction_error_is_signed() -> None:
    result = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(predicted_retention=0.95),
        metrics=_metrics(),
    )

    assert 0 <= result.observed_retention_score <= 1
    assert 0 <= result.observed_engagement_score <= 1
    assert 0 <= result.observed_shareability_score <= 1
    assert result.prediction_error < 0
    assert [signal.signal_name for signal in result.outcome_signals] == [
        "hook_retention",
        "mid_story_retention",
        "completion",
        "engagement",
        "shareability",
    ]


def test_low_performance_generates_editorial_recommendations() -> None:
    metrics = dataclasses.replace(
        _metrics(),
        retention_3s=0.40,
        retention_10s=0.22,
        completion_rate=0.18,
        likes=8,
        comments=1,
        shares=0,
        average_view_duration_seconds=5.0,
    )
    result = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(predicted_retention=0.80),
        metrics=metrics,
    )

    assert "STRENGTHEN_OPENING_HOOK" in result.recommendations
    assert "ACCELERATE_STORY_PROGRESSION" in result.recommendations
    assert "SHORTEN_OR_TIGHTEN_TIMELINE" in result.recommendations
    assert "IMPROVE_COMMENT_PROMPT_OR_EMOTIONAL_PAYOFF" in result.recommendations
    assert "INCREASE_SURPRISE_OR_SHARE_VALUE" in result.recommendations
    assert "REVIEW_RETENTION_SCORING_CALIBRATION" in result.recommendations


def test_insufficient_sample_is_blocked_for_learning_review() -> None:
    result = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(),
        metrics=_metrics(views=25),
        minimum_views=100,
    )

    assert result.learning_state == "insufficient_data"
    assert result.blockers == ("INSUFFICIENT_VIEWS",)


def test_identity_and_replay_are_deterministic() -> None:
    first = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(),
        metrics=_metrics(),
    )
    second = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(),
        metrics=_metrics(),
    )

    assert first.learning_id == second.learning_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_rejects_invalid_metrics_and_contract_identities() -> None:
    with pytest.raises(PerformanceFeedbackLearningError, match="between 0 and 1"):
        dataclasses.replace(_metrics(), retention_3s=1.1).validate()

    with pytest.raises(PerformanceFeedbackLearningError, match="UTC"):
        dataclasses.replace(_metrics(), measured_at="2026-08-03T13:30:00").validate()

    with pytest.raises(PerformanceFeedbackLearningError, match="invalid timeline identity"):
        build_editorial_learning_report(
            timeline={"timeline_id": "BAD"},
            editorial_score=_score(),
            metrics=_metrics(),
        )

    with pytest.raises(PerformanceFeedbackLearningError, match="positive integer"):
        build_editorial_learning_report(
            timeline=_timeline(),
            editorial_score=_score(),
            metrics=_metrics(),
            minimum_views=0,
        )


def test_operational_learning_capabilities_cannot_be_forged() -> None:
    result = build_editorial_learning_report(
        timeline=_timeline(),
        editorial_score=_score(),
        metrics=_metrics(),
    )

    for field in (
        "analytics_fetch_enabled",
        "weight_update_enabled",
        "model_training_enabled",
        "auto_render",
        "auto_publish",
    ):
        forged = dataclasses.replace(result, **{field: True})
        with pytest.raises(PerformanceFeedbackLearningError, match="operational capabilities"):
            forged.validate()
