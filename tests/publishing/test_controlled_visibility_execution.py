from __future__ import annotations

from dataclasses import replace

import pytest

from publishing.controlled_visibility_execution import (
    EXECUTION_CONFIRMATION,
    ControlledVisibilityExecutionError,
    execute_controlled_visibility_change,
)


def _decision(**updates):
    payload = {
        "decision_id": "YTVISIBILITY-1234567890ABCDEF1234",
        "youtube_result_id": "YTRESULT-1234567890ABCDEF1234",
        "youtube_video_id": "video-001",
        "current_visibility": "private",
        "target_visibility": "public",
        "decision_state": "ready_for_manual_publication",
        "manual_publication_allowed": True,
        "blockers": [],
    }
    payload.update(updates)
    return payload


def _update(video_id: str, visibility: str):
    return {"youtube_video_id": video_id, "privacy_status": visibility}


def _verify(video_id: str):
    return {"youtube_video_id": video_id, "privacy_status": "public"}


def test_executes_and_verifies_single_visibility_change():
    result = execute_controlled_visibility_change(
        decision=_decision(),
        execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update,
        verify_visibility=_verify,
    )
    assert result.execution_state == "published"
    assert result.visibility_change_executed is True
    assert result.network_used is True
    assert result.verified_visibility == "public"
    assert result.blockers == ()
    result.validate()


def test_second_human_confirmation_is_required():
    result = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation="wrong",
        update_visibility=_update, verify_visibility=_verify,
    )
    assert result.execution_state == "blocked"
    assert "SECOND_HUMAN_CONFIRMATION_REQUIRED" in result.blockers
    assert result.network_used is False


def test_no_change_does_not_call_network():
    calls = []
    def update(video_id, visibility):
        calls.append((video_id, visibility))
        return {}
    result = execute_controlled_visibility_change(
        decision=_decision(current_visibility="unlisted", target_visibility="unlisted", decision_state="no_change_required", manual_publication_allowed=False),
        execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=update,
        verify_visibility=_verify,
    )
    assert result.execution_state == "no_change"
    assert result.visibility_change_executed is False
    assert result.network_used is False
    assert calls == []


def test_blocked_decision_is_fail_closed():
    result = execute_controlled_visibility_change(
        decision=_decision(decision_state="blocked", manual_publication_allowed=False, blockers=["UPSTREAM_BLOCKER"]),
        execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update,
        verify_visibility=_verify,
    )
    assert result.execution_state == "blocked"
    assert "VISIBILITY_DECISION_NOT_READY" in result.blockers
    assert "VISIBILITY_DECISION_HAS_BLOCKERS" in result.blockers


def test_update_video_identity_mismatch_fails():
    result = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=lambda *_: {"youtube_video_id": "other", "privacy_status": "public"},
        verify_visibility=_verify,
    )
    assert result.execution_state == "failed"
    assert "YOUTUBE_UPDATE_VIDEO_ID_MISMATCH" in result.blockers


def test_post_update_verification_is_mandatory():
    result = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update,
        verify_visibility=lambda video_id: {"youtube_video_id": video_id, "privacy_status": "unlisted"},
    )
    assert result.execution_state == "failed"
    assert "YOUTUBE_VISIBILITY_VERIFICATION_FAILED" in result.blockers


def test_replay_is_deterministic():
    first = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update, verify_visibility=_verify,
    )
    second = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update, verify_visibility=_verify,
    )
    assert first.to_dict() == second.to_dict()


def test_tampered_evidence_is_rejected():
    result = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update, verify_visibility=_verify,
    )
    with pytest.raises(ControlledVisibilityExecutionError, match="evidence mismatch"):
        replace(result, evidence_sha256="0" * 64).validate()


def test_credentials_and_auto_publish_cannot_be_enabled():
    result = execute_controlled_visibility_change(
        decision=_decision(), execution_confirmation=EXECUTION_CONFIRMATION,
        update_visibility=_update, verify_visibility=_verify,
    )
    with pytest.raises(ControlledVisibilityExecutionError):
        replace(result, credentials_persisted=True).validate()
    with pytest.raises(ControlledVisibilityExecutionError):
        replace(result, auto_publish=True).validate()
