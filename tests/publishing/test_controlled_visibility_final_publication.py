from dataclasses import replace

import pytest

from publishing.controlled_visibility_final_publication import (
    CONFIRMATION_PHRASE,
    ControlledVisibilityError,
    build_controlled_visibility_decision,
)


def _intake(**changes):
    data = {
        "intake_id": "YTRESULT-1234567890ABCDEF1234",
        "youtube_video_id": "video-123",
        "intake_state": "processed",
        "privacy_status": "private",
        "blockers": [],
    }
    data.update(changes)
    return data


def _decision(**changes):
    args = {
        "youtube_intake": _intake(),
        "requested_by": "human-reviewer",
        "decision_note": "Approved for public visibility after final review.",
        "target_visibility": "public",
        "confirmation_phrase": CONFIRMATION_PHRASE,
    }
    args.update(changes)
    return build_controlled_visibility_decision(**args)


def test_builds_ready_manual_publication_decision():
    result = _decision()
    result.validate()
    assert result.decision_state == "ready_for_manual_publication"
    assert result.manual_publication_allowed is True
    assert result.current_visibility == "private"
    assert result.target_visibility == "public"
    assert result.blockers == ()
    assert result.network_enabled is False
    assert result.visibility_change_executed is False
    assert result.auto_publish is False


def test_same_visibility_requires_no_change():
    result = _decision(target_visibility="private")
    assert result.decision_state == "no_change_required"
    assert result.manual_publication_allowed is False


def test_requires_processed_video_and_human_confirmation():
    result = _decision(
        youtube_intake=_intake(intake_state="processing"),
        confirmation_phrase="wrong",
    )
    assert result.decision_state == "blocked"
    assert "YOUTUBE_VIDEO_NOT_PROCESSED" in result.blockers
    assert "EXPLICIT_HUMAN_VISIBILITY_CONFIRMATION_REQUIRED" in result.blockers


def test_rejects_invalid_visibility_and_upstream_blockers():
    result = _decision(
        youtube_intake=_intake(blockers=["CHANNEL_MISMATCH"]),
        target_visibility="secret",
    )
    assert result.decision_state == "blocked"
    assert "TARGET_VISIBILITY_INVALID" in result.blockers
    assert "YOUTUBE_RESULT_HAS_BLOCKERS" in result.blockers


def test_replay_is_deterministic():
    assert _decision().to_dict() == _decision().to_dict()


def test_detects_evidence_tampering():
    result = _decision()
    with pytest.raises(ControlledVisibilityError, match="evidence mismatch"):
        replace(result, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    result = _decision()
    with pytest.raises(ControlledVisibilityError, match="cannot execute publication"):
        replace(result, network_enabled=True).validate()
    with pytest.raises(ControlledVisibilityError, match="cannot execute publication"):
        replace(result, visibility_change_executed=True).validate()
    with pytest.raises(ControlledVisibilityError, match="cannot execute publication"):
        replace(result, auto_publish=True).validate()
