"""
FOOTBALL-SHORTS-AI-0053A
GOVERNED PUBLICATION CONTRACT

Defines the immutable request boundary between Factory v1 publishing readiness
and any future platform publisher. This module never authenticates, uploads,
schedules, or publishes content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


SUPPORTED_PLATFORMS = {
    "youtube_shorts",
    "tiktok",
    "instagram_reels",
    "facebook_reels",
}

SUPPORTED_VISIBILITY = {
    "private",
    "unlisted",
    "public",
}


class GovernedPublicationContractError(ValueError):
    """Raised when a publication request violates the governed boundary."""


@dataclass(frozen=True)
class HumanApproval:
    approved: bool
    approved_by: str
    approved_at: str
    approval_reference: str

    def validate(self) -> None:
        if not self.approved:
            raise GovernedPublicationContractError(
                "explicit human approval is required"
            )
        if not self.approved_by.strip():
            raise GovernedPublicationContractError("approved_by is required")
        if not self.approval_reference.strip():
            raise GovernedPublicationContractError(
                "approval_reference is required"
            )
        _parse_utc_timestamp(self.approved_at)


@dataclass(frozen=True)
class GovernedPublicationRequest:
    schema: str
    request_id: str
    video_id: str
    publishing_package_id: str
    readiness_evidence_sha256: str
    platform: str
    title: str
    description: str
    hashtags: tuple[str, ...]
    video_path: str
    thumbnail_path: str
    subtitles_path: str
    visibility: str
    scheduled_at: str | None
    approval: HumanApproval
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.governed-publication-request.v1":
            raise GovernedPublicationContractError(
                "unsupported governed publication schema"
            )
        for name, value in {
            "request_id": self.request_id,
            "video_id": self.video_id,
            "publishing_package_id": self.publishing_package_id,
            "title": self.title,
            "description": self.description,
            "video_path": self.video_path,
            "thumbnail_path": self.thumbnail_path,
            "subtitles_path": self.subtitles_path,
        }.items():
            if not value.strip():
                raise GovernedPublicationContractError(f"{name} is required")
        if self.platform not in SUPPORTED_PLATFORMS:
            raise GovernedPublicationContractError("unsupported platform")
        if self.visibility not in SUPPORTED_VISIBILITY:
            raise GovernedPublicationContractError("unsupported visibility")
        if len(self.readiness_evidence_sha256) != 64:
            raise GovernedPublicationContractError(
                "readiness evidence checksum must be SHA-256"
            )
        if not self.hashtags or any(
            not item.startswith("#") for item in self.hashtags
        ):
            raise GovernedPublicationContractError("valid hashtags are required")
        if self.scheduled_at is not None:
            _parse_utc_timestamp(self.scheduled_at)
        self.approval.validate()
        if self.execution_enabled:
            raise GovernedPublicationContractError(
                "publication execution is not activated in 0053A"
            )
        if self.auto_publish:
            raise GovernedPublicationContractError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "request_id": self.request_id,
            "video_id": self.video_id,
            "publishing_package_id": self.publishing_package_id,
            "readiness_evidence_sha256": self.readiness_evidence_sha256,
            "platform": self.platform,
            "metadata": {
                "title": self.title,
                "description": self.description,
                "hashtags": list(self.hashtags),
                "visibility": self.visibility,
                "scheduled_at": self.scheduled_at,
            },
            "artifacts": {
                "video_path": self.video_path,
                "thumbnail_path": self.thumbnail_path,
                "subtitles_path": self.subtitles_path,
            },
            "approval": {
                "approved": self.approval.approved,
                "approved_by": self.approval.approved_by,
                "approved_at": self.approval.approved_at,
                "approval_reference": self.approval.approval_reference,
            },
            "execution_enabled": False,
            "auto_publish": False,
        }


def build_governed_publication_request(
    *,
    readiness: Mapping[str, object],
    publishing_package: Mapping[str, object],
    approval: HumanApproval,
    visibility: str = "private",
    scheduled_at: str | None = None,
) -> GovernedPublicationRequest:
    """Build a deterministic, non-executable publication request."""

    if readiness.get("status") != "ready_for_publish":
        raise GovernedPublicationContractError(
            "video is not ready_for_publish"
        )
    if readiness.get("auto_publish") is not False:
        raise GovernedPublicationContractError(
            "readiness must explicitly disable auto_publish"
        )

    metadata = publishing_package.get("metadata")
    if not isinstance(metadata, Mapping):
        raise GovernedPublicationContractError(
            "publishing metadata must be an object"
        )
    artifacts = readiness.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise GovernedPublicationContractError(
            "readiness artifacts must be an object"
        )

    video_id = _required_text(readiness, "video_id")
    package_id = _required_text(readiness, "publishing_package_id")
    platform = _required_text(readiness, "platform")
    title = _required_text(metadata, "title")
    description = _required_text(metadata, "description")
    hashtags = _hashtags(metadata.get("hashtags"))
    evidence_sha256 = canonical_sha256(readiness)

    identity = {
        "video_id": video_id,
        "publishing_package_id": package_id,
        "platform": platform,
        "readiness_evidence_sha256": evidence_sha256,
        "visibility": visibility,
        "scheduled_at": scheduled_at,
        "approval_reference": approval.approval_reference,
    }

    request = GovernedPublicationRequest(
        schema="football-shorts-ai.governed-publication-request.v1",
        request_id=f"PUB-{canonical_sha256(identity)[:20].upper()}",
        video_id=video_id,
        publishing_package_id=package_id,
        readiness_evidence_sha256=evidence_sha256,
        platform=platform,
        title=title,
        description=description,
        hashtags=hashtags,
        video_path=_required_text(artifacts, "video_path"),
        thumbnail_path=_required_text(artifacts, "thumbnail_path"),
        subtitles_path=_required_text(artifacts, "subtitles_path"),
        visibility=visibility,
        scheduled_at=scheduled_at,
        approval=approval,
        execution_enabled=False,
        auto_publish=False,
    )
    request.validate()
    return request


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GovernedPublicationContractError(f"{key} is required")
    return value.strip()


def _hashtags(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise GovernedPublicationContractError("hashtags must be a list")
    result = tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )
    if not result or any(not item.startswith("#") for item in result):
        raise GovernedPublicationContractError("valid hashtags are required")
    return result


def _parse_utc_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GovernedPublicationContractError(
            "timestamp must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise GovernedPublicationContractError("timestamp must use UTC")
    return parsed


__all__ = [
    "GovernedPublicationContractError",
    "GovernedPublicationRequest",
    "HumanApproval",
    "SUPPORTED_PLATFORMS",
    "SUPPORTED_VISIBILITY",
    "build_governed_publication_request",
    "canonical_sha256",
]
