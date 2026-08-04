from dataclasses import replace

import pytest

from publishing.controlled_youtube_upload_workflow_binding import (
    CONFIRMATION_PHRASE,
    YouTubeWorkflowBindingError,
    build_controlled_youtube_workflow_binding,
)


def _authorization(**overrides):
    payload = {
        "authorization_id": "YTPUBAUTH-0123456789ABCDEF0123",
        "render_intake_id": "RENDERINTAKE-0123456789ABCDEF0123",
        "authorization_state": "authorized_for_handover",
        "upload_handover_allowed": True,
        "youtube_channel_id": "UC_TEST_CHANNEL",
        "credential_profile": "primary-youtube-oauth",
    }
    payload.update(overrides)
    return payload


def _build(**overrides):
    arguments = {
        "publishing_authorization": _authorization(),
        "requested_by": "nuno",
        "execution_note": "Controlled one-time YouTube upload preparation.",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "client_id_secret_name": "YOUTUBE_OAUTH_CLIENT_ID",
        "client_secret_secret_name": "YOUTUBE_OAUTH_CLIENT_SECRET",
        "refresh_token_secret_name": "YOUTUBE_OAUTH_REFRESH_TOKEN",
    }
    arguments.update(overrides)
    return build_controlled_youtube_workflow_binding(**arguments)


def test_ready_binding_references_secret_names_without_reading_values():
    binding = _build()
    binding.validate()
    assert binding.binding_state == "ready_for_manual_dispatch"
    assert binding.manual_dispatch_allowed is True
    assert binding.blockers == ()
    assert binding.secret_values_read is False
    assert binding.network_enabled is False
    assert binding.upload_enabled is False
    assert binding.publish_enabled is False
    assert binding.auto_publish is False
    assert binding.client_id_secret_name == "YOUTUBE_OAUTH_CLIENT_ID"


def test_explicit_human_confirmation_is_required():
    binding = _build(confirmation_phrase="UPLOAD")
    assert binding.binding_state == "blocked"
    assert binding.manual_dispatch_allowed is False
    assert "EXPLICIT_HUMAN_UPLOAD_CONFIRMATION_REQUIRED" in binding.blockers


def test_unapproved_handover_is_fail_closed():
    binding = _build(
        publishing_authorization=_authorization(
            authorization_state="blocked",
            upload_handover_allowed=False,
        )
    )
    assert binding.binding_state == "blocked"
    assert "YOUTUBE_PUBLISHING_AUTHORIZATION_NOT_GRANTED" in binding.blockers
    assert "YOUTUBE_UPLOAD_HANDOVER_NOT_ALLOWED" in binding.blockers


@pytest.mark.parametrize(
    "field,blocker",
    [
        ("client_id_secret_name", "YOUTUBE_CLIENT_ID_SECRET_NAME_REQUIRED"),
        ("client_secret_secret_name", "YOUTUBE_CLIENT_SECRET_SECRET_NAME_REQUIRED"),
        ("refresh_token_secret_name", "YOUTUBE_REFRESH_TOKEN_SECRET_NAME_REQUIRED"),
    ],
)
def test_all_oauth_secret_names_are_required(field, blocker):
    binding = _build(**{field: ""})
    assert blocker in binding.blockers


def test_secret_names_are_uppercase_identifiers():
    binding = _build(client_id_secret_name="youtube-client-id")
    assert "YOUTUBE_CLIENT_ID_SECRET_NAME_INVALID" in binding.blockers


def test_replay_is_deterministic():
    first = _build()
    second = _build()
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_detected():
    binding = _build()
    with pytest.raises(YouTubeWorkflowBindingError, match="evidence mismatch"):
        replace(binding, execution_note="tampered").validate()


def test_external_operations_cannot_be_enabled():
    binding = _build()
    with pytest.raises(YouTubeWorkflowBindingError, match="cannot enable external operations"):
        replace(binding, upload_enabled=True).validate()
