"""
FOOTBALL-SHORTS-AI-0053N
CONTROLLED YOUTUBE POST-UPLOAD CERTIFICATION

Certifies the 0053L/0053M post-upload boundary with deterministic in-memory
fixtures only. No real filesystem, network, credential, YouTube mutation,
publication or automatic publishing operation is performed.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from typing import BinaryIO, Mapping

from publishing.controlled_youtube_post_upload_processing import (
    ControlledYouTubePostUploadError,
    YouTubePostUploadActivationPolicy,
    execute_controlled_youtube_post_upload_processing,
)
from publishing.youtube_post_upload_processing_asset_binding_design import (
    PostUploadAsset,
    PostUploadPolicy,
    YouTubePostUploadProcessingAssetBindingDesign,
    canonical_sha256,
)


class ControlledYouTubePostUploadCertificationError(AssertionError):
    """Raised when one certification scenario does not behave as required."""


THUMBNAIL_BYTES = b"\x89PNG\r\n\x1a\nfootball-shorts-ai-thumbnail"
SUBTITLES_BYTES = (
    b"WEBVTT\n\n00:00.000 --> 00:02.000\nFootball Shorts AI certification\n"
)
EXPECTED_CHANNEL_ID = "UC1234567890ABCDEFGHIJKL"
YOUTUBE_VIDEO_ID = "YT-VIDEO-0053N"


@dataclass
class MemoryAssetSource:
    assets: Mapping[str, bytes]

    def open_binary(self, relative_path: str) -> BinaryIO:
        if relative_path not in self.assets:
            raise ControlledYouTubePostUploadCertificationError(
                f"unexpected asset path: {relative_path}"
            )
        return io.BytesIO(self.assets[relative_path])


class FakePostUploadProcessor:
    def __init__(
        self,
        *,
        initial_states: tuple[str, ...] = ("processing", "succeeded"),
        channel_id: str = EXPECTED_CHANNEL_ID,
        visibility: str = "private",
        thumbnail_receipt_success: bool = True,
        subtitles_receipt_success: bool = True,
        final_thumbnail_bound: bool = True,
        final_subtitles_bound: bool = True,
    ) -> None:
        self._states = list(initial_states)
        self._channel_id = channel_id
        self._visibility = visibility
        self._thumbnail_receipt_success = thumbnail_receipt_success
        self._subtitles_receipt_success = subtitles_receipt_success
        self._final_thumbnail_bound = final_thumbnail_bound
        self._final_subtitles_bound = final_subtitles_bound
        self._thumbnail_called = False
        self._subtitles_called = False

    def inspect_video(self, youtube_video_id: str) -> Mapping[str, object]:
        _assert(youtube_video_id == YOUTUBE_VIDEO_ID, "unexpected YouTube video id")
        if self._states:
            state = self._states.pop(0)
            is_final = not self._states and state == "succeeded"
        else:
            state = "succeeded"
            is_final = True
        return {
            "processing_state": state,
            "channel_id": self._channel_id,
            "visibility": self._visibility,
            "thumbnail_bound": (
                self._final_thumbnail_bound and self._thumbnail_called and is_final
            ),
            "subtitles_bound": (
                self._final_subtitles_bound and self._subtitles_called and is_final
            ),
        }

    def bind_thumbnail(
        self,
        youtube_video_id: str,
        asset: PostUploadAsset,
    ) -> Mapping[str, object]:
        _assert(youtube_video_id == YOUTUBE_VIDEO_ID, "thumbnail video id mismatch")
        _assert(asset.asset_type == "thumbnail", "thumbnail asset type mismatch")
        self._thumbnail_called = True
        return {
            "operation": "thumbnail",
            "status": "succeeded" if self._thumbnail_receipt_success else "failed",
            "youtube_video_id": youtube_video_id,
        }

    def bind_subtitles(
        self,
        youtube_video_id: str,
        asset: PostUploadAsset,
    ) -> Mapping[str, object]:
        _assert(youtube_video_id == YOUTUBE_VIDEO_ID, "subtitles video id mismatch")
        _assert(asset.asset_type == "subtitles", "subtitles asset type mismatch")
        self._subtitles_called = True
        return {
            "operation": "subtitles",
            "status": "succeeded" if self._subtitles_receipt_success else "failed",
            "youtube_video_id": youtube_video_id,
        }


def _design(
    *,
    thumbnail_sha256: str | None = None,
    subtitles_sha256: str | None = None,
    maximum_checks: int = 5,
) -> YouTubePostUploadProcessingAssetBindingDesign:
    thumbnail = PostUploadAsset(
        asset_type="thumbnail",
        path="dashboard/assets/VID-000001-thumbnail.png",
        sha256=thumbnail_sha256 or _sha256(THUMBNAIL_BYTES),
        mime_type="image/png",
        language=None,
    )
    subtitles = PostUploadAsset(
        asset_type="subtitles",
        path="dashboard/assets/VID-000001-en.vtt",
        sha256=subtitles_sha256 or _sha256(SUBTITLES_BYTES),
        mime_type="text/vtt",
        language="en",
    )
    policy = PostUploadPolicy(max_processing_checks=maximum_checks)
    checks = {
        "upload_completed": True,
        "upload_identity_matches": True,
        "youtube_video_id_present": True,
        "channel_verification_bound": True,
        "expected_channel_id_present": True,
        "thumbnail_valid": True,
        "subtitles_valid": True,
        "processing_success_required": True,
        "visibility_remains_non_public": True,
        "network_disabled": True,
        "mutation_disabled": True,
        "publication_disabled": True,
        "auto_publish_disabled": True,
    }
    evidence = {
        "upload_id": "YTUPLOAD-0053N",
        "upload_design_id": "YTUPLOADDESIGN-0053N",
        "youtube_video_id": YOUTUBE_VIDEO_ID,
        "expected_channel_verification_id": "YTVERIFY-0053N",
        "expected_channel_id": EXPECTED_CHANNEL_ID,
        "assets": [thumbnail.to_dict(), subtitles.to_dict()],
        "operations": [
            "bind_subtitles",
            "bind_thumbnail",
            "confirm_channel_binding",
            "confirm_visibility",
            "verify_processing_state",
        ],
        "policy": policy.to_dict(),
        "checks": checks,
    }
    evidence_sha256 = canonical_sha256(evidence)
    design = YouTubePostUploadProcessingAssetBindingDesign(
        schema="football-shorts-ai.youtube-post-upload-design.v1",
        design_id=f"YTPOSTDESIGN-{evidence_sha256[:20].upper()}",
        upload_id="YTUPLOAD-0053N",
        upload_design_id="YTUPLOADDESIGN-0053N",
        youtube_video_id=YOUTUBE_VIDEO_ID,
        expected_channel_verification_id="YTVERIFY-0053N",
        expected_channel_id=EXPECTED_CHANNEL_ID,
        assets=(thumbnail, subtitles),
        operations=(
            "bind_subtitles",
            "bind_thumbnail",
            "confirm_channel_binding",
            "confirm_visibility",
            "verify_processing_state",
        ),
        policy=policy,
        checks=checks,
        blockers=(),
        status="DESIGN_READY",
        evidence_sha256=evidence_sha256,
        network_enabled=False,
        mutation_enabled=False,
        publication_enabled=False,
        auto_publish=False,
    )
    design.validate()
    return design


def _active_policy() -> YouTubePostUploadActivationPolicy:
    return YouTubePostUploadActivationPolicy(
        inspection_enabled=True,
        asset_read_enabled=True,
        thumbnail_binding_enabled=True,
        subtitles_binding_enabled=True,
        final_confirmation_enabled=True,
        network_enabled=True,
        mutation_enabled=True,
        publication_enabled=False,
        auto_publish=False,
    )


def _source(
    *,
    thumbnail: bytes = THUMBNAIL_BYTES,
    subtitles: bytes = SUBTITLES_BYTES,
) -> MemoryAssetSource:
    return MemoryAssetSource(
        {
            "dashboard/assets/VID-000001-thumbnail.png": thumbnail,
            "dashboard/assets/VID-000001-en.vtt": subtitles,
        }
    )


def certify_not_activated() -> dict[str, object]:
    result = execute_controlled_youtube_post_upload_processing(
        design=_design(),
        policy=YouTubePostUploadActivationPolicy(),
        processor=None,
        asset_source=None,
    )
    _assert(result.status == "NOT_ACTIVATED", "default policy must fail closed")
    _assert(not result.network_accessed, "default path accessed network")
    _assert(not result.mutation_executed, "default path executed mutation")
    return result.to_dict()


def certify_success() -> dict[str, object]:
    result = execute_controlled_youtube_post_upload_processing(
        design=_design(),
        policy=_active_policy(),
        processor=FakePostUploadProcessor(),
        asset_source=_source(),
    )
    _assert(result.status == "COMPLETED", "controlled success did not complete")
    _assert(result.processing_checks == 3, "unexpected processing check count")
    _assert(result.final_inspection is not None, "final inspection missing")
    _assert(result.final_inspection.thumbnail_bound, "thumbnail was not confirmed")
    _assert(result.final_inspection.subtitles_bound, "subtitles were not confirmed")
    _assert(not result.publication_enabled, "publication was enabled")
    _assert(not result.auto_publish, "automatic publishing was enabled")
    return result.to_dict()


def certify_channel_mismatch_blocked() -> dict[str, object]:
    result = execute_controlled_youtube_post_upload_processing(
        design=_design(),
        policy=_active_policy(),
        processor=FakePostUploadProcessor(channel_id="UC0000000000000000000000"),
        asset_source=_source(),
    )
    _assert(result.status == "BLOCKED", "channel mismatch was not blocked")
    _assert("CHANNEL_IDENTITY_MATCHES" in result.blockers, "channel blocker missing")
    _assert(not result.mutation_executed, "mutation occurred after channel mismatch")
    return result.to_dict()


def certify_checksum_mismatch_blocked() -> dict[str, object]:
    result = execute_controlled_youtube_post_upload_processing(
        design=_design(),
        policy=_active_policy(),
        processor=FakePostUploadProcessor(),
        asset_source=_source(thumbnail=b"tampered-thumbnail"),
    )
    _assert(result.status == "BLOCKED", "checksum mismatch was not blocked")
    _assert("THUMBNAIL_CHECKSUM_MATCHES" in result.blockers, "checksum blocker missing")
    _assert(not result.mutation_executed, "mutation occurred after checksum mismatch")
    return result.to_dict()


def certify_processing_failure_rejected() -> str:
    try:
        execute_controlled_youtube_post_upload_processing(
            design=_design(),
            policy=_active_policy(),
            processor=FakePostUploadProcessor(initial_states=("processing", "failed")),
            asset_source=_source(),
        )
    except ControlledYouTubePostUploadError as exc:
        _assert("failed" in str(exc).lower(), "processing failure attribution missing")
        return type(exc).__name__
    raise ControlledYouTubePostUploadCertificationError(
        "failed processing state did not fail closed"
    )


def certify_incomplete_bindings_blocked() -> dict[str, object]:
    result = execute_controlled_youtube_post_upload_processing(
        design=_design(),
        policy=_active_policy(),
        processor=FakePostUploadProcessor(final_subtitles_bound=False),
        asset_source=_source(),
    )
    _assert(result.status == "BLOCKED", "incomplete binding was not blocked")
    _assert("SUBTITLES_BOUND" in result.blockers, "subtitles blocker missing")
    return result.to_dict()


def certify_deterministic_replay() -> str:
    first = certify_success()
    second = certify_success()
    first.pop("execution_id", None)
    second.pop("execution_id", None)
    first_sha = canonical_sha256(first)
    second_sha = canonical_sha256(second)
    _assert(first_sha == second_sha, "controlled replay is not deterministic")
    return first_sha


def run_certification() -> dict[str, object]:
    scenarios = {
        "not_activated": certify_not_activated(),
        "controlled_success": certify_success(),
        "channel_mismatch": certify_channel_mismatch_blocked(),
        "checksum_mismatch": certify_checksum_mismatch_blocked(),
        "processing_failure": certify_processing_failure_rejected(),
        "incomplete_bindings": certify_incomplete_bindings_blocked(),
        "deterministic_replay_sha256": certify_deterministic_replay(),
    }
    report = {
        "schema": "football-shorts-ai.controlled-youtube-post-upload-certification.v1",
        "artifact": "FOOTBALL-SHORTS-AI-0053N",
        "status": "CERTIFIED",
        "scenarios": scenarios,
        "real_network": False,
        "real_credentials": False,
        "real_mutations": False,
        "publication_enabled": False,
        "auto_publish": False,
    }
    report["evidence_sha256"] = canonical_sha256(report)
    return report


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ControlledYouTubePostUploadCertificationError(message)


if __name__ == "__main__":
    certification = run_certification()
    print(json.dumps(certification, ensure_ascii=False, sort_keys=True, indent=2))
    print("CERTIFIED")
    print("REAL_NETWORK=DISABLED")
    print("REAL_CREDENTIALS=DISABLED")
    print("REAL_MUTATIONS=DISABLED")
    print("PUBLICATION=DISABLED")
    print("AUTO_PUBLISH=DISABLED")


__all__ = [
    "ControlledYouTubePostUploadCertificationError",
    "certify_channel_mismatch_blocked",
    "certify_checksum_mismatch_blocked",
    "certify_deterministic_replay",
    "certify_incomplete_bindings_blocked",
    "certify_not_activated",
    "certify_processing_failure_rejected",
    "certify_success",
    "run_certification",
]
