"""
FOOTBALL-SHORTS-AI-0054I
TIMELINE-TO-FACTORY PRODUCTION PACKAGE INTEGRATION

Transforms a governed timeline and its story enrichment into a deterministic
Factory input package. This boundary performs no media acquisition, rendering,
network access or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from studio.story_timeline_enrichment import StoryTimelineEnrichment
from studio.timeline_composition import TimelineComposition


class TimelineFactoryPackageError(ValueError):
    """Raised when timeline evidence cannot safely enter Factory preparation."""


@dataclass(frozen=True)
class FactoryScene:
    scene_order: int
    clip_id: str
    asset_id: str
    provider: str
    source_start_seconds: float
    source_end_seconds: float
    duration_seconds: float
    transition: str
    narrative_beat: str
    narration_text: str
    on_screen_text: str | None
    rights_status: str
    render_allowed: bool
    source_evidence_sha256: str

    def validate(self) -> None:
        if self.scene_order < 1:
            raise TimelineFactoryPackageError("scene_order must be positive")
        if not self.clip_id.startswith("CLIP-"):
            raise TimelineFactoryPackageError("scene must reference CLIP evidence")
        if not self.asset_id.startswith("EXT-"):
            raise TimelineFactoryPackageError("scene must reference EXT asset")
        if self.source_end_seconds <= self.source_start_seconds:
            raise TimelineFactoryPackageError("scene source timestamps are invalid")
        if round(self.source_end_seconds - self.source_start_seconds, 3) != round(self.duration_seconds, 3):
            raise TimelineFactoryPackageError("scene duration is inconsistent")
        if not self.render_allowed:
            raise TimelineFactoryPackageError("non-renderable scene cannot enter Factory package")
        if not _is_sha256(self.source_evidence_sha256):
            raise TimelineFactoryPackageError("scene evidence must be SHA-256")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "scene_order": self.scene_order,
            "clip_id": self.clip_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "duration_seconds": self.duration_seconds,
            "transition": self.transition,
            "narrative_beat": self.narrative_beat,
            "narration_text": self.narration_text,
            "on_screen_text": self.on_screen_text,
            "rights_status": self.rights_status,
            "render_allowed": True,
            "source_evidence_sha256": self.source_evidence_sha256,
        }


@dataclass(frozen=True)
class TimelineFactoryPackage:
    schema: str
    package_id: str
    timeline_id: str
    enrichment_id: str
    title: str
    aspect_ratio: str
    resolution: str
    fps: int
    total_duration_seconds: float
    scenes: tuple[FactoryScene, ...]
    captions_required: bool
    music_mood: str
    package_state: str
    blockers: tuple[str, ...]
    timeline_evidence_sha256: str
    enrichment_evidence_sha256: str
    evidence_sha256: str
    execution_enabled: bool = False
    render_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.timeline-factory-package.v1":
            raise TimelineFactoryPackageError("unsupported Factory package schema")
        if not self.package_id.startswith("FACTORYPKG-"):
            raise TimelineFactoryPackageError("package_id must start with FACTORYPKG-")
        if not self.timeline_id.startswith("TIMELINE-"):
            raise TimelineFactoryPackageError("invalid timeline identity")
        if not self.enrichment_id.startswith("STORYTL-"):
            raise TimelineFactoryPackageError("invalid enrichment identity")
        if self.aspect_ratio != "9:16" or self.resolution != "1080x1920":
            raise TimelineFactoryPackageError("Factory package must remain vertical 1080x1920")
        if not self.scenes:
            raise TimelineFactoryPackageError("Factory package requires scenes")
        for expected, scene in enumerate(self.scenes, start=1):
            scene.validate()
            if scene.scene_order != expected:
                raise TimelineFactoryPackageError("scene order must be contiguous")
        expected_duration = round(sum(scene.duration_seconds for scene in self.scenes), 3)
        if round(self.total_duration_seconds, 3) != expected_duration:
            raise TimelineFactoryPackageError("package duration is inconsistent")
        if self.package_state == "ready_for_factory" and self.blockers:
            raise TimelineFactoryPackageError("ready package cannot contain blockers")
        if self.package_state == "blocked" and not self.blockers:
            raise TimelineFactoryPackageError("blocked package requires blockers")
        if self.execution_enabled or self.render_enabled or self.auto_render or self.auto_publish:
            raise TimelineFactoryPackageError("0054I cannot execute rendering or publishing")
        for value in (
            self.timeline_evidence_sha256,
            self.enrichment_evidence_sha256,
            self.evidence_sha256,
        ):
            if not _is_sha256(value):
                raise TimelineFactoryPackageError("package evidence must be SHA-256")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "package_id": self.package_id,
            "timeline_id": self.timeline_id,
            "enrichment_id": self.enrichment_id,
            "title": self.title,
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "fps": self.fps,
            "total_duration_seconds": self.total_duration_seconds,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "captions_required": self.captions_required,
            "music_mood": self.music_mood,
            "package_state": self.package_state,
            "blockers": list(self.blockers),
            "timeline_evidence_sha256": self.timeline_evidence_sha256,
            "enrichment_evidence_sha256": self.enrichment_evidence_sha256,
            "evidence_sha256": self.evidence_sha256,
            "execution_enabled": False,
            "render_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }


def build_timeline_factory_package(
    *,
    timeline: TimelineComposition,
    enrichment: StoryTimelineEnrichment,
) -> TimelineFactoryPackage:
    timeline.validate()
    enrichment.validate(timeline)
    if enrichment.timeline_id != timeline.timeline_id:
        raise TimelineFactoryPackageError("timeline and enrichment identities differ")

    blockers = set(timeline.blockers) | set(enrichment.blockers)
    if timeline.timeline_state != "ready_for_factory":
        blockers.add("TIMELINE_NOT_READY")
    if enrichment.enrichment_state != "ready_for_factory":
        blockers.add("ENRICHMENT_NOT_READY")

    beats = tuple(enrichment.beats)
    narration = tuple(enrichment.narration)
    scenes: list[FactoryScene] = []
    for clip in timeline.clips:
        if not clip.render_allowed:
            blockers.add(f"CLIP_NOT_RENDERABLE:{clip.clip_id}")
            continue
        beat = _beat_for_clip(beats, clip.clip_id)
        cue = _narration_for_beat(narration, getattr(beat, "beat_type", "development"))
        scenes.append(
            FactoryScene(
                scene_order=len(scenes) + 1,
                clip_id=clip.clip_id,
                asset_id=clip.asset_id,
                provider=clip.provider,
                source_start_seconds=clip.start_seconds,
                source_end_seconds=clip.end_seconds,
                duration_seconds=clip.duration_seconds,
                transition=clip.transition,
                narrative_beat=getattr(beat, "beat_type", "development"),
                narration_text=getattr(cue, "text", "") if cue is not None else "",
                on_screen_text=getattr(beat, "on_screen_text", None),
                rights_status=clip.rights_status,
                render_allowed=clip.render_allowed,
                source_evidence_sha256=clip.evidence_sha256,
            )
        )

    state = "ready_for_factory" if not blockers and scenes else "blocked"
    unsigned = {
        "schema": "football-shorts-ai.timeline-factory-package.v1",
        "timeline_id": timeline.timeline_id,
        "enrichment_id": enrichment.enrichment_id,
        "title": timeline.title,
        "aspect_ratio": timeline.aspect_ratio,
        "resolution": timeline.resolution,
        "fps": timeline.fps,
        "total_duration_seconds": round(sum(scene.duration_seconds for scene in scenes), 3),
        "scenes": [scene.to_dict() for scene in scenes],
        "captions_required": bool(enrichment.captions_required),
        "music_mood": str(enrichment.music_mood),
        "package_state": state,
        "blockers": sorted(blockers),
        "timeline_evidence_sha256": timeline.evidence_sha256,
        "enrichment_evidence_sha256": enrichment.evidence_sha256,
        "execution_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    evidence = canonical_sha256(unsigned)
    result = TimelineFactoryPackage(
        package_id=f"FACTORYPKG-{evidence[:20].upper()}",
        evidence_sha256=evidence,
        scenes=tuple(scenes),
        blockers=tuple(sorted(blockers)),
        **{key: value for key, value in unsigned.items() if key not in {"scenes", "blockers"}},
    )
    result.validate()
    return result


def _beat_for_clip(beats: tuple[object, ...], clip_id: str) -> object | None:
    for beat in beats:
        clip_ids = tuple(getattr(beat, "clip_ids", ()))
        if clip_id in clip_ids:
            return beat
    return beats[0] if beats else None


def _narration_for_beat(cues: tuple[object, ...], beat_type: str) -> object | None:
    for cue in cues:
        if getattr(cue, "beat_type", None) == beat_type:
            return cue
    return None


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
    "FactoryScene",
    "TimelineFactoryPackage",
    "TimelineFactoryPackageError",
    "build_timeline_factory_package",
    "canonical_sha256",
]
