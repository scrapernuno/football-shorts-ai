"""
FOOTBALL-SHORTS-AI-0053L
YOUTUBE POST-UPLOAD PROCESSING AND ASSET BINDING DESIGN

Defines the governed post-upload design for processing verification, thumbnail
and subtitle binding, channel confirmation and visibility confirmation. This
module does not call YouTube APIs, read credentials, mutate remote videos,
schedule publication or make content public.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Protocol, runtime_checkable

from publishing.controlled_youtube_resumable_upload import ControlledYouTubeUploadResult
from publishing.controlled_youtube_upload_design import ControlledYouTubeUploadDesign


SUPPORTED_PROCESSING_STATES = {"uploaded", "processing", "succeeded", "failed", "rejected"}
SUPPORTED_VISIBILITY = {"private", "unlisted"}
SUPPORTED_ASSET_TYPES = {"thumbnail", "subtitles"}
SUPPORTED_OPERATIONS = {
    "verify_processing_state",
    "confirm_channel_binding",
    "bind_thumbnail",
    "bind_subtitles",
    "confirm_visibility",
}


class YouTubePostUploadDesignError(ValueError):
    """Raised when post-upload design evidence is malformed or unsafe."""


@dataclass(frozen=True)
class PostUploadAsset:
    asset_type: str
    path: str
    sha256: str
    mime_type: str
    language: str | None = None

    def validate(self) -> None:
        if self.asset_type not in SUPPORTED_ASSET_TYPES:
            raise YouTubePostUploadDesignError("unsupported post-upload asset type")
        path = PurePosixPath(self.path)
        if path.is_absolute() or ".." in path.parts or not self.path.strip():
            raise YouTubePostUploadDesignError("asset path must be relative and safe")
        if not _is_sha256(self.sha256):
            raise YouTubePostUploadDesignError("asset checksum must be SHA-256")
        if self.asset_type == "thumbnail":
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                raise YouTubePostUploadDesignError("thumbnail must be JPG or PNG")
            if self.mime_type not in {"image/jpeg", "image/png"}:
                raise YouTubePostUploadDesignError("invalid thumbnail MIME type")
            if self.language is not None:
                raise YouTubePostUploadDesignError("thumbnail cannot declare language")
        else:
            if path.suffix.lower() not in {".srt", ".vtt"}:
                raise YouTubePostUploadDesignError("subtitles must be SRT or VTT")
            if self.mime_type not in {"application/x-subrip", "text/vtt"}:
                raise YouTubePostUploadDesignError("invalid subtitles MIME type")
            if not self.language or not self.language.strip():
                raise YouTubePostUploadDesignError("subtitle language is required")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "asset_type": self.asset_type,
            "path": self.path,
            "sha256": self.sha256,
            "mime_type": self.mime_type,
            "language": self.language,
        }


@dataclass(frozen=True)
class PostUploadPolicy:
    required_processing_state: str = "succeeded"
    required_visibility: str = "private"
    require_channel_identity_match: bool = True
    require_thumbnail_binding: bool = True
    require_subtitles_binding: bool = True
    max_processing_checks: int = 20
    network_enabled: bool = False
    mutation_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.required_processing_state != "succeeded":
            raise YouTubePostUploadDesignError("processing must succeed before completion")
        if self.required_visibility not in SUPPORTED_VISIBILITY:
            raise YouTubePostUploadDesignError("post-upload visibility must remain non-public")
        if not self.require_channel_identity_match:
            raise YouTubePostUploadDesignError("channel identity match is mandatory")
        if not self.require_thumbnail_binding or not self.require_subtitles_binding:
            raise YouTubePostUploadDesignError("thumbnail and subtitles binding are mandatory")
        if not isinstance(self.max_processing_checks, int) or isinstance(self.max_processing_checks, bool):
            raise YouTubePostUploadDesignError("max_processing_checks must be an integer")
        if not 1 <= self.max_processing_checks <= 100:
            raise YouTubePostUploadDesignError("max_processing_checks is outside governed limits")
        if self.network_enabled or self.mutation_enabled or self.publication_enabled:
            raise YouTubePostUploadDesignError("0053L cannot enable network, mutation or publication")
        if self.auto_publish:
            raise YouTubePostUploadDesignError("automatic publishing must remain disabled")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "required_processing_state": self.required_processing_state,
            "required_visibility": self.required_visibility,
            "require_channel_identity_match": True,
            "require_thumbnail_binding": True,
            "require_subtitles_binding": True,
            "max_processing_checks": self.max_processing_checks,
            "network_enabled": False,
            "mutation_enabled": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


@dataclass(frozen=True)
class YouTubePostUploadProcessingAssetBindingDesign:
    schema: str
    design_id: str
    upload_id: str
    upload_design_id: str
    youtube_video_id: str
    expected_channel_verification_id: str
    expected_channel_id: str
    assets: tuple[PostUploadAsset, ...]
    operations: tuple[str, ...]
    policy: PostUploadPolicy
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    status: str
    evidence_sha256: str
    network_enabled: bool = False
    mutation_enabled: bool = False
    publication_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-post-upload-design.v1":
            raise YouTubePostUploadDesignError("unsupported post-upload design schema")
        if not self.design_id.startswith("YTPOSTDESIGN-"):
            raise YouTubePostUploadDesignError("invalid design_id")
        if not self.upload_id.startswith("YTUPLOAD-"):
            raise YouTubePostUploadDesignError("invalid upload_id")
        if not self.upload_design_id.startswith("YTUPLOADDESIGN-"):
            raise YouTubePostUploadDesignError("invalid upload design identity")
        if not self.youtube_video_id.strip():
            raise YouTubePostUploadDesignError("youtube_video_id is required")
        if not self.expected_channel_verification_id.startswith("YTVERIFY-"):
            raise YouTubePostUploadDesignError("invalid channel verification identity")
        if not self.expected_channel_id.strip():
            raise YouTubePostUploadDesignError("expected_channel_id is required")
        if len(self.assets) != 2 or {item.asset_type for item in self.assets} != SUPPORTED_ASSET_TYPES:
            raise YouTubePostUploadDesignError("exactly one thumbnail and one subtitles asset are required")
        for asset in self.assets:
            asset.validate()
        if set(self.operations) != SUPPORTED_OPERATIONS:
            raise YouTubePostUploadDesignError("post-upload operation set is incomplete")
        self.policy.validate()
        if set(self.checks.values()) - {True, False}:
            raise YouTubePostUploadDesignError("checks must be boolean")
        if self.status not in {"DESIGN_READY", "BLOCKED"}:
            raise YouTubePostUploadDesignError("unsupported design status")
        if self.status == "DESIGN_READY" and self.blockers:
            raise YouTubePostUploadDesignError("ready design cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise YouTubePostUploadDesignError("blocked design requires blockers")
        if not _is_sha256(self.evidence_sha256):
            raise YouTubePostUploadDesignError("evidence_sha256 must be SHA-256")
        if self.network_enabled or self.mutation_enabled or self.publication_enabled or self.auto_publish:
            raise YouTubePostUploadDesignError("post-upload design must remain non-executable")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "design_id": self.design_id,
            "upload_id": self.upload_id,
            "upload_design_id": self.upload_design_id,
            "youtube_video_id": self.youtube_video_id,
            "expected_channel_verification_id": self.expected_channel_verification_id,
            "expected_channel_id": self.expected_channel_id,
            "assets": [asset.to_dict() for asset in self.assets],
            "operations": list(self.operations),
            "policy": self.policy.to_dict(),
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "status": self.status,
            "evidence_sha256": self.evidence_sha256,
            "network_enabled": False,
            "mutation_enabled": False,
            "publication_enabled": False,
            "auto_publish": False,
        }


@runtime_checkable
class YouTubePostUploadProcessor(Protocol):
    def inspect_video(self, youtube_video_id: str) -> Mapping[str, object]: ...
    def bind_thumbnail(self, youtube_video_id: str, asset: PostUploadAsset) -> Mapping[str, object]: ...
    def bind_subtitles(self, youtube_video_id: str, asset: PostUploadAsset) -> Mapping[str, object]: ...


def build_youtube_post_upload_processing_asset_binding_design(
    *,
    upload_design: ControlledYouTubeUploadDesign,
    upload_result: ControlledYouTubeUploadResult,
    expected_channel_id: str,
    thumbnail_path: str,
    thumbnail_sha256: str,
    thumbnail_mime_type: str,
    subtitles_path: str,
    subtitles_sha256: str,
    subtitles_mime_type: str,
    subtitles_language: str,
) -> YouTubePostUploadProcessingAssetBindingDesign:
    upload_design.validate()
    upload_result.validate()

    thumbnail = PostUploadAsset("thumbnail", thumbnail_path, thumbnail_sha256, thumbnail_mime_type)
    subtitles = PostUploadAsset("subtitles", subtitles_path, subtitles_sha256, subtitles_mime_type, subtitles_language)
    thumbnail.validate()
    subtitles.validate()
    policy = PostUploadPolicy()
    policy.validate()

    checks = {
        "upload_completed": upload_result.status == "UPLOADED",
        "upload_identity_matches": upload_result.design_id == upload_design.design_id,
        "youtube_video_id_present": bool(upload_result.youtube_video_id),
        "channel_verification_bound": upload_design.channel_verification_id.startswith("YTVERIFY-"),
        "expected_channel_id_present": bool(expected_channel_id.strip()),
        "thumbnail_valid": True,
        "subtitles_valid": True,
        "processing_success_required": policy.required_processing_state == "succeeded",
        "visibility_remains_non_public": policy.required_visibility in SUPPORTED_VISIBILITY,
        "network_disabled": not policy.network_enabled,
        "mutation_disabled": not policy.mutation_enabled,
        "publication_disabled": not policy.publication_enabled,
        "auto_publish_disabled": not policy.auto_publish,
    }
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)
    youtube_video_id = upload_result.youtube_video_id or "BLOCKED"
    evidence = {
        "upload_id": upload_result.upload_id,
        "upload_design_id": upload_design.design_id,
        "youtube_video_id": youtube_video_id,
        "expected_channel_verification_id": upload_design.channel_verification_id,
        "expected_channel_id": expected_channel_id,
        "assets": [thumbnail.to_dict(), subtitles.to_dict()],
        "operations": sorted(SUPPORTED_OPERATIONS),
        "policy": policy.to_dict(),
        "checks": checks,
    }
    evidence_sha256 = canonical_sha256(evidence)
    result = YouTubePostUploadProcessingAssetBindingDesign(
        schema="football-shorts-ai.youtube-post-upload-design.v1",
        design_id=f"YTPOSTDESIGN-{evidence_sha256[:20].upper()}",
        upload_id=upload_result.upload_id,
        upload_design_id=upload_design.design_id,
        youtube_video_id=youtube_video_id,
        expected_channel_verification_id=upload_design.channel_verification_id,
        expected_channel_id=expected_channel_id,
        assets=(thumbnail, subtitles),
        operations=tuple(sorted(SUPPORTED_OPERATIONS)),
        policy=policy,
        checks=checks,
        blockers=blockers,
        status="DESIGN_READY" if not blockers else "BLOCKED",
        evidence_sha256=evidence_sha256,
        network_enabled=False,
        mutation_enabled=False,
        publication_enabled=False,
        auto_publish=False,
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
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
    "PostUploadAsset",
    "PostUploadPolicy",
    "SUPPORTED_ASSET_TYPES",
    "SUPPORTED_OPERATIONS",
    "SUPPORTED_PROCESSING_STATES",
    "SUPPORTED_VISIBILITY",
    "YouTubePostUploadDesignError",
    "YouTubePostUploadProcessingAssetBindingDesign",
    "YouTubePostUploadProcessor",
    "build_youtube_post_upload_processing_asset_binding_design",
    "canonical_sha256",
]
