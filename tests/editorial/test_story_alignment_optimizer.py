from __future__ import annotations

import dataclasses

import pytest

from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_alignment_optimizer import (
    StoryAlignmentError,
    canonical_sha256,
    optimize_story_alignment,
)
from editorial.story_scene_matching import build_story_scene_matching
from editorial.viral_hook_optimizer import optimize_viral_hook


SOURCE_SHA = "e" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-ALIGN001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "alignment-video-1",
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
            "competition": "Champions League",
            "semantic_tags": ["hook", "shot", "bicycle kick"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.98,
            "visual_quality": 0.95,
            "emotion_intensity": 0.96,
            "hook_potential": 0.99,
            "climax_potential": 0.70,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 5.0,
            "scene_type": "build_up",
            "shot_type": "wide",
            "emotion": "anticipation",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "Champions League",
            "semantic_tags": ["build up", "cross", "context"],
            "ball_visible": True,
            "motion_intensity": 0.70,
            "visual_quality": 0.90,
            "emotion_intensity": 0.72,
            "hook_potential": 0.45,
            "climax_potential": 0.42,
        },
        {
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "Champions League",
            "semantic_tags": ["goal", "net", "climax"],
            "ball_visible": True,
            "scoreboard_visible": True,
            "crowd_reaction": 0.99,
            "motion_intensity": 0.91,
            "visual_quality": 0.97,
            "emotion_intensity": 1.0,
            "hook_potential": 0.82,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 8.0,
            "end_seconds": 11.0,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "Champions League",
            "semantic_tags": ["celebration", "crowd", "reaction"],
            "face_visible": True,
            "crowd_reaction": 0.98,
            "motion_intensity": 0.80,
            "visual_quality": 0.94,
            "emotion_intensity": 0.99,
            "hook_potential": 0.73,
            "climax_potential": 0.90,
        },
    ]


def _story() -> dict[str, object]:
    return {
        "beats": [
            {
                "role": "hook",
                "text": "Ninguém acreditou neste remate de Cristiano Ronaldo.",
                "keywords": ["bicycle kick", "shot", "surprise"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["shot"],
                "emotions": ["surprise"],
            },
            {
                "role": "development",
                "text": "Tudo começou com o cruzamento para a área.",
                "keywords": ["build up", "cross", "context"],
                "actions": ["build_up"],
                "emotions": ["anticipation"],
            },
            {
                "role": "climax",
                "text": "A bola entrou e o estádio explodiu.",
                "keywords": ["goal", "net", "climax"],
                "actions": ["goal"],
                "emotions": ["celebration"],
            },
            {
                "role": "reaction",
                "text": "A celebração tornou o momento inesquecível.",
                "keywords": ["celebration", "crowd", "reaction"],
                "actions": ["celebration"],
                "emotions": ["joy"],
            },
        ]
    }


def _pipeline(*, rights_status: str = "owned"):
    index = build_semantic_scene_index(
        asset=_asset(rights_status=rights_status),
        segments=_segments(),
    )
    understanding = build_football_scene_understanding(index)
    matching = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
        max_candidates_per_beat=4,
    )
    hook = optimize_viral_hook(
        matching=matching,
        index=index,
        understanding=understanding,
    )
    return matching, hook


def test_builds_distinct_narrative_sequence_with_optimized_hook() -> None:
    matching, hook = _pipeline()
    report = optimize_story_alignment(matching=matching, hook=hook)

    assert report.alignment_state == "aligned"
    assert report.blockers == ()
    assert len(report.scenes) == 4
    assert report.scenes[0].scene_id == hook.selected_scene_id
    assert [scene.beat_role for scene in report.scenes] == [
        "hook",
        "development",
        "climax",
        "reaction",
    ]
    assert len(set(report.selected_scene_ids)) == 4
    assert report.repeated_scene_count == 0
    assert report.sequence_diversity_score == 1.0
    assert report.narrative_progression_score == 1.0


def test_transitions_follow_editorial_role() -> None:
    matching, hook = _pipeline()
    report = optimize_story_alignment(matching=matching, hook=hook)

    assert [scene.transition for scene in report.scenes] == [
        "none",
        "crossfade",
        "cut",
        "cut",
    ]
    assert all(scene.render_allowed for scene in report.scenes)
    assert all(scene.match_score > 0 for scene in report.scenes)


def test_reference_only_sequence_remains_ranked_but_blocked() -> None:
    matching, hook = _pipeline(rights_status="reference_only")
    report = optimize_story_alignment(matching=matching, hook=hook)

    assert report.alignment_state == "blocked"
    assert report.blockers
    assert all(scene.render_allowed is False for scene in report.scenes)
    assert all(scene.blockers == ("SCENE_NOT_RENDERABLE",) for scene in report.scenes)


def test_hook_and_matching_identity_must_agree() -> None:
    matching, hook = _pipeline()
    forged = dataclasses.replace(hook, story_match_report_id="STORYMATCH-OTHER")

    with pytest.raises(StoryAlignmentError, match="does not belong"):
        optimize_story_alignment(matching=matching, hook=forged)


def test_identity_and_replay_are_deterministic() -> None:
    matching, hook = _pipeline()
    first = optimize_story_alignment(matching=matching, hook=hook)
    second = optimize_story_alignment(matching=matching, hook=hook)

    assert first.alignment_id == second.alignment_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_operational_capabilities_cannot_be_forged() -> None:
    matching, hook = _pipeline()
    report = optimize_story_alignment(matching=matching, hook=hook)

    forged = dataclasses.replace(report, auto_render=True)
    with pytest.raises(StoryAlignmentError, match="operational capabilities"):
        forged.validate()


def test_tampered_evidence_is_rejected() -> None:
    matching, hook = _pipeline()
    report = optimize_story_alignment(matching=matching, hook=hook)

    forged = dataclasses.replace(report, evidence_sha256="0" * 64)
    with pytest.raises(StoryAlignmentError, match="evidence mismatch"):
        forged.validate()
