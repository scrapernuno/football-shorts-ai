from __future__ import annotations

import dataclasses

import pytest

from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_scene_matching import build_story_scene_matching
from editorial.viral_hook_optimizer import (
    ViralHookOptimizerError,
    canonical_sha256,
    optimize_viral_hook,
)


SOURCE_SHA = "c" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-HOOK001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "hook-video-1",
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
            "visual_quality": 0.95,
            "emotion_intensity": 0.97,
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
            "crowd_reaction": 0.99,
            "motion_intensity": 0.90,
            "visual_quality": 0.96,
            "emotion_intensity": 1.0,
            "hook_potential": 0.86,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 5.0,
            "end_seconds": 8.5,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["celebration", "crowd", "reaction"],
            "face_visible": True,
            "crowd_reaction": 0.95,
            "motion_intensity": 0.74,
            "visual_quality": 0.91,
            "emotion_intensity": 0.97,
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
                "actions": ["goal"],
            },
        ]
    }


def _evidence(*, rights_status: str = "owned"):
    index = build_semantic_scene_index(
        asset=_asset(rights_status=rights_status),
        segments=_segments(),
    )
    understanding = build_football_scene_understanding(index)
    matching = build_story_scene_matching(
        story=_story(),
        index=index,
        understanding=understanding,
        max_candidates_per_beat=3,
    )
    return index, understanding, matching


def test_selects_strongest_opening_scene() -> None:
    index, understanding, matching = _evidence()
    report = optimize_viral_hook(
        matching=matching,
        index=index,
        understanding=understanding,
    )

    assert report.optimization_state == "optimized"
    assert report.blockers == ()
    assert report.selected_scene_id.endswith("-0001")
    assert report.opening_duration_seconds == 2.0
    assert report.candidates[0].scene_id == report.selected_scene_id
    assert report.candidates[0].final_hook_score >= report.candidates[1].final_hook_score
    assert report.candidates[0].immediate_impact_score > 0.8
    assert report.candidates[0].surprise_score > 0.8


def test_exposes_ranked_alternatives_and_component_scores() -> None:
    index, understanding, matching = _evidence()
    report = optimize_viral_hook(
        matching=matching,
        index=index,
        understanding=understanding,
        max_alternatives=2,
    )

    assert [candidate.rank for candidate in report.candidates] == [1, 2, 3]
    assert len(report.alternative_scene_ids) == 2
    assert report.selected_scene_id not in report.alternative_scene_ids
    assert all(0.0 <= candidate.clarity_score <= 1.0 for candidate in report.candidates)
    assert all(0.0 <= candidate.duration_fit_score <= 1.0 for candidate in report.candidates)


def test_reference_only_candidates_are_ranked_but_blocked() -> None:
    index, understanding, matching = _evidence(rights_status="reference_only")
    report = optimize_viral_hook(
        matching=matching,
        index=index,
        understanding=understanding,
    )

    assert report.optimization_state == "blocked"
    assert report.blockers == ("NO_RENDERABLE_HOOK_CANDIDATE",)
    assert all(candidate.render_allowed is False for candidate in report.candidates)
    assert all(candidate.blockers == ("HOOK_SCENE_NOT_RENDERABLE",) for candidate in report.candidates)


def test_identity_and_replay_are_deterministic() -> None:
    index, understanding, matching = _evidence()
    first = optimize_viral_hook(matching=matching, index=index, understanding=understanding)
    second = optimize_viral_hook(matching=matching, index=index, understanding=understanding)

    assert first.optimization_id == second.optimization_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_requires_exactly_one_hook_and_valid_alternative_limit() -> None:
    index, understanding, matching = _evidence()

    with pytest.raises(ViralHookOptimizerError, match="between 0 and 5"):
        optimize_viral_hook(
            matching=matching,
            index=index,
            understanding=understanding,
            max_alternatives=6,
        )

    story = {
        "beats": [
            {"role": "development", "text": "A jogada começou no meio-campo."}
        ]
    }
    without_hook = build_story_scene_matching(
        story=story,
        index=index,
        understanding=understanding,
    )
    with pytest.raises(ViralHookOptimizerError, match="exactly one hook"):
        optimize_viral_hook(
            matching=without_hook,
            index=index,
            understanding=understanding,
        )


def test_operational_capabilities_cannot_be_forged() -> None:
    index, understanding, matching = _evidence()
    report = optimize_viral_hook(matching=matching, index=index, understanding=understanding)

    forged = dataclasses.replace(report, auto_render=True)
    with pytest.raises(ViralHookOptimizerError, match="operational capabilities"):
        forged.validate()
