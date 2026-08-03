from dataclasses import replace

import pytest

from director.human_review_final_approval import (
    DirectorApprovalError,
    build_director_approval,
)


def _ranking(*, state="ranked", blockers=()):
    return {
        "ranking_id": "DIRRANK-1234567890ABCDEFGHIJ",
        "ranking_state": state,
        "ranked_variant_ids": [
            "DIRVAR-FAST00000000000001",
            "DIRVAR-BALANCED000000001",
        ],
        "recommended_variant_id": "DIRVAR-FAST00000000000001",
        "blockers": list(blockers),
    }


def test_approves_recommended_variant_for_factory_handover():
    report = build_director_approval(
        ranking_report=_ranking(),
        reviewer_id="editor-001",
        decision="approved",
        notes="Abertura forte e ritmo adequado.",
    )
    report.validate()
    assert report.approval_state == "approved"
    assert report.selected_variant_id == "DIRVAR-FAST00000000000001"
    assert report.factory_handover_allowed is True
    assert report.blockers == ()


def test_approves_an_alternative_ranked_variant():
    report = build_director_approval(
        ranking_report=_ranking(),
        reviewer_id="editor-001",
        decision="approved",
        selected_variant_id="DIRVAR-BALANCED000000001",
    )
    assert report.approval_state == "approved"
    assert report.selected_variant_id == "DIRVAR-BALANCED000000001"


def test_rejects_variant_and_blocks_handover():
    report = build_director_approval(
        ranking_report=_ranking(), reviewer_id="editor-001", decision="rejected"
    )
    assert report.approval_state == "rejected"
    assert report.factory_handover_allowed is False
    assert "EDITORIAL_VARIANT_REJECTED" in report.blockers


def test_requests_changes_and_blocks_handover():
    report = build_director_approval(
        ranking_report=_ranking(),
        reviewer_id="editor-001",
        decision="changes_requested",
        notes="Substituir o segundo excerto.",
    )
    assert report.approval_state == "changes_requested"
    assert "EDITORIAL_CHANGES_REQUESTED" in report.blockers


def test_blocked_ranking_cannot_be_approved():
    report = build_director_approval(
        ranking_report=_ranking(state="blocked", blockers=("VARIANT_RENDER_NOT_ALLOWED",)),
        reviewer_id="editor-001",
        decision="approved",
    )
    assert report.approval_state == "blocked"
    assert report.factory_handover_allowed is False
    assert "DIRECTOR_RANKING_NOT_READY" in report.blockers
    assert "DIRECTOR_RANKING_BLOCKED" in report.blockers


def test_unknown_variant_is_fail_closed():
    report = build_director_approval(
        ranking_report=_ranking(),
        reviewer_id="editor-001",
        decision="approved",
        selected_variant_id="DIRVAR-UNKNOWN00000000001",
    )
    assert report.approval_state == "blocked"
    assert "SELECTED_VARIANT_NOT_RANKED" in report.blockers


def test_replay_is_deterministic():
    kwargs = {
        "ranking_report": _ranking(),
        "reviewer_id": "editor-001",
        "decision": "approved",
    }
    first = build_director_approval(**kwargs)
    second = build_director_approval(**kwargs)
    assert first.to_dict() == second.to_dict()


def test_tampered_evidence_is_rejected():
    report = build_director_approval(
        ranking_report=_ranking(), reviewer_id="editor-001", decision="approved"
    )
    with pytest.raises(DirectorApprovalError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_director_approval(
        ranking_report=_ranking(), reviewer_id="editor-001", decision="approved"
    )
    with pytest.raises(DirectorApprovalError, match="operational capabilities"):
        replace(report, render_enabled=True).validate()


def test_invalid_decision_and_missing_reviewer_are_rejected():
    with pytest.raises(DirectorApprovalError, match="unsupported decision"):
        build_director_approval(
            ranking_report=_ranking(), reviewer_id="editor-001", decision="publish"
        )
    with pytest.raises(DirectorApprovalError, match="reviewer_id"):
        build_director_approval(
            ranking_report=_ranking(), reviewer_id=" ", decision="approved"
        )
