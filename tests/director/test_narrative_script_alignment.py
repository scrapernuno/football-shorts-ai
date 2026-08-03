from dataclasses import replace

import pytest

from director.narrative_script_alignment import (
    NarrativeScriptAlignmentError,
    build_narrative_script_alignment,
)


def _director_report(*, state="proposed", render_allowed=True):
    segments = [
        {
            "segment_id": "DIRSEG-HOOK000000000001",
            "clip_id": "VIRALCLIP-HOOK00000001",
            "editorial_role": "hook",
            "start_seconds": 0.0,
            "end_seconds": 2.5,
        },
        {
            "segment_id": "DIRSEG-DEV0000000000002",
            "clip_id": "VIRALCLIP-DEV000000002",
            "editorial_role": "development",
            "start_seconds": 2.5,
            "end_seconds": 6.0,
        },
        {
            "segment_id": "DIRSEG-GOAL00000000003",
            "clip_id": "VIRALCLIP-GOAL00000003",
            "editorial_role": "climax",
            "start_seconds": 6.0,
            "end_seconds": 9.5,
        },
    ]
    return {
        "director_id": "AIDIRECTOR-TEST000000000001",
        "director_state": state,
        "recommended_variant_id": "DIRVAR-BALANCED00000001",
        "variants": [
            {
                "variant_id": "DIRVAR-BALANCED00000001",
                "strategy": "balanced",
                "render_allowed": render_allowed,
                "segments": segments,
            }
        ],
    }


def _script_beats(*, semantic_score=0.92):
    return [
        {
            "role": "hook",
            "script_text": "Ninguém esperava o que aconteceu a seguir.",
            "semantic_score": semantic_score,
            "confidence": 0.94,
            "evidence_id": "SCRIPT-HOOK-001",
        },
        {
            "role": "development",
            "script_text": "A jogada começou longe da baliza e acelerou em segundos.",
            "semantic_score": semantic_score,
            "confidence": 0.91,
            "evidence_id": "SCRIPT-DEV-001",
        },
        {
            "role": "climax",
            "script_text": "O remate entrou e o estádio explodiu.",
            "semantic_score": semantic_score,
            "confidence": 0.96,
            "evidence_id": "SCRIPT-CLIMAX-001",
        },
    ]


def test_aligns_script_beats_to_director_segments():
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )

    report.validate()
    assert report.alignment_state == "aligned"
    assert report.blockers == ()
    assert len(report.beats) == 3
    assert [item.role for item in report.beats] == ["hook", "development", "climax"]
    assert [item.position for item in report.beats] == [0, 1, 2]
    assert report.beats[0].segment_id == "DIRSEG-HOOK000000000001"
    assert report.beats[2].clip_id == "VIRALCLIP-GOAL00000003"
    assert report.average_alignment_score > 0.8
    assert report.total_duration_seconds == 9.5


def test_narration_timing_remains_inside_each_clip():
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )

    for beat in report.beats:
        assert beat.start_seconds <= beat.narration_start_seconds
        assert beat.narration_start_seconds < beat.narration_end_seconds
        assert beat.narration_end_seconds <= beat.end_seconds


def test_low_semantic_alignment_requires_review():
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(semantic_score=0.20),
        minimum_alignment_score=0.75,
    )

    assert report.alignment_state == "review_required"
    assert "SCRIPT_ALIGNMENT_REVIEW_REQUIRED" in report.blockers


def test_script_segment_count_mismatch_requires_review():
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats()[:2],
    )

    assert report.alignment_state == "review_required"
    assert "SCRIPT_SEGMENT_COUNT_MISMATCH" in report.blockers
    assert len(report.beats) == 2


def test_render_blocked_variant_requires_review():
    report = build_narrative_script_alignment(
        director_report=_director_report(render_allowed=False),
        script_beats=_script_beats(),
    )

    assert report.alignment_state == "review_required"
    assert "DIRECTOR_VARIANT_RENDER_BLOCKED" in report.blockers


def test_blocked_director_report_remains_blocked():
    report = build_narrative_script_alignment(
        director_report=_director_report(state="blocked"),
        script_beats=_script_beats(),
    )

    assert report.alignment_state == "blocked"
    assert "DIRECTOR_REPORT_BLOCKED" in report.blockers


def test_replay_is_deterministic():
    first = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )
    second = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )

    assert first.alignment_id == second.alignment_id
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.to_dict() == second.to_dict()


def test_unknown_variant_is_rejected():
    with pytest.raises(NarrativeScriptAlignmentError, match="selected director variant is unknown"):
        build_narrative_script_alignment(
            director_report=_director_report(),
            script_beats=_script_beats(),
            variant_id="DIRVAR-UNKNOWN0000000001",
        )


def test_evidence_tampering_is_detected():
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )
    tampered = replace(report, evidence_sha256="0" * 64)

    with pytest.raises(NarrativeScriptAlignmentError, match="alignment evidence mismatch"):
        tampered.validate()


@pytest.mark.parametrize(
    "field",
    [
        "network_enabled",
        "acquisition_enabled",
        "model_training_enabled",
        "extraction_enabled",
        "render_enabled",
        "auto_publish",
    ],
)
def test_operational_capabilities_cannot_be_enabled(field):
    report = build_narrative_script_alignment(
        director_report=_director_report(),
        script_beats=_script_beats(),
    )
    modified = replace(report, **{field: True})

    with pytest.raises(NarrativeScriptAlignmentError, match="cannot enable operational capabilities"):
        modified.validate()
