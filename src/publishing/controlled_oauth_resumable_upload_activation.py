"""FOOTBALL-SHORTS-AI-0061H — controlled OAuth resolution and upload activation.

Secret values are resolved only at explicit execution time. Tokens and resumable
session URIs are never persisted. Upload remains single-use and publication is not
performed by this module.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from publishing.controlled_youtube_resumable_upload import (
    YouTubeUploadActivationPolicy,
    execute_controlled_youtube_upload,
)


class ControlledOAuthUploadActivationError(ValueError):
    pass


@dataclass(frozen=True)
class OAuthSecretMaterial:
    client_id: str
    client_secret: str
    refresh_token: str

    def validate(self) -> None:
        if not self.client_id.strip() or not self.client_secret.strip() or not self.refresh_token.strip():
            raise ControlledOAuthUploadActivationError("OAuth secret material is incomplete")


class LocalArtifactSource:
    def open_binary(self, relative_path: str):
        path = Path(relative_path)
        if not path.is_file():
            raise ControlledOAuthUploadActivationError(f"video artifact missing: {relative_path}")
        return path.open("rb")


class GoogleResumableUploadClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SESSION_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"

    def __init__(self, *, secrets: OAuthSecretMaterial, opener: Callable[..., object] = urllib.request.urlopen) -> None:
        secrets.validate()
        self._secrets = secrets
        self._opener = opener
        self._access_token: str | None = None

    def _token(self) -> str:
        if self._access_token:
            return self._access_token
        body = urllib.parse.urlencode({
            "client_id": self._secrets.client_id,
            "client_secret": self._secrets.client_secret,
            "refresh_token": self._secrets.refresh_token,
            "grant_type": "refresh_token",
        }).encode()
        request = urllib.request.Request(self.TOKEN_URL, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
        payload = self._json_response(request)
        token = str(payload.get("access_token", ""))
        if not token:
            raise ControlledOAuthUploadActivationError("OAuth token response did not contain access_token")
        self._access_token = token
        return token

    def create_session(self, payload: Mapping[str, object]) -> str:
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ControlledOAuthUploadActivationError("upload metadata is invalid")
        body = json.dumps({
            "snippet": {
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "tags": list(metadata.get("tags", ())),
                "categoryId": str(metadata.get("category_id", "17")),
            },
            "status": {
                "privacyStatus": metadata.get("privacy_status", "private"),
                "selfDeclaredMadeForKids": bool(metadata.get("made_for_kids", False)),
            },
        }).encode()
        request = urllib.request.Request(
            self.SESSION_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(payload.get("artifact", {}).get("size_bytes", "")),
            },
        )
        response = self._opener(request, timeout=60)
        location = str(response.headers.get("Location", ""))
        if not location.startswith("https://"):
            raise ControlledOAuthUploadActivationError("YouTube did not return a resumable session URI")
        return location

    def upload_chunk(self, *, session_uri: str, offset: int, data: bytes, total_size: int) -> Mapping[str, object]:
        end = offset + len(data) - 1
        request = urllib.request.Request(
            session_uri,
            data=data,
            method="PUT",
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": "video/mp4",
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {offset}-{end}/{total_size}",
            },
        )
        try:
            response = self._opener(request, timeout=180)
            payload = json.loads(response.read().decode() or "{}")
            video_id = str(payload.get("id", ""))
            if not video_id:
                raise ControlledOAuthUploadActivationError("completed upload response did not contain video id")
            return {"accepted_offset": offset, "next_offset": offset + len(data), "complete": True, "youtube_video_id": video_id}
        except urllib.error.HTTPError as exc:
            if exc.code != 308:
                raise ControlledOAuthUploadActivationError(f"YouTube chunk upload failed with HTTP {exc.code}") from exc
            range_header = str(exc.headers.get("Range", ""))
            next_offset = offset + len(data)
            if range_header.startswith("bytes=0-"):
                next_offset = int(range_header.split("-")[-1]) + 1
            return {"accepted_offset": offset, "next_offset": next_offset, "complete": False, "youtube_video_id": None}

    def _json_response(self, request: urllib.request.Request) -> Mapping[str, object]:
        try:
            response = self._opener(request, timeout=60)
            payload = json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            raise ControlledOAuthUploadActivationError(f"OAuth request failed with HTTP {exc.code}") from exc
        if not isinstance(payload, Mapping):
            raise ControlledOAuthUploadActivationError("OAuth response is invalid")
        return payload


def resolve_oauth_secrets(*, binding: Mapping[str, object], environ: Mapping[str, str] | None = None) -> OAuthSecretMaterial:
    env = os.environ if environ is None else environ
    if binding.get("binding_state") != "ready_for_manual_dispatch" or binding.get("manual_dispatch_allowed") is not True:
        raise ControlledOAuthUploadActivationError("workflow binding is not ready")
    names = (
        str(binding.get("client_id_secret_name", "")),
        str(binding.get("client_secret_secret_name", "")),
        str(binding.get("refresh_token_secret_name", "")),
    )
    if not all(names):
        raise ControlledOAuthUploadActivationError("OAuth secret names are incomplete")
    secrets = OAuthSecretMaterial(*(str(env.get(name, "")) for name in names))
    secrets.validate()
    return secrets


def execute_authorized_youtube_upload_once(*, binding: Mapping[str, object], design, explicit_execute: bool, environ: Mapping[str, str] | None = None, opener: Callable[..., object] = urllib.request.urlopen):
    if not explicit_execute:
        raise ControlledOAuthUploadActivationError("explicit upload execution confirmation required")
    secrets = resolve_oauth_secrets(binding=binding, environ=environ)
    client = GoogleResumableUploadClient(secrets=secrets, opener=opener)
    policy = YouTubeUploadActivationPolicy(
        artifact_read_enabled=True,
        session_creation_enabled=True,
        chunk_transfer_enabled=True,
        network_enabled=True,
        upload_enabled=True,
        publication_enabled=False,
        auto_publish=False,
    )
    result = execute_controlled_youtube_upload(
        design=design,
        policy=policy,
        artifact_source=LocalArtifactSource(),
        upload_client=client,
    )
    if result.status != "UPLOADED":
        raise ControlledOAuthUploadActivationError("controlled upload did not complete")
    return result


__all__ = [
    "ControlledOAuthUploadActivationError",
    "GoogleResumableUploadClient",
    "LocalArtifactSource",
    "OAuthSecretMaterial",
    "execute_authorized_youtube_upload_once",
    "resolve_oauth_secrets",
]
