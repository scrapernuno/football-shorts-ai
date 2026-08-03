"""
FOOTBALL-SHORTS-AI-0054F
TIMELINE STUDIO AND MULTI-CLIP COMPOSITION CONTRACT

Builds deterministic vertical-video timeline plans from governed clip selections.
The contract records composition intent only. It never downloads provider media,
opens local assets, renders video, publishes content or enables automatic actions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from studio.governed_clip_selection import GovernedClipSelection


class TimelineCompositionError(ValueError):
    """Raised when a timeline composition is malformed or unsafe."""


SUPPORTED_TIMELINE_STATES = {
    "draft",
    "reviewed",
    "ready_for_factory",
    "blocked",
    "archived",
}

SUPPORTED_TRANSITIONS = {
    "cut",
    "fade",
    "crossfade",
    "zoom",
    "none",
}

SUPPORTED_ASPECT_RATIOS = {"9:16"}
SUPPORTED_RESOLUTIONS = {"1080x1920"}
MIN_TIMELINE_DURATION_SECONDS = 3.0
MAX_TIMELINE_DURATION_SECONDS = 90.0
MAX_TIMELINE_CLIPS = 30


@dataclass(frozen=True)
class TimelineClip:
    order: int
    clip_id: str
    asset_id: str
    provider: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    transition: str
    render_allowed: bool
    rights_status: str
    evidence_sha256: str

    def validate(self) -> None:
        if not isinstance(self.order, int) or isinstance(self.order, bool) or self.order < 1:
            raise TimelineCompositionError("clip order must be a positive integer")
        if not self.clip_id.startswith("CLIP-"):
            raise TimelineCompositionError("timeline clip must reference CLIP- evidence")
        if not self.asset_id.startswith("EXT-"):
            raise TimelineCompositionError("timeline clip must reference EXT- asset")
        if self.end_seconds <= self.start_seconds:
            raise TimelineCompositionError("timeline clip timestamps are invalid")
        expected = round(self.end_seconds - self.start_seconds, 3)
        if round(self.duration_seconds, 3) != expected:
            raise TimelineCompositionError("timeline clip duration is inconsistent")
        if self.transition not in SUPPORTED_TRANSITIONS:
            raise TimelineCompositionError("unsupported clip transition")
        if not _is_sha256(self.evidence_sha256):
            raise TimelineCompositionError("clip evidence must be SHA-256")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "order": self.order,
            "clip_id": self.clip_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "transition": self.transition,
            "render_allowed": self.render_allowed,
            "rights_status": self.rights_status,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True)
class TimelineTrack:
    track_type: str
    asset_reference: str | None
    enabled: bool
    start_seconds: float
    end_seconds: float
    volume: float | None = None
    language: str | None = None

    def validate(self) -> None:
        if self.track_type not in {"voiceover", "music", "captions"}:
            raise TimelineCompositionError("unsupported timeline track type")
        if self.start_seconds < 0 or self.end_seconds < self.start_seconds:
            raise TimelineCompositionError("timeline track timestamps are invalid")
        if self.enabled and not (self.asset_reference and self.asset_reference.strip()):
            raise TimelineCompositionError("enabled track requires asset_reference")
        if self.volume is not None and not 0 <= self.volume <= 1:
            raise TimelineCompositionError("track volume must be between 0 and 1")
        if self.track_type == "captions" and self.enabled and not self.language:
            raise TimelineCompositionError("enabled captions require language")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "track_type": self.track_type,
            "asset_reference": self.asset_reference,
            "enabled": self.enabled,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "volume": self.volume,
            "language": self.language,
        }


@dataclass(frozen=True)
class TimelineComposition:
    schema: str
    timeline_id: str
    title: str
    aspect_ratio: str
    resolution: str
    fps: int
    clips: tuple[TimelineClip, ...]
    tracks: tuple[TimelineTrack, ...]
    total_duration_seconds: float
    timeline_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    render_enabled: bool = False
    auto_acquire: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.timeline-composition.v1":
            raise TimelineCompositionError("unsupported timeline schema")
        if not self.timeline_id.startswith("TIMELINE-"):
            raise TimelineCompositionError("timeline_id must start with TIMELINE-")
        if not self.title.strip():
            raise TimelineCompositionError("timeline title is required")
        if self.aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise TimelineCompositionError("timeline must use vertical 9:16 format")
        if self.resolution not in SUPPORTED_RESOLUTIONS:
            raise TimelineCompositionError("unsupported timeline resolution")
        if self.fps not in {24, 25, 30, 50, 60}:
            raise TimelineCompositionError("unsupported timeline fps")
        if not 1 <= len(self.clips) <= MAX_TIMELINE_CLIPS:
            raise TimelineCompositionError("timeline clip count is outside governed limits")
        orders = [clip.order for clip in self.clips]
        if orders != list(range(1, len(self.clips) + 1)):
            raise TimelineCompositionError("timeline clip order must be contiguous")
        if len({clip.clip_id for clip in self.clips}) != len(self.clips):
            raise TimelineCompositionError("timeline cannot contain duplicate clip_id")
        for clip in self.clips:
            clip.validate()
        for track in self.tracks:
            track.validate()
            if track.enabled and track.end_seconds > self.total_duration_seconds:
                raise TimelineCompositionError("track exceeds timeline duration")
        expected_duration = round(sum(clip.duration_seconds for clip in self.clips), 3)
        if round(self.total_duration_seconds, 3) != expected_duration:
            raise TimelineCompositionError("total timeline duration is inconsistent")
        if not MIN_TIMELINE_DURATION_SECONDS <= self.total_duration_seconds <= MAX_TIMELINE_DURATION_SECONDS:
            raise TimelineCompositionError("timeline duration is outside governed limits")
        if self.timeline_state not in SUPPORTED_TIMELINE_STATES:
            raise TimelineCompositionError("unsupported timeline state")
        renderable = all(clip.render_allowed for clip in self.clips)
        if self.timeline_state == "ready_for_factory" and not renderable:
            raise TimelineCompositionError("non-renderable timeline cannot be ready for factory")
        if self.timeline_state == "ready_for_factory" and self.blockers:
            raise TimelineCompositionError("ready timeline cannot contain blockers")
        if self.timeline_state == "blocked" and not self.blockers:
            raise TimelineCompositionError("blocked timeline requires blockers")
        if self.render_enabled:
            raise TimelineCompositionError("0054F cannot enable rendering")
        if self.auto_acquire or self.auto_render or self.auto_publish:
            raise TimelineCompositionError("automatic timeline actions are forbidden")
        if not _is_sha256(self.evidence_sha256):
            raise TimelineCompositionError("timeline evidence must be SHA-256")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "timeline_id": self.timeline_id,
            "title": self.title,
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "fps": self.fps,
            "clips": [clip.to_dict() for clip in self.clips],
            "tracks": [track.to_dict() for track in self.tracks],
            "total_duration_seconds": self.total_duration_seconds,
            "timeline_state": self.timeline_state,
            "blockers": list(self.blockers),
            "evidence_sha256": self.evidence_sha256,
            "render_enabled": False,
            "auto_acquire": False,
            "auto_render": False,
            "auto_publish": False,
        }


def build_timeline_composition(
    *,
    title: str,
    selections: Iterable[GovernedClipSelection],
    transitions: Iterable[str] | None = None,
    tracks: Iterable[TimelineTrack] = (),
    timeline_state: str = "draft",
    fps: int = 30,
) -> TimelineComposition:
    clips_source = tuple(selections)
    if not clips_source:
        raise TimelineCompositionError("timeline requires at least one clip")
    for selection in clips_source:
        selection.validate()

    transition_values = tuple(transitions or ("cut",) * len(clips_source))
    if len(transition_values) != len(clips_source):
        raise TimelineCompositionError("one transition is required per clip")

    clips = tuple(
        TimelineClip(
            order=index,
            clip_id=selection.clip_id,
            asset_id=selection.asset_id,
            provider=selection.provider,
            start_seconds=selection.start_seconds,
            end_seconds=selection.end_seconds,
            duration_seconds=selection.duration_seconds,
            transition=transition_values[index - 1],
            render_allowed=selection.render_allowed,
            rights_status=selection.rights_status,
            evidence_sha256=selection.evidence_sha256,
        )
        for index, selection in enumerate(clips_source, start=1)
    )
    track_values = tuple(tracks)
    total_duration = round(sum(clip.duration_seconds for clip in clips), 3)
    blockers = tuple(
        sorted(
            {
                f"CLIP_NOT_RENDERABLE:{clip.clip_id}"
                for clip in clips
                if not clip.render_allowed
            }
        )
    )
    resolved_state = timeline_state
    if blockers and timeline_state == "ready_for_factory":
        resolved_state = "blocked"

    unsigned = {
        "schema": "football-shorts-ai.timeline-composition.v1",
        "title": title.strip(),
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "fps": fps,
        "clips": [clip.to_dict() for clip in clips],
        "tracks": [track.to_dict() for track in track_values],
        "total_duration_seconds": total_duration,
        "timeline_state": resolved_state,
        "blockers": list(blockers),
        "render_enabled": False,
        "auto_acquire": False,
        "auto_render": False,
        "auto_publish": False,
    }
    evidence_sha256 = canonical_sha256(unsigned)
    result = TimelineComposition(
        schema="football-shorts-ai.timeline-composition.v1",
        timeline_id=f"TIMELINE-{evidence_sha256[:20].upper()}",
        title=title.strip(),
        aspect_ratio="9:16",
        resolution="1080x1920",
        fps=fps,
        clips=clips,
        tracks=track_values,
        total_duration_seconds=total_duration,
        timeline_state=resolved_state,
        blockers=blockers,
        evidence_sha256=evidence_sha256,
        render_enabled=False,
        auto_acquire=False,
        auto_render=False,
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
    "MAX_TIMELINE_CLIPS",
    "MAX_TIMELINE_DURATION_SECONDS",
    "MIN_TIMELINE_DURATION_SECONDS",
    "SUPPORTED_TIMELINE_STATES",
    "SUPPORTED_TRANSITIONS",
    "TimelineClip",
    "TimelineComposition",
    "TimelineCompositionError",
    "TimelineTrack",
    "build_timeline_composition",
    "canonical_sha256",
]
