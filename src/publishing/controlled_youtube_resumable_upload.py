"""
FOOTBALL-SHORTS-AI-0053J
CONTROLLED YOUTUBE RESUMABLE UPLOAD IMPLEMENTATION

Executes a 0053I upload design only through injected byte-source and resumable
upload clients. The default policy is fail-closed. No concrete filesystem,
Google SDK, HTTP client, credential resolver, upload activation, scheduling or
publication implementation is provided here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import BinaryIO, Mapping, Protocol, runtime_checkable

from publishing.controlled_youtube_upload_design import (
    ControlledYouTubeUploadDesign,
    YouTubeResumableUploadClient,
)


class ControlledYouTubeResumableUploadError(ValueError):
    """Raised when controlled upload cannot proceed safely."""


@dataclass(frozen=True)
class YouTubeUploadActivationPolicy:
    artifact_read_enabled: bool = False
    session_creation_enabled: bool = False
    chunk_transfer_enabled: bool = False
    network_enabled: bool = False
    upload_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.publication_enabled:
            raise ControlledYouTubeResumableUploadError(
                "0053J cannot enable publication"
            )
        if self.auto_publish:
            raise ControlledYouTubeResumableUploadError(
                "automatic publishing must remain disabled"
            )
        execution = (
            self.artifact_read_enabled,
            self.session_creation_enabled,
            self.chunk_transfer_enabled,
            self.upload_enabled,
        )
        if any(execution) and not self.network_enabled:
            raise ControlledYouTubeResumableUploadError(
                "controlled upload requires explicit network activation"
            )
        if self.session_creation_enabled and not self.artifact_read_enabled:
            raise ControlledYouTubeResumableUploadError(
                "session creation requires artifact reading"
            )
        if self.chunk_transfer_enabled and not self.session_creation_enabled:
            raise ControlledYouTubeResumableUploadError(
                "chunk transfer requires session creation"
            )
        if self.upload_enabled and not self.chunk_transfer_enabled:
            raise ControlledYouTubeResumableUploadError(
                "upload activation requires chunk transfer"
            )


@runtime_checkable
class UploadArtifactSource(Protocol):
    """Injected boundary for opening the governed MP4 artifact."""

    def open_binary(self, relative_path: str) -> BinaryIO:
        ...


@dataclass(frozen=True)
class UploadChunkReceipt:
    accepted_offset: int
    next_offset: int
    complete: bool
    youtube_video_id: str | None = None

    def validate(self, *, total_size: int) -> None:
        if self.accepted_offset < 0 or self.next_offset < 0:
            raise ControlledYouTubeResumableUploadError(
                "upload offsets cannot be negative"
            )
        if self.next_offset < self.accepted_offset:
            raise ControlledYouTubeResumableUploadError(
                "next_offset cannot move backwards"
            )
        if self.next_offset > total_size:
            raise ControlledYouTubeResumableUploadError(
                "next_offset exceeds artifact size"
            )
        if self.complete:
            if self.next_offset != total_size:
                raise ControlledYouTubeResumableUploadError(
                    "complete receipt must consume the entire artifact"
                )
            if not self.youtube_video_id or not self.youtube_video_id.strip():
                raise ControlledYouTubeResumableUploadError(
                    "complete receipt requires youtube_video_id"
                )
        elif self.youtube_video_id is not None:
            raise ControlledYouTubeResumableUploadError(
                "incomplete receipt cannot contain youtube_video_id"
            )


@dataclass(frozen=True)
class ControlledYouTubeUploadResult:
    schema: str
    upload_id: str
    design_id: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    bytes_read: int
    bytes_transferred: int
    chunk_count: int
    youtube_video_id: str | None
    artifact_sha256: str | None
    session_fingerprint: str | None
    network_accessed: bool
    upload_executed: bool
    session_uri_persisted: bool = False
    access_token_persisted: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-upload.v1":
            raise ControlledYouTubeResumableUploadError("unsupported result schema")
        if not self.upload_id.startswith("YTUPLOAD-"):
            raise ControlledYouTubeResumableUploadError("invalid upload_id")
        if not self.design_id.startswith("YTUPLOADDESIGN-"):
            raise ControlledYouTubeResumableUploadError("invalid design_id")
        if self.status not in {"UPLOADED", "BLOCKED", "NOT_ACTIVATED"}:
            raise ControlledYouTubeResumableUploadError("unsupported upload status")
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubeResumableUploadError("checks must be boolean")
        for name, value in {
            "bytes_read": self.bytes_read,
            "bytes_transferred": self.bytes_transferred,
            "chunk_count": self.chunk_count,
        }.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ControlledYouTubeResumableUploadError(f"invalid {name}")
        if self.status == "UPLOADED":
            if self.blockers or not self.youtube_video_id:
                raise ControlledYouTubeResumableUploadError(
                    "uploaded result is internally inconsistent"
                )
            if not self.upload_executed or not self.network_accessed:
                raise ControlledYouTubeResumableUploadError(
                    "uploaded result requires controlled execution"
                )
        elif not self.blockers:
            raise ControlledYouTubeResumableUploadError(
                "non-uploaded result requires blockers"
            )
        if self.session_uri_persisted or self.access_token_persisted:
            raise ControlledYouTubeResumableUploadError(
                "session URI and access token persistence are forbidden"
            )
        if self.publication_enabled or self.auto_publish:
            raise ControlledYouTubeResumableUploadError(
                "publication and automatic publishing must remain disabled"
            )
        for value in (self.artifact_sha256, self.session_fingerprint):
            if value is not None and not _is_sha256(value):
                raise ControlledYouTubeResumableUploadError(
                    "result fingerprints must be SHA-256"
                )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "upload_id": self.upload_id,
            "design_id": self.design_id,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "bytes_read": self.bytes_read,
            "bytes_transferred": self.bytes_transferred,
            "chunk_count": self.chunk_count,
            "youtube_video_id": self.youtube_video_id,
            "artifact_sha256": self.artifact_sha256,
            "session_fingerprint": self.session_fingerprint,
            "network_accessed": self.network_accessed,
            "upload_executed": self.upload_executed,
            "session_uri_persisted": False,
            "access_token_persisted": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


def execute_controlled_youtube_upload(
    *,
    design: ControlledYouTubeUploadDesign,
    policy: YouTubeUploadActivationPolicy,
    artifact_source: UploadArtifactSource | None,
    upload_client: YouTubeResumableUploadClient | None,
) -> ControlledYouTubeUploadResult:
    """Execute one resumable upload only when every activation gate is explicit."""

    design.validate()
    policy.validate()

    activated = all(
        (
            policy.artifact_read_enabled,
            policy.session_creation_enabled,
            policy.chunk_transfer_enabled,
            policy.network_enabled,
            policy.upload_enabled,
        )
    )
    if not activated:
        checks = {
            "design_ready": design.status == "DESIGN_READY",
            "artifact_read_activated": policy.artifact_read_enabled,
            "session_creation_activated": policy.session_creation_enabled,
            "chunk_transfer_activated": policy.chunk_transfer_enabled,
            "network_activated": policy.network_enabled,
            "upload_activated": policy.upload_enabled,
            "publication_disabled": not policy.publication_enabled,
            "auto_publish_disabled": not policy.auto_publish,
        }
        return _build_result(
            design=design,
            status="NOT_ACTIVATED",
            checks=checks,
            bytes_read=0,
            bytes_transferred=0,
            chunk_count=0,
            youtube_video_id=None,
            artifact_sha256=None,
            session_fingerprint=None,
            network_accessed=False,
            upload_executed=False,
        )

    if design.status != "DESIGN_READY":
        raise ControlledYouTubeResumableUploadError(
            "blocked upload design cannot enter controlled execution"
        )
    if artifact_source is None or upload_client is None:
        raise ControlledYouTubeResumableUploadError(
            "artifact_source and upload_client are required"
        )

    session_payload = {
        "design_id": design.design_id,
        "request_id": design.request_id,
        "preparation_id": design.preparation_id,
        "channel_verification_id": design.channel_verification_id,
        "idempotency_key": design.idempotency_key,
        "artifact": design.artifact.to_dict(),
        "metadata": design.metadata.to_dict(),
        "protocol": design.policy.protocol,
        "publication_enabled": False,
        "auto_publish": False,
    }
    session_uri = upload_client.create_session(session_payload)
    if not isinstance(session_uri, str) or not session_uri.strip():
        raise ControlledYouTubeResumableUploadError(
            "resumable client returned an empty session URI"
        )
    session_fingerprint = canonical_sha256({"session_uri": session_uri})

    digest = hashlib.sha256()
    offset = 0
    bytes_read = 0
    bytes_transferred = 0
    chunk_count = 0
    youtube_video_id: str | None = None

    with artifact_source.open_binary(design.artifact.video_path) as stream:
        while offset < design.artifact.size_bytes:
            remaining = design.artifact.size_bytes - offset
            requested = min(design.policy.chunk_size_bytes, remaining)
            data = stream.read(requested)
            if not isinstance(data, bytes):
                raise ControlledYouTubeResumableUploadError(
                    "artifact source must return bytes"
                )
            if not data:
                raise ControlledYouTubeResumableUploadError(
                    "artifact ended before declared size"
                )
            if len(data) > requested:
                raise ControlledYouTubeResumableUploadError(
                    "artifact source returned more bytes than requested"
                )

            digest.update(data)
            bytes_read += len(data)
            raw_receipt = upload_client.upload_chunk(
                session_uri=session_uri,
                offset=offset,
                data=data,
                total_size=design.artifact.size_bytes,
            )
            receipt = _normalize_receipt(raw_receipt)
            receipt.validate(total_size=design.artifact.size_bytes)
            if receipt.accepted_offset != offset:
                raise ControlledYouTubeResumableUploadError(
                    "upload receipt offset does not match request offset"
                )
            if receipt.next_offset != offset + len(data):
                raise ControlledYouTubeResumableUploadError(
                    "upload receipt did not accept the complete chunk"
                )

            offset = receipt.next_offset
            bytes_transferred += len(data)
            chunk_count += 1
            if receipt.complete:
                youtube_video_id = receipt.youtube_video_id
                break

    artifact_sha256 = digest.hexdigest()
    checks = {
        "design_ready": True,
        "artifact_size_matches": bytes_read == design.artifact.size_bytes,
        "artifact_checksum_matches": artifact_sha256 == design.artifact.video_sha256,
        "all_bytes_transferred": bytes_transferred == design.artifact.size_bytes,
        "upload_completed": youtube_video_id is not None,
        "session_not_persisted": not design.policy.persist_session_uri,
        "access_token_not_persisted": not design.policy.persist_access_token,
        "publication_disabled": not policy.publication_enabled,
        "auto_publish_disabled": not policy.auto_publish,
    }
    status = "UPLOADED" if all(checks.values()) else "BLOCKED"
    return _build_result(
        design=design,
        status=status,
        checks=checks,
        bytes_read=bytes_read,
        bytes_transferred=bytes_transferred,
        chunk_count=chunk_count,
        youtube_video_id=youtube_video_id,
        artifact_sha256=artifact_sha256,
        session_fingerprint=session_fingerprint,
        network_accessed=True,
        upload_executed=True,
    )


def _normalize_receipt(payload: Mapping[str, object]) -> UploadChunkReceipt:
    if not isinstance(payload, Mapping):
        raise ControlledYouTubeResumableUploadError(
            "upload receipt must be an object"
        )
    receipt = UploadChunkReceipt(
        accepted_offset=_required_int(payload, "accepted_offset"),
        next_offset=_required_int(payload, "next_offset"),
        complete=_required_bool(payload, "complete"),
        youtube_video_id=_optional_text(payload, "youtube_video_id"),
    )
    return receipt


def _build_result(
    *,
    design: ControlledYouTubeUploadDesign,
    status: str,
    checks: Mapping[str, bool],
    bytes_read: int,
    bytes_transferred: int,
    chunk_count: int,
    youtube_video_id: str | None,
    artifact_sha256: str | None,
    session_fingerprint: str | None,
    network_accessed: bool,
    upload_executed: bool,
) -> ControlledYouTubeUploadResult:
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    evidence = {
        "design_id": design.design_id,
        "status": status,
        "checks": dict(checks),
        "bytes_read": bytes_read,
        "bytes_transferred": bytes_transferred,
        "chunk_count": chunk_count,
        "youtube_video_id": youtube_video_id,
        "artifact_sha256": artifact_sha256,
        "session_fingerprint": session_fingerprint,
        "network_accessed": network_accessed,
        "upload_executed": upload_executed,
        "publication_enabled": False,
        "auto_publish": False,
    }
    result = ControlledYouTubeUploadResult(
        schema="football-shorts-ai.controlled-youtube-upload.v1",
        upload_id=f"YTUPLOAD-{canonical_sha256(evidence)[:20].upper()}",
        design_id=design.design_id,
        status=status,
        checks=dict(checks),
        blockers=blockers,
        bytes_read=bytes_read,
        bytes_transferred=bytes_transferred,
        chunk_count=chunk_count,
        youtube_video_id=youtube_video_id if status == "UPLOADED" else None,
        artifact_sha256=artifact_sha256,
        session_fingerprint=session_fingerprint,
        network_accessed=network_accessed,
        upload_executed=upload_executed,
        session_uri_persisted=False,
        access_token_persisted=False,
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


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ControlledYouTubeResumableUploadError(f"{key} must be an integer")
    return value


def _required_bool(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ControlledYouTubeResumableUploadError(f"{key} must be boolean")
    return value


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ControlledYouTubeResumableUploadError(f"{key} must be non-empty text")
    return value.strip()


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "ControlledYouTubeResumableUploadError",
    "ControlledYouTubeUploadResult",
    "UploadArtifactSource",
    "UploadChunkReceipt",
    "YouTubeUploadActivationPolicy",
    "canonical_sha256",
    "execute_controlled_youtube_upload",
]
