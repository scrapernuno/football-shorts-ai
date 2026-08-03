from __future__ import annotations

import dataclasses

import pytest

from editorial.automatic_timeline_builder import (
    AutomaticTimelineBuilderError,
    build_automatic_timeline,
    canonical_sha256,
)
from editorial.editorial_quality_scoring import score_editorial_quality
from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_alignment_optimizer import optimize_story_alignment
from editorial.story_scene_matching import build_story_scene_matching
from editorial.viral_hook_optimizer import optimize_viral_hook


SOURCE_SHA = "d" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-AUTOTL001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "automatic-timeline-video",
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
            "semantic_tags": ["hook", "shot", "surprise"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.98,
            "visual_quality": 0.95,
            "emotion_intensity": 0.97,
            "hook_potential": 0.99,
            "climax_potential": 0.75,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 5.5,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "semantic_tags": ["goal", "climax", "net"],
            "ball_visible": True,
            "crowd_reaction": 0.99,
            "motion_intensity": 0.90,
            "visual_quality": 0.96,
            "emotion_intensity": 1.0,
            "hook_potential": 0.85,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 5.5,
            "end_seconds": 9.0,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "semantic_tags": ["celebration", "crowd", "reaction"],
            "face_visible": True,
            "crowd_reaction": 0.97,
            "motion_intensity": 0.78,
            "visual_quality": 0.93,
            "emotion_intensity": 0.99,
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
                "keywords": ["hook", "shot", "surprise"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["shot"],
                "emotions": ["surprise"],
            },
            {
                "role": "climax",
                "text": "A bola entrou e o estádio explodiu.",
                "keywords": ["goal", "climax", "net"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["goal"],
                "emotions": ["celebration"],
            },
            {
                "role": "reaction",
                "text": "A celebração confirmou um momento histórico.",
                "keywords": ["celebration", "crowd", "reaction"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["celebration"],
                "emotions": ["joy"],
            },
        ]
    }


def _pipeline(*, rights_status: str = "owned"):
    index = build_semantic_scene_index(asset=_asset(rights_status=rights_status), segments=_segments())
    understanding = build_football_scene_understanding(index)
    matching = build_story_scene_matching(story=_story(), index=index, understanding=understanding)
    hook = optimize_viral_hook(matching=matching, index=index, understanding=understanding)
    alignment = optimize_story_alignment(matching=matching, hook=hook)
    score = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )
    return index, alignment, score


def test_builds_vertical_review_ready_timeline() -> None:
    index, alignment, score = _pipeline()
    result = build_automatic_timeline(
        title="Cristiano Ronaldo Impossible Goal",
        alignment=alignment,
        score=score,
        index=index,
    )

    assert result.timeline_state == "ready_for_review"
    assert result.blockers == ()
    assert result.aspect_ratio == "9:16"
    assert result.resolution == "1080x1920"
    assert result.fps == 30
    assert result.total_duration_seconds == 9.0
    assert [clip.order for clip in result.clips] == [1, 2, 3]
    assert [clip.timeline_start_seconds for clip in result.clips] == [0.0, 2.0, 5.5]
    assert [clip.timeline_end_seconds for clip in result.clips] == [2.0, 5.5, 9.0]
    assert result.clips[0].beat_role == "hook"
    assert result.clips[1].beat_role == "climax"
    assert result.clips[2].beat_role == "reaction"
    assert result.editorial_quality_score == score.editorial_quality_score
    assert result.viral_potential_score == score.viral_potential_score


def test_preserves_source_timestamps_text_and_transitions() -> None:
    index, alignment, score = _pipeline()
    result = build_automatic_timeline(title="Story", alignment=alignment, score=score, index=index)

    for clip, aligned in zip(result.clips, alignment.scenes, strict=True):
        source = next(scene for scene in index.scenes if scene.scene_id == aligned.scene_id)
        assert clip.source_start_seconds == source.start_seconds
        assert clip.source_end_seconds == source.end_seconds
        assert clip.beat_text == aligned.beat_text
        assert clip.transition == aligned.transition
        assert clip.match_score == aligned.match_score
        assert clip.source_evidence_sha256 == source.evidence_sha256


def test_reference_only_timeline_is_blocked() -> None:
    index, alignment, score = _pipeline(rights_status="reference_only")
    result = build_automatic_timeline(title="Reference Story", alignment=alignment, score=score, index=index)

    assert result.timeline_state == "blocked"
    assert "EDITORIAL_SCORE_BLOCKED" in result.blockers
    assert all(clip.render_allowed is False for clip in result.clips)
    assert all(clip.rights_status == "reference_only" for clip in result.clips)
    assert all(clip.blockers for clip in result.clips)


def test_rejects_mismatched_score_and_invalid_configuration() -> None:
    index, alignment, score = _pipeline()
    forged = dataclasses.replace(score, alignment_id="ALIGN-OTHER")

    with pytest.raises(AutomaticTimelineBuilderError, match="do not match"):
        build_automatic_timeline(title="Story", alignment=alignment, score=forged, index=index)

    with pytest.raises(AutomaticTimelineBuilderError, match="title is required"):
        build_automatic_timeline(title="   ", alignment=alignment, score=score, index=index)

    with pytest.raises(AutomaticTimelineBuilderError, match="unsupported timeline fps"):
        build_automatic_timeline(title="Story", alignment=alignment, score=score, index=index, fps=29)


def test_identity_and_replay_are_deterministic() -> None:
    index, alignment, score = _pipeline()
    first = build_automatic_timeline(title="Story", alignment=alignment, score=score, index=index)
    second = build_automatic_timeline(title="Story", alignment=alignment, score=score, index=index)

    assert first.timeline_id == second.timeline_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_operational_capabilities_cannot_be_forged() -> None:
    index, alignment, score = _pipeline()
    result = build_automatic_timeline(title="Story", alignment=alignment, score=score, index=index)

    forged = dataclasses.replace(result, auto_render=True)
    with pytest.raises(AutomaticTimelineBuilderError, match="operational capabilities"):
        forged.validate()
