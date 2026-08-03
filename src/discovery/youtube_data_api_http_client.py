"""
FOOTBALL-SHORTS-AI-0055B
YOUTUBE DATA API HTTP CLIENT AND SECRET RESOLUTION

Concrete metadata-only YouTube Data API v3 client. The API key is resolved from
an injected secret source for each request session, never returned, logged or
persisted. Video download, acquisition, rendering and publishing are out of scope.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence

from discovery.youtube_discovery_provider import YouTubeDataApiClient


class YouTubeDataApiHttpError(RuntimeError):
    """Raised when controlled YouTube metadata access fails."""


class SecretTextResolver(Protocol):
    def resolve_text(self, secret_name: str) -> str:
        ...


OpenUrl = Callable[..., object]
Sleep = Callable[[float], None]


@dataclass(frozen=True)
class YouTubeDataApiHttpPolicy:
    enabled: bool = False
    network_enabled: bool = False
    secret_resolution_enabled: bool = False
    api_key_secret_name: str = "YOUTUBE_DATA_API_KEY"
    base_url: str = "https://www.googleapis.com/youtube/v3"
    timeout_seconds: float = 10.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    metadata_only: bool = True
    download_enabled: bool = False
    acquisition_enabled: bool = False
    publishing_enabled: bool = False

    def validate(self) -> None:
        if self.enabled and not (
            self.network_enabled and self.secret_resolution_enabled
        ):
            raise YouTubeDataApiHttpError(
                "enabled client requires network and secret resolution"
            )
        if not self.api_key_secret_name.strip():
            raise YouTubeDataApiHttpError("api_key_secret_name is required")
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise YouTubeDataApiHttpError("base_url must be absolute HTTPS")
        if not 0.1 <= self.timeout_seconds <= 60:
            raise YouTubeDataApiHttpError("timeout_seconds is outside limits")
        if not 1 <= self.max_attempts <= 5:
            raise YouTubeDataApiHttpError("max_attempts is outside limits")
        if not 0 <= self.retry_backoff_seconds <= 10:
            raise YouTubeDataApiHttpError("retry_backoff_seconds is outside limits")
        if not self.metadata_only:
            raise YouTubeDataApiHttpError("client must remain metadata-only")
        if self.download_enabled or self.acquisition_enabled or self.publishing_enabled:
            raise YouTubeDataApiHttpError("media mutation capabilities are forbidden")


class YouTubeDataApiHttpClient(YouTubeDataApiClient):
    """Controlled urllib-based implementation of the 0055A client protocol."""

    def __init__(
        self,
        *,
        secret_resolver: SecretTextResolver,
        policy: YouTubeDataApiHttpPolicy,
        open_url: OpenUrl = urllib.request.urlopen,
        sleep: Sleep = time.sleep,
    ) -> None:
        policy.validate()
        self._secret_resolver = secret_resolver
        self._policy = policy
        self._open_url = open_url
        self._sleep = sleep

    def search_videos(
        self,
        *,
        query: str,
        max_results: int,
        region_code: str,
        relevance_language: str,
        video_duration: str,
        video_embeddable: bool,
        safe_search: str,
    ) -> Sequence[Mapping[str, object]]:
        payload = self._request_json(
            "search",
            {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": str(max_results),
                "regionCode": region_code,
                "relevanceLanguage": relevance_language,
                "videoDuration": video_duration,
                "videoEmbeddable": "true" if video_embeddable else "false",
                "safeSearch": safe_search,
            },
        )
        return _items(payload)

    def list_videos(
        self,
        *,
        video_ids: Sequence[str],
    ) -> Sequence[Mapping[str, object]]:
        normalized = tuple(dict.fromkeys(value.strip() for value in video_ids if value.strip()))
        if not normalized:
            return ()
        if len(normalized) > 50:
            raise YouTubeDataApiHttpError("videos.list accepts at most 50 IDs")
        payload = self._request_json(
            "videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(normalized),
                "maxResults": str(len(normalized)),
            },
        )
        return _items(payload)

    def _request_json(
        self,
        resource: str,
        parameters: Mapping[str, str],
    ) -> Mapping[str, object]:
        if not self._policy.enabled:
            raise YouTubeDataApiHttpError("YouTube Data API HTTP client is not activated")

        api_key = self._secret_resolver.resolve_text(
            self._policy.api_key_secret_name
        ).strip()
        if not api_key:
            raise YouTubeDataApiHttpError("YouTube Data API key is unavailable")

        query = urllib.parse.urlencode({**parameters, "key": api_key})
        url = f"{self._policy.base_url.rstrip('/')}/{resource}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "football-shorts-ai/0055B",
            },
            method="GET",
        )

        last_error: Exception | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                with self._open_url(
                    request,
                    timeout=self._policy.timeout_seconds,
                ) as response:
                    status = int(getattr(response, "status", 200))
                    body = response.read()
                if status != 200:
                    raise YouTubeDataApiHttpError(
                        f"YouTube Data API returned HTTP {status}"
                    )
                return _decode_json(body)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
            except YouTubeDataApiHttpError:
                raise

            if attempt < self._policy.max_attempts:
                self._sleep(self._policy.retry_backoff_seconds * attempt)

        error_name = type(last_error).__name__ if last_error is not None else "UnknownError"
        raise YouTubeDataApiHttpError(
            f"YouTube Data API request failed after controlled retries: {error_name}"
        ) from last_error


def _decode_json(body: object) -> Mapping[str, object]:
    if not isinstance(body, (bytes, bytearray)):
        raise YouTubeDataApiHttpError("YouTube response body must be bytes")
    try:
        payload = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise YouTubeDataApiHttpError("YouTube response is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise YouTubeDataApiHttpError("YouTube response root must be an object")
    if "error" in payload:
        raise YouTubeDataApiHttpError("YouTube Data API returned an error payload")
    return payload


def _items(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = payload.get("items")
    if not isinstance(value, list):
        raise YouTubeDataApiHttpError("YouTube response items must be an array")
    if any(not isinstance(item, Mapping) for item in value):
        raise YouTubeDataApiHttpError("YouTube response contains an invalid item")
    return tuple(value)


__all__ = [
    "SecretTextResolver",
    "YouTubeDataApiHttpClient",
    "YouTubeDataApiHttpError",
    "YouTubeDataApiHttpPolicy",
]
