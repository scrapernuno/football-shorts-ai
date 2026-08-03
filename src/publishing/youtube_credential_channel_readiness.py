"""
FOOTBALL-SHORTS-AI-0053E
YOUTUBE CREDENTIAL AND CHANNEL READINESS CONTRACT

Defines a fail-closed, secret-neutral readiness boundary for future YouTube
publisher activation. This module validates declared credential metadata,
required OAuth scopes and channel identity evidence without reading secrets,
calling Google APIs, authenticating, uploading, scheduling or publishing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping


YOUTUBE_PLATFORM = "youtube_shorts"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
SUPPORTED_CREDENTIAL_TYPES = {"oauth2_refresh_token"}
SUPPORTED_CHANNEL_STATUS = {"active", "suspended", "unknown"}
MAX_EVIDENCE_AGE_SECONDS = 24 * 60 * 60
_CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


class YouTubeCredentialChannelReadinessError(ValueError):
    """Raised when YouTube credential or channel evidence is unsafe."""


@dataclass(frozen=True)
class YouTubeCredentialDeclaration:
    credential_type: str
    client_id_reference: str
    client_secret_reference: str
    refresh_token_reference: str
    scopes: tuple[str, ...]
    secret_values_loaded: bool = False

    def validate(self) -> None:
        if self.credential_type not in SUPPORTED_CREDENTIAL_TYPES:
            raise YouTubeCredentialChannelReadinessError(
                "unsupported YouTube credential type"
            )
        for name, value in {
            "client_id_reference": self.client_id_reference,
            "client_secret_reference": self.client_secret_reference,
            "refresh_token_reference": self.refresh_token_reference,
        }.items():
            if not value.strip():
                raise YouTubeCredentialChannelReadinessError(f"{name} is required")
            if _looks_like_secret_value(value):
                raise YouTubeCredentialChannelReadinessError(
                    f"{name} must be a secret reference, not a secret value"
                )
        if not self.scopes:
            raise YouTubeCredentialChannelReadinessError("OAuth scopes are required")
        if len(set(self.scopes)) != len(self.scopes):
            raise YouTubeCredentialChannelReadinessError("OAuth scopes must be unique")
        if any(not item.startswith("https://www.googleapis.com/auth/") for item in self.scopes):
            raise YouTubeCredentialChannelReadinessError("invalid Google OAuth scope")
        if self.secret_values_loaded:
            raise YouTubeCredentialChannelReadinessError(
                "0053E must not load credential secret values"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "credential_type": self.credential_type,
            "client_id_reference": self.client_id_reference,
            "client_secret_reference": self.client_secret_reference,
            "refresh_token_reference": self.refresh_token_reference,
            "scopes": list(self.scopes),
            "secret_values_loaded": False,
        }


@dataclass(frozen=True)
class YouTubeChannelDeclaration:
    channel_id: str
    channel_title: str
    channel_handle: str | None
    owner_reference: str
    status: str
    uploads_enabled: bool
    shorts_eligible: bool
    made_for_kids: bool | None
    verified_at: str
    verification_reference: str
    network_verified: bool = False

    def validate(self) -> None:
        if not _CHANNEL_ID_RE.fullmatch(self.channel_id):
            raise YouTubeCredentialChannelReadinessError("invalid YouTube channel_id")
        if not self.channel_title.strip():
            raise YouTubeCredentialChannelReadinessError("channel_title is required")
        if self.channel_handle is not None and not self.channel_handle.startswith("@"):
            raise YouTubeCredentialChannelReadinessError("channel_handle must start with @")
        if not self.owner_reference.strip():
            raise YouTubeCredentialChannelReadinessError("owner_reference is required")
        if self.status not in SUPPORTED_CHANNEL_STATUS:
            raise YouTubeCredentialChannelReadinessError("unsupported channel status")
        if not self.verification_reference.strip():
            raise YouTubeCredentialChannelReadinessError(
                "verification_reference is required"
            )
        _parse_utc_timestamp(self.verified_at)
        if self.network_verified:
            raise YouTubeCredentialChannelReadinessError(
                "0053E does not perform network channel verification"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "channel_handle": self.channel_handle,
            "owner_reference": self.owner_reference,
            "status": self.status,
            "uploads_enabled": self.uploads_enabled,
            "shorts_eligible": self.shorts_eligible,
            "made_for_kids": self.made_for_kids,
            "verified_at": self.verified_at,
            "verification_reference": self.verification_reference,
            "network_verified": False,
        }


@dataclass(frozen=True)
class YouTubeCredentialChannelReadiness:
    schema: str
    readiness_id: str
    platform: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    credential_sha256: str
    channel_sha256: str
    evaluated_at: str
    execution_enabled: bool = False
    auto_publish: bool = False
    network_accessed: bool = False
    secret_values_loaded: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-credential-channel-readiness.v1":
            raise YouTubeCredentialChannelReadinessError("unsupported readiness schema")
        if not self.readiness_id.startswith("YTREADY-"):
            raise YouTubeCredentialChannelReadinessError("invalid readiness_id")
        if self.platform != YOUTUBE_PLATFORM:
            raise YouTubeCredentialChannelReadinessError("invalid platform")
        if self.status not in {"READY_FOR_CREDENTIAL_ACTIVATION", "BLOCKED"}:
            raise YouTubeCredentialChannelReadinessError("unsupported readiness status")
        if set(self.checks.values()) - {True, False}:
            raise YouTubeCredentialChannelReadinessError("readiness checks must be boolean")
        if self.status == "READY_FOR_CREDENTIAL_ACTIVATION" and self.blockers:
            raise YouTubeCredentialChannelReadinessError("ready result cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise YouTubeCredentialChannelReadinessError("blocked result requires blockers")
        if not _is_sha256(self.credential_sha256) or not _is_sha256(self.channel_sha256):
            raise YouTubeCredentialChannelReadinessError("invalid evidence checksum")
        _parse_utc_timestamp(self.evaluated_at)
        if self.execution_enabled or self.auto_publish:
            raise YouTubeCredentialChannelReadinessError(
                "publication execution and auto-publish must remain disabled"
            )
        if self.network_accessed or self.secret_values_loaded:
            raise YouTubeCredentialChannelReadinessError(
                "0053E cannot access network or secret values"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "readiness_id": self.readiness_id,
            "platform": self.platform,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "credential_sha256": self.credential_sha256,
            "channel_sha256": self.channel_sha256,
            "evaluated_at": self.evaluated_at,
            "execution_enabled": False,
            "auto_publish": False,
            "network_accessed": False,
            "secret_values_loaded": False,
        }


def evaluate_youtube_credential_channel_readiness(
    *,
    credential: YouTubeCredentialDeclaration,
    channel: YouTubeChannelDeclaration,
    evaluated_at: str,
) -> YouTubeCredentialChannelReadiness:
    """Evaluate offline readiness without resolving or reading credentials."""

    credential.validate()
    channel.validate()
    now = _parse_utc_timestamp(evaluated_at)
    verified = _parse_utc_timestamp(channel.verified_at)

    checks: dict[str, bool] = {
        "credential_type_supported": (
            credential.credential_type in SUPPORTED_CREDENTIAL_TYPES
        ),
        "client_id_reference_present": bool(credential.client_id_reference.strip()),
        "client_secret_reference_present": bool(
            credential.client_secret_reference.strip()
        ),
        "refresh_token_reference_present": bool(
            credential.refresh_token_reference.strip()
        ),
        "youtube_upload_scope_declared": YOUTUBE_UPLOAD_SCOPE in credential.scopes,
        "youtube_readonly_scope_declared": YOUTUBE_READONLY_SCOPE in credential.scopes,
        "secret_values_not_loaded": not credential.secret_values_loaded,
        "channel_id_valid": bool(_CHANNEL_ID_RE.fullmatch(channel.channel_id)),
        "channel_active": channel.status == "active",
        "uploads_enabled": channel.uploads_enabled,
        "shorts_eligible": channel.shorts_eligible,
        "channel_owner_declared": bool(channel.owner_reference.strip()),
        "channel_evidence_not_future_dated": verified <= now,
        "channel_evidence_fresh": (
            timedelta(0) <= now - verified <= timedelta(seconds=MAX_EVIDENCE_AGE_SECONDS)
        ),
        "network_not_accessed": not channel.network_verified,
        "execution_disabled": True,
        "auto_publish_disabled": True,
    }

    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    credential_sha256 = canonical_sha256(credential.to_dict())
    channel_sha256 = canonical_sha256(channel.to_dict())
    identity = {
        "credential_sha256": credential_sha256,
        "channel_sha256": channel_sha256,
        "evaluated_at": _format_utc(now),
        "checks": checks,
    }

    result = YouTubeCredentialChannelReadiness(
        schema="football-shorts-ai.youtube-credential-channel-readiness.v1",
        readiness_id=f"YTREADY-{canonical_sha256(identity)[:20].upper()}",
        platform=YOUTUBE_PLATFORM,
        status="READY_FOR_CREDENTIAL_ACTIVATION" if not blockers else "BLOCKED",
        checks=checks,
        blockers=blockers,
        credential_sha256=credential_sha256,
        channel_sha256=channel_sha256,
        evaluated_at=_format_utc(now),
        execution_enabled=False,
        auto_publish=False,
        network_accessed=False,
        secret_values_loaded=False,
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _looks_like_secret_value(value: str) -> bool:
    lowered = value.strip().lower()
    allowed_prefixes = (
        "secret://",
        "env://",
        "github-actions-secret://",
        "vault://",
        "reference://",
    )
    return not lowered.startswith(allowed_prefixes)


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _parse_utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise YouTubeCredentialChannelReadinessError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise YouTubeCredentialChannelReadinessError(
            "timestamp must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise YouTubeCredentialChannelReadinessError("timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "MAX_EVIDENCE_AGE_SECONDS",
    "SUPPORTED_CHANNEL_STATUS",
    "SUPPORTED_CREDENTIAL_TYPES",
    "YOUTUBE_PLATFORM",
    "YOUTUBE_READONLY_SCOPE",
    "YOUTUBE_UPLOAD_SCOPE",
    "YouTubeChannelDeclaration",
    "YouTubeCredentialChannelReadiness",
    "YouTubeCredentialChannelReadinessError",
    "YouTubeCredentialDeclaration",
    "canonical_sha256",
    "evaluate_youtube_credential_channel_readiness",
]
