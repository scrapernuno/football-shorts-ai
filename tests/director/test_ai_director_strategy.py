from dataclasses import replace

import pytest

from director.ai_director_strategy import (
    AIDirectorStrategyError,
    build_ai_director_strategy_report,
)


def _clip_plan(*, planning_state="planned", render_allowed=True):
    return {
        "plan_id": "CLIPPLAN-0058A00000000000001",
        "planning_state": planning_state,
        "clips": [
            {
                "clip_id": "VIRALCLIP-HOOK0000000001",
                "scene_id": "VSCENE-HOOK000000000001",
                "editorial_role": "hook",
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "priority": 1,
                "viral_score": 0.91,
                "confidence": 0.95,
                "render_allowed": render_allowed,
            },
            {
                "clip_id": "VIRALCLIP-DEV00000000002",
                "scene_id": "VSCENE-DEV0000000000002",
                "editorial_role": "development",
                "start_seconds": 2.0,
                "end_seconds": 5.5,
                "priority": 2,
                "viral_score": 0.72,
                "confidence": 0.92,
                "render_allowed": render_allowed,
            },
            {
                "clip_id": "VIRALCLIP-GOAL0000000003",
                "scene_id": "VSCENE-GOAL000000000002",
                "editorial_role": "climax",
                "start_seconds": 5.5,
                "end_seconds": 8.5,
                "priority": 3,
                "viral_score": 0.99,
                "confidence": 0.98,
                "render_allowed": render_allowed,
            },
            {
                "clip_id": "VIRALCLIP-REACT000000004",
                "scene_id": "VSCENE-REACT00000000003",
                "editorial_role": "reaction",
                "start_seconds": 8.5,
                "end_seconds": 11.5,
                "priority": 4,
                "viral_score": 0.94,
                "confidence": 0.96,
                "render_allowed": render_allowed,
            },
            {
                "clip_id": "VIRALCLIP-END00000000005",
                "scene_id": "VSCENE-END0000000000004",
                "editorial_role": "resolution",
                "start_seconds": 11.5,
                "end_seconds": 14.0,
                "priority": 5,
                "viral_score": 0.70,
                "confidence": 0.90,
                "render_allowed": render_allowed,
            },
        ],
    }


def test_builds_four_reviewable_director_variants():
    report = build_ai_director_strategy_report(clip_plan=_clip_plan())

    report.validate()
    assert report.director_state == "proposed"
    assert report.blockers == ()
    assert len(report.variants) == 4
    assert {item.strategy for item in report.variants} == {
        "fast", "emotional", "informative", "balanced"
    }
    assert report.recommended_variant_id is not None
    assert all(item.render_allowed for item in report.variants)


def test_fast_variant_is_shorter_and_preserves_narrative_order():
    report = build_ai_director_strategy_report(clip_plan=_clip_plan())
    fast = next(item for item in report.variants if item.strategy == "fast")
    emotional = next(item for item in report.variants if item.strategy == "emotional")

    assert len(fast.segments) == 3
    assert fast.total_duration_seconds <= emotional.total_duration_seconds
    role_order = {"hook": 0, "development": 1, "climax": 2, "reaction": 3, "resolution": 4, "cta": 5}
    assert [role_order[item.editorial_role] for item in fast.segments] == sorted(
        role_order[item.editorial_role] for item in fast.segments
    )


def test_recommendation_is_deterministic():
    first = build_ai_director_strategy_report(clip_plan=_clip_plan())
    second = build_ai_director_strategy_report(clip_plan=_clip_plan())

    assert first.to_dict() == second.to_dict()
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.director_id == second.director_id


def test_reference_or_unrenderable_clips_require_review():
    report = build_ai_director_strategy_report(
        clip_plan=_clip_plan(render_allowed=False)
    )

    assert report.director_state == "review_required"
    assert "DIRECTOR_VARIANT_RENDER_BLOCKED" in report.blockers
    assert all(not item.render_allowed for item in report.variants)
    assert all("CLIP_RENDER_NOT_ALLOWED" in item.blockers for item in report.variants)


def test_blocked_clip_plan_remains_blocked():
    report = build_ai_director_strategy_report(
        clip_plan=_clip_plan(planning_state="blocked", render_allowed=False)
    )

    assert report.director_state == "blocked"
    assert "CLIP_PLAN_BLOCKED" in report.blockers


def test_empty_plan_is_fail_closed():
    report = build_ai_director_strategy_report(
        clip_plan={
            "plan_id": "CLIPPLAN-0058AEMPTY000000001",
            "planning_state": "planned",
            "clips": [],
        }
    )

    assert report.director_state == "blocked"
    assert "CLIP_PLAN_EMPTY" in report.blockers
    assert report.variants == ()
    assert report.recommended_variant_id is None


def test_invalid_strategy_is_rejected():
    with pytest.raises(AIDirectorStrategyError, match="unsupported"):
        build_ai_director_strategy_report(
            clip_plan=_clip_plan(),
            strategies=("fast", "unsafe"),
        )


def test_evidence_tampering_is_detected():
    report = build_ai_director_strategy_report(clip_plan=_clip_plan())
    tampered = replace(report, recommended_variant_id=report.variants[-1].variant_id)

    with pytest.raises(AIDirectorStrategyError, match="evidence mismatch"):
        tampered.validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_ai_director_strategy_report(clip_plan=_clip_plan())

    for field in (
        "network_enabled",
        "acquisition_enabled",
        "model_training_enabled",
        "extraction_enabled",
        "render_enabled",
        "auto_publish",
    ):
        with pytest.raises(AIDirectorStrategyError, match="cannot enable"):
            replace(report, **{field: True}).validate()
