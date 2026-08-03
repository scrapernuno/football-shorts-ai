"""
FOOTBALL-SHORTS-AI-0053G
CONTROLLED YOUTUBE OAUTH AND CHANNEL VERIFICATION IMPLEMENTATION

Executes the 0053F design only through injected secret and YouTube clients.
The default policy is fail-closed. No concrete secret backend, HTTP client,
Google SDK, upload, scheduling or publication implementation is provided here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol, runtime_checkable

from publishing.youtube_oauth_channel_verification_design import (
    SecretReferenceResolver,
    YouTubeChannelVerifier,
    YouTubeOAuthChannelVerificationDesign,
)


class ControlledYouTubeVerificationError(ValueError):
    """Raised when controlled OAuth/channel verification cannot proceed safely."""


@dataclass(frozen=True)
class YouTubeVerificationActivationPolicy:
    secret_resolution_enabled: bool = False
    oauth_exchange_enabled: bool = False
    channel_verification_enabled: bool = False
    network_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.publication_enabled:
            raise ControlledYouTubeVerificationError(
                "0053G cannot enable publication"
            )
        if self.auto_publish:
            raise ControlledYouTubeVerificationError(
                "automatic publishing must remain disabled"
            )
        enabled = (
            self.secret_resolution_enabled,
            self.oauth_exchange_enabled,
            self.channel_verification_enabled,
        )
        if any(enabled) and not self.network_enabled:
            raise ControlledYouTubeVerificationError(
                "controlled verification requires explicit network activation"
            )
        if self.oauth_exchange_enabled and not self.secret_resolution_enabled:
            raise ControlledYouTubeVerificationError(
                "OAuth exchange requires secret resolution"
            )
        if self.channel_verification_enabled and not self.oauth_exchange_enabled:
            raise ControlledYouTubeVerificationError(
                "channel verification requires OAuth exchange"
            )


@dataclass(frozen=True)
class EphemeralOAuthCredentials:
    client_id: str
    client_secret: str
    refresh_token: str

    def validate(self) -> None:
        if not self.client_id:
            raise ControlledYouTubeVerificationError("resolved client_id is empty")
        if not self.client_secret:
            raise ControlledYouTubeVerificationError("resolved client_secret is empty")
        if not self.refresh_token:
            raise ControlledYouTubeVerificationError("resolved refresh_token is empty")

    def redacted_fingerprint(self) -> str:
        self.validate()
        return canonical_sha256(
            {
                "client_id_sha256": _sha256_text(self.client_id),
                "client_secret_sha256": _sha256_text(self.client_secret),
                "refresh_token_sha256": _sha256_text(self.refresh_token),
            }
        )


@dataclass(frozen=True)
class OAuthAccessToken:
    access_token: str
    token_type: str
    expires_in_seconds: int
    scopes: tuple[str, ...]

    def validate(self) -> None:
        if not self.access_token:
            raise ControlledYouTubeVerificationError("access token is empty")
        if self.token_type.lower() != "bearer":
            raise ControlledYouTubeVerificationError("unsupported token type")
        if not isinstance(self.expires_in_seconds, int) or isinstance(
            self.expires_in_seconds, bool
        ):
            raise ControlledYouTubeVerificationError(
                "expires_in_seconds must be an integer"
            )
        if self.expires_in_seconds <= 0 or self.expires_in_seconds > 24 * 60 * 60:
            raise ControlledYouTubeVerificationError(
                "access token lifetime is outside the governed range"
            )
        if not self.scopes:
            raise ControlledYouTubeVerificationError("access token scopes are required")

    def redacted_fingerprint(self) -> str:
        self.validate()
        return canonical_sha256(
            {
                "access_token_sha256": _sha256_text(self.access_token),
                "token_type": self.token_type.lower(),
                "expires_in_seconds": self.expires_in_seconds,
                "scopes": sorted(self.scopes),
            }
        )


@runtime_checkable
class YouTubeOAuthClient(Protocol):
    """Injected boundary for exchanging a refresh token for an access token."""

    def exchange_refresh_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        scopes: tuple[str, ...],
    ) -> OAuthAccessToken:
        ...


@dataclass(frozen=True)
class VerifiedYouTubeChannel:
    channel_id: str
    channel_title: str
    owner_reference: str
    status: str
    uploads_enabled: bool
    shorts_eligible: bool

    def validate(self) -> None:
        if not self.channel_id.strip():
            raise ControlledYouTubeVerificationError("verified channel_id is required")
        if not self.channel_title.strip():
            raise ControlledYouTubeVerificationError(
                "verified channel_title is required"
            )
        if not self.owner_reference.strip():
            raise ControlledYouTubeVerificationError(
                "verified owner_reference is required"
            )
        if self.status not in {"active", "suspended", "unknown"}:
            raise ControlledYouTubeVerificationError(
                "unsupported verified channel status"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "owner_reference": self.owner_reference,
            "status": self.status,
            "uploads_enabled": self.uploads_enabled,
            "shorts_eligible": self.shorts_eligible,
        }


@dataclass(frozen=True)
class ControlledYouTubeVerificationResult:
    schema: str
    verification_id: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    design_id: str
    credential_fingerprint: str | None
    access_token_fingerprint: str | None
    verified_channel: VerifiedYouTubeChannel | None
    verified_at: str
    network_accessed: bool
    secret_values_ephemeral: bool = True
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-verification.v1":
            raise ControlledYouTubeVerificationError("unsupported result schema")
        if not self.verification_id.startswith("YTVERIFY-"):
            raise ControlledYouTubeVerificationError("invalid verification_id")
        if self.status not in {"VERIFIED", "BLOCKED", "NOT_ACTIVATED"}:
            raise ControlledYouTubeVerificationError("unsupported verification status")
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubeVerificationError("checks must be boolean")
        if self.status == "VERIFIED":
            if self.blockers or self.verified_channel is None:
                raise ControlledYouTubeVerificationError(
                    "verified result is internally inconsistent"
                )
        elif not self.blockers:
            raise ControlledYouTubeVerificationError(
                "non-verified result requires blockers"
            )
        if self.publication_enabled or self.auto_publish:
            raise ControlledYouTubeVerificationError(
                "publication and auto-publish must remain disabled"
            )
        if not self.secret_values_ephemeral:
            raise ControlledYouTubeVerificationError(
                "resolved secret values must remain ephemeral"
            )
        _parse_utc_timestamp(self.verified_at)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "verification_id": self.verification_id,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "design_id": self.design_id,
            "credential_fingerprint": self.credential_fingerprint,
            "access_token_fingerprint": self.access_token_fingerprint,
            "verified_channel": (
                self.verified_channel.to_dict()
                if self.verified_channel is not None
                else None
            ),
            "verified_at": self.verified_at,
            "network_accessed": self.network_accessed,
            "secret_values_ephemeral": True,
            "publication_enabled": False,
            "auto_publish": False,
        }


def execute_controlled_youtube_verification(
    *,
    design: YouTubeOAuthChannelVerificationDesign,
    policy: YouTubeVerificationActivationPolicy,
    resolver: SecretReferenceResolver | None,
    oauth_client: YouTubeOAuthClient | None,
    channel_verifier: YouTubeChannelVerifier | None,
    verified_at: str,
) -> ControlledYouTubeVerificationResult:
    """Execute the injected verification chain when every gate is explicit."""

    design.validate()
    policy.validate()
    now = _parse_utc_timestamp(verified_at)

    activated = all(
        (
            policy.secret_resolution_enabled,
            policy.oauth_exchange_enabled,
            policy.channel_verification_enabled,
            policy.network_enabled,
        )
    )

    if not activated:
        checks = {
            "design_ready": design.status == "DESIGN_READY",
            "secret_resolution_activated": policy.secret_resolution_enabled,
            "oauth_exchange_activated": policy.oauth_exchange_enabled,
            "channel_verification_activated": policy.channel_verification_enabled,
            "network_activated": policy.network_enabled,
            "publication_disabled": not policy.publication_enabled,
            "auto_publish_disabled": not policy.auto_publish,
        }
        return _build_result(
            design=design,
            status="NOT_ACTIVATED",
            checks=checks,
            credential_fingerprint=None,
            access_token_fingerprint=None,
            verified_channel=None,
            verified_at=now,
            network_accessed=False,
        )

    if design.status != "DESIGN_READY":
        raise ControlledYouTubeVerificationError(
            "blocked design cannot enter controlled execution"
        )
    if resolver is None or oauth_client is None or channel_verifier is None:
        raise ControlledYouTubeVerificationError(
            "resolver, OAuth client and channel verifier are required"
        )

    bindings = {item.logical_name: item for item in design.oauth_plan.bindings}
    credentials = EphemeralOAuthCredentials(
        client_id=resolver.resolve_reference(bindings["client_id"].reference),
        client_secret=resolver.resolve_reference(bindings["client_secret"].reference),
        refresh_token=resolver.resolve_reference(bindings["refresh_token"].reference),
    )
    credentials.validate()

    token = oauth_client.exchange_refresh_token(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        refresh_token=credentials.refresh_token,
        scopes=design.oauth_plan.required_scopes,
    )
    token.validate()

    raw_channel = channel_verifier.verify_channel(token.access_token)
    channel = _normalize_verified_channel(raw_channel)

    checks = {
        "design_ready": True,
        "credentials_resolved": True,
        "access_token_received": True,
        "required_scopes_present": set(design.oauth_plan.required_scopes).issubset(
            set(token.scopes)
        ),
        "channel_identity_matches": (
            channel.channel_id == design.channel_plan.expected_channel_id
        ),
        "owner_identity_matches": (
            channel.owner_reference == design.channel_plan.expected_owner_reference
        ),
        "channel_active": channel.status == "active",
        "uploads_enabled": channel.uploads_enabled,
        "shorts_eligible": channel.shorts_eligible,
        "publication_disabled": not policy.publication_enabled,
        "auto_publish_disabled": not policy.auto_publish,
    }

    status = "VERIFIED" if all(checks.values()) else "BLOCKED"
    return _build_result(
        design=design,
        status=status,
        checks=checks,
        credential_fingerprint=credentials.redacted_fingerprint(),
        access_token_fingerprint=token.redacted_fingerprint(),
        verified_channel=channel,
        verified_at=now,
        network_accessed=True,
    )


def _build_result(
    *,
    design: YouTubeOAuthChannelVerificationDesign,
    status: str,
    checks: Mapping[str, bool],
    credential_fingerprint: str | None,
    access_token_fingerprint: str | None,
    verified_channel: VerifiedYouTubeChannel | None,
    verified_at: datetime,
    network_accessed: bool,
) -> ControlledYouTubeVerificationResult:
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    evidence = {
        "design_id": design.design_id,
        "status": status,
        "checks": dict(checks),
        "credential_fingerprint": credential_fingerprint,
        "access_token_fingerprint": access_token_fingerprint,
        "verified_channel": (
            verified_channel.to_dict() if verified_channel is not None else None
        ),
        "verified_at": _format_utc(verified_at),
        "network_accessed": network_accessed,
        "publication_enabled": False,
        "auto_publish": False,
    }
    result = ControlledYouTubeVerificationResult(
        schema="football-shorts-ai.controlled-youtube-verification.v1",
        verification_id=f"YTVERIFY-{canonical_sha256(evidence)[:20].upper()}",
        status=status,
        checks=dict(checks),
        blockers=blockers,
        design_id=design.design_id,
        credential_fingerprint=credential_fingerprint,
        access_token_fingerprint=access_token_fingerprint,
        verified_channel=verified_channel if status == "VERIFIED" else None,
        verified_at=_format_utc(verified_at),
        network_accessed=network_accessed,
        secret_values_ephemeral=True,
        publication_enabled=False,
        auto_publish=False,
    )
    result.validate()
    return result


def _normalize_verified_channel(payload: Mapping[str, object]) -> VerifiedYouTubeChannel:
    channel = VerifiedYouTubeChannel(
        channel_id=_required_text(payload, "channel_id"),
        channel_title=_required_text(payload, "channel_title"),
        owner_reference=_required_text(payload, "owner_reference"),
        status=_required_text(payload, "status"),
        uploads_enabled=_required_bool(payload, "uploads_enabled"),
        shorts_eligible=_required_bool(payload, "shorts_eligible"),
    )
    channel.validate()
    return channel


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ControlledYouTubeVerificationError(f"{key} is required")
    return value.strip()


def _required_bool(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ControlledYouTubeVerificationError(f"{key} must be boolean")
    return value


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ControlledYouTubeVerificationError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ControlledYouTubeVerificationError(
            "timestamp must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ControlledYouTubeVerificationError("timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ControlledYouTubeVerificationError",
    "ControlledYouTubeVerificationResult",
    "EphemeralOAuthCredentials",
    "OAuthAccessToken",
    "VerifiedYouTubeChannel",
    "YouTubeOAuthClient",
    "YouTubeVerificationActivationPolicy",
    "canonical_sha256",
    "execute_controlled_youtube_verification",
]
