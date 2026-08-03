"""
FOOTBALL-SHORTS-AI-0053M
CONTROLLED YOUTUBE POST-UPLOAD PROCESSING IMPLEMENTATION

Executes a 0053L post-upload design only through injected asset and YouTube
processor boundaries. All activation gates are disabled by default. No concrete
filesystem, HTTP client, Google SDK, credential resolver, publication or public
visibility implementation is provided here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import BinaryIO, Mapping, Protocol, runtime_checkable

from publishing.youtube_post_upload_processing_asset_binding_design import (
    PostUploadAsset,
    SUPPORTED_PROCESSING_STATES,
    YouTubePostUploadProcessingAssetBindingDesign,
    YouTubePostUploadProcessor,
)


class ControlledYouTubePostUploadError(ValueError):
    """Raised when controlled post-upload processing cannot proceed safely."""


@dataclass(frozen=True)
class YouTubePostUploadActivationPolicy:
    inspection_enabled: bool = False
    asset_read_enabled: bool = False
    thumbnail_binding_enabled: bool = False
    subtitles_binding_enabled: bool = False
    final_confirmation_enabled: bool = False
    network_enabled: bool = False
    mutation_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.publication_enabled:
            raise ControlledYouTubePostUploadError(
                "0053M cannot enable publication"
            )
        if self.auto_publish:
            raise ControlledYouTubePostUploadError(
                "automatic publishing must remain disabled"
            )
        execution_flags = (
            self.inspection_enabled,
            self.asset_read_enabled,
            self.thumbnail_binding_enabled,
            self.subtitles_binding_enabled,
            self.final_confirmation_enabled,
            self.mutation_enabled,
        )
        if any(execution_flags) and not self.network_enabled:
            raise ControlledYouTubePostUploadError(
                "controlled post-upload execution requires explicit network activation"
            )
        if self.thumbnail_binding_enabled and not self.asset_read_enabled:
            raise ControlledYouTubePostUploadError(
                "thumbnail binding requires asset reading"
            )
        if self.subtitles_binding_enabled and not self.asset_read_enabled:
            raise ControlledYouTubePostUploadError(
                "subtitles binding requires asset reading"
            )
        if (
            self.thumbnail_binding_enabled or self.subtitles_binding_enabled
        ) and not self.mutation_enabled:
            raise ControlledYouTubePostUploadError(
                "asset binding requires explicit mutation activation"
            )
        if self.final_confirmation_enabled and not self.inspection_enabled:
            raise ControlledYouTubePostUploadError(
                "final confirmation requires inspection"
            )


@runtime_checkable
class PostUploadAssetSource(Protocol):
    """Injected boundary for opening governed thumbnail and subtitle assets."""

    def open_binary(self, relative_path: str) -> BinaryIO:
        ...


@dataclass(frozen=True)
class AssetEvidence:
    asset_type: str
    sha256: str
    size_bytes: int

    def validate(self) -> None:
        if self.asset_type not in {"thumbnail", "subtitles"}:
            raise ControlledYouTubePostUploadError("unsupported asset evidence type")
        if not _is_sha256(self.sha256):
            raise ControlledYouTubePostUploadError("asset evidence checksum must be SHA-256")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool):
            raise ControlledYouTubePostUploadError("asset size must be an integer")
        if self.size_bytes <= 0:
            raise ControlledYouTubePostUploadError("asset size must be positive")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "asset_type": self.asset_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class PostUploadInspection:
    processing_state: str
    channel_id: str
    visibility: str
    thumbnail_bound: bool
    subtitles_bound: bool

    def validate(self) -> None:
        if self.processing_state not in SUPPORTED_PROCESSING_STATES:
            raise ControlledYouTubePostUploadError("unsupported processing state")
        if not self.channel_id.strip():
            raise ControlledYouTubePostUploadError("inspected channel_id is required")
        if self.visibility not in {"private", "unlisted", "public"}:
            raise ControlledYouTubePostUploadError("unsupported inspected visibility")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "processing_state": self.processing_state,
            "channel_id": self.channel_id,
            "visibility": self.visibility,
            "thumbnail_bound": self.thumbnail_bound,
            "subtitles_bound": self.subtitles_bound,
        }


@dataclass(frozen=True)
class ControlledYouTubePostUploadResult:
    schema: str
    execution_id: str
    design_id: str
    youtube_video_id: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    processing_checks: int
    initial_inspection: PostUploadInspection | None
    final_inspection: PostUploadInspection | None
    asset_evidence: tuple[AssetEvidence, ...]
    thumbnail_receipt_sha256: str | None
    subtitles_receipt_sha256: str | None
    network_accessed: bool
    mutation_executed: bool
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-post-upload.v1":
            raise ControlledYouTubePostUploadError("unsupported result schema")
        if not self.execution_id.startswith("YTPOST-"):
            raise ControlledYouTubePostUploadError("invalid execution_id")
        if not self.design_id.startswith("YTPOSTDESIGN-"):
            raise ControlledYouTubePostUploadError("invalid design_id")
        if not self.youtube_video_id.strip():
            raise ControlledYouTubePostUploadError("youtube_video_id is required")
        if self.status not in {"COMPLETED", "BLOCKED", "NOT_ACTIVATED"}:
            raise ControlledYouTubePostUploadError("unsupported result status")
        if set(self.checks.values()) - {True, False}:
            raise ControlledYouTubePostUploadError("checks must be boolean")
        if not isinstance(self.processing_checks, int) or isinstance(
            self.processing_checks, bool
        ) or self.processing_checks < 0:
            raise ControlledYouTubePostUploadError("invalid processing_checks")
        if self.status == "COMPLETED":
            if self.blockers or self.final_inspection is None:
                raise ControlledYouTubePostUploadError(
                    "completed result is internally inconsistent"
                )
            if not self.network_accessed or not self.mutation_executed:
                raise ControlledYouTubePostUploadError(
                    "completed result requires controlled network mutation"
                )
        elif not self.blockers:
            raise ControlledYouTubePostUploadError(
                "non-completed result requires blockers"
            )
        for inspection in (self.initial_inspection, self.final_inspection):
            if inspection is not None:
                inspection.validate()
        if self.asset_evidence:
            if {item.asset_type for item in self.asset_evidence} != {
                "thumbnail",
                "subtitles",
            }:
                raise ControlledYouTubePostUploadError(
                    "asset evidence must contain thumbnail and subtitles"
                )
            for item in self.asset_evidence:
                item.validate()
        for value in (
            self.thumbnail_receipt_sha256,
            self.subtitles_receipt_sha256,
        ):
            if value is not None and not _is_sha256(value):
                raise ControlledYouTubePostUploadError(
                    "binding receipt fingerprints must be SHA-256"
                )
        if self.publication_enabled or self.auto_publish:
            raise ControlledYouTubePostUploadError(
                "publication and automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "execution_id": self.execution_id,
            "design_id": self.design_id,
            "youtube_video_id": self.youtube_video_id,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "processing_checks": self.processing_checks,
            "initial_inspection": (
                self.initial_inspection.to_dict()
                if self.initial_inspection is not None
                else None
            ),
            "final_inspection": (
                self.final_inspection.to_dict()
                if self.final_inspection is not None
                else None
            ),
            "asset_evidence": [item.to_dict() for item in self.asset_evidence],
            "thumbnail_receipt_sha256": self.thumbnail_receipt_sha256,
            "subtitles_receipt_sha256": self.subtitles_receipt_sha256,
            "network_accessed": self.network_accessed,
            "mutation_executed": self.mutation_executed,
            "publication_enabled": False,
            "auto_publish": False,
        }


def execute_controlled_youtube_post_upload_processing(
    *,
    design: YouTubePostUploadProcessingAssetBindingDesign,
    policy: YouTubePostUploadActivationPolicy,
    processor: YouTubePostUploadProcessor | None,
    asset_source: PostUploadAssetSource | None,
) -> ControlledYouTubePostUploadResult:
    """Execute post-upload checks and bindings only when every gate is explicit."""

    design.validate()
    policy.validate()

    activated = all(
        (
            policy.inspection_enabled,
            policy.asset_read_enabled,
            policy.thumbnail_binding_enabled,
            policy.subtitles_binding_enabled,
            policy.final_confirmation_enabled,
            policy.network_enabled,
            policy.mutation_enabled,
        )
    )
    if not activated:
        checks = {
            "design_ready": design.status == "DESIGN_READY",
            "inspection_activated": policy.inspection_enabled,
            "asset_read_activated": policy.asset_read_enabled,
            "thumbnail_binding_activated": policy.thumbnail_binding_enabled,
            "subtitles_binding_activated": policy.subtitles_binding_enabled,
            "final_confirmation_activated": policy.final_confirmation_enabled,
            "network_activated": policy.network_enabled,
            "mutation_activated": policy.mutation_enabled,
            "publication_disabled": not policy.publication_enabled,
            "auto_publish_disabled": not policy.auto_publish,
        }
        return _build_result(
            design=design,
            status="NOT_ACTIVATED",
            checks=checks,
            processing_checks=0,
            initial_inspection=None,
            final_inspection=None,
            asset_evidence=(),
            thumbnail_receipt_sha256=None,
            subtitles_receipt_sha256=None,
            network_accessed=False,
            mutation_executed=False,
        )

    if design.status != "DESIGN_READY":
        raise ControlledYouTubePostUploadError(
            "blocked post-upload design cannot enter controlled execution"
        )
    if processor is None or asset_source is None:
        raise ControlledYouTubePostUploadError(
            "processor and asset_source are required"
        )

    initial, processing_checks = _wait_for_processing(
        processor=processor,
        youtube_video_id=design.youtube_video_id,
        maximum=design.policy.max_processing_checks,
    )

    assets = {item.asset_type: item for item in design.assets}
    thumbnail_evidence = _read_asset_evidence(
        asset=assets["thumbnail"],
        source=asset_source,
    )
    subtitles_evidence = _read_asset_evidence(
        asset=assets["subtitles"],
        source=asset_source,
    )

    pre_binding_checks = {
        "processing_succeeded": initial.processing_state
        == design.policy.required_processing_state,
        "channel_identity_matches": initial.channel_id == design.expected_channel_id,
        "visibility_non_public": initial.visibility
        == design.policy.required_visibility,
        "thumbnail_checksum_matches": (
            thumbnail_evidence.sha256 == assets["thumbnail"].sha256
        ),
        "subtitles_checksum_matches": (
            subtitles_evidence.sha256 == assets["subtitles"].sha256
        ),
    }
    if not all(pre_binding_checks.values()):
        return _build_result(
            design=design,
            status="BLOCKED",
            checks={
                **pre_binding_checks,
                "thumbnail_bound": False,
                "subtitles_bound": False,
                "final_processing_succeeded": False,
                "final_channel_identity_matches": False,
                "final_visibility_matches": False,
                "publication_disabled": not policy.publication_enabled,
                "auto_publish_disabled": not policy.auto_publish,
            },
            processing_checks=processing_checks,
            initial_inspection=initial,
            final_inspection=None,
            asset_evidence=(thumbnail_evidence, subtitles_evidence),
            thumbnail_receipt_sha256=None,
            subtitles_receipt_sha256=None,
            network_accessed=True,
            mutation_executed=False,
        )

    thumbnail_receipt = processor.bind_thumbnail(
        design.youtube_video_id,
        assets["thumbnail"],
    )
    subtitles_receipt = processor.bind_subtitles(
        design.youtube_video_id,
        assets["subtitles"],
    )
    thumbnail_bound = _receipt_succeeded(thumbnail_receipt, "thumbnail")
    subtitles_bound = _receipt_succeeded(subtitles_receipt, "subtitles")

    final = _normalize_inspection(processor.inspect_video(design.youtube_video_id))
    processing_checks += 1
    checks = {
        **pre_binding_checks,
        "thumbnail_bound": thumbnail_bound and final.thumbnail_bound,
        "subtitles_bound": subtitles_bound and final.subtitles_bound,
        "final_processing_succeeded": (
            final.processing_state == design.policy.required_processing_state
        ),
        "final_channel_identity_matches": (
            final.channel_id == design.expected_channel_id
        ),
        "final_visibility_matches": (
            final.visibility == design.policy.required_visibility
        ),
        "publication_disabled": not policy.publication_enabled,
        "auto_publish_disabled": not policy.auto_publish,
    }
    status = "COMPLETED" if all(checks.values()) else "BLOCKED"
    return _build_result(
        design=design,
        status=status,
        checks=checks,
        processing_checks=processing_checks,
        initial_inspection=initial,
        final_inspection=final,
        asset_evidence=(thumbnail_evidence, subtitles_evidence),
        thumbnail_receipt_sha256=canonical_sha256(thumbnail_receipt),
        subtitles_receipt_sha256=canonical_sha256(subtitles_receipt),
        network_accessed=True,
        mutation_executed=True,
    )


def _wait_for_processing(
    *,
    processor: YouTubePostUploadProcessor,
    youtube_video_id: str,
    maximum: int,
) -> tuple[PostUploadInspection, int]:
    last: PostUploadInspection | None = None
    for attempt in range(1, maximum + 1):
        last = _normalize_inspection(processor.inspect_video(youtube_video_id))
        if last.processing_state == "succeeded":
            return last, attempt
        if last.processing_state in {"failed", "rejected"}:
            return last, attempt
    if last is None:
        raise ControlledYouTubePostUploadError("processing inspection produced no result")
    return last, maximum


def _read_asset_evidence(
    *,
    asset: PostUploadAsset,
    source: PostUploadAssetSource,
) -> AssetEvidence:
    digest = hashlib.sha256()
    size = 0
    with source.open_binary(asset.path) as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not isinstance(chunk, bytes):
                raise ControlledYouTubePostUploadError(
                    "asset source must return bytes"
                )
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    evidence = AssetEvidence(
        asset_type=asset.asset_type,
        sha256=digest.hexdigest(),
        size_bytes=size,
    )
    evidence.validate()
    return evidence


def _normalize_inspection(payload: Mapping[str, object]) -> PostUploadInspection:
    if not isinstance(payload, Mapping):
        raise ControlledYouTubePostUploadError("inspection must be an object")
    inspection = PostUploadInspection(
        processing_state=_required_text(payload, "processing_state"),
        channel_id=_required_text(payload, "channel_id"),
        visibility=_required_text(payload, "visibility"),
        thumbnail_bound=_required_bool(payload, "thumbnail_bound"),
        subtitles_bound=_required_bool(payload, "subtitles_bound"),
    )
    inspection.validate()
    return inspection


def _receipt_succeeded(payload: Mapping[str, object], expected_asset_type: str) -> bool:
    if not isinstance(payload, Mapping):
        raise ControlledYouTubePostUploadError("binding receipt must be an object")
    asset_type = _required_text(payload, "asset_type")
    succeeded = _required_bool(payload, "succeeded")
    if asset_type != expected_asset_type:
        raise ControlledYouTubePostUploadError("binding receipt asset type mismatch")
    return succeeded


def _build_result(
    *,
    design: YouTubePostUploadProcessingAssetBindingDesign,
    status: str,
    checks: Mapping[str, bool],
    processing_checks: int,
    initial_inspection: PostUploadInspection | None,
    final_inspection: PostUploadInspection | None,
    asset_evidence: tuple[AssetEvidence, ...],
    thumbnail_receipt_sha256: str | None,
    subtitles_receipt_sha256: str | None,
    network_accessed: bool,
    mutation_executed: bool,
) -> ControlledYouTubePostUploadResult:
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    evidence = {
        "design_id": design.design_id,
        "youtube_video_id": design.youtube_video_id,
        "status": status,
        "checks": dict(checks),
        "processing_checks": processing_checks,
        "initial_inspection": (
            initial_inspection.to_dict() if initial_inspection is not None else None
        ),
        "final_inspection": (
            final_inspection.to_dict() if final_inspection is not None else None
        ),
        "asset_evidence": [item.to_dict() for item in asset_evidence],
        "thumbnail_receipt_sha256": thumbnail_receipt_sha256,
        "subtitles_receipt_sha256": subtitles_receipt_sha256,
        "network_accessed": network_accessed,
        "mutation_executed": mutation_executed,
        "publication_enabled": False,
        "auto_publish": False,
    }
    result = ControlledYouTubePostUploadResult(
        schema="football-shorts-ai.controlled-youtube-post-upload.v1",
        execution_id=f"YTPOST-{canonical_sha256(evidence)[:20].upper()}",
        design_id=design.design_id,
        youtube_video_id=design.youtube_video_id,
        status=status,
        checks=dict(checks),
        blockers=blockers,
        processing_checks=processing_checks,
        initial_inspection=initial_inspection,
        final_inspection=final_inspection,
        asset_evidence=asset_evidence,
        thumbnail_receipt_sha256=thumbnail_receipt_sha256,
        subtitles_receipt_sha256=subtitles_receipt_sha256,
        network_accessed=network_accessed,
        mutation_executed=mutation_executed,
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


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ControlledYouTubePostUploadError(f"{key} is required")
    return value.strip()


def _required_bool(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ControlledYouTubePostUploadError(f"{key} must be boolean")
    return value


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "AssetEvidence",
    "ControlledYouTubePostUploadError",
    "ControlledYouTubePostUploadResult",
    "PostUploadAssetSource",
    "PostUploadInspection",
    "YouTubePostUploadActivationPolicy",
    "canonical_sha256",
    "execute_controlled_youtube_post_upload_processing",
]
