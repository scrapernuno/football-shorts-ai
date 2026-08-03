from __future__ import annotations

import dataclasses

import pytest

from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_scene_matching import (
    StorySceneMatchingError,
    build_story_scene_matching,
    canonical_sha256,
)


SOURCE_SHA = "b" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-MATCH001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "match-video-1",
        "rights_status": rights_status,
        "preview_allowed": True,
        "render_allowed": rights_status == "owned",
        "evidence_sha256": SOURCE_SHA,
    }


def _segments() -> list[dict[str, object]]:
    return [
        {
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "scene_type": "shot",
            "shot_type": "close_up",
            "emotion": "surprise",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["bicycle kick", "spectacular", "hook"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.98,
            "visual_quality": 0.94,
            "emotion_intensity": 0.96,
            "hook_potential": 0.99,
            "climax_potential": 0.70,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 5.0,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["goal", "net", "climax"],
            "ball_visible": True,
            "scoreboard_visible": True,
            "crowd_reaction": 0.99,
            "motion_intensity": 0.90,
            "visual_quality": 0.96,
            "emotion_intensity": 1.0,
            "hook_potential": 0.85,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["celebration", "crowd", "reaction"],
            "face_visible": True,
            "crowd_reaction": 0.96,
            "motion_intensity": 0.76,
            "visual_quality": 0.92,
            "emotion_intensity": 0.98,
            "hook_potential": 0.72,
            "climax_potential": 0.88,
        },
    ]


def _story() -> dict[str, object]:
    return {
        "beats": [
            {
                "role": "hook",
                "text": "Ninguém esperava este remate de Cristiano Ronaldo.",
                "keywords": ["remate", "surpresa", "bicycle kick"],
                "players": ["Cristiano Ronaldo"],
                "teams": ["Portugal"],
                "competition": "UEFA Nations League",
                "emotions": ["surprise"],
                "actions": ["shot"],
            },
            {
                "role": "climax",
                "text": "A bola entrou e decidiu tudo.",
                "keywords": ["goal", "net", "climax"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["goal"],
                "emotions": ["celebration"],
            },
            {
                "role": "reaction",
                "text": "O estádio explodiu na celebração.",
                "keywords": ["celebration", "crowd", "reaction"],
                "actions": ["celebration"],
                "emotions": ["joy"],
            },
        ]
    }


def _evidence(*, rights_status: str = "owned"):
    index = build_semantic_scene_index(
        asset=_asset(rights_status=rights_status),
        segments=_segments(),
    )
    understanding = build_football_scene_understanding(index)
    return index, understanding


def test_matches_story_beats_to_expected_scenes() -> None:
    index, understanding = _evidence()
    report = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
    )

    assert report.report_state == "matched"
    assert report.blockers == ()
    assert len(report.matches) == 3
    assert report.matches[0].selected_scene_id.endswith("-0001")
    assert report.matches[1].selected_scene_id.endswith("-0002")
    assert report.matches[2].selected_scene_id.endswith("-0003")
    assert all(match.match_state == "matched" for match in report.matches)


def test_candidate_ranking_exposes_component_scores_and_terms() -> None:
    index, understanding = _evidence()
    report = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
        max_candidates_per_beat=3,
    )

    hook = report.matches[0]
    assert [candidate.rank for candidate in hook.candidates] == [1, 2, 3]
    assert hook.candidates[0].total_score >= hook.candidates[1].total_score
    assert hook.candidates[0].role_score == 1.0
    assert hook.candidates[0].action_score == 1.0
    assert hook.candidates[0].entity_score == 1.0
    assert hook.candidates[0].rights_score == 1.0
    assert "cristiano_ronaldo" in hook.candidates[0].matched_terms
    assert "shot" in hook.candidates[0].matched_terms


def test_reference_only_scenes_are_ranked_but_report_is_blocked() -> None:
    index, understanding = _evidence(rights_status="reference_only")
    report = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
    )

    assert report.report_state == "blocked"
    assert len(report.blockers) == 3
    assert all(match.match_state == "blocked" for match in report.matches)
    assert all(
        candidate.render_allowed is False
        for match in report.matches
        for candidate in match.candidates
    )
    assert all(
        candidate.blockers == ("SCENE_NOT_RENDERABLE",)
        for match in report.matches
        for candidate in match.candidates
    )


def test_text_keywords_are_derived_when_not_supplied() -> None:
    index, understanding = _evidence()
    story = {
        "beats": [
            {
                "role": "climax",
                "text": "Cristiano Ronaldo marcou um goal espetacular",
                "players": ["Cristiano Ronaldo"],
                "actions": ["goal"],
            }
        ]
    }
    report = build_story_scene_matching(
        story=story,
        index=index,
        understanding=understanding,
    )

    assert "cristiano" in report.matches[0].beat.keywords
    assert "ronaldo" in report.matches[0].beat.keywords
    assert "goal" in report.matches[0].beat.keywords
    assert report.matches[0].selected_scene_id.endswith("-0002")


def test_identity_and_replay_are_deterministic() -> None:
    index, understanding = _evidence()
    first = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
    )
    second = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
    )

    assert first.report_id == second.report_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_rejects_invalid_story_and_candidate_limit() -> None:
    index, understanding = _evidence()

    with pytest.raises(StorySceneMatchingError, match="story beats are required"):
        build_story_scene_matching(
            story={},
            index=index,
            understanding=understanding,
        )

    with pytest.raises(StorySceneMatchingError, match="between 1 and 20"):
        build_story_scene_matching(
            story=_story(),
            index=index,
            understanding=understanding,
            max_candidates_per_beat=21,
        )

    story = {"beats": [{"role": "invalid", "text": "Text"}]}
    with pytest.raises(StorySceneMatchingError, match="unsupported story role"):
        build_story_scene_matching(
            story=story,
            index=index,
            understanding=understanding,
        )


def test_operational_capabilities_cannot_be_forged() -> None:
    index, understanding = _evidence()
    report = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
    )

    forged = dataclasses.replace(report, auto_render=True)
    with pytest.raises(StorySceneMatchingError, match="operational capabilities"):
        forged.validate(index, understanding)
