from dataclasses import replace

import pytest

from publishing.controlled_youtube_publishing_gate import (
    ControlledYouTubePublishingGateError,
    build_controlled_youtube_publishing_authorization,
)


def _handover(**overrides):
    payload = {
        "handover_state": "approved_for_handover",
        "publishing_handover_allowed": True,
        "render_review_id": "RENDERINTAKE-ABCDEF0123456789ABCD",
        "output_uri": "artifacts/final/football-short.mp4",
        "output_sha256": "a" * 64,
        "title": "O golo que mudou tudo",
        "description": "O momento decisivo explicado em menos de um minuto.",
        "tags": ["futebol", "shorts", "golo", "futebol"],
        "privacy_status": "private",
        "made_for_kids": False,
    }
    payload.update(overrides)
    return payload


def _authorization(**overrides):
    kwargs = {
        "handover": _handover(),
        "requested_by": "Nuno Freitas",
        "authorization_note": "Autorizo apenas o handover controlado para upload manual.",
        "channel_id": "UC0123456789ABCDEFGHIJ",
        "credential_profile": "youtube-production-oauth",
        "explicit_human_command": True,
    }
    kwargs.update(overrides)
    return build_controlled_youtube_publishing_authorization(**kwargs)


def test_authorizes_only_handover_without_enabling_upload_or_publish():
    result = _authorization()
    result.validate()
    assert result.authorization_state == "authorized_for_handover"
    assert result.upload_handover_allowed is True
    assert result.blockers == ()
    assert result.tags == ("futebol", "golo", "shorts")
    assert result.network_enabled is False
    assert result.credential_access_enabled is False
    assert result.upload_enabled is False
    assert result.publish_enabled is False
    assert result.auto_publish is False


def test_requires_explicit_human_upload_command():
    result = _authorization(explicit_human_command=False)
    assert result.authorization_state == "review_required"
    assert result.upload_handover_allowed is False
    assert "EXPLICIT_HUMAN_UPLOAD_COMMAND_REQUIRED" in result.blockers


def test_blocks_when_render_handover_is_not_approved():
    result = _authorization(handover=_handover(handover_state="rejected", publishing_handover_allowed=False))
    assert result.authorization_state == "blocked"
    assert "PUBLISHING_HANDOVER_NOT_APPROVED" in result.blockers


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("requested_by", "", "HUMAN_REQUESTER_REQUIRED"),
        ("authorization_note", "", "AUTHORIZATION_NOTE_REQUIRED"),
        ("channel_id", "", "YOUTUBE_CHANNEL_ID_REQUIRED"),
        ("credential_profile", "", "YOUTUBE_CREDENTIAL_PROFILE_REQUIRED"),
    ],
)
def test_requires_human_channel_and_credential_fields(field, value, blocker):
    result = _authorization(**{field: value})
    assert result.authorization_state == "review_required"
    assert blocker in result.blockers


def test_requires_valid_render_hash_and_metadata():
    result = _authorization(handover=_handover(output_sha256="bad", title="", description=""))
    assert "RENDER_OUTPUT_SHA256_INVALID" in result.blockers
    assert "YOUTUBE_TITLE_REQUIRED" in result.blockers
    assert "YOUTUBE_DESCRIPTION_REQUIRED" in result.blockers


def test_invalid_privacy_is_fail_closed():
    result = _authorization(handover=_handover(privacy_status="friends"))
    assert result.authorization_state == "review_required"
    assert "YOUTUBE_PRIVACY_STATUS_INVALID" in result.blockers


def test_replay_is_deterministic():
    first = _authorization()
    second = _authorization()
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_rejected():
    result = _authorization()
    with pytest.raises(ControlledYouTubePublishingGateError, match="evidence mismatch"):
        replace(result, title="Título adulterado").validate()


def test_operational_capabilities_cannot_be_enabled():
    result = _authorization()
    with pytest.raises(ControlledYouTubePublishingGateError, match="cannot enable operational capabilities"):
        replace(result, upload_enabled=True).validate()
    with pytest.raises(ControlledYouTubePublishingGateError, match="cannot enable operational capabilities"):
        replace(result, publish_enabled=True).validate()
    with pytest.raises(ControlledYouTubePublishingGateError, match="cannot enable operational capabilities"):
        replace(result, credential_access_enabled=True).validate()
