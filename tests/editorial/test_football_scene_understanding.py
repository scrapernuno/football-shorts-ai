from __future__ import annotations

import dataclasses

import pytest

from editorial.football_scene_understanding import (
    FootballSceneUnderstandingError,
    build_football_scene_understanding,
    classify_scene,
)
from editorial.semantic_scene_indexer import build_semantic_scene_index


SOURCE_SHA = "a" * 64


def _asset(*, rights_status: str = "owned", render_allowed: bool = True) -> dict[str, object]:
    return {
        "asset_id": "EXT-SEMANTIC001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "video-001",
        "evidence_sha256": SOURCE_SHA,
        "rights_status": rights_status,
        "preview_allowed": True,
        "render_allowed": render_allowed,
    }


def _segments() -> list[dict[str, object]]:
    return [
        {
            "start_seconds": 0,
            "end_seconds": 3,
            "scene_type": "shot",
            "shot_type": "close_up",
            "emotion": "surprise",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Real Madrid"],
            "competition": "Champions League",
            "semantic_tags": ["bicycle kick", "goal chance", "football"],
            "ball_visible": True,
            "face_visible": True,
            "crowd_reaction": 0.7,
            "motion_intensity": 0.9,
            "visual_quality": 0.85,
            "emotion_intensity": 0.8,
            "hook_potential": 0.95,
            "climax_potential": 0.75,
        },
        {
            "start_seconds": 3,
            "end_seconds": 7,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Real Madrid"],
            "competition": "Champions League",
            "semantic_tags": ["goal", "net", "crowd"],
            "ball_visible": True,
            "scoreboard_visible": True,
            "crowd_reaction": 0.95,
            "motion_intensity": 0.8,
            "visual_quality": 0.9,
            "emotion_intensity": 0.95,
            "hook_potential": 0.8,
            "climax_potential": 0.99,
        },
        {
            "start_seconds": 7,
            "end_seconds": 11,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Real Madrid"],
            "semantic_tags": ["celebration", "fans"],
            "face_visible": True,
            "crowd_reaction": 1.0,
            "motion_intensity": 0.7,
            "visual_quality": 0.88,
            "emotion_intensity": 1.0,
            "hook_potential": 0.7,
            "climax_potential": 0.9,
        },
    ]


def _index(*, rights_status: str = "owned", render_allowed: bool = True):
    return build_semantic_scene_index(
        asset=_asset(rights_status=rights_status, render_allowed=render_allowed),
        segments=_segments(),
    )


def test_classifies_every_scene_and_selects_top_editorial_moments() -> None:
    index = _index()
    report = build_football_scene_understanding(index)

    assert report.report_state == "classified"
    assert report.blockers == ()
    assert len(report.classifications) == 3
    assert [item.action for item in report.classifications] == ["shot", "goal", "celebration"]
    assert report.top_hook_scene_id == index.scenes[0].scene_id
    assert report.top_climax_scene_id == index.scenes[1].scene_id
    assert report.classifications[0].editorial_role == "hook"
    assert report.classifications[1].editorial_role == "climax"
    assert all(0 <= item.viral_signal_score <= 1 for item in report.classifications)


def test_reference_only_index_remains_blocked_but_is_classified() -> None:
    index = _index(rights_status="reference_only", render_allowed=False)
    report = build_football_scene_understanding(index)

    assert report.report_state == "blocked"
    assert "REFERENCE_ONLY_SCENES_NOT_RENDERABLE" in report.blockers
    assert len(report.classifications) == 3
    assert all(item.blockers == ("SCENE_NOT_RENDERABLE",) for item in report.classifications)


def test_scores_combine_semantic_motion_emotion_quality_and_crowd() -> None:
    index = _index()
    shot = classify_scene(index.scenes[0])
    goal = classify_scene(index.scenes[1])

    assert shot.semantic_strength > 0.8
    assert shot.motion_strength == 0.9
    assert goal.crowd_strength == 0.95
    assert goal.quality_score == 0.9
    assert shot.hook_score > goal.hook_score
    assert goal.climax_score > shot.climax_score


def test_labels_are_normalized_unique_and_sorted() -> None:
    item = classify_scene(_index().scenes[0])

    assert item.labels == tuple(sorted(set(item.labels)))
    assert "shot" in item.labels
    assert "hook" in item.labels
    assert "surprise" in item.labels
    assert "bicycle kick" in item.labels


def test_identity_and_replay_are_deterministic() -> None:
    index = _index()
    first = build_football_scene_understanding(index)
    second = build_football_scene_understanding(index)

    assert first.report_id == second.report_id
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.to_dict() == second.to_dict()


def test_scene_evidence_change_changes_classification_identity() -> None:
    first_index = _index()
    altered_segments = _segments()
    altered_segments[0] = {**altered_segments[0], "hook_potential": 0.5}
    second_index = build_semantic_scene_index(asset=_asset(), segments=altered_segments)

    first = classify_scene(first_index.scenes[0])
    second = classify_scene(second_index.scenes[0])

    assert first.classification_id != second.classification_id
    assert first.evidence_sha256 != second.evidence_sha256


def test_forged_automatic_capabilities_are_rejected() -> None:
    scene = _index().scenes[0]
    item = classify_scene(scene)

    with pytest.raises(FootballSceneUnderstandingError, match="cannot execute"):
        dataclasses.replace(item, auto_render=True).validate(scene)


def test_report_rejects_wrong_index_binding() -> None:
    index = _index()
    report = build_football_scene_understanding(index)
    other_segments = _segments()
    other_segments[2] = {**other_segments[2], "end_seconds": 12}
    other = build_semantic_scene_index(asset=_asset(), segments=other_segments)

    with pytest.raises(FootballSceneUnderstandingError, match="identity mismatch"):
        report.validate(other)
