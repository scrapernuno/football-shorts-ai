from dataclasses import replace

import pytest

from director.viral_performance_prediction import (
    ViralPerformancePredictionError,
    build_variant_ranking,
)


def _variants():
    return [
        {
            "variant_id": "DIRVAR-FAST000000000000001",
            "strategy": "fast",
            "hook_strength_score": 0.96,
            "predicted_retention_score": 0.92,
            "pace_score": 0.98,
            "emotional_arc_score": 0.76,
            "information_density_score": 0.62,
            "confidence": 0.91,
            "render_allowed": True,
        },
        {
            "variant_id": "DIRVAR-EMOTIONAL000000001",
            "strategy": "emotional",
            "hook_strength_score": 0.86,
            "predicted_retention_score": 0.90,
            "pace_score": 0.72,
            "emotional_arc_score": 0.99,
            "information_density_score": 0.68,
            "confidence": 0.93,
            "render_allowed": True,
        },
        {
            "variant_id": "DIRVAR-INFORMATIVE0000001",
            "strategy": "informative",
            "hook_strength_score": 0.72,
            "predicted_retention_score": 0.80,
            "pace_score": 0.67,
            "emotional_arc_score": 0.70,
            "information_density_score": 0.98,
            "confidence": 0.90,
            "render_allowed": True,
        },
        {
            "variant_id": "DIRVAR-BALANCED000000001",
            "strategy": "balanced",
            "hook_strength_score": 0.90,
            "predicted_retention_score": 0.94,
            "pace_score": 0.88,
            "emotional_arc_score": 0.90,
            "information_density_score": 0.86,
            "confidence": 0.95,
            "render_allowed": True,
        },
    ]


def test_ranks_variants_and_recommends_best_candidate():
    report = build_variant_ranking(variants=_variants())

    report.validate()
    assert report.ranking_state == "ranked"
    assert report.blockers == ()
    assert len(report.predictions) == 4
    assert report.recommended_variant_id == report.ranked_variant_ids[0]
    assert report.recommended_variant_id == "DIRVAR-BALANCED000000001"
    assert all(0.0 <= item.viral_score <= 1.0 for item in report.predictions)


def test_ranking_is_deterministic():
    first = build_variant_ranking(variants=_variants())
    second = build_variant_ranking(variants=_variants())

    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_low_confidence_requires_review():
    variants = _variants()
    variants[0] = {**variants[0], "confidence": 0.20}
    report = build_variant_ranking(variants=variants)

    assert report.ranking_state == "review_required"
    assert "VARIANT_REVIEW_REQUIRED" in report.blockers
    prediction = next(item for item in report.predictions if item.variant_id == variants[0]["variant_id"])
    assert "VARIANT_PREDICTION_REVIEW_REQUIRED" in prediction.blockers


def test_render_blocked_variant_requires_review_and_is_not_recommended():
    variants = _variants()
    variants[3] = {**variants[3], "render_allowed": False}
    report = build_variant_ranking(variants=variants)

    assert report.ranking_state == "review_required"
    blocked = next(item for item in report.predictions if item.variant_id == variants[3]["variant_id"])
    assert "VARIANT_RENDER_NOT_ALLOWED" in blocked.blockers
    assert report.recommended_variant_id != blocked.variant_id


def test_missing_variants_is_fail_closed():
    report = build_variant_ranking(variants=[])

    assert report.ranking_state == "blocked"
    assert report.recommended_variant_id is None
    assert "DIRECTOR_VARIANTS_MISSING" in report.blockers


def test_invalid_minimum_confidence_is_rejected():
    with pytest.raises(ViralPerformancePredictionError):
        build_variant_ranking(variants=_variants(), minimum_confidence=1.1)


def test_invalid_variant_identity_is_rejected():
    variants = _variants()
    variants[0] = {**variants[0], "variant_id": "INVALID"}
    with pytest.raises(ViralPerformancePredictionError):
        build_variant_ranking(variants=variants)


def test_evidence_tampering_is_detected():
    report = build_variant_ranking(variants=_variants())
    altered = replace(report, recommended_variant_id="DIRVAR-FAST000000000000001")

    with pytest.raises(ViralPerformancePredictionError, match="evidence mismatch"):
        altered.validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_variant_ranking(variants=_variants())
    altered = replace(report, auto_publish=True)

    with pytest.raises(ViralPerformancePredictionError, match="cannot enable operational capabilities"):
        altered.validate()
