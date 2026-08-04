"""FOOTBALL-SHORTS-AI-0061I — YouTube upload result intake and processing verification.

Normalizes one controlled 0061H upload result plus an injected YouTube processing
snapshot. It does not change visibility, upload media, read credentials or publish.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class YouTubeUploadResultIntakeError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class YouTubeUploadResultIntake:
    schema: str
    intake_id: str
    upload_id: str
    youtube_video_id: str
    youtube_channel_id: str
    processing_status: str
    upload_status: str
    privacy_status: str
    embeddable: bool
    watch_url: str
    thumbnail_url: str
    intake_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    visibility_change_allowed: bool = False
    network_enabled: bool = False
    upload_enabled: bool = False
    publish_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema, "intake_id": self.intake_id,
            "upload_id": self.upload_id, "youtube_video_id": self.youtube_video_id,
            "youtube_channel_id": self.youtube_channel_id,
            "processing_status": self.processing_status, "upload_status": self.upload_status,
            "privacy_status": self.privacy_status, "embeddable": self.embeddable,
            "watch_url": self.watch_url, "thumbnail_url": self.thumbnail_url,
            "intake_state": self.intake_state, "blockers": list(self.blockers),
            "visibility_change_allowed": False, "network_enabled": False,
            "upload_enabled": False, "publish_enabled": False, "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-upload-result-intake.v1": raise YouTubeUploadResultIntakeError("unsupported intake schema")
        if not self.intake_id.startswith("YTRESULT-"): raise YouTubeUploadResultIntakeError("invalid intake identity")
        if not self.upload_id.startswith("YTUPLOAD-"): raise YouTubeUploadResultIntakeError("invalid upload identity")
        if self.intake_state not in {"processed", "processing", "review_required", "blocked"}: raise YouTubeUploadResultIntakeError("unsupported intake state")
        if self.intake_state == "processed" and (self.blockers or self.processing_status != "succeeded"): raise YouTubeUploadResultIntakeError("processed state requires successful processing")
        if self.intake_state != "processed" and not self.blockers: raise YouTubeUploadResultIntakeError("non-processed state requires blockers")
        if any((self.visibility_change_allowed, self.network_enabled, self.upload_enabled, self.publish_enabled, self.auto_publish)): raise YouTubeUploadResultIntakeError("0061I cannot enable external operations")
        if tuple(sorted(set(self.blockers))) != self.blockers: raise YouTubeUploadResultIntakeError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256: raise YouTubeUploadResultIntakeError("intake evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate(); return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_youtube_upload_result_intake(*, upload_result: Mapping[str, object], processing_snapshot: Mapping[str, object], expected_channel_id: str) -> YouTubeUploadResultIntake:
    blockers: set[str] = set()
    upload_id = str(upload_result.get("upload_id", ""))
    video_id = str(upload_result.get("youtube_video_id", ""))
    if upload_result.get("status") != "UPLOADED": blockers.add("YOUTUBE_UPLOAD_NOT_SUCCESSFUL")
    if not upload_id.startswith("YTUPLOAD-"): blockers.add("YOUTUBE_UPLOAD_ID_INVALID")
    if not video_id: blockers.add("YOUTUBE_VIDEO_ID_MISSING")
    channel_id = str(processing_snapshot.get("channel_id", ""))
    if not expected_channel_id: blockers.add("EXPECTED_CHANNEL_ID_REQUIRED")
    elif channel_id != expected_channel_id: blockers.add("YOUTUBE_CHANNEL_MISMATCH")
    processing = str(processing_snapshot.get("processing_status", "unknown"))
    upload_status = str(processing_snapshot.get("upload_status", "unknown"))
    privacy = str(processing_snapshot.get("privacy_status", "unknown"))
    if processing == "failed": blockers.add("YOUTUBE_PROCESSING_FAILED")
    elif processing != "succeeded": blockers.add("YOUTUBE_PROCESSING_PENDING")
    if upload_status not in {"uploaded", "processed"}: blockers.add("YOUTUBE_UPLOAD_STATUS_INVALID")
    if privacy not in {"private", "unlisted"}: blockers.add("YOUTUBE_PRIVACY_STATUS_UNEXPECTED")
    state = "blocked" if "YOUTUBE_UPLOAD_NOT_SUCCESSFUL" in blockers or "YOUTUBE_VIDEO_ID_MISSING" in blockers else "processing" if "YOUTUBE_PROCESSING_PENDING" in blockers else "review_required" if blockers else "processed"
    watch = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
    core = {"schema":"football-shorts-ai.youtube-upload-result-intake.v1","upload_id":upload_id,"youtube_video_id":video_id,"youtube_channel_id":channel_id,"processing_status":processing,"upload_status":upload_status,"privacy_status":privacy,"embeddable":bool(processing_snapshot.get("embeddable",False)),"watch_url":watch,"thumbnail_url":thumb,"intake_state":state,"blockers":sorted(blockers),"visibility_change_allowed":False,"network_enabled":False,"upload_enabled":False,"publish_enabled":False,"auto_publish":False}
    intake_id = f"YTRESULT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "intake_id": intake_id}
    result = YouTubeUploadResultIntake(intake_id=intake_id, evidence_sha256=canonical_sha256(unsigned), blockers=tuple(sorted(blockers)), **{k:v for k,v in core.items() if k != "blockers"})
    result.validate(); return result


__all__ = ["YouTubeUploadResultIntake", "YouTubeUploadResultIntakeError", "build_youtube_upload_result_intake", "canonical_sha256"]