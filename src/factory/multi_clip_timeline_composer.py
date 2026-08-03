"""FOOTBALL-SHORTS-AI-0060C — deterministic multi-clip timeline composer.

Consumes a governed 0060A preview manifest and produces a continuous browser
preview timeline. No media acquisition, extraction, rendering or publication is
performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class TimelineComposerError(ValueError):
    pass


@dataclass(frozen=True)
class TimelineClip:
    timeline_clip_id: str
    segment_id: str
    clip_id: str
    role: str
    source_uri: str
    source_start_seconds: float
    source_end_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    playback_rate: float
    transition: str
    script_text: str
    preview_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.timeline_clip_id.startswith("TLINECLIP-"):
            raise TimelineComposerError("invalid timeline clip identity")
        if self.source_end_seconds <= self.source_start_seconds:
            raise TimelineComposerError("invalid source range")
        if self.timeline_end_seconds <= self.timeline_start_seconds:
            raise TimelineComposerError("invalid timeline range")
        if not 0.25 <= self.playback_rate <= 4.0:
            raise TimelineComposerError("playback_rate outside governed limits")
        if self.preview_allowed and self.blockers:
            raise TimelineComposerError("previewable clip cannot have blockers")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "timeline_clip_id": self.timeline_clip_id,
            "segment_id": self.segment_id,
            "clip_id": self.clip_id,
            "role": self.role,
            "source_uri": self.source_uri,
            "source_start_seconds": round(self.source_start_seconds, 3),
            "source_end_seconds": round(self.source_end_seconds, 3),
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "playback_rate": round(self.playback_rate, 4),
            "transition": self.transition,
            "script_text": self.script_text,
            "preview_allowed": self.preview_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class MultiClipTimeline:
    schema: str
    timeline_id: str
    source_manifest_id: str
    clips: tuple[TimelineClip, ...]
    total_duration_seconds: float
    current_preview_index: int
    timeline_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.multi-clip-timeline.v1":
            raise TimelineComposerError("unsupported schema")
        if not self.timeline_id.startswith("TIMELINE-"):
            raise TimelineComposerError("invalid timeline identity")
        if self.timeline_state not in {"composed", "review_required", "blocked"}:
            raise TimelineComposerError("unsupported timeline state")
        previous_end = 0.0
        for index, clip in enumerate(self.clips):
            clip.validate()
            if index == 0 and abs(clip.timeline_start_seconds) > 0.001:
                raise TimelineComposerError("timeline must start at zero")
            if abs(clip.timeline_start_seconds - previous_end) > 0.001:
                raise TimelineComposerError("timeline clips must be continuous")
            previous_end = clip.timeline_end_seconds
        if abs(previous_end - self.total_duration_seconds) > 0.001:
            raise TimelineComposerError("timeline duration mismatch")
        if self.timeline_state == "composed" and (self.blockers or not self.clips):
            raise TimelineComposerError("composed timeline must be unblocked")
        if self.timeline_state != "composed" and not self.blockers:
            raise TimelineComposerError("non-composed timeline needs blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise TimelineComposerError("0060C cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise TimelineComposerError("timeline evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "timeline_id": self.timeline_id,
            "source_manifest_id": self.source_manifest_id,
            "clips": [item.to_dict() for item in self.clips],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "current_preview_index": self.current_preview_index,
            "timeline_state": self.timeline_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def compose_multi_clip_timeline(manifest: Mapping[str, object]) -> MultiClipTimeline:
    manifest_id = str(manifest.get("manifest_id") or manifest.get("preview_id") or "")
    segments = manifest.get("segments", ())
    blockers: set[str] = set(str(item) for item in manifest.get("blockers", ()))
    if manifest.get("preview_state") != "preview_ready":
        blockers.add("PREVIEW_MANIFEST_NOT_READY")
    if not isinstance(segments, Sequence) or isinstance(segments, (str, bytes)) or not segments:
        blockers.add("PREVIEW_SEGMENTS_MISSING")
        segments = ()

    clips: list[TimelineClip] = []
    cursor = 0.0
    for raw in segments:
        if not isinstance(raw, Mapping):
            raise TimelineComposerError("segment must be an object")
        source_start = float(raw.get("source_start_seconds", raw.get("start_seconds", 0.0)))
        source_end = float(raw.get("source_end_seconds", raw.get("end_seconds", 0.0)))
        playback_rate = float(raw.get("playback_rate", 1.0))
        duration = (source_end - source_start) / playback_rate if playback_rate > 0 else 0.0
        clip_blockers = set(str(item) for item in raw.get("blockers", ()))
        preview_allowed = bool(raw.get("preview_allowed", False))
        if not preview_allowed:
            clip_blockers.add("CLIP_PREVIEW_NOT_ALLOWED")
        if not str(raw.get("source_uri", "")).strip():
            clip_blockers.add("CLIP_SOURCE_MISSING")
        if duration <= 0:
            clip_blockers.add("CLIP_DURATION_INVALID")
        core = {
            "segment_id": str(raw.get("segment_id", "")),
            "clip_id": str(raw.get("clip_id", "")),
            "source_uri": str(raw.get("source_uri", "")),
            "source_start_seconds": source_start,
            "source_end_seconds": source_end,
            "timeline_start_seconds": cursor,
            "timeline_end_seconds": cursor + max(duration, 0.0),
        }
        clip = TimelineClip(
            timeline_clip_id=f"TLINECLIP-{canonical_sha256(core)[:20].upper()}",
            segment_id=core["segment_id"],
            clip_id=core["clip_id"],
            role=str(raw.get("role", "development")),
            source_uri=core["source_uri"],
            source_start_seconds=source_start,
            source_end_seconds=source_end,
            timeline_start_seconds=round(cursor, 3),
            timeline_end_seconds=round(cursor + max(duration, 0.0), 3),
            playback_rate=playback_rate,
            transition=str(raw.get("transition", "cut")),
            script_text=str(raw.get("script_text", "")),
            preview_allowed=preview_allowed and not clip_blockers,
            blockers=tuple(sorted(clip_blockers)),
        )
        clips.append(clip)
        blockers.update(clip_blockers)
        cursor = clip.timeline_end_seconds

    state = "blocked" if not clips else "review_required" if blockers else "composed"
    base = {
        "schema": "football-shorts-ai.multi-clip-timeline.v1",
        "source_manifest_id": manifest_id,
        "clips": [item.to_dict() for item in clips],
        "total_duration_seconds": round(cursor, 3),
        "current_preview_index": 0,
        "timeline_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    timeline_id = f"TIMELINE-{canonical_sha256(base)[:20].upper()}"
    unsigned = {**base, "timeline_id": timeline_id}
    result = MultiClipTimeline(
        schema=base["schema"],
        timeline_id=timeline_id,
        source_manifest_id=manifest_id,
        clips=tuple(clips),
        total_duration_seconds=round(cursor, 3),
        current_preview_index=0,
        timeline_state=state,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


__all__ = ["MultiClipTimeline", "TimelineClip", "TimelineComposerError", "compose_multi_clip_timeline"]
