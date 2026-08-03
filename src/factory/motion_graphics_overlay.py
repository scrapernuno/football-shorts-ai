"""FOOTBALL-SHORTS-AI-0060G — governed motion graphics overlay planning.

Creates deterministic browser-preview overlay instructions only. No generation,
acquisition, extraction, rendering, publication or network access is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class MotionGraphicsError(ValueError):
    pass


SUPPORTED_KINDS = {"scoreboard", "lower_third", "event", "callout", "cta"}
SUPPORTED_POSITIONS = {"top_left", "top_center", "top_right", "center", "bottom_left", "bottom_center", "bottom_right"}
SUPPORTED_ANIMATIONS = {"none", "fade", "slide_up", "slide_left", "scale", "pulse"}
SUPPORTED_STATES = {"composed", "review_required", "blocked"}


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MotionGraphicCue:
    cue_id: str
    kind: str
    timeline_start_seconds: float
    timeline_end_seconds: float
    primary_text: str
    secondary_text: str
    position: str
    animation_in: str
    animation_out: str
    emphasis_score: float
    overlay_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.cue_id.startswith("GFXCUE-"):
            raise MotionGraphicsError("invalid cue identity")
        if self.kind not in SUPPORTED_KINDS:
            raise MotionGraphicsError("unsupported overlay kind")
        if self.position not in SUPPORTED_POSITIONS:
            raise MotionGraphicsError("unsupported overlay position")
        if self.animation_in not in SUPPORTED_ANIMATIONS or self.animation_out not in SUPPORTED_ANIMATIONS:
            raise MotionGraphicsError("unsupported overlay animation")
        if not 0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise MotionGraphicsError("invalid overlay interval")
        if not self.primary_text.strip():
            raise MotionGraphicsError("primary overlay text required")
        if not 0 <= self.emphasis_score <= 1:
            raise MotionGraphicsError("emphasis score out of range")
        if self.overlay_allowed and self.blockers:
            raise MotionGraphicsError("allowed overlay cannot have blockers")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise MotionGraphicsError("blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "cue_id": self.cue_id,
            "kind": self.kind,
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "primary_text": self.primary_text,
            "secondary_text": self.secondary_text,
            "position": self.position,
            "animation_in": self.animation_in,
            "animation_out": self.animation_out,
            "emphasis_score": round(self.emphasis_score, 3),
            "overlay_allowed": self.overlay_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class MotionGraphicsTrack:
    schema: str
    graphics_id: str
    timeline_id: str
    cues: tuple[MotionGraphicCue, ...]
    graphics_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    generation_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "graphics_id": self.graphics_id,
            "timeline_id": self.timeline_id,
            "cues": [cue.to_dict() for cue in self.cues],
            "graphics_state": self.graphics_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "generation_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.motion-graphics-track.v1":
            raise MotionGraphicsError("unsupported graphics schema")
        if not self.graphics_id.startswith("MOTIONGFX-") or not self.timeline_id.startswith("TIMELINE-"):
            raise MotionGraphicsError("invalid graphics identity")
        if self.graphics_state not in SUPPORTED_STATES:
            raise MotionGraphicsError("unsupported graphics state")
        for cue in self.cues:
            cue.validate()
        if self.graphics_state == "composed" and (self.blockers or not self.cues or any(not cue.overlay_allowed for cue in self.cues)):
            raise MotionGraphicsError("composed state requires allowed cues")
        if self.graphics_state != "composed" and not self.blockers:
            raise MotionGraphicsError("non-composed state requires blockers")
        if any((self.network_enabled, self.generation_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise MotionGraphicsError("0060G cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise MotionGraphicsError("motion graphics evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_motion_graphics_track(*, timeline: Mapping[str, object], cue_inputs: Sequence[Mapping[str, object]]) -> MotionGraphicsTrack:
    timeline_id = str(timeline.get("timeline_id", ""))
    total_duration = float(timeline.get("total_duration_seconds", 0) or 0)
    blockers: set[str] = set()
    if not timeline_id.startswith("TIMELINE-") or timeline.get("composition_state") != "composed":
        blockers.add("TIMELINE_NOT_COMPOSED")

    cues: list[MotionGraphicCue] = []
    for raw in cue_inputs:
        cue_blockers: set[str] = set()
        start = float(raw.get("timeline_start_seconds", 0))
        end = float(raw.get("timeline_end_seconds", 0))
        text = str(raw.get("primary_text", "")).strip()
        if not text:
            cue_blockers.add("OVERLAY_TEXT_MISSING")
        if total_duration > 0 and end > total_duration + 0.001:
            cue_blockers.add("OVERLAY_OUTSIDE_TIMELINE")
        core = {
            "kind": str(raw.get("kind", "callout")),
            "timeline_start_seconds": start,
            "timeline_end_seconds": end,
            "primary_text": text or "MISSING",
            "secondary_text": str(raw.get("secondary_text", "")),
            "position": str(raw.get("position", "bottom_center")),
            "animation_in": str(raw.get("animation_in", "fade")),
            "animation_out": str(raw.get("animation_out", "fade")),
            "emphasis_score": float(raw.get("emphasis_score", 0.5)),
            "overlay_allowed": not cue_blockers,
            "blockers": tuple(sorted(cue_blockers)),
        }
        cue = MotionGraphicCue(cue_id=f"GFXCUE-{canonical_sha256(core)[:20].upper()}", **core)
        cue.validate()
        cues.append(cue)

    if not cues:
        blockers.add("MOTION_GRAPHICS_CUES_MISSING")
    if any(cue.blockers for cue in cues):
        blockers.add("MOTION_GRAPHICS_REVIEW_REQUIRED")
    state = "blocked" if "TIMELINE_NOT_COMPOSED" in blockers or not cues else "review_required" if blockers else "composed"
    core = {
        "schema": "football-shorts-ai.motion-graphics-track.v1",
        "timeline_id": timeline_id,
        "cues": [cue.to_dict() for cue in cues],
        "graphics_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "generation_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    graphics_id = f"MOTIONGFX-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "graphics_id": graphics_id}
    result = MotionGraphicsTrack(
        schema=core["schema"], graphics_id=graphics_id, timeline_id=timeline_id,
        cues=tuple(cues), graphics_state=state, blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["MotionGraphicCue", "MotionGraphicsError", "MotionGraphicsTrack", "build_motion_graphics_track", "canonical_sha256"]
