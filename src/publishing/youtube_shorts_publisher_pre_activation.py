"""
FOOTBALL-SHORTS-AI-0053D
YOUTUBE SHORTS PUBLISHER PRE-ACTIVATION

Defines the governed YouTube Shorts publisher profile and validates prepared
publication requests without authenticating, uploading, scheduling or publishing.
Execution remains fail-closed and automatic publishing remains disabled.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from publishing.governed_publication_contract import GovernedPublicationRequest
from publishing.platform_publisher_abstraction import (
    DisabledPlatformPublisher,
    PlatformPublisherAbstractionError,
    PreparedPublication,
    PublisherCapabilities,
    PublisherExecutionResult,
    prepare_publication,
)


YOUTUBE_SHORTS_PLATFORM = "youtube_shorts"
YOUTUBE_SHORTS_MAX_TITLE_LENGTH = 100
YOUTUBE_SHORTS_MAX_DESCRIPTION_LENGTH = 5000
YOUTUBE_SHORTS_MAX_HASHTAG_COUNT = 15


class YouTubeShortsPreActivationError(ValueError):
    """Raised when YouTube Shorts pre-activation evidence is unsafe."""


@dataclass(frozen=True)
class YouTubeShortsPreActivationReport:
    schema: str
    status: str
    preparation_id: str
    request_id: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    capabilities_sha256: str
    execution_status: str
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-shorts-pre-activation.v1":
            raise YouTubeShortsPreActivationError("unsupported pre-activation schema")
        if self.status not in {"READY_FOR_ACTIVATION", "BLOCKED"}:
            raise YouTubeShortsPreActivationError("unsupported pre-activation status")
        if not self.preparation_id.startswith("PREP-"):
            raise YouTubeShortsPreActivationError("invalid preparation_id")
        if not self.request_id.strip():
            raise YouTubeShortsPreActivationError("request_id is required")
        if set(self.checks.values()) - {True, False}:
            raise YouTubeShortsPreActivationError("checks must be boolean")
        if self.status == "READY_FOR_ACTIVATION" and self.blockers:
            raise YouTubeShortsPreActivationError("ready report cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise YouTubeShortsPreActivationError("blocked report requires blockers")
        if not _is_sha256(self.capabilities_sha256):
            raise YouTubeShortsPreActivationError("capabilities checksum must be SHA-256")
        if self.execution_status != "NOT_EXECUTED":
            raise YouTubeShortsPreActivationError("pre-activation cannot execute publication")
        if self.execution_enabled:
            raise YouTubeShortsPreActivationError("execution must remain disabled")
        if self.auto_publish:
            raise YouTubeShortsPreActivationError("automatic publishing must remain disabled")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "status": self.status,
            "preparation_id": self.preparation_id,
            "request_id": self.request_id,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "capabilities_sha256": self.capabilities_sha256,
            "execution_status": self.execution_status,
            "execution_enabled": False,
            "auto_publish": False,
        }


def youtube_shorts_capabilities() -> PublisherCapabilities:
    """Return the governed, non-executable YouTube Shorts capability profile."""

    capabilities = PublisherCapabilities(
        platform=YOUTUBE_SHORTS_PLATFORM,
        supports_video_upload=True,
        supports_thumbnail_upload=True,
        supports_subtitles_upload=True,
        supports_scheduling=True,
        supports_visibility=("private", "unlisted", "public"),
        max_title_length=YOUTUBE_SHORTS_MAX_TITLE_LENGTH,
        max_description_length=YOUTUBE_SHORTS_MAX_DESCRIPTION_LENGTH,
        max_hashtag_count=YOUTUBE_SHORTS_MAX_HASHTAG_COUNT,
        execution_enabled=False,
        auto_publish=False,
    )
    capabilities.validate()
    return capabilities


class YouTubeShortsPreActivationPublisher(DisabledPlatformPublisher):
    """Fail-closed YouTube Shorts publisher used before credential activation."""

    def __init__(self) -> None:
        super().__init__(youtube_shorts_capabilities())

    def prepare(self, request: GovernedPublicationRequest) -> PreparedPublication:
        if request.platform != YOUTUBE_SHORTS_PLATFORM:
            raise YouTubeShortsPreActivationError("request platform is not youtube_shorts")
        return prepare_publication(request=request, capabilities=self.capabilities)

    def execute(self, prepared: PreparedPublication) -> PublisherExecutionResult:
        if prepared.status != "READY":
            raise YouTubeShortsPreActivationError(
                "blocked preparation cannot reach publisher execution boundary"
            )
        return super().execute(prepared)


def certify_youtube_shorts_pre_activation(
    request: GovernedPublicationRequest,
) -> YouTubeShortsPreActivationReport:
    """Certify one request against the disabled YouTube Shorts publisher."""

    request.validate()
    publisher = YouTubeShortsPreActivationPublisher()
    prepared = publisher.prepare(request)

    checks: dict[str, bool] = {
        "platform_youtube_shorts": request.platform == YOUTUBE_SHORTS_PLATFORM,
        "preparation_ready": prepared.status == "READY",
        "video_mp4_path": request.video_path.lower().endswith(".mp4"),
        "vertical_asset_declared": bool(request.video_path.strip()),
        "human_approval_present": request.approval.approved,
        "title_within_youtube_limit": len(request.title) <= YOUTUBE_SHORTS_MAX_TITLE_LENGTH,
        "description_within_youtube_limit": (
            len(request.description) <= YOUTUBE_SHORTS_MAX_DESCRIPTION_LENGTH
        ),
        "hashtags_within_youtube_limit": (
            len(request.hashtags) <= YOUTUBE_SHORTS_MAX_HASHTAG_COUNT
        ),
        "execution_disabled": not request.execution_enabled,
        "auto_publish_disabled": not request.auto_publish,
        "credentials_not_required_pre_activation": True,
        "network_not_required_pre_activation": True,
    }
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)

    execution_status = "NOT_EXECUTED"
    if not blockers:
        execution_status = publisher.execute(prepared).status

    report = YouTubeShortsPreActivationReport(
        schema="football-shorts-ai.youtube-shorts-pre-activation.v1",
        status="READY_FOR_ACTIVATION" if not blockers else "BLOCKED",
        preparation_id=prepared.preparation_id,
        request_id=request.request_id,
        checks=checks,
        blockers=blockers,
        capabilities_sha256=canonical_sha256(publisher.capabilities.to_dict()),
        execution_status=execution_status,
        execution_enabled=False,
        auto_publish=False,
    )
    report.validate()
    return report


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "YOUTUBE_SHORTS_MAX_DESCRIPTION_LENGTH",
    "YOUTUBE_SHORTS_MAX_HASHTAG_COUNT",
    "YOUTUBE_SHORTS_MAX_TITLE_LENGTH",
    "YOUTUBE_SHORTS_PLATFORM",
    "YouTubeShortsPreActivationError",
    "YouTubeShortsPreActivationPublisher",
    "YouTubeShortsPreActivationReport",
    "canonical_sha256",
    "certify_youtube_shorts_pre_activation",
    "youtube_shorts_capabilities",
]
