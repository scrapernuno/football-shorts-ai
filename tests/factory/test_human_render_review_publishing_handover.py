from dataclasses import replace

import pytest

from factory.human_render_review_publishing_handover import (
    HumanRenderReviewError,
    build_publishing_handover,
)


def _intake(**overrides):
    base = {
        "intake_id": "RENDERINTAKE-0123456789ABCDEFGHIJ",
        "render_package_id": "RENDERPKG-0123456789ABCDEFGHIJ",
        "output_uri": "dashboard/media/final-short.mp4",
        "output_sha256": "a" * 64,
        "review_state": "ready_for_review",
    }
    base.update(overrides)
    return base


def _approved():
    return build_publishing_handover(
        intake=_intake(), reviewer="Nuno Freitas", decision="approved",
        review_note="Vídeo revisto integralmente e aprovado para handover.",
        title="O golo que mudou tudo", description="O momento decisivo explicado em menos de um minuto.",
        tags=("football", "goal", "shorts"), privacy_status="private",
    )


def test_approved_render_creates_inert_publishing_handover():
    report = _approved()
    report.validate()
    assert report.handover_state == "approved_for_handover"
    assert report.publishing_handover_allowed is True
    assert report.blockers == ()
    assert report.handover_id.startswith("PUBHANDOVER-")
    assert report.upload_enabled is False
    assert report.publish_enabled is False
    assert report.auto_publish is False


def test_rejected_render_is_fail_closed():
    report = build_publishing_handover(
        intake=_intake(), reviewer="Editor", decision="rejected",
        review_note="Qualidade visual insuficiente.", title="", description="", tags=(),
    )
    assert report.handover_state == "rejected"
    assert "RENDER_REJECTED_BY_HUMAN" in report.blockers
    assert report.publishing_handover_allowed is False


def test_changes_requested_is_fail_closed():
    report = build_publishing_handover(
        intake=_intake(), reviewer="Editor", decision="changes_requested",
        review_note="Ajustar legendas e volume da narração.", title="", description="", tags=(),
    )
    assert report.handover_state == "changes_requested"
    assert "RENDER_CHANGES_REQUESTED" in report.blockers


def test_unready_intake_blocks_handover():
    report = build_publishing_handover(
        intake=_intake(review_state="blocked"), reviewer="Editor", decision="approved",
        review_note="Tentativa inválida.", title="Título", description="Descrição", tags=(),
    )
    assert report.handover_state == "blocked"
    assert "RENDER_INTAKE_NOT_READY" in report.blockers


def test_approved_decision_requires_metadata_and_human_review():
    report = build_publishing_handover(
        intake=_intake(), reviewer="", decision="approved", review_note="",
        title="", description="", tags=(),
    )
    assert report.handover_state == "blocked"
    assert "HUMAN_REVIEWER_REQUIRED" in report.blockers
    assert "REVIEW_NOTE_REQUIRED" in report.blockers
    assert "PUBLISHING_TITLE_REQUIRED" in report.blockers
    assert "PUBLISHING_DESCRIPTION_REQUIRED" in report.blockers


def test_replay_is_deterministic_and_tags_are_normalized():
    first = _approved()
    second = build_publishing_handover(
        intake=_intake(), reviewer="Nuno Freitas", decision="approved",
        review_note="Vídeo revisto integralmente e aprovado para handover.",
        title="O golo que mudou tudo", description="O momento decisivo explicado em menos de um minuto.",
        tags=("shorts", "football", "goal", "football"), privacy_status="private",
    )
    assert first == second
    assert first.tags == ("football", "goal", "shorts")


def test_evidence_tampering_is_detected():
    report = _approved()
    with pytest.raises(HumanRenderReviewError, match="evidence mismatch"):
        replace(report, title="Título adulterado").validate()


def test_operational_capabilities_cannot_be_enabled():
    report = _approved()
    with pytest.raises(HumanRenderReviewError, match="cannot enable publishing capabilities"):
        replace(report, publish_enabled=True).validate()
