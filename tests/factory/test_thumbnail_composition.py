from dataclasses import replace

import pytest

from factory.thumbnail_composition import (
    ThumbnailCompositionError,
    build_thumbnail_composition,
)


def _candidate(**overrides):
    data = {
        "source_uri": "assets/authorized/goal-frame.jpg",
        "headline": "O GOLO IMPOSSÍVEL",
        "subheadline": "A jogada que mudou tudo",
        "emotion": "euphoria",
        "focal_x": 0.67,
        "focal_y": 0.42,
        "crop_scale": 1.25,
        "contrast_score": 0.91,
        "face_visibility_score": 0.88,
        "text_readability_score": 0.94,
        "click_potential_score": 0.96,
        "rights_status": "owned",
    }
    data.update(overrides)
    return data


def test_builds_and_selects_best_authorized_thumbnail():
    report = build_thumbnail_composition(
        source_variant_id="DIRVAR-FAST000000000001",
        candidate_inputs=[_candidate(), _candidate(
            source_uri="assets/authorized/reaction-frame.jpg",
            headline="NINGUÉM ACREDITOU",
            click_potential_score=0.84,
        )],
    )
    report.validate()
    assert report.composition_state == "composed"
    assert report.selected_candidate_id == report.candidates[0].candidate_id
    assert report.blockers == ()
    assert report.network_enabled is False
    assert report.generation_enabled is False
    assert report.render_enabled is False
    assert report.auto_publish is False


def test_reference_only_candidate_is_fail_closed():
    report = build_thumbnail_composition(
        source_variant_id="DIRVAR-FAST000000000001",
        candidate_inputs=[_candidate(rights_status="reference_only")],
    )
    assert report.composition_state == "review_required"
    assert report.selected_candidate_id is None
    assert report.candidates[0].preview_allowed is False
    assert "THUMBNAIL_MEDIA_NOT_AUTHORIZED" in report.candidates[0].blockers


def test_missing_variant_blocks_composition():
    report = build_thumbnail_composition(source_variant_id="", candidate_inputs=[_candidate()])
    assert report.composition_state == "blocked"
    assert "APPROVED_VARIANT_MISSING" in report.blockers


def test_missing_source_requires_review():
    report = build_thumbnail_composition(
        source_variant_id="DIRVAR-FAST000000000001",
        candidate_inputs=[_candidate(source_uri="")],
    )
    assert report.composition_state == "review_required"
    assert "THUMBNAIL_SOURCE_MISSING" in report.candidates[0].blockers


def test_replay_is_deterministic():
    args = {
        "source_variant_id": "DIRVAR-FAST000000000001",
        "candidate_inputs": [_candidate()],
    }
    first = build_thumbnail_composition(**args)
    second = build_thumbnail_composition(**args)
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_evidence_tampering_is_detected():
    report = build_thumbnail_composition(
        source_variant_id="DIRVAR-FAST000000000001",
        candidate_inputs=[_candidate()],
    )
    with pytest.raises(ThumbnailCompositionError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_thumbnail_composition(
        source_variant_id="DIRVAR-FAST000000000001",
        candidate_inputs=[_candidate()],
    )
    with pytest.raises(ThumbnailCompositionError, match="operational capabilities"):
        replace(report, generation_enabled=True).validate()
