"""
FOOTBALL-SHORTS-AI-0053H
CONTROLLED YOUTUBE VERIFICATION CERTIFICATION

Deterministic offline certification for the controlled YouTube OAuth and channel
verification runtime. Uses injected fakes only; no real secrets, network access,
Google API calls, upload, scheduling or publication are performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from publishing.controlled_youtube_oauth_channel_verification import (
    OAuthAccessToken,
    YouTubeVerificationActivationPolicy,
    execute_controlled_youtube_verification,
)
from publishing.youtube_credential_channel_readiness import (
    YOUTUBE_READONLY_SCOPE,
    YOUTUBE_UPLOAD_SCOPE,
    YouTubeChannelDeclaration,
    YouTubeCredentialDeclaration,
)
from publishing.youtube_oauth_channel_verification_design import (
    build_youtube_oauth_channel_verification_design,
)


class ControlledYouTubeVerificationCertificationError(ValueError):
    """Raised when the controlled verification certification is inconsistent."""


@dataclass(frozen=True)
class ControlledYouTubeVerificationCertification:
    schema: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    scenario_statuses: Mapping[str, str]
    evidence_sha256: str
    network_real: bool = False
    secrets_real: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-verification-certification.v1":
            raise ControlledYouTubeVerificationCertificationError(
                "unsupported certification schema"
            )
        if self.status not in {"CERTIFIED", "BLOCKED"}:
            raise ControlledYouTubeVerificationCertificationError(
                "unsupported certification status"
            )
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubeVerificationCertificationError(
                "certification checks must be boolean"
            )
        if self.status == "CERTIFIED" and self.blockers:
            raise ControlledYouTubeVerificationCertificationError(
                "certified result cannot contain blockers"
            )
        if self.status == "BLOCKED" and not self.blockers:
            raise ControlledYouTubeVerificationCertificationError(
                "blocked result requires blockers"
            )
        if len(self.evidence_sha256) != 64:
            raise ControlledYouTubeVerificationCertificationError(
                "evidence_sha256 must be SHA-256"
            )
        if self.network_real or self.secrets_real:
            raise ControlledYouTubeVerificationCertificationError(
                "certification cannot use real network or secrets"
            )
        if self.publication_enabled or self.auto_publish:
            raise ControlledYouTubeVerificationCertificationError(
                "publication and auto-publish must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "scenario_statuses": dict(self.scenario_statuses),
            "evidence_sha256": self.evidence_sha256,
            "network_real": False,
            "secrets_real": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


class _StaticSecretResolver:
    def resolve_reference(self, reference: str) -> str:
        return {
            "secret://youtube/client-id": "fake-client-id",
            "secret://youtube/client-secret": "fake-client-secret",
            "secret://youtube/refresh-token": "fake-refresh-token",
        }[reference]


class _StaticOAuthClient:
    def exchange_refresh_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        scopes: tuple[str, ...],
    ) -> OAuthAccessToken:
        assert client_id and client_secret and refresh_token
        return OAuthAccessToken(
            access_token="fake-access-token",
            token_type="Bearer",
            expires_in_seconds=3600,
            scopes=scopes,
        )


class _StaticChannelVerifier:
    def __init__(self, *, channel_id: str, uploads_enabled: bool = True) -> None:
        self.channel_id = channel_id
        self.uploads_enabled = uploads_enabled

    def verify_channel(self, access_token: str) -> Mapping[str, object]:
        assert access_token == "fake-access-token"
        return {
            "channel_id": self.channel_id,
            "channel_title": "Football Shorts AI",
            "owner_reference": "owner://football-shorts-ai",
            "status": "active",
            "uploads_enabled": self.uploads_enabled,
            "shorts_eligible": True,
        }


def certify_controlled_youtube_verification() -> ControlledYouTubeVerificationCertification:
    """Certify fail-closed and successful injected verification scenarios."""

    credential = YouTubeCredentialDeclaration(
        credential_type="oauth2_refresh_token",
        client_id_reference="secret://youtube/client-id",
        client_secret_reference="secret://youtube/client-secret",
        refresh_token_reference="secret://youtube/refresh-token",
        scopes=(YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE),
        secret_values_loaded=False,
    )
    channel = YouTubeChannelDeclaration(
        channel_id="UC1234567890123456789012",
        channel_title="Football Shorts AI",
        channel_handle="@footballshortsai",
        owner_reference="owner://football-shorts-ai",
        status="active",
        uploads_enabled=True,
        shorts_eligible=True,
        made_for_kids=False,
        verified_at="2026-08-03T08:00:00Z",
        verification_reference="offline-certification-fixture",
        network_verified=False,
    )
    design = build_youtube_oauth_channel_verification_design(
        credential=credential,
        channel=channel,
    )

    not_activated = execute_controlled_youtube_verification(
        design=design,
        policy=YouTubeVerificationActivationPolicy(),
        resolver=None,
        oauth_client=None,
        channel_verifier=None,
        verified_at="2026-08-03T08:30:00Z",
    )

    active_policy = YouTubeVerificationActivationPolicy(
        secret_resolution_enabled=True,
        oauth_exchange_enabled=True,
        channel_verification_enabled=True,
        network_enabled=True,
        publication_enabled=False,
        auto_publish=False,
    )
    verified = execute_controlled_youtube_verification(
        design=design,
        policy=active_policy,
        resolver=_StaticSecretResolver(),
        oauth_client=_StaticOAuthClient(),
        channel_verifier=_StaticChannelVerifier(channel_id=channel.channel_id),
        verified_at="2026-08-03T08:30:00Z",
    )
    identity_blocked = execute_controlled_youtube_verification(
        design=design,
        policy=active_policy,
        resolver=_StaticSecretResolver(),
        oauth_client=_StaticOAuthClient(),
        channel_verifier=_StaticChannelVerifier(
            channel_id="UC9999999999999999999999"
        ),
        verified_at="2026-08-03T08:30:00Z",
    )
    capability_blocked = execute_controlled_youtube_verification(
        design=design,
        policy=active_policy,
        resolver=_StaticSecretResolver(),
        oauth_client=_StaticOAuthClient(),
        channel_verifier=_StaticChannelVerifier(
            channel_id=channel.channel_id,
            uploads_enabled=False,
        ),
        verified_at="2026-08-03T08:30:00Z",
    )
    replay = execute_controlled_youtube_verification(
        design=design,
        policy=active_policy,
        resolver=_StaticSecretResolver(),
        oauth_client=_StaticOAuthClient(),
        channel_verifier=_StaticChannelVerifier(channel_id=channel.channel_id),
        verified_at="2026-08-03T08:30:00Z",
    )

    checks = {
        "default_policy_not_activated": not_activated.status == "NOT_ACTIVATED",
        "controlled_success_verified": verified.status == "VERIFIED",
        "identity_mismatch_blocked": identity_blocked.status == "BLOCKED",
        "upload_capability_failure_blocked": capability_blocked.status == "BLOCKED",
        "verified_channel_matches": (
            verified.verified_channel is not None
            and verified.verified_channel.channel_id == channel.channel_id
        ),
        "required_scopes_preserved": verified.checks.get("required_scopes_present", False),
        "redacted_fingerprints_present": bool(
            verified.credential_fingerprint and verified.access_token_fingerprint
        ),
        "replay_deterministic": verified.to_dict() == replay.to_dict(),
        "publication_disabled_all_scenarios": all(
            not item.publication_enabled
            for item in (
                not_activated,
                verified,
                identity_blocked,
                capability_blocked,
                replay,
            )
        ),
        "auto_publish_disabled_all_scenarios": all(
            not item.auto_publish
            for item in (
                not_activated,
                verified,
                identity_blocked,
                capability_blocked,
                replay,
            )
        ),
        "real_network_not_used": True,
        "real_secrets_not_used": True,
    }
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    scenario_statuses = {
        "not_activated": not_activated.status,
        "verified": verified.status,
        "identity_mismatch": identity_blocked.status,
        "upload_capability_failure": capability_blocked.status,
        "deterministic_replay": replay.status,
    }
    evidence = {
        "checks": checks,
        "scenario_statuses": scenario_statuses,
        "design_id": design.design_id,
        "verification_ids": {
            "not_activated": not_activated.verification_id,
            "verified": verified.verification_id,
            "identity_mismatch": identity_blocked.verification_id,
            "upload_capability_failure": capability_blocked.verification_id,
            "replay": replay.verification_id,
        },
        "network_real": False,
        "secrets_real": False,
        "publication_enabled": False,
        "auto_publish": False,
    }
    result = ControlledYouTubeVerificationCertification(
        schema="football-shorts-ai.controlled-youtube-verification-certification.v1",
        status="CERTIFIED" if not blockers else "BLOCKED",
        checks=checks,
        blockers=blockers,
        scenario_statuses=scenario_statuses,
        evidence_sha256=canonical_sha256(evidence),
        network_real=False,
        secrets_real=False,
        publication_enabled=False,
        auto_publish=False,
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


def main() -> int:
    result = certify_controlled_youtube_verification()
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0053H")
    print("CONTROLLED YOUTUBE VERIFICATION CERTIFICATION")
    print("=" * 72)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print("REAL_NETWORK=DISABLED")
    print("REAL_SECRETS=DISABLED")
    print("PUBLICATION=DISABLED")
    print("AUTO_PUBLISH=DISABLED")
    return 0 if result.status == "CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ControlledYouTubeVerificationCertification",
    "ControlledYouTubeVerificationCertificationError",
    "canonical_sha256",
    "certify_controlled_youtube_verification",
    "main",
]
