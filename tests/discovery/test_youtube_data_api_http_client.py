from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse

import pytest

from discovery.youtube_data_api_http_client import (
    YouTubeDataApiHttpClient,
    YouTubeDataApiHttpError,
    YouTubeDataApiHttpPolicy,
)


class SecretResolver:
    def __init__(self, value: str = "test-secret-key") -> None:
        self.value = value
        self.calls: list[str] = []

    def resolve_text(self, secret_name: str) -> str:
        self.calls.append(secret_name)
        return self.value


class Response(io.BytesIO):
    def __init__(self, payload: object, status: int = 200) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
        return False


def enabled_policy(**changes) -> YouTubeDataApiHttpPolicy:
    values = {
        "enabled": True,
        "network_enabled": True,
        "secret_resolution_enabled": True,
        "timeout_seconds": 4,
        "max_attempts": 3,
        "retry_backoff_seconds": 0,
    }
    values.update(changes)
    return YouTubeDataApiHttpPolicy(**values)


def test_disabled_client_fails_before_secret_or_network() -> None:
    resolver = SecretResolver()
    calls = []
    client = YouTubeDataApiHttpClient(
        secret_resolver=resolver,
        policy=YouTubeDataApiHttpPolicy(),
        open_url=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    with pytest.raises(YouTubeDataApiHttpError, match="not activated"):
        client.search_videos(
            query="football",
            max_results=5,
            region_code="PT",
            relevance_language="pt",
            video_duration="short",
            video_embeddable=True,
            safe_search="moderate",
        )

    assert resolver.calls == []
    assert calls == []


def test_search_builds_governed_youtube_request() -> None:
    resolver = SecretResolver()
    captured = []

    def open_url(request, *, timeout):
        captured.append((request, timeout))
        return Response({"items": [{"id": {"videoId": "abc123"}}]})

    client = YouTubeDataApiHttpClient(
        secret_resolver=resolver,
        policy=enabled_policy(),
        open_url=open_url,
    )
    items = client.search_videos(
        query="Champions League",
        max_results=12,
        region_code="PT",
        relevance_language="pt",
        video_duration="short",
        video_embeddable=True,
        safe_search="moderate",
    )

    assert items[0]["id"]["videoId"] == "abc123"
    request, timeout = captured[0]
    parsed = urllib.parse.urlparse(request.full_url)
    query = urllib.parse.parse_qs(parsed.query)
    assert parsed.path.endswith("/search")
    assert query["part"] == ["snippet"]
    assert query["type"] == ["video"]
    assert query["videoEmbeddable"] == ["true"]
    assert query["key"] == ["test-secret-key"]
    assert timeout == 4
    assert resolver.calls == ["YOUTUBE_DATA_API_KEY"]


def test_videos_list_requests_metadata_only() -> None:
    captured = []

    def open_url(request, *, timeout):
        captured.append(request.full_url)
        return Response({"items": [{"id": "one"}, {"id": "two"}]})

    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver(),
        policy=enabled_policy(),
        open_url=open_url,
    )
    result = client.list_videos(video_ids=("one", "two", "one"))

    assert len(result) == 2
    query = urllib.parse.parse_qs(urllib.parse.urlparse(captured[0]).query)
    assert query["id"] == ["one,two"]
    assert query["part"] == ["snippet,contentDetails,statistics,status"]


def test_retries_transient_failure_without_disclosing_secret() -> None:
    attempts = 0
    sleeps = []

    def open_url(request, *, timeout):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.URLError("temporary")
        return Response({"items": []})

    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver("highly-sensitive-key"),
        policy=enabled_policy(),
        open_url=open_url,
        sleep=sleeps.append,
    )
    assert client.list_videos(video_ids=("one",)) == ()
    assert attempts == 3
    assert len(sleeps) == 2


def test_permanent_failure_is_redacted() -> None:
    def open_url(request, *, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "forbidden",
            hdrs=None,
            fp=None,
        )

    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver("never-print-this-key"),
        policy=enabled_policy(),
        open_url=open_url,
    )
    with pytest.raises(YouTubeDataApiHttpError) as captured:
        client.list_videos(video_ids=("one",))

    assert "never-print-this-key" not in str(captured.value)


def test_empty_secret_fails_closed_without_network() -> None:
    calls = []
    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver("   "),
        policy=enabled_policy(),
        open_url=lambda *args, **kwargs: calls.append(1),
    )
    with pytest.raises(YouTubeDataApiHttpError, match="unavailable"):
        client.list_videos(video_ids=("one",))
    assert calls == []


def test_rejects_invalid_json_and_error_payload() -> None:
    class BadResponse(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): return False

    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver(),
        policy=enabled_policy(),
        open_url=lambda *args, **kwargs: BadResponse(b"not-json"),
    )
    with pytest.raises(YouTubeDataApiHttpError, match="valid JSON"):
        client.list_videos(video_ids=("one",))

    client = YouTubeDataApiHttpClient(
        secret_resolver=SecretResolver(),
        policy=enabled_policy(),
        open_url=lambda *args, **kwargs: Response({"error": {"code": 403}}),
    )
    with pytest.raises(YouTubeDataApiHttpError, match="error payload"):
        client.list_videos(video_ids=("one",))


def test_policy_forbids_media_and_publication_capabilities() -> None:
    for field in ("download_enabled", "acquisition_enabled", "publishing_enabled"):
        with pytest.raises(YouTubeDataApiHttpError, match="forbidden"):
            enabled_policy(**{field: True}).validate()
