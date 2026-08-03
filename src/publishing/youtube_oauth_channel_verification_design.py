"""
FOOTBALL-SHORTS-AI-0053F
YOUTUBE OAUTH CREDENTIAL RESOLUTION AND CHANNEL VERIFICATION DESIGN

Defines the governed, provider-neutral design for resolving YouTube OAuth
credential references and verifying channel identity in a later controlled
activation phase. This module does not read secret values, call Google APIs,
authenticate, refresh tokens, upload, schedule or publish content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from publishing.youtube_credential_channel_readiness import (
    YOUTUBE_PLATFORM,
    YOUTUBE_READONLY_SCOPE,
    YOUTUBE_UPLOAD_SCOPE,
    YouTubeChannelDeclaration,
    YouTubeCredentialDeclaration,
)


SUPPORTED_SECRET_BACKENDS = {
    "github_actions_secret",
    "environment",
    "vault",
    "external_secret_manager",
}

SUPPORTED_VERIFICATION_OPERATIONS = {
    "resolve_credential_references",
    "exchange_refresh_token",
    "fetch_authenticated_channel",
    "verify_upload_capability",
    "verify_shorts_eligibility",
}


class YouTubeOAuthChannelVerificationDesignError(ValueError):
    """Raised when the governed OAuth/channel verification design is unsafe."""


@dataclass(frozen=True)
class SecretReferenceBinding:
    logical_name: str
    reference: str
    backend: str
    required: bool = True
    secret_value_loaded: bool = False

    def validate(self) -> None:
        if not self.logical_name.strip():
            raise YouTubeOAuthChannelVerificationDesignError(
                "logical_name is required"
            )
        if not self.reference.strip():
            raise YouTubeOAuthChannelVerificationDesignError(
                "secret reference is required"
            )
        if self.backend not in SUPPORTED_SECRET_BACKENDS:
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported secret backend"
            )
        if self.secret_value_loaded:
            raise YouTubeOAuthChannelVerificationDesignError(
                "0053F cannot load secret values"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "logical_name": self.logical_name,
            "reference": self.reference,
            "backend": self.backend,
            "required": self.required,
            "secret_value_loaded": False,
        }


@dataclass(frozen=True)
class OAuthResolutionPlan:
    schema: str
    platform: str
    credential_type: str
    bindings: tuple[SecretReferenceBinding, ...]
    required_scopes: tuple[str, ...]
    token_endpoint_authority: str
    access_token_persistence_allowed: bool
    refresh_token_persistence_allowed: bool
    network_enabled: bool = False
    secret_values_loaded: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-oauth-resolution-plan.v1":
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported OAuth resolution plan schema"
            )
        if self.platform != YOUTUBE_PLATFORM:
            raise YouTubeOAuthChannelVerificationDesignError("invalid platform")
        if self.credential_type != "oauth2_refresh_token":
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported credential type"
            )
        if len(self.bindings) != 3:
            raise YouTubeOAuthChannelVerificationDesignError(
                "exactly three credential bindings are required"
            )
        for binding in self.bindings:
            binding.validate()
        logical_names = {binding.logical_name for binding in self.bindings}
        if logical_names != {"client_id", "client_secret", "refresh_token"}:
            raise YouTubeOAuthChannelVerificationDesignError(
                "credential bindings are incomplete"
            )
        required_scopes = {YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE}
        if not required_scopes.issubset(set(self.required_scopes)):
            raise YouTubeOAuthChannelVerificationDesignError(
                "required YouTube OAuth scopes are missing"
            )
        if not self.token_endpoint_authority.strip():
            raise YouTubeOAuthChannelVerificationDesignError(
                "token endpoint authority is required"
            )
        if self.access_token_persistence_allowed:
            raise YouTubeOAuthChannelVerificationDesignError(
                "access tokens must remain ephemeral"
            )
        if self.refresh_token_persistence_allowed:
            raise YouTubeOAuthChannelVerificationDesignError(
                "refresh token persistence outside the secret backend is forbidden"
            )
        if self.network_enabled or self.secret_values_loaded:
            raise YouTubeOAuthChannelVerificationDesignError(
                "0053F cannot enable network or load secrets"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "platform": self.platform,
            "credential_type": self.credential_type,
            "bindings": [binding.to_dict() for binding in self.bindings],
            "required_scopes": list(self.required_scopes),
            "token_endpoint_authority": self.token_endpoint_authority,
            "access_token_persistence_allowed": False,
            "refresh_token_persistence_allowed": False,
            "network_enabled": False,
            "secret_values_loaded": False,
        }


@dataclass(frozen=True)
class ChannelVerificationPlan:
    schema: str
    platform: str
    expected_channel_id: str
    expected_owner_reference: str
    operations: tuple[str, ...]
    require_active_channel: bool
    require_uploads_enabled: bool
    require_shorts_eligible: bool
    require_identity_match: bool
    network_enabled: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-channel-verification-plan.v1":
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported channel verification plan schema"
            )
        if self.platform != YOUTUBE_PLATFORM:
            raise YouTubeOAuthChannelVerificationDesignError("invalid platform")
        if not self.expected_channel_id.strip():
            raise YouTubeOAuthChannelVerificationDesignError(
                "expected_channel_id is required"
            )
        if not self.expected_owner_reference.strip():
            raise YouTubeOAuthChannelVerificationDesignError(
                "expected_owner_reference is required"
            )
        if not self.operations:
            raise YouTubeOAuthChannelVerificationDesignError(
                "verification operations are required"
            )
        if any(
            operation not in SUPPORTED_VERIFICATION_OPERATIONS
            for operation in self.operations
        ):
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported verification operation"
            )
        required = {
            "resolve_credential_references",
            "exchange_refresh_token",
            "fetch_authenticated_channel",
            "verify_upload_capability",
            "verify_shorts_eligibility",
        }
        if set(self.operations) != required:
            raise YouTubeOAuthChannelVerificationDesignError(
                "verification operation sequence is incomplete"
            )
        if not all(
            (
                self.require_active_channel,
                self.require_uploads_enabled,
                self.require_shorts_eligible,
                self.require_identity_match,
            )
        ):
            raise YouTubeOAuthChannelVerificationDesignError(
                "all channel verification requirements must remain mandatory"
            )
        if self.network_enabled:
            raise YouTubeOAuthChannelVerificationDesignError(
                "0053F cannot enable network access"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "platform": self.platform,
            "expected_channel_id": self.expected_channel_id,
            "expected_owner_reference": self.expected_owner_reference,
            "operations": list(self.operations),
            "require_active_channel": True,
            "require_uploads_enabled": True,
            "require_shorts_eligible": True,
            "require_identity_match": True,
            "network_enabled": False,
        }


@dataclass(frozen=True)
class YouTubeOAuthChannelVerificationDesign:
    schema: str
    design_id: str
    oauth_plan: OAuthResolutionPlan
    channel_plan: ChannelVerificationPlan
    checks: Mapping[str, bool]
    status: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    execution_enabled: bool = False
    auto_publish: bool = False
    network_accessed: bool = False
    secret_values_loaded: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-oauth-channel-design.v1":
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported design schema"
            )
        if not self.design_id.startswith("YTDESIGN-"):
            raise YouTubeOAuthChannelVerificationDesignError("invalid design_id")
        self.oauth_plan.validate()
        self.channel_plan.validate()
        if set(self.checks.values()) - {True, False}:
            raise YouTubeOAuthChannelVerificationDesignError(
                "design checks must be boolean"
            )
        if self.status not in {"DESIGN_READY", "BLOCKED"}:
            raise YouTubeOAuthChannelVerificationDesignError(
                "unsupported design status"
            )
        if self.status == "DESIGN_READY" and self.blockers:
            raise YouTubeOAuthChannelVerificationDesignError(
                "ready design cannot contain blockers"
            )
        if self.status == "BLOCKED" and not self.blockers:
            raise YouTubeOAuthChannelVerificationDesignError(
                "blocked design requires blockers"
            )
        if not _is_sha256(self.evidence_sha256):
            raise YouTubeOAuthChannelVerificationDesignError(
                "evidence_sha256 must be SHA-256"
            )
        if self.execution_enabled or self.auto_publish:
            raise YouTubeOAuthChannelVerificationDesignError(
                "execution and automatic publishing must remain disabled"
            )
        if self.network_accessed or self.secret_values_loaded:
            raise YouTubeOAuthChannelVerificationDesignError(
                "design phase cannot access network or secret values"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "design_id": self.design_id,
            "oauth_plan": self.oauth_plan.to_dict(),
            "channel_plan": self.channel_plan.to_dict(),
            "checks": dict(self.checks),
            "status": self.status,
            "blockers": list(self.blockers),
            "evidence_sha256": self.evidence_sha256,
            "execution_enabled": False,
            "auto_publish": False,
            "network_accessed": False,
            "secret_values_loaded": False,
        }


@runtime_checkable
class SecretReferenceResolver(Protocol):
    """Future provider-neutral secret resolver boundary."""

    def resolve_reference(self, reference: str) -> str:
        ...


@runtime_checkable
class YouTubeChannelVerifier(Protocol):
    """Future provider-neutral YouTube channel verification boundary."""

    def verify_channel(self, access_token: str) -> Mapping[str, object]:
        ...


def build_youtube_oauth_channel_verification_design(
    *,
    credential: YouTubeCredentialDeclaration,
    channel: YouTubeChannelDeclaration,
) -> YouTubeOAuthChannelVerificationDesign:
    """Build the offline governed design without resolving secrets or using network."""

    credential.validate()
    channel.validate()

    bindings = (
        SecretReferenceBinding(
            logical_name="client_id",
            reference=credential.client_id_reference,
            backend=_backend_from_reference(credential.client_id_reference),
        ),
        SecretReferenceBinding(
            logical_name="client_secret",
            reference=credential.client_secret_reference,
            backend=_backend_from_reference(credential.client_secret_reference),
        ),
        SecretReferenceBinding(
            logical_name="refresh_token",
            reference=credential.refresh_token_reference,
            backend=_backend_from_reference(credential.refresh_token_reference),
        ),
    )

    oauth_plan = OAuthResolutionPlan(
        schema="football-shorts-ai.youtube-oauth-resolution-plan.v1",
        platform=YOUTUBE_PLATFORM,
        credential_type=credential.credential_type,
        bindings=bindings,
        required_scopes=credential.scopes,
        token_endpoint_authority="google-oauth-token-endpoint",
        access_token_persistence_allowed=False,
        refresh_token_persistence_allowed=False,
        network_enabled=False,
        secret_values_loaded=False,
    )

    channel_plan = ChannelVerificationPlan(
        schema="football-shorts-ai.youtube-channel-verification-plan.v1",
        platform=YOUTUBE_PLATFORM,
        expected_channel_id=channel.channel_id,
        expected_owner_reference=channel.owner_reference,
        operations=(
            "resolve_credential_references",
            "exchange_refresh_token",
            "fetch_authenticated_channel",
            "verify_upload_capability",
            "verify_shorts_eligibility",
        ),
        require_active_channel=True,
        require_uploads_enabled=True,
        require_shorts_eligible=True,
        require_identity_match=True,
        network_enabled=False,
    )

    checks: dict[str, bool] = {
        "credential_declaration_valid": True,
        "channel_declaration_valid": True,
        "three_secret_references_declared": len(bindings) == 3,
        "required_scopes_declared": {
            YOUTUBE_UPLOAD_SCOPE,
            YOUTUBE_READONLY_SCOPE,
        }.issubset(set(credential.scopes)),
        "access_token_ephemeral": not oauth_plan.access_token_persistence_allowed,
        "refresh_token_secret_backend_only": (
            not oauth_plan.refresh_token_persistence_allowed
        ),
        "channel_identity_bound": bool(channel.channel_id.strip()),
        "owner_identity_bound": bool(channel.owner_reference.strip()),
        "network_disabled": not oauth_plan.network_enabled
        and not channel_plan.network_enabled,
        "secret_values_not_loaded": not credential.secret_values_loaded,
        "execution_disabled": True,
        "auto_publish_disabled": True,
    }

    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    evidence = {
        "oauth_plan": oauth_plan.to_dict(),
        "channel_plan": channel_plan.to_dict(),
        "checks": checks,
        "execution_enabled": False,
        "auto_publish": False,
        "network_accessed": False,
        "secret_values_loaded": False,
    }
    evidence_sha256 = canonical_sha256(evidence)

    design = YouTubeOAuthChannelVerificationDesign(
        schema="football-shorts-ai.youtube-oauth-channel-design.v1",
        design_id=f"YTDESIGN-{evidence_sha256[:20].upper()}",
        oauth_plan=oauth_plan,
        channel_plan=channel_plan,
        checks=checks,
        status="DESIGN_READY" if not blockers else "BLOCKED",
        blockers=blockers,
        evidence_sha256=evidence_sha256,
        execution_enabled=False,
        auto_publish=False,
        network_accessed=False,
        secret_values_loaded=False,
    )
    design.validate()
    return design


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _backend_from_reference(reference: str) -> str:
    lowered = reference.strip().lower()
    if lowered.startswith("github-actions-secret://"):
        return "github_actions_secret"
    if lowered.startswith("env://"):
        return "environment"
    if lowered.startswith("vault://"):
        return "vault"
    if lowered.startswith("secret://") or lowered.startswith("reference://"):
        return "external_secret_manager"
    raise YouTubeOAuthChannelVerificationDesignError(
        "unsupported secret reference scheme"
    )


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "ChannelVerificationPlan",
    "OAuthResolutionPlan",
    "SUPPORTED_SECRET_BACKENDS",
    "SUPPORTED_VERIFICATION_OPERATIONS",
    "SecretReferenceBinding",
    "SecretReferenceResolver",
    "YouTubeChannelVerifier",
    "YouTubeOAuthChannelVerificationDesign",
    "YouTubeOAuthChannelVerificationDesignError",
    "build_youtube_oauth_channel_verification_design",
    "canonical_sha256",
]
