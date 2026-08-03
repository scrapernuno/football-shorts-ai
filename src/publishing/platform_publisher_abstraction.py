"""
FOOTBALL-SHORTS-AI-0053C
PLATFORM PUBLISHER ABSTRACTION

Defines the provider-neutral boundary for future publishing integrations.
This module validates and prepares governed publication requests and normalizes
publisher results. It never authenticates, uploads, schedules, or publishes
content by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from publishing.governed_publication_contract import (
    GovernedPublicationRequest,
    SUPPORTED_PLATFORMS,
)


SUPPORTED_PREPARATION_STATUS = {
    "READY",
    "BLOCKED",
}

SUPPORTED_EXECUTION_STATUS = {
    "NOT_EXECUTED",
    "SUCCEEDED",
    "FAILED",
}


class PlatformPublisherAbstractionError(ValueError):
    """Raised when a publisher boundary contract is malformed or unsafe."""


@dataclass(frozen=True)
class PublisherCapabilities:
    platform: str
    supports_video_upload: bool
    supports_thumbnail_upload: bool
    supports_subtitles_upload: bool
    supports_scheduling: bool
    supports_visibility: tuple[str, ...]
    max_title_length: int
    max_description_length: int
    max_hashtag_count: int
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.platform not in SUPPORTED_PLATFORMS:
            raise PlatformPublisherAbstractionError("unsupported publisher platform")
        if not self.supports_video_upload:
            raise PlatformPublisherAbstractionError("video upload capability is required")
        if not self.supports_visibility:
            raise PlatformPublisherAbstractionError("supported visibility is required")
        if any(not value.strip() for value in self.supports_visibility):
            raise PlatformPublisherAbstractionError("invalid visibility capability")
        for name, value in {
            "max_title_length": self.max_title_length,
            "max_description_length": self.max_description_length,
            "max_hashtag_count": self.max_hashtag_count,
        }.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise PlatformPublisherAbstractionError(f"{name} must be positive")
        if self.execution_enabled:
            raise PlatformPublisherAbstractionError(
                "publisher execution is not activated in 0053C"
            )
        if self.auto_publish:
            raise PlatformPublisherAbstractionError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "platform": self.platform,
            "supports_video_upload": self.supports_video_upload,
            "supports_thumbnail_upload": self.supports_thumbnail_upload,
            "supports_subtitles_upload": self.supports_subtitles_upload,
            "supports_scheduling": self.supports_scheduling,
            "supports_visibility": list(self.supports_visibility),
            "max_title_length": self.max_title_length,
            "max_description_length": self.max_description_length,
            "max_hashtag_count": self.max_hashtag_count,
            "execution_enabled": False,
            "auto_publish": False,
        }


@dataclass(frozen=True)
class PreparedPublication:
    schema: str
    preparation_id: str
    request_id: str
    platform: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    normalized_payload: Mapping[str, object]
    request_sha256: str
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.prepared-publication.v1":
            raise PlatformPublisherAbstractionError("unsupported preparation schema")
        if not self.preparation_id.startswith("PREP-"):
            raise PlatformPublisherAbstractionError("invalid preparation_id")
        if not self.request_id.strip():
            raise PlatformPublisherAbstractionError("request_id is required")
        if self.platform not in SUPPORTED_PLATFORMS:
            raise PlatformPublisherAbstractionError("unsupported platform")
        if self.status not in SUPPORTED_PREPARATION_STATUS:
            raise PlatformPublisherAbstractionError("unsupported preparation status")
        if set(self.checks.values()) - {True, False}:
            raise PlatformPublisherAbstractionError("preparation checks must be boolean")
        if self.status == "READY" and self.blockers:
            raise PlatformPublisherAbstractionError("ready preparation cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise PlatformPublisherAbstractionError("blocked preparation requires blockers")
        if not _is_sha256(self.request_sha256):
            raise PlatformPublisherAbstractionError("request_sha256 must be SHA-256")
        if self.execution_enabled:
            raise PlatformPublisherAbstractionError(
                "publisher execution remains disabled"
            )
        if self.auto_publish:
            raise PlatformPublisherAbstractionError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "preparation_id": self.preparation_id,
            "request_id": self.request_id,
            "platform": self.platform,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "normalized_payload": dict(self.normalized_payload),
            "request_sha256": self.request_sha256,
            "execution_enabled": False,
            "auto_publish": False,
        }


@dataclass(frozen=True)
class PublisherExecutionResult:
    schema: str
    execution_id: str
    preparation_id: str
    platform: str
    status: str
    external_publication_id: str | None
    external_url: str | None
    error_code: str | None
    error_message: str | None
    evidence_sha256: str
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.publisher-execution-result.v1":
            raise PlatformPublisherAbstractionError("unsupported result schema")
        if not self.execution_id.startswith("EXEC-"):
            raise PlatformPublisherAbstractionError("invalid execution_id")
        if not self.preparation_id.startswith("PREP-"):
            raise PlatformPublisherAbstractionError("invalid preparation_id")
        if self.platform not in SUPPORTED_PLATFORMS:
            raise PlatformPublisherAbstractionError("unsupported platform")
        if self.status not in SUPPORTED_EXECUTION_STATUS:
            raise PlatformPublisherAbstractionError("unsupported execution status")
        if self.status == "SUCCEEDED":
            if not self.external_publication_id or self.error_code or self.error_message:
                raise PlatformPublisherAbstractionError("successful result is inconsistent")
        if self.status == "FAILED":
            if not self.error_code or not self.error_message:
                raise PlatformPublisherAbstractionError("failed result requires error evidence")
        if self.status == "NOT_EXECUTED" and (
            self.external_publication_id
            or self.external_url
            or self.error_code
            or self.error_message
        ):
            raise PlatformPublisherAbstractionError(
                "non-executed result cannot contain provider outcome"
            )
        if not _is_sha256(self.evidence_sha256):
            raise PlatformPublisherAbstractionError("evidence_sha256 must be SHA-256")
        if self.execution_enabled:
            raise PlatformPublisherAbstractionError(
                "publisher execution remains disabled"
            )
        if self.auto_publish:
            raise PlatformPublisherAbstractionError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "execution_id": self.execution_id,
            "preparation_id": self.preparation_id,
            "platform": self.platform,
            "status": self.status,
            "external_publication_id": self.external_publication_id,
            "external_url": self.external_url,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "evidence_sha256": self.evidence_sha256,
            "execution_enabled": False,
            "auto_publish": False,
        }


@runtime_checkable
class PlatformPublisher(Protocol):
    """Provider-neutral contract implemented by future concrete publishers."""

    @property
    def capabilities(self) -> PublisherCapabilities:
        ...

    def prepare(self, request: GovernedPublicationRequest) -> PreparedPublication:
        ...

    def execute(self, prepared: PreparedPublication) -> PublisherExecutionResult:
        ...


class DisabledPlatformPublisher:
    """Fail-closed reference publisher used until concrete execution is activated."""

    def __init__(self, capabilities: PublisherCapabilities) -> None:
        capabilities.validate()
        self._capabilities = capabilities

    @property
    def capabilities(self) -> PublisherCapabilities:
        return self._capabilities

    def prepare(self, request: GovernedPublicationRequest) -> PreparedPublication:
        return prepare_publication(request=request, capabilities=self.capabilities)

    def execute(self, prepared: PreparedPublication) -> PublisherExecutionResult:
        prepared.validate()
        if prepared.platform != self.capabilities.platform:
            raise PlatformPublisherAbstractionError("publisher platform mismatch")
        evidence = {
            "preparation_id": prepared.preparation_id,
            "platform": prepared.platform,
            "status": "NOT_EXECUTED",
            "execution_enabled": False,
            "auto_publish": False,
        }
        result = PublisherExecutionResult(
            schema="football-shorts-ai.publisher-execution-result.v1",
            execution_id=f"EXEC-{canonical_sha256(evidence)[:20].upper()}",
            preparation_id=prepared.preparation_id,
            platform=prepared.platform,
            status="NOT_EXECUTED",
            external_publication_id=None,
            external_url=None,
            error_code=None,
            error_message=None,
            evidence_sha256=canonical_sha256(evidence),
            execution_enabled=False,
            auto_publish=False,
        )
        result.validate()
        return result


def prepare_publication(
    *,
    request: GovernedPublicationRequest,
    capabilities: PublisherCapabilities,
) -> PreparedPublication:
    """Validate and normalize one governed request without executing it."""

    request.validate()
    capabilities.validate()

    checks = {
        "platform_matches": request.platform == capabilities.platform,
        "visibility_supported": request.visibility in capabilities.supports_visibility,
        "title_within_limit": len(request.title) <= capabilities.max_title_length,
        "description_within_limit": (
            len(request.description) <= capabilities.max_description_length
        ),
        "hashtag_count_within_limit": (
            len(request.hashtags) <= capabilities.max_hashtag_count
        ),
        "video_path_present": bool(request.video_path.strip()),
        "thumbnail_supported_or_optional": (
            capabilities.supports_thumbnail_upload or bool(request.thumbnail_path.strip())
        ),
        "subtitles_supported_or_optional": (
            capabilities.supports_subtitles_upload or bool(request.subtitles_path.strip())
        ),
        "schedule_supported": (
            request.scheduled_at is None or capabilities.supports_scheduling
        ),
        "human_approval_present": request.approval.approved,
        "request_execution_disabled": not request.execution_enabled,
        "request_auto_publish_disabled": not request.auto_publish,
        "publisher_execution_disabled": not capabilities.execution_enabled,
        "publisher_auto_publish_disabled": not capabilities.auto_publish,
    }

    blockers = tuple(
        name.upper()
        for name, passed in checks.items()
        if not passed
    )
    normalized_payload = {
        "platform": request.platform,
        "title": request.title.strip(),
        "description": request.description.strip(),
        "hashtags": list(request.hashtags),
        "visibility": request.visibility,
        "scheduled_at": request.scheduled_at,
        "video_path": request.video_path,
        "thumbnail_path": request.thumbnail_path,
        "subtitles_path": request.subtitles_path,
        "approval_reference": request.approval.approval_reference,
        "execution_enabled": False,
        "auto_publish": False,
    }
    request_sha256 = canonical_sha256(request.to_dict())
    identity = {
        "request_sha256": request_sha256,
        "platform": request.platform,
        "capabilities": capabilities.to_dict(),
        "normalized_payload": normalized_payload,
    }

    prepared = PreparedPublication(
        schema="football-shorts-ai.prepared-publication.v1",
        preparation_id=f"PREP-{canonical_sha256(identity)[:20].upper()}",
        request_id=request.request_id,
        platform=request.platform,
        status="READY" if not blockers else "BLOCKED",
        checks=checks,
        blockers=blockers,
        normalized_payload=normalized_payload,
        request_sha256=request_sha256,
        execution_enabled=False,
        auto_publish=False,
    )
    prepared.validate()
    return prepared


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
    "DisabledPlatformPublisher",
    "PlatformPublisher",
    "PlatformPublisherAbstractionError",
    "PreparedPublication",
    "PublisherCapabilities",
    "PublisherExecutionResult",
    "SUPPORTED_EXECUTION_STATUS",
    "SUPPORTED_PREPARATION_STATUS",
    "canonical_sha256",
    "prepare_publication",
]
