"""
FOOTBALL-SHORTS-AI-0053K
CONTROLLED YOUTUBE UPLOAD CERTIFICATION

Certifies the fail-closed resumable upload implementation using only injected,
deterministic in-memory doubles. No real filesystem, credentials, network,
Google API, scheduling or publication is used.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, replace
from typing import BinaryIO, Mapping

from publishing.controlled_youtube_resumable_upload import (
    ControlledYouTubeResumableUploadError,
    UploadArtifactSource,
    YouTubeUploadActivationPolicy,
    execute_controlled_youtube_upload,
)
from publishing.controlled_youtube_upload_design import (
    ControlledYouTubeUploadDesign,
)


class ControlledYouTubeUploadCertificationError(RuntimeError):
    """Raised when certification evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class CertificationScenario:
    name: str
    status: str
    passed: bool
    evidence: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "passed": self.passed,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class ControlledYouTubeUploadCertification:
    schema: str
    certification_id: str
    status: str
    scenarios: tuple[CertificationScenario, ...]
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    evidence_sha256: str
    real_network_used: bool = False
    real_credentials_used: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-upload-certification.v1":
            raise ControlledYouTubeUploadCertificationError(
                "unsupported certification schema"
            )
        if not self.certification_id.startswith("YTUPLOADCERT-"):
            raise ControlledYouTubeUploadCertificationError(
                "invalid certification_id"
            )
        if self.status not in {"CERTIFIED", "BLOCKED"}:
            raise ControlledYouTubeUploadCertificationError(
                "unsupported certification status"
            )
        if not self.scenarios:
            raise ControlledYouTubeUploadCertificationError(
                "certification scenarios are required"
            )
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubeUploadCertificationError(
                "certification checks must be boolean"
            )
        if self.status == "CERTIFIED" and self.blockers:
            raise ControlledYouTubeUploadCertificationError(
                "certified result cannot contain blockers"
            )
        if self.status == "BLOCKED" and not self.blockers:
            raise ControlledYouTubeUploadCertificationError(
                "blocked result requires blockers"
            )
        if not _is_sha256(self.evidence_sha256):
            raise ControlledYouTubeUploadCertificationError(
                "evidence_sha256 must be SHA-256"
            )
        if self.real_network_used or self.real_credentials_used:
            raise ControlledYouTubeUploadCertificationError(
                "certification cannot use real network or credentials"
            )
        if self.publication_enabled or self.auto_publish:
            raise ControlledYouTubeUploadCertificationError(
                "publication and auto-publish must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "evidence_sha256": self.evidence_sha256,
            "real_network_used": False,
            "real_credentials_used": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


class MemoryArtifactSource(UploadArtifactSource):
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def open_binary(self, relative_path: str) -> BinaryIO:
        if not relative_path:
            raise ControlledYouTubeUploadCertificationError(
                "relative_path is required"
            )
        return io.BytesIO(self._payload)


class StaticResumableClient:
    def __init__(
        self,
        *,
        youtube_video_id: str = "yt-video-cert-001",
        offset_delta: int = 0,
    ) -> None:
        self.youtube_video_id = youtube_video_id
        self.offset_delta = offset_delta
        self.created_sessions = 0
        self.uploaded_chunks = 0

    def create_session(self, payload: Mapping[str, object]) -> str:
        self.created_sessions += 1
        if not payload.get("idempotency_key"):
            raise ControlledYouTubeUploadCertificationError(
                "idempotency key was not supplied"
            )
        return "memory://youtube/resumable/session-001"

    def upload_chunk(
        self,
        *,
        session_uri: str,
        offset: int,
        data: bytes,
        total_size: int,
    ) -> Mapping[str, object]:
        if not session_uri.startswith("memory://"):
            raise ControlledYouTubeUploadCertificationError(
                "unexpected session URI"
            )
        self.uploaded_chunks += 1
        next_offset = offset + len(data) + self.offset_delta
        complete = next_offset == total_size
        return {
            "accepted_offset": offset,
            "next_offset": next_offset,
            "complete": complete,
            "youtube_video_id": self.youtube_video_id if complete else None,
        }


def certify_controlled_youtube_upload(
    *,
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> ControlledYouTubeUploadCertification:
    """Run deterministic upload certification scenarios against one design."""

    design.validate()
    if design.status != "DESIGN_READY":
        raise ControlledYouTubeUploadCertificationError(
            "certification requires a DESIGN_READY upload design"
        )
    if not isinstance(artifact_bytes, bytes) or not artifact_bytes:
        raise ControlledYouTubeUploadCertificationError(
            "non-empty artifact_bytes are required"
        )

    scenarios = (
        _scenario_not_activated(design),
        _scenario_success(design, artifact_bytes),
        _scenario_checksum_mismatch(design, artifact_bytes),
        _scenario_declared_size_too_large(design, artifact_bytes),
        _scenario_invalid_receipt_offset(design, artifact_bytes),
        _scenario_replay_determinism(design, artifact_bytes),
    )

    checks = {
        "all_scenarios_passed": all(item.passed for item in scenarios),
        "not_activated_certified": scenarios[0].passed,
        "successful_upload_certified": scenarios[1].passed,
        "checksum_mismatch_blocked": scenarios[2].passed,
        "premature_eof_rejected": scenarios[3].passed,
        "invalid_receipt_rejected": scenarios[4].passed,
        "deterministic_replay_certified": scenarios[5].passed,
        "real_network_disabled": True,
        "real_credentials_disabled": True,
        "publication_disabled": True,
        "auto_publish_disabled": True,
    }
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    evidence = {
        "design_id": design.design_id,
        "scenarios": [item.to_dict() for item in scenarios],
        "checks": checks,
        "real_network_used": False,
        "real_credentials_used": False,
        "publication_enabled": False,
        "auto_publish": False,
    }
    evidence_sha256 = canonical_sha256(evidence)

    result = ControlledYouTubeUploadCertification(
        schema="football-shorts-ai.controlled-youtube-upload-certification.v1",
        certification_id=f"YTUPLOADCERT-{evidence_sha256[:20].upper()}",
        status="CERTIFIED" if not blockers else "BLOCKED",
        scenarios=scenarios,
        checks=checks,
        blockers=blockers,
        evidence_sha256=evidence_sha256,
        real_network_used=False,
        real_credentials_used=False,
        publication_enabled=False,
        auto_publish=False,
    )
    result.validate()
    return result


def _activated_policy() -> YouTubeUploadActivationPolicy:
    return YouTubeUploadActivationPolicy(
        artifact_read_enabled=True,
        session_creation_enabled=True,
        chunk_transfer_enabled=True,
        network_enabled=True,
        upload_enabled=True,
        publication_enabled=False,
        auto_publish=False,
    )


def _scenario_not_activated(
    design: ControlledYouTubeUploadDesign,
) -> CertificationScenario:
    result = execute_controlled_youtube_upload(
        design=design,
        policy=YouTubeUploadActivationPolicy(),
        artifact_source=None,
        upload_client=None,
    )
    passed = (
        result.status == "NOT_ACTIVATED"
        and not result.network_accessed
        and not result.upload_executed
        and result.youtube_video_id is None
    )
    return CertificationScenario(
        name="default_policy_not_activated",
        status=result.status,
        passed=passed,
        evidence=result.to_dict(),
    )


def _scenario_success(
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> CertificationScenario:
    client = StaticResumableClient()
    result = execute_controlled_youtube_upload(
        design=design,
        policy=_activated_policy(),
        artifact_source=MemoryArtifactSource(artifact_bytes),
        upload_client=client,
    )
    passed = (
        result.status == "UPLOADED"
        and result.artifact_sha256 == hashlib.sha256(artifact_bytes).hexdigest()
        and result.bytes_read == len(artifact_bytes)
        and result.bytes_transferred == len(artifact_bytes)
        and result.youtube_video_id == client.youtube_video_id
        and client.created_sessions == 1
        and client.uploaded_chunks == result.chunk_count
        and not result.session_uri_persisted
        and not result.access_token_persisted
    )
    return CertificationScenario(
        name="successful_resumable_upload",
        status=result.status,
        passed=passed,
        evidence=result.to_dict(),
    )


def _scenario_checksum_mismatch(
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> CertificationScenario:
    bad_design = replace(
        design,
        artifact=replace(design.artifact, video_sha256="0" * 64),
    )
    result = execute_controlled_youtube_upload(
        design=bad_design,
        policy=_activated_policy(),
        artifact_source=MemoryArtifactSource(artifact_bytes),
        upload_client=StaticResumableClient(),
    )
    passed = (
        result.status == "BLOCKED"
        and "ARTIFACT_CHECKSUM_MATCHES" in result.blockers
        and result.youtube_video_id is None
    )
    return CertificationScenario(
        name="checksum_mismatch_blocked",
        status=result.status,
        passed=passed,
        evidence=result.to_dict(),
    )


def _scenario_declared_size_too_large(
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> CertificationScenario:
    bad_design = replace(
        design,
        artifact=replace(
            design.artifact,
            size_bytes=len(artifact_bytes) + 1,
            video_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
        ),
    )
    passed = False
    message = ""
    try:
        execute_controlled_youtube_upload(
            design=bad_design,
            policy=_activated_policy(),
            artifact_source=MemoryArtifactSource(artifact_bytes),
            upload_client=StaticResumableClient(),
        )
    except ControlledYouTubeResumableUploadError as exc:
        message = str(exc)
        passed = "ended before declared size" in message
    return CertificationScenario(
        name="declared_size_too_large_rejected",
        status="REJECTED" if passed else "FAILED",
        passed=passed,
        evidence={"error": message},
    )


def _scenario_invalid_receipt_offset(
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> CertificationScenario:
    passed = False
    message = ""
    try:
        execute_controlled_youtube_upload(
            design=design,
            policy=_activated_policy(),
            artifact_source=MemoryArtifactSource(artifact_bytes),
            upload_client=StaticResumableClient(offset_delta=1),
        )
    except ControlledYouTubeResumableUploadError as exc:
        message = str(exc)
        passed = "complete chunk" in message or "exceeds artifact size" in message
    return CertificationScenario(
        name="invalid_receipt_offset_rejected",
        status="REJECTED" if passed else "FAILED",
        passed=passed,
        evidence={"error": message},
    )


def _scenario_replay_determinism(
    design: ControlledYouTubeUploadDesign,
    artifact_bytes: bytes,
) -> CertificationScenario:
    first = execute_controlled_youtube_upload(
        design=design,
        policy=_activated_policy(),
        artifact_source=MemoryArtifactSource(artifact_bytes),
        upload_client=StaticResumableClient(),
    )
    second = execute_controlled_youtube_upload(
        design=design,
        policy=_activated_policy(),
        artifact_source=MemoryArtifactSource(artifact_bytes),
        upload_client=StaticResumableClient(),
    )
    passed = first.to_dict() == second.to_dict()
    return CertificationScenario(
        name="deterministic_replay",
        status="PASS" if passed else "FAIL",
        passed=passed,
        evidence={
            "first_upload_id": first.upload_id,
            "second_upload_id": second.upload_id,
            "same_payload": passed,
        },
    )


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
    "CertificationScenario",
    "ControlledYouTubeUploadCertification",
    "ControlledYouTubeUploadCertificationError",
    "MemoryArtifactSource",
    "StaticResumableClient",
    "canonical_sha256",
    "certify_controlled_youtube_upload",
]
