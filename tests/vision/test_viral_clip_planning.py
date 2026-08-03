from dataclasses import replace

import pytest

from vision.viral_clip_planning import (
    ViralClipPlanningError,
    build_viral_clip_plan,
)


def ranking(state="ranked", blockers=()):
    moments = [
        {
            "moment_id": "VIRALMOMENT-HOOK0000000000000001",
            "scene_id": "VSCENE-HOOK000000000000001",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "editorial_role": "hook",
            "viral_moment_score": 0.94,
            "confidence": 0.93,
            "evidence_ids": ["VEVENT-HOOK", "VSCENE-HOOK000000000000001"],
            "blockers": [],
        },
        {
            "moment_id": "VIRALMOMENT-CLIMAX000000000001",
            "scene_id": "VSCENE-CLIMAX000000000001",
            "start_seconds": 8.0,
            "end_seconds": 11.0,
            "editorial_role": "climax",
            "viral_moment_score": 0.99,
            "confidence": 0.97,
            "evidence_ids": ["VEVENT-GOAL", "VSCENE-CLIMAX000000000001"],
            "blockers": [],
        },
    ]
    return {
        "ranking_id": "VIRALRANK-00000000000000000001",
        "ranking_state": state,
        "blockers": list(blockers),
        "candidates": moments,
        "ranked_moment_ids": [moments[1]["moment_id"], moments[0]["moment_id"]],
        "top_hook_moment_id": moments[0]["moment_id"],
        "top_climax_moment_id": moments[1]["moment_id"],
    }


def test_builds_owned_clip_plan_with_hook_and_climax():
    result = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-OWNED-001", rights_status="owned"
    )
    assert result.planning_state == "planned"
    assert len(result.clips) == 2
    assert result.selected_hook_clip_id is not None
    assert result.selected_climax_clip_id is not None
    assert all(item.render_allowed for item in result.clips)
    assert [item.priority for item in result.clips] == [1, 2]


def test_applies_pre_and_post_roll_deterministically():
    result = build_viral_clip_plan(
        ranking_report=ranking(),
        asset_id="EXT-LICENSED-001",
        rights_status="licensed",
        pre_roll_seconds=0.5,
        post_roll_seconds=1.0,
    )
    climax = result.clips[0]
    assert climax.source_start_seconds == 7.5
    assert climax.source_end_seconds == 12.0
    assert climax.duration_seconds == 4.5


def test_reference_only_is_fail_closed():
    result = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-REFERENCE-001", rights_status="reference_only"
    )
    assert result.planning_state == "blocked"
    assert "REFERENCE_ONLY_RENDER_BLOCKED" in result.blockers
    assert all(not item.render_allowed for item in result.clips)
    assert all("REFERENCE_ONLY_RENDER_BLOCKED" in item.blockers for item in result.clips)


def test_review_required_moment_propagates_review_gate():
    payload = ranking()
    payload["candidates"][0]["blockers"] = ["VIRAL_MOMENT_REVIEW_REQUIRED"]
    result = build_viral_clip_plan(
        ranking_report=payload, asset_id="EXT-OWNED-002", rights_status="owned"
    )
    assert result.planning_state == "review_required"
    assert "CLIP_REVIEW_REQUIRED" in result.blockers
    assert any(not item.render_allowed for item in result.clips)


def test_blocked_ranking_remains_blocked():
    result = build_viral_clip_plan(
        ranking_report=ranking(state="blocked", blockers=("VISION_REPORT_NOT_ANALYZED",)),
        asset_id="EXT-OWNED-003",
        rights_status="owned",
    )
    assert result.planning_state == "blocked"
    assert "VIRAL_RANKING_NOT_READY" in result.blockers


def test_missing_candidates_is_blocked():
    payload = ranking()
    payload["candidates"] = []
    payload["ranked_moment_ids"] = []
    result = build_viral_clip_plan(
        ranking_report=payload, asset_id="EXT-OWNED-004", rights_status="owned"
    )
    assert result.planning_state == "blocked"
    assert "VIRAL_CLIP_CANDIDATES_MISSING" in result.blockers


def test_replay_is_deterministic():
    first = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-OWNED-005", rights_status="owned"
    )
    second = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-OWNED-005", rights_status="owned"
    )
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampered_evidence_is_rejected():
    result = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-OWNED-006", rights_status="owned"
    )
    with pytest.raises(ViralClipPlanningError, match="evidence mismatch"):
        replace(result, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    result = build_viral_clip_plan(
        ranking_report=ranking(), asset_id="EXT-OWNED-007", rights_status="owned"
    )
    for field in (
        "network_enabled",
        "acquisition_enabled",
        "extraction_enabled",
        "model_training_enabled",
        "render_enabled",
        "auto_publish",
    ):
        with pytest.raises(ViralClipPlanningError, match="cannot enable operational capabilities"):
            replace(result, **{field: True}).validate()


@pytest.mark.parametrize("rights", ["unknown", "public", "fair_use"])
def test_invalid_rights_are_rejected(rights):
    with pytest.raises(ViralClipPlanningError, match="unsupported rights"):
        build_viral_clip_plan(
            ranking_report=ranking(), asset_id="EXT-INVALID", rights_status=rights
        )


def test_invalid_maximum_clips_is_rejected():
    with pytest.raises(ViralClipPlanningError, match="maximum_clips"):
        build_viral_clip_plan(
            ranking_report=ranking(),
            asset_id="EXT-OWNED-008",
            rights_status="owned",
            maximum_clips=0,
        )
