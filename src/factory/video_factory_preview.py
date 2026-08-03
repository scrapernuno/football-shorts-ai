"""FOOTBALL-SHORTS-AI-0060A — governed browser preview manifest."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class VideoFactoryPreviewError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PreviewSegment:
    segment_id: str
    asset_id: str
    media_uri: str
    clip_id: str
    role: str
    script_text: str
    source_start_seconds: float
    source_end_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    playback_rate: float
    transition: str
    rights_status: str
    preview_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.segment_id.startswith("PREVIEWSEG-"):
            raise VideoFactoryPreviewError("invalid segment identity")
        if not 0 <= self.source_start_seconds < self.source_end_seconds:
            raise VideoFactoryPreviewError("invalid source timing")
        if not 0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise VideoFactoryPreviewError("invalid timeline timing")
        if not 0.25 <= self.playback_rate <= 4.0:
            raise VideoFactoryPreviewError("invalid playback rate")
        if self.rights_status not in {"owned", "licensed", "reference_only", "unknown"}:
            raise VideoFactoryPreviewError("invalid rights status")
        if self.preview_allowed and (self.blockers or not self.media_uri):
            raise VideoFactoryPreviewError("playable segment is incomplete")
        if self.rights_status == "reference_only" and self.preview_allowed:
            raise VideoFactoryPreviewError("reference-only segment cannot be played")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "segment_id": self.segment_id,
            "asset_id": self.asset_id,
            "media_uri": self.media_uri,
            "clip_id": self.clip_id,
            "role": self.role,
            "script_text": self.script_text,
            "source_start_seconds": round(self.source_start_seconds, 3),
            "source_end_seconds": round(self.source_end_seconds, 3),
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "playback_rate": round(self.playback_rate, 4),
            "transition": self.transition,
            "rights_status": self.rights_status,
            "preview_allowed": self.preview_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class VideoFactoryPreviewManifest:
    schema: str
    preview_id: str
    handover_package_id: str
    segments: tuple[PreviewSegment, ...]
    total_duration_seconds: float
    preview_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "preview_id": self.preview_id,
            "handover_package_id": self.handover_package_id,
            "segments": [item.to_dict() for item in self.segments],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "preview_state": self.preview_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.video-factory-preview.v1":
            raise VideoFactoryPreviewError("unsupported schema")
        if not self.preview_id.startswith("FACTORYPREVIEW-"):
            raise VideoFactoryPreviewError("invalid preview identity")
        if not self.handover_package_id.startswith("FACTORYPKG-"):
            raise VideoFactoryPreviewError("invalid handover identity")
        if self.preview_state not in {"preview_ready", "review_required", "blocked"}:
            raise VideoFactoryPreviewError("invalid preview state")
        previous = 0.0
        for index, item in enumerate(self.segments):
            item.validate()
            if index and abs(item.timeline_start_seconds - previous) > 0.001:
                raise VideoFactoryPreviewError("timeline must be continuous")
            previous = item.timeline_end_seconds
        expected = self.segments[-1].timeline_end_seconds if self.segments else 0.0
        if abs(expected - self.total_duration_seconds) > 0.001:
            raise VideoFactoryPreviewError("duration mismatch")
        if self.preview_state == "preview_ready" and (self.blockers or not self.segments or not all(x.preview_allowed for x in self.segments)):
            raise VideoFactoryPreviewError("ready preview requires playable segments")
        if self.preview_state != "preview_ready" and not self.blockers:
            raise VideoFactoryPreviewError("non-ready preview requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise VideoFactoryPreviewError("operational capabilities are forbidden")
        if canonical_sha256(self.unsigned()) != self.evidence_sha256:
            raise VideoFactoryPreviewError("evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self.unsigned(), "evidence_sha256": self.evidence_sha256}


def build_video_factory_preview(*, handover: Mapping[str, object], media: Mapping[str, Mapping[str, object]]) -> VideoFactoryPreviewManifest:
    package_id = str(handover.get("package_id", handover.get("handover_package_id", "")))
    if not package_id.startswith("FACTORYPKG-"):
        raise VideoFactoryPreviewError("handover package id is required")
    blockers: set[str] = set()
    if handover.get("handover_state") != "ready_for_factory":
        blockers.add("FACTORY_HANDOVER_NOT_READY")
    segments: list[PreviewSegment] = []
    rows: Sequence[object] = handover.get("items", handover.get("timeline_items", ()))
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        asset_id = str(row.get("asset_id", ""))
        source = media.get(asset_id, {})
        rights = str(source.get("rights_status", "unknown"))
        uri = str(source.get("media_uri", ""))
        item_blockers: set[str] = set()
        if not uri:
            item_blockers.add("PREVIEW_SOURCE_MISSING")
        if rights not in {"owned", "licensed"}:
            item_blockers.add("PREVIEW_MEDIA_NOT_ALLOWED")
        if not bool(row.get("render_allowed", True)):
            item_blockers.add("FACTORY_ITEM_RENDER_NOT_ALLOWED")
        core = {
            "asset_id": asset_id,
            "media_uri": uri,
            "clip_id": str(row.get("clip_id", "")),
            "role": str(row.get("role", "development")),
            "script_text": str(row.get("script_text", "")),
            "source_start_seconds": float(row.get("source_start_seconds", 0)),
            "source_end_seconds": float(row.get("source_end_seconds", 0)),
            "timeline_start_seconds": float(row.get("timeline_start_seconds", 0)),
            "timeline_end_seconds": float(row.get("timeline_end_seconds", 0)),
            "playback_rate": float(row.get("playback_rate", 1)),
            "transition": str(row.get("transition", "cut")),
            "rights_status": rights,
            "preview_allowed": not item_blockers,
            "blockers": tuple(sorted(item_blockers)),
        }
        segments.append(PreviewSegment(segment_id=f"PREVIEWSEG-{canonical_sha256(core)[:20].upper()}", **core))
        blockers.update(item_blockers)
    if not segments:
        blockers.add("FACTORY_PREVIEW_SEGMENTS_MISSING")
    state = "blocked" if "FACTORY_HANDOVER_NOT_READY" in blockers or not segments else "review_required" if blockers else "preview_ready"
    total = segments[-1].timeline_end_seconds if segments else 0.0
    core = {
        "schema": "football-shorts-ai.video-factory-preview.v1",
        "handover_package_id": package_id,
        "segments": [x.to_dict() for x in segments],
        "total_duration_seconds": round(total, 3),
        "preview_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    preview_id = f"FACTORYPREVIEW-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "preview_id": preview_id}
    result = VideoFactoryPreviewManifest(
        schema=core["schema"], preview_id=preview_id, handover_package_id=package_id,
        segments=tuple(segments), total_duration_seconds=total, preview_state=state,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result
