from dataclasses import replace

import pytest

from publishing.publication_result_intake import (
    PublicationResultIntakeError,
    build_publication_result_intake,
)


def _execution(**overrides):
    payload = {
        "execution_id": "YTVISEXEC-1234567890ABCDEF1234",
        "decision_id": "YTVISIBILITY-1234567890ABCDEF12",
        "youtube_video_id": "video123",
        "previous_visibility": "private",
        "requested_visibility": "public",
        "verified_visibility": "public",
        "execution_state": "published",
        "visibility_change_executed": True,
        "blockers": [],
        "network_used": True,
        "credentials_persisted": False,
        "auto_publish": False,
    }
    payload.update(overrides)
    return payload


def test_confirmed_publication_intake():
    result = build_publication_result_intake(execution_result=_execution())
    assert result.intake_state == "confirmed"
    assert result.publication_confirmed is True
    assert result.verified_visibility == "public"
    assert result.publication_url.endswith("video123")
    assert result.blockers == ()
    result.validate()


def test_no_change_is_confirmed_when_consistent():
    result = build_publication_result_intake(execution_result=_execution(
        previous_visibility="unlisted", requested_visibility="unlisted",
        verified_visibility="unlisted", execution_state="no_change",
        visibility_change_executed=False, network_used=False,
    ))
    assert result.intake_state == "confirmed"
    assert result.publication_confirmed is True


def test_failed_execution_is_blocked():
    result = build_publication_result_intake(execution_result=_execution(
        execution_state="failed", visibility_change_executed=False,
        verified_visibility="private", blockers=["HTTP_FAILURE"],
    ))
    assert result.intake_state == "blocked"
    assert "VISIBILITY_EXECUTION_NOT_SUCCESSFUL" in result.blockers
    assert "VISIBILITY_EXECUTION_HAS_BLOCKERS" in result.blockers


def test_visibility_mismatch_is_blocked():
    result = build_publication_result_intake(execution_result=_execution(
        verified_visibility="unlisted"
    ))
    assert result.intake_state == "blocked"
    assert "YOUTUBE_VISIBILITY_NOT_CONFIRMED" in result.blockers


def test_credential_persistence_and_auto_publish_are_blocked():
    result = build_publication_result_intake(execution_result=_execution(
        credentials_persisted=True, auto_publish=True
    ))
    assert "CREDENTIAL_PERSISTENCE_REPORTED" in result.blockers
    assert "AUTOMATIC_PUBLICATION_REPORTED" in result.blockers


def test_replay_is_deterministic():
    first = build_publication_result_intake(execution_result=_execution())
    second = build_publication_result_intake(execution_result=_execution())
    assert first.to_dict() == second.to_dict()


def test_tampered_evidence_is_rejected():
    result = build_publication_result_intake(execution_result=_execution())
    with pytest.raises(PublicationResultIntakeError, match="evidence mismatch"):
        replace(result, verified_visibility="unlisted").validate()


def test_intake_cannot_enable_external_operations():
    result = build_publication_result_intake(execution_result=_execution())
    with pytest.raises(PublicationResultIntakeError, match="external operations"):
        replace(result, network_used_by_intake=True).validate()
