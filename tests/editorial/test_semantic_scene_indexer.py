from __future__ import annotations

import dataclasses

import pytest

from editorial.semantic_scene_indexer import (
    SemanticSceneIndexError,
    build_semantic_scene_index,
    canonical_sha256,
)


SOURCE_SHA = "a" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-SEMANTIC001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "source-video-1",
        "rights_status": rights_status,
        "preview_allowed": True,
        "render_allowed": rights_status == "owned",
        "evidence_sha256": SOURCE_SHA,
    }


def _segments() -> list[dict[str, object]]:
    return [
        {
            "start_seconds": 0.0,
            "end_seconds": 2.5,
            "scene_type": "shot",
            "shot_type": "close_up",
            "emotion": "surprise",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["hook", "shot", "football"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.92,
            "visual_quality": 0.88,
            "emotion_intensity": 0.94,
            "hook_potential": 0.98,
            "climax_potential": 0.76,
        },
        {
            "start_seconds": 2.5,
            "end_seconds": 6.0,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["goal", "climax", "crowd"],
            "ball_visible": True,
            "scoreboard_visible": True,
            "crowd_reaction": 0.97,
            "motion_intensity": 0.85,
            "visual_quality": 0.91,
            "emotion_intensity": 0.99,
            "hook_potential": 0.84,
            "climax_potential": 0.99,
        },
    ]


def test_builds_deterministic_scene_index_for_owned_media() -> None:
    result = build_semantic_scene_index(asset=_asset(), segments=_segments())

    assert result.index_state == "indexed"
    assert result.blockers == ()
    assert result.asset_id == "EXT-SEMANTIC001"
    assert result.total_duration_seconds == 6.0
    assert len(result.scenes) == 2
    assert result.scenes[0].scene_id.endswith("-0001")
    assert result.scenes[1].scene_id.endswith("-0002")
    assert result.scenes[0].signals.scene_type == "shot"
    assert result.scenes[1].signals.scene_type == "goal"
    assert result.scenes[0].signals.hook_potential == 0.98
    assert result.scenes[1].signals.climax_potential == 0.99
    assert all(scene.render_allowed for scene in result.scenes)


def test_reference_only_video_is_indexed_for_preview_but_blocked_for_render() -> None:
    result = build_semantic_scene_index(
        asset=_asset(rights_status="reference_only"),
        segments=_segments(),
    )

    assert result.index_state == "blocked"
    assert result.blockers == ("REFERENCE_ONLY_SCENES_NOT_RENDERABLE",)
    assert all(scene.preview_allowed for scene in result.scenes)
    assert all(scene.render_allowed is False for scene in result.scenes)


def test_terms_are_normalized_sorted_and_deduplicated() -> None:
    segments = _segments()
    segments[0]["players"] = ["Messi", "Ronaldo", "Messi"]
    segments[0]["semantic_tags"] = ["shot", "football", "shot"]

    result = build_semantic_scene_index(asset=_asset(), segments=segments)

    assert result.scenes[0].signals.players == ("Messi", "Ronaldo")
    assert result.scenes[0].signals.semantic_tags == ("football", "shot")


def test_rejects_overlapping_scenes() -> None:
    segments = _segments()
    segments[1]["start_seconds"] = 2.0

    with pytest.raises(SemanticSceneIndexError, match="overlap"):
        build_semantic_scene_index(asset=_asset(), segments=segments)


def test_rejects_invalid_scores_and_long_scenes() -> None:
    segments = _segments()
    segments[0]["hook_potential"] = 1.1
    with pytest.raises(SemanticSceneIndexError, match="between 0 and 1"):
        build_semantic_scene_index(asset=_asset(), segments=segments)

    long_scene = [{"start_seconds": 0, "end_seconds": 31}]
    with pytest.raises(SemanticSceneIndexError, match="exceeds 30 seconds"):
        build_semantic_scene_index(asset=_asset(), segments=long_scene)


def test_identity_and_replay_are_deterministic() -> None:
    first = build_semantic_scene_index(asset=_asset(), segments=_segments())
    second = build_semantic_scene_index(asset=_asset(), segments=_segments())

    assert first.index_id == second.index_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_operational_capabilities_cannot_be_forged() -> None:
    result = build_semantic_scene_index(asset=_asset(), segments=_segments())

    forged_index = dataclasses.replace(result, auto_match=True)
    with pytest.raises(SemanticSceneIndexError, match="automatic execution"):
        forged_index.validate()

    forged_scene = dataclasses.replace(result.scenes[0], inference_executed=True)
    with pytest.raises(SemanticSceneIndexError, match="operational capabilities"):
        forged_scene.validate()


def test_empty_segments_and_invalid_source_evidence_are_rejected() -> None:
    with pytest.raises(SemanticSceneIndexError, match="segments are required"):
        build_semantic_scene_index(asset=_asset(), segments=[])

    asset = _asset()
    asset["evidence_sha256"] = "invalid"
    with pytest.raises(SemanticSceneIndexError, match="SHA-256"):
        build_semantic_scene_index(asset=asset, segments=_segments())
