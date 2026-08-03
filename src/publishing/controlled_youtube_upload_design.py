"""
FOOTBALL-SHORTS-AI-0053I
CONTROLLED YOUTUBE UPLOAD DESIGN

Defines the governed design boundary for a future resumable YouTube upload.
This module validates upload inputs, metadata, idempotency, chunk policy and
post-upload actions without authenticating, opening a network connection,
creating an upload session, transferring bytes, scheduling or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Protocol, runtime_checkable

from publishing.governed_publication_contract import GovernedPublicationRequest
from publishing.platform_publisher_abstraction import PreparedPublication
from publishing.youtube_shorts_publisher_pre_activation import (
    YOUTUBE_SHORTS_PLATFORM,
)


SUPPORTED_UPLOAD_PROTOCOLS = {"resumable"}
SUPPORTED_INITIAL_PRIVACY = {"private", "unlisted"}
SUPPORTED_POST_UPLOAD_ACTIONS = {
    "verify_processing_state",
    "apply_thumbnail",
    "apply_subtitles",
    "confirm_channel_binding",
    "confirm_visibility",
}
MIN_CHUNK_SIZE_BYTES = 256 * 1024
MAX_CHUNK_SIZE_BYTES = 32 * 1024 * 1024
DEFAULT_CHUNK_SIZE_BYTES = 8 * 1024 * 1024


class ControlledYouTubeUploadDesignError(ValueError):
    """Raised when the controlled upload design is malformed or unsafe."""


@dataclass(frozen=True)
class YouTubeUploadArtifact:
    video_id: str
    video_path: str
    video_sha256: str
    size_bytes: int
    mime_type: str = "video/mp4"

    def validate(self) -> None:
        if not self.video_id.strip():
            raise ControlledYouTubeUploadDesignError("video_id is required")
        path = PurePosixPath(self.video_path)
        if path.is_absolute() or ".." in path.parts:
            raise ControlledYouTubeUploadDesignError("video_path must be relative and safe")
        if path.suffix.lower() != ".mp4":
            raise ControlledYouTubeUploadDesignError("YouTube upload requires an MP4")
        if not _is_sha256(self.video_sha256):
            raise ControlledYouTubeUploadDesignError("video_sha256 must be SHA-256")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool):
            raise ControlledYouTubeUploadDesignError("size_bytes must be an integer")
        if self.size_bytes <= 0:
            raise ControlledYouTubeUploadDesignError("size_bytes must be positive")
        if self.mime_type != "video/mp4":
            raise ControlledYouTubeUploadDesignError("mime_type must be video/mp4")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "video_id": self.video_id,
            "video_path": self.video_path,
            "video_sha256": self.video_sha256,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
        }


@dataclass(frozen=True)
class YouTubeUploadMetadata:
    title: str
    description: str
    tags: tuple[str, ...]
    category_id: str
    made_for_kids: bool
    contains_synthetic_media: bool
    initial_privacy: str
    scheduled_at: str | None

    def validate(self) -> None:
        if not self.title.strip() or len(self.title) > 100:
            raise ControlledYouTubeUploadDesignError("invalid YouTube title")
        if not self.description.strip() or len(self.description) > 5000:
            raise ControlledYouTubeUploadDesignError("invalid YouTube description")
        if not self.tags or any(not tag.strip() for tag in self.tags):
            raise ControlledYouTubeUploadDesignError("at least one non-empty tag is required")
        if len(set(self.tags)) != len(self.tags):
            raise ControlledYouTubeUploadDesignError("tags must be unique")
        if not self.category_id.isdigit():
            raise ControlledYouTubeUploadDesignError("category_id must be numeric")
        if self.initial_privacy not in SUPPORTED_INITIAL_PRIVACY:
            raise ControlledYouTubeUploadDesignError(
                "initial upload privacy must be private or unlisted"
            )
        if self.scheduled_at is not None and self.initial_privacy != "private":
            raise ControlledYouTubeUploadDesignError(
                "scheduled uploads must initially be private"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "category_id": self.category_id,
            "made_for_kids": self.made_for_kids,
            "contains_synthetic_media": self.contains_synthetic_media,
            "initial_privacy": self.initial_privacy,
            "scheduled_at": self.scheduled_at,
        }


@dataclass(frozen=True)
class ResumableUploadPolicy:
    protocol: str = "resumable"
    chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES
    max_attempts: int = 5
    idempotency_required: bool = True
    persist_session_uri: bool = False
    persist_access_token: bool = False
    network_enabled: bool = False
    upload_enabled: bool = False

    def validate(self) -> None:
        if self.protocol not in SUPPORTED_UPLOAD_PROTOCOLS:
            raise ControlledYouTubeUploadDesignError("unsupported upload protocol")
        if not isinstance(self.chunk_size_bytes, int) or isinstance(
            self.chunk_size_bytes, bool
        ):
            raise ControlledYouTubeUploadDesignError("chunk_size_bytes must be an integer")
        if not MIN_CHUNK_SIZE_BYTES <= self.chunk_size_bytes <= MAX_CHUNK_SIZE_BYTES:
            raise ControlledYouTubeUploadDesignError("chunk size is outside governed limits")
        if self.chunk_size_bytes % MIN_CHUNK_SIZE_BYTES != 0:
            raise ControlledYouTubeUploadDesignError(
                "chunk size must be a multiple of 256 KiB"
            )
        if not isinstance(self.max_attempts, int) or isinstance(self.max_attempts, bool):
            raise ControlledYouTubeUploadDesignError("max_attempts must be an integer")
        if not 1 <= self.max_attempts <= 10:
            raise ControlledYouTubeUploadDesignError("max_attempts is outside governed limits")
        if not self.idempotency_required:
            raise ControlledYouTubeUploadDesignError("idempotency must remain mandatory")
        if self.persist_session_uri:
            raise ControlledYouTubeUploadDesignError(
                "upload session URI persistence is not allowed in the design phase"
            )
        if self.persist_access_token:
            raise ControlledYouTubeUploadDesignError("access-token persistence is forbidden")
        if self.network_enabled or self.upload_enabled:
            raise ControlledYouTubeUploadDesignError(
                "0053I cannot enable network or upload execution"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "protocol": self.protocol,
            "chunk_size_bytes": self.chunk_size_bytes,
            "max_attempts": self.max_attempts,
            "idempotency_required": True,
            "persist_session_uri": False,
            "persist_access_token": False,
            "network_enabled": False,
            "upload_enabled": False,
        }


@dataclass(frozen=True)
class ControlledYouTubeUploadDesign:
    schema: str
    design_id: str
    request_id: str
    preparation_id: str
    channel_verification_id: str
    artifact: YouTubeUploadArtifact
    metadata: YouTubeUploadMetadata
    policy: ResumableUploadPolicy
    idempotency_key: str
    post_upload_actions: tuple[str, ...]
    checks: Mapping[str, bool]
    status: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    upload_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-upload-design.v1":
            raise ControlledYouTubeUploadDesignError("unsupported upload design schema")
        if not self.design_id.startswith("YTUPLOADDESIGN-"):
            raise ControlledYouTubeUploadDesignError("invalid design_id")
        if not self.request_id.strip() or not self.preparation_id.startswith("PREP-"):
            raise ControlledYouTubeUploadDesignError("invalid request or preparation identity")
        if not self.channel_verification_id.startswith("YTVERIFY-"):
            raise ControlledYouTubeUploadDesignError("invalid channel verification identity")
        self.artifact.validate()
        self.metadata.validate()
        self.policy.validate()
        if not _is_sha256(self.idempotency_key):
            raise ControlledYouTubeUploadDesignError("idempotency_key must be SHA-256")
        if set(self.post_upload_actions) != SUPPORTED_POST_UPLOAD_ACTIONS:
            raise ControlledYouTubeUploadDesignError(
                "post-upload action set is incomplete"
            )
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubeUploadDesignError("checks must be boolean")
        if self.status not in {"DESIGN_READY", "BLOCKED"}:
            raise ControlledYouTubeUploadDesignError("unsupported design status")
        if self.status == "DESIGN_READY" and self.blockers:
            raise ControlledYouTubeUploadDesignError("ready design cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise ControlledYouTubeUploadDesignError("blocked design requires blockers")
        if not _is_sha256(self.evidence_sha256):
            raise ControlledYouTubeUploadDesignError("evidence_sha256 must be SHA-256")
        if self.network_enabled or self.upload_enabled or self.publication_enabled:
            raise ControlledYouTubeUploadDesignError(
                "design cannot enable network, upload or publication"
            )
        if self.auto_publish:
            raise ControlledYouTubeUploadDesignError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "design_id": self.design_id,
            "request_id": self.request_id,
            "preparation_id": self.preparation_id,
            "channel_verification_id": self.channel_verification_id,
            "artifact": self.artifact.to_dict(),
            "metadata": self.metadata.to_dict(),
            "policy": self.policy.to_dict(),
            "idempotency_key": self.idempotency_key,
            "post_upload_actions": list(self.post_upload_actions),
            "checks": dict(self.checks),
            "status": self.status,
            "blockers": list(self.blockers),
            "evidence_sha256": self.evidence_sha256,
            "network_enabled": False,
            "upload_enabled": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


@runtime_checkable
class YouTubeResumableUploadClient(Protocol):
    """Future injected boundary for creating and advancing resumable uploads."""

    def create_session(self, payload: Mapping[str, object]) -> str:
        ...

    def upload_chunk(
        self,
        *,
        session_uri: str,
        offset: int,
        data: bytes,
        total_size: int,
    ) -> Mapping[str, object]:
        ...


@runtime_checkable
class YouTubePostUploadClient(Protocol):
    """Future injected boundary for governed post-upload operations."""

    def verify_video(self, youtube_video_id: str) -> Mapping[str, object]:
        ...


def build_controlled_youtube_upload_design(
    *,
    request: GovernedPublicationRequest,
    prepared: PreparedPublication,
    channel_verification_id: str,
    video_sha256: str,
    size_bytes: int,
    category_id: str = "17",
    made_for_kids: bool = False,
    contains_synthetic_media: bool = True,
    chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES,
) -> ControlledYouTubeUploadDesign:
    """Build an offline, non-executable upload design from governed evidence."""

    request.validate()
    prepared.validate()

    artifact = YouTubeUploadArtifact(
        video_id=request.video_id,
        video_path=request.video_path,
        video_sha256=video_sha256,
        size_bytes=size_bytes,
    )
    metadata = YouTubeUploadMetadata(
        title=request.title,
        description=request.description,
        tags=tuple(tag.lstrip("#") for tag in request.hashtags),
        category_id=category_id,
        made_for_kids=made_for_kids,
        contains_synthetic_media=contains_synthetic_media,
        initial_privacy=request.visibility if request.visibility != "public" else "private",
        scheduled_at=request.scheduled_at,
    )
    policy = ResumableUploadPolicy(chunk_size_bytes=chunk_size_bytes)

    checks = {
        "platform_youtube_shorts": request.platform == YOUTUBE_SHORTS_PLATFORM,
        "prepared_publication_ready": prepared.status == "READY",
        "request_identity_matches": prepared.request_id == request.request_id,
        "preparation_platform_matches": prepared.platform == request.platform,
        "channel_verification_present": channel_verification_id.startswith("YTVERIFY-"),
        "video_path_mp4": request.video_path.lower().endswith(".mp4"),
        "video_checksum_valid": _is_sha256(video_sha256),
        "video_size_positive": isinstance(size_bytes, int)
        and not isinstance(size_bytes, bool)
        and size_bytes > 0,
        "human_approval_present": request.approval.approved,
        "initial_visibility_not_public": metadata.initial_privacy in SUPPORTED_INITIAL_PRIVACY,
        "resumable_protocol": policy.protocol == "resumable",
        "idempotency_required": policy.idempotency_required,
        "network_disabled": not policy.network_enabled,
        "upload_disabled": not policy.upload_enabled,
        "publication_disabled": True,
        "auto_publish_disabled": not request.auto_publish,
    }
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)

    artifact.validate()
    metadata.validate()
    policy.validate()

    idempotency_payload = {
        "request_id": request.request_id,
        "preparation_id": prepared.preparation_id,
        "channel_verification_id": channel_verification_id,
        "video_sha256": video_sha256,
        "metadata": metadata.to_dict(),
    }
    idempotency_key = canonical_sha256(idempotency_payload)
    evidence = {
        "artifact": artifact.to_dict(),
        "metadata": metadata.to_dict(),
        "policy": policy.to_dict(),
        "idempotency_key": idempotency_key,
        "post_upload_actions": sorted(SUPPORTED_POST_UPLOAD_ACTIONS),
        "checks": checks,
        "network_enabled": False,
        "upload_enabled": False,
        "publication_enabled": False,
        "auto_publish": False,
    }
    evidence_sha256 = canonical_sha256(evidence)

    result = ControlledYouTubeUploadDesign(
        schema="football-shorts-ai.controlled-youtube-upload-design.v1",
        design_id=f"YTUPLOADDESIGN-{evidence_sha256[:20].upper()}",
        request_id=request.request_id,
        preparation_id=prepared.preparation_id,
        channel_verification_id=channel_verification_id,
        artifact=artifact,
        metadata=metadata,
        policy=policy,
        idempotency_key=idempotency_key,
        post_upload_actions=tuple(sorted(SUPPORTED_POST_UPLOAD_ACTIONS)),
        checks=checks,
        status="DESIGN_READY" if not blockers else "BLOCKED",
        blockers=blockers,
        evidence_sha256=evidence_sha256,
        network_enabled=False,
        upload_enabled=False,
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


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "ControlledYouTubeUploadDesign",
    "ControlledYouTubeUploadDesignError",
    "DEFAULT_CHUNK_SIZE_BYTES",
    "MAX_CHUNK_SIZE_BYTES",
    "MIN_CHUNK_SIZE_BYTES",
    "ResumableUploadPolicy",
    "SUPPORTED_INITIAL_PRIVACY",
    "SUPPORTED_POST_UPLOAD_ACTIONS",
    "SUPPORTED_UPLOAD_PROTOCOLS",
    "YouTubePostUploadClient",
    "YouTubeResumableUploadClient",
    "YouTubeUploadArtifact",
    "YouTubeUploadMetadata",
    "build_controlled_youtube_upload_design",
    "canonical_sha256",
]
