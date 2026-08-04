from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from publishing.youtube_visibility_oauth_adapter import (
    OAuthCredentialValues,
    YouTubeVisibilityAdapterError,
    YouTubeVisibilityOAuthAdapter,
)


@dataclass
class Response:
    payload: dict
    status: int = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class Opener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return self.responses.pop(0)


def _adapter(opener):
    return YouTubeVisibilityOAuthAdapter(
        credentials=OAuthCredentialValues("client", "secret", "refresh"),
        opener=opener,
    )


def test_updates_and_verifies_visibility_with_one_ephemeral_token():
    opener = Opener([
        Response({"access_token": "access"}),
        Response({"id": "video-1", "status": {"privacyStatus": "public"}}),
        Response({"items": [{"id": "video-1", "status": {"privacyStatus": "public"}}]}),
    ])
    adapter = _adapter(opener)
    assert adapter.update_visibility("video-1", "public")["privacy_status"] == "public"
    assert adapter.verify_visibility("video-1")["privacy_status"] == "public"
    assert len(opener.requests) == 3
    assert opener.requests[1][0].get_method() == "PUT"
    assert opener.requests[2][0].get_method() == "GET"
    assert b'"privacyStatus":"public"' in opener.requests[1][0].data
    assert opener.requests[1][0].headers["Authorization"] == "Bearer access"
    adapter.clear_ephemeral_token()


def test_rejects_missing_credentials():
    with pytest.raises(YouTubeVisibilityAdapterError):
        YouTubeVisibilityOAuthAdapter(credentials=OAuthCredentialValues("", "x", "y"))


def test_rejects_unsupported_visibility_without_network():
    opener = Opener([])
    with pytest.raises(YouTubeVisibilityAdapterError):
        _adapter(opener).update_visibility("video-1", "scheduled")
    assert opener.requests == []


def test_rejects_http_failure_without_exposing_secret_values():
    opener = Opener([Response({"error": "bad"}, status=401)])
    with pytest.raises(YouTubeVisibilityAdapterError) as caught:
        _adapter(opener).verify_visibility("video-1")
    message = str(caught.value)
    assert "401" in message
    assert "client" not in message
    assert "secret" not in message
    assert "refresh" not in message


def test_requires_exact_single_video_identity():
    opener = Opener([
        Response({"access_token": "access"}),
        Response({"items": []}),
    ])
    with pytest.raises(YouTubeVisibilityAdapterError):
        _adapter(opener).verify_visibility("video-1")


def test_access_token_response_must_be_complete():
    opener = Opener([Response({})])
    with pytest.raises(YouTubeVisibilityAdapterError):
        _adapter(opener).verify_visibility("video-1")
