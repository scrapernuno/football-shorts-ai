"""FOOTBALL-SHORTS-AI-0062B — concrete OAuth YouTube visibility adapter.

Exchanges a refresh token ephemerally, reads the current video status, performs one
``videos.update(part=status)`` request and verifies the resulting privacy status.
No token, credential or HTTP response is persisted.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Mapping


class YouTubeVisibilityAdapterError(RuntimeError):
    pass


SUPPORTED_VISIBILITY = {"private", "unlisted", "public"}
TOKEN_URL = "https://oauth2.googleapis.com/token"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass(frozen=True)
class OAuthCredentialValues:
    client_id: str
    client_secret: str
    refresh_token: str

    def validate(self) -> None:
        if not self.client_id.strip() or not self.client_secret.strip() or not self.refresh_token.strip():
            raise YouTubeVisibilityAdapterError("complete OAuth credential values are required")


class YouTubeVisibilityOAuthAdapter:
    def __init__(
        self,
        *,
        credentials: OAuthCredentialValues,
        opener: Callable[..., object] = urllib.request.urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        credentials.validate()
        if timeout_seconds <= 0:
            raise YouTubeVisibilityAdapterError("timeout must be positive")
        self._credentials = credentials
        self._opener = opener
        self._timeout = timeout_seconds
        self._access_token: str | None = None

    def _request_json(self, request: urllib.request.Request) -> Mapping[str, object]:
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read()
        except Exception as exc:
            raise YouTubeVisibilityAdapterError(f"YouTube HTTP request failed: {type(exc).__name__}") from exc
        if status < 200 or status >= 300:
            raise YouTubeVisibilityAdapterError(f"YouTube HTTP request failed with status {status}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise YouTubeVisibilityAdapterError("YouTube returned invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise YouTubeVisibilityAdapterError("YouTube response must be an object")
        return payload

    def _token(self) -> str:
        if self._access_token:
            return self._access_token
        body = urllib.parse.urlencode(
            {
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "refresh_token": self._credentials.refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            TOKEN_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        payload = self._request_json(request)
        token = str(payload.get("access_token", "")).strip()
        if not token:
            raise YouTubeVisibilityAdapterError("OAuth response did not contain an access token")
        self._access_token = token
        return token

    def _authorized_request(self, url: str, *, method: str, payload: Mapping[str, object] | None = None) -> Mapping[str, object]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Authorization": f"Bearer {self._token()}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        return self._request_json(urllib.request.Request(url, data=data, method=method, headers=headers))

    @staticmethod
    def _normalize_video(payload: Mapping[str, object], expected_video_id: str) -> dict[str, object]:
        items = payload.get("items")
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], Mapping):
            raise YouTubeVisibilityAdapterError("YouTube video lookup did not return exactly one video")
        item = items[0]
        video_id = str(item.get("id", ""))
        status = item.get("status")
        if video_id != expected_video_id or not isinstance(status, Mapping):
            raise YouTubeVisibilityAdapterError("YouTube video response identity is invalid")
        privacy = str(status.get("privacyStatus", ""))
        if privacy not in SUPPORTED_VISIBILITY:
            raise YouTubeVisibilityAdapterError("YouTube returned unsupported privacy status")
        return {"youtube_video_id": video_id, "privacy_status": privacy}

    def verify_visibility(self, youtube_video_id: str) -> Mapping[str, object]:
        video_id = youtube_video_id.strip()
        if not video_id:
            raise YouTubeVisibilityAdapterError("youtube_video_id is required")
        query = urllib.parse.urlencode({"part": "status", "id": video_id})
        payload = self._authorized_request(f"{VIDEOS_URL}?{query}", method="GET")
        return self._normalize_video(payload, video_id)

    def update_visibility(self, youtube_video_id: str, target_visibility: str) -> Mapping[str, object]:
        video_id = youtube_video_id.strip()
        if not video_id:
            raise YouTubeVisibilityAdapterError("youtube_video_id is required")
        if target_visibility not in SUPPORTED_VISIBILITY:
            raise YouTubeVisibilityAdapterError("unsupported target visibility")
        query = urllib.parse.urlencode({"part": "status"})
        payload = self._authorized_request(
            f"{VIDEOS_URL}?{query}",
            method="PUT",
            payload={"id": video_id, "status": {"privacyStatus": target_visibility}},
        )
        item = payload
        if "items" not in payload:
            item = {"items": [payload]}
        return self._normalize_video(item, video_id)

    def clear_ephemeral_token(self) -> None:
        self._access_token = None


__all__ = [
    "OAuthCredentialValues",
    "SUPPORTED_VISIBILITY",
    "YouTubeVisibilityAdapterError",
    "YouTubeVisibilityOAuthAdapter",
]
