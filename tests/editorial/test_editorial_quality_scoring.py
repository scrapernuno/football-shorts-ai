from __future__ import annotations

import dataclasses

import pytest

from editorial.editorial_quality_scoring import (
    EditorialQualityScoringError,
    canonical_sha256,
    score_editorial_quality,
)
from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_alignment_optimizer import optimize_story_alignment
from editorial.story_scene_matching import build_story_scene_matching
from editorial.viral_hook_optimizer import optimize_viral_hook


SOURCE_SHA = "f" * 64


def _asset(*, rights_status: str = "owned") -> dict[str, object]:
    return {
        "asset_id": "EXT-SCORE001",
        "provider": "local_library" if rights_status == "owned" else "youtube",
        "provider_asset_id": "score-video-1",
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
            "semantic_tags": ["hook", "shot", "spectacular"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.97,
            "visual_quality": 0.95,
            "emotion_intensity": 0.96,
            "hook_potential": 0.99,
            "climax_potential": 0.72,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 5.0,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "semantic_tags": ["goal", "climax", "net"],
            "ball_visible": True,
            "crowd_reaction": 0.98,
            "motion_intensity": 0.89,
            "visual_quality": 0.96,
            "emotion_intensity": 1.0,
            "hook_potential": 0.84,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "semantic_tags": ["celebration", "reaction", "crowd"],
            "face_visible": True,
            "crowd_reaction": 0.97,
            "motion_intensity": 0.78,
            "visual_quality": 0.93,
            "emotion_intensity": 0.99,
            "hook_potential": 0.70,
            "climax_potential": 0.88,
        },
    ]


def _story() -> dict[str, object]:
    return {
        "beats": [
            {
                "role": "hook",
                "text": "Ninguém esperava este remate de Cristiano Ronaldo.",
                "keywords": ["shot", "spectacular", "hook"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["shot"],
                "emotions": ["surprise"],
            },
            {
                "role": "climax",
                "text": "A bola entrou e decidiu tudo.",
                "keywords": ["goal", "net", "climax"],
                "actions": ["goal"],
                "emotions": ["celebration"],
            },
            {
                "role": "reaction",
                "text": "O estádio explodiu em celebração.",
                "keywords": ["celebration", "reaction", "crowd"],
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
    )
    hook = optimize_viral_hook(
        matching=matching,
        index=index,
        understanding=understanding,
    )
    alignment = optimize_story_alignment(matching=matching, hook=hook)
    return index, understanding, matching, hook, alignment


def test_scores_complete_owned_editorial_sequence() -> None:
    index, understanding, matching, hook, alignment = _pipeline()
    report = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )

    assert report.score_state == "scored"
    assert report.blockers == ()
    assert report.rights_readiness_score == 1.0
    assert report.hook_strength_score > 0.8
    assert report.retention_potential_score > 0.7
    assert report.viral_potential_score > 0.7
    assert report.editorial_quality_score > 0.7
    assert report.quality_band in {"strong", "excellent"}


def test_score_components_are_bounded_and_auditable() -> None:
    index, understanding, matching, hook, alignment = _pipeline()
    report = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )

    payload = report.to_dict()
    for key, value in payload.items():
        if key.endswith("_score"):
            assert 0.0 <= value <= 1.0
    assert payload["schema"] == "football-shorts-ai.editorial-quality-score.v1"
    assert payload["score_id"].startswith("EDITSCORE-")
    assert len(payload["evidence_sha256"]) == 64


def test_reference_only_sequence_is_scored_but_blocked() -> None:
    index, understanding, matching, hook, alignment = _pipeline(
        rights_status="reference_only"
    )
    report = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )

    assert report.score_state == "blocked"
    assert report.blockers
    assert report.rights_readiness_score == 0.0
    assert report.viral_potential_score > 0.0


def test_evidence_chain_mismatch_is_rejected() -> None:
    index, understanding, matching, hook, alignment = _pipeline()
    forged = dataclasses.replace(
        alignment,
        hook_optimization_id="HOOKOPT-OTHER",
    )

    with pytest.raises(EditorialQualityScoringError, match="do not match"):
        score_editorial_quality(
            alignment=forged,
            hook=hook,
            matching=matching,
            index=index,
            understanding=understanding,
        )


def test_identity_and_replay_are_deterministic() -> None:
    first_inputs = _pipeline()
    second_inputs = _pipeline()
    first = score_editorial_quality(
        index=first_inputs[0],
        understanding=first_inputs[1],
        matching=first_inputs[2],
        hook=first_inputs[3],
        alignment=first_inputs[4],
    )
    second = score_editorial_quality(
        index=second_inputs[0],
        understanding=second_inputs[1],
        matching=second_inputs[2],
        hook=second_inputs[3],
        alignment=second_inputs[4],
    )

    assert first.score_id == second.score_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_operational_capabilities_cannot_be_forged() -> None:
    index, understanding, matching, hook, alignment = _pipeline()
    report = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )

    forged = dataclasses.replace(report, auto_publish=True)
    with pytest.raises(EditorialQualityScoringError, match="operational capabilities"):
        forged.validate()
