from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

from publishing.controlled_oauth_resumable_upload_activation import (
    ControlledOAuthUploadActivationError,
    GoogleResumableUploadClient,
    OAuthSecretMaterial,
    resolve_oauth_secrets,
)


def _binding(**overrides):
    payload = {
        "binding_state": "ready_for_manual_dispatch",
        "manual_dispatch_allowed": True,
        "client_id_secret_name": "YOUTUBE_OAUTH_CLIENT_ID",
        "client_secret_secret_name": "YOUTUBE_OAUTH_CLIENT_SECRET",
        "refresh_token_secret_name": "YOUTUBE_OAUTH_REFRESH_TOKEN",
    }
    payload.update(overrides)
    return payload


def _env():
    return {
        "YOUTUBE_OAUTH_CLIENT_ID": "client-id",
        "YOUTUBE_OAUTH_CLIENT_SECRET": "client-secret",
        "YOUTUBE_OAUTH_REFRESH_TOKEN": "refresh-token",
    }


class Response:
    def __init__(self, payload=b"{}", headers=None):
        self._payload = payload
        self.headers = headers or {}

    def read(self):
        return self._payload


def test_resolves_secret_values_only_from_governed_names():
    result = resolve_oauth_secrets(binding=_binding(), environ=_env())
    assert result.client_id == "client-id"
    assert result.client_secret == "client-secret"
    assert result.refresh_token == "refresh-token"


def test_blocked_binding_cannot_read_secrets():
    with pytest.raises(ControlledOAuthUploadActivationError, match="not ready"):
        resolve_oauth_secrets(binding=_binding(binding_state="blocked", manual_dispatch_allowed=False), environ=_env())


def test_missing_secret_is_fail_closed():
    env = _env()
    del env["YOUTUBE_OAUTH_REFRESH_TOKEN"]
    with pytest.raises(ControlledOAuthUploadActivationError, match="incomplete"):
        resolve_oauth_secrets(binding=_binding(), environ=env)


def test_token_and_session_creation_do_not_persist_secret_material():
    requests = []

    def opener(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/token"):
            return Response(json.dumps({"access_token": "ephemeral-token"}).encode())
        return Response(headers={"Location": "https://upload.youtube.test/session/1"})

    client = GoogleResumableUploadClient(
        secrets=OAuthSecretMaterial("client-id", "client-secret", "refresh-token"),
        opener=opener,
    )
    uri = client.create_session({
        "artifact": {"size_bytes": 4},
        "metadata": {"title": "Title", "description": "Description", "tags": ["football"], "privacy_status": "private"},
    })
    assert uri == "https://upload.youtube.test/session/1"
    assert len(requests) == 2
    assert "refresh-token" in requests[0].data.decode()
    assert requests[1].headers["Authorization"] == "Bearer ephemeral-token"
    assert not hasattr(client, "refresh_token")


def test_completed_chunk_returns_video_identity():
    responses = iter([
        Response(json.dumps({"access_token": "token"}).encode()),
        Response(json.dumps({"id": "youtube-video-1"}).encode()),
    ])
    client = GoogleResumableUploadClient(
        secrets=OAuthSecretMaterial("id", "secret", "refresh"),
        opener=lambda request, timeout: next(responses),
    )
    receipt = client.upload_chunk(session_uri="https://upload.youtube.test/session", offset=0, data=b"abcd", total_size=4)
    assert receipt == {"accepted_offset": 0, "next_offset": 4, "complete": True, "youtube_video_id": "youtube-video-1"}


def test_http_308_is_normalized_as_incomplete_chunk():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Response(json.dumps({"access_token": "token"}).encode())
        headers = Message()
        headers["Range"] = "bytes=0-3"
        raise urllib.error.HTTPError(request.full_url, 308, "Resume Incomplete", headers, io.BytesIO())

    client = GoogleResumableUploadClient(
        secrets=OAuthSecretMaterial("id", "secret", "refresh"),
        opener=opener,
    )
    receipt = client.upload_chunk(session_uri="https://upload.youtube.test/session", offset=0, data=b"abcd", total_size=8)
    assert receipt["complete"] is False
    assert receipt["next_offset"] == 4


def test_non_308_upload_failure_is_fail_closed():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Response(json.dumps({"access_token": "token"}).encode())
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", Message(), io.BytesIO())

    client = GoogleResumableUploadClient(
        secrets=OAuthSecretMaterial("id", "secret", "refresh"),
        opener=opener,
    )
    with pytest.raises(ControlledOAuthUploadActivationError, match="HTTP 403"):
        client.upload_chunk(session_uri="https://upload.youtube.test/session", offset=0, data=b"abcd", total_size=4)
