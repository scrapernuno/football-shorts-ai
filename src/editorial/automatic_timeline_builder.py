"""
FOOTBALL-SHORTS-AI-0056G
AUTOMATIC TIMELINE BUILDER FROM EDITORIAL ALIGNMENT

Transforms governed 0056E alignment and 0056F score evidence into a deterministic
vertical timeline proposal. This module prepares composition evidence only. It does
not acquire media, render video, call models, access the network or publish content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from editorial.editorial_quality_scoring import EditorialQualityReport
from editorial.semantic_scene_indexer import SemanticSceneIndex
from editorial.story_alignment_optimizer import StoryAlignmentReport


class AutomaticTimelineBuilderError(ValueError):
    """Raised when automatic editorial timeline evidence is invalid."""


@dataclass(frozen=True)
class AutomaticTimelineClip:
    order: int
    beat_id: str
    beat_role: str
    beat_text: str
    scene_id: str
    asset_id: str
    provider: str
    source_start_seconds: float
    source_end_seconds: float
    duration_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    transition: str
    match_score: float
    render_allowed: bool
    rights_status: str
    source_evidence_sha256: str
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if self.order < 1:
            raise AutomaticTimelineBuilderError("timeline clip order must be positive")
        if not self.beat_id.startswith("BEAT-"):
            raise AutomaticTimelineBuilderError("invalid beat identity")
        if not self.scene_id.startswith("SCENE-"):
            raise AutomaticTimelineBuilderError("invalid scene identity")
        if not self.asset_id.startswith("EXT-"):
            raise AutomaticTimelineBuilderError("invalid asset identity")
        if self.source_end_seconds <= self.source_start_seconds:
            raise AutomaticTimelineBuilderError("source timestamps are invalid")
        expected = round(self.source_end_seconds - self.source_start_seconds, 3)
        if round(self.duration_seconds, 3) != expected:
            raise AutomaticTimelineBuilderError("clip duration is inconsistent")
        if round(self.timeline_end_seconds - self.timeline_start_seconds, 3) != round(self.duration_seconds, 3):
            raise AutomaticTimelineBuilderError("timeline placement is inconsistent")
        if self.transition not in {"none", "cut", "fade", "crossfade", "zoom"}:
            raise AutomaticTimelineBuilderError("unsupported timeline transition")
        if not 0.0 <= self.match_score <= 1.0:
            raise AutomaticTimelineBuilderError("match score must be between 0 and 1")
        if self.render_allowed and self.blockers:
            raise AutomaticTimelineBuilderError("renderable clip cannot contain blockers")
        if not self.render_allowed and not self.blockers:
            raise AutomaticTimelineBuilderError("non-renderable clip requires blockers")
        _validate_sha256(self.source_evidence_sha256)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "order": self.order,
            "beat_id": self.beat_id,
            "beat_role": self.beat_role,
            "beat_text": self.beat_text,
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "duration_seconds": self.duration_seconds,
            "timeline_start_seconds": self.timeline_start_seconds,
            "timeline_end_seconds": self.timeline_end_seconds,
            "transition": self.transition,
            "match_score": self.match_score,
            "render_allowed": self.render_allowed,
            "rights_status": self.rights_status,
            "source_evidence_sha256": self.source_evidence_sha256,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class AutomaticTimelinePlan:
    schema: str
    timeline_id: str
    alignment_id: str
    editorial_score_id: str
    title: str
    aspect_ratio: str
    resolution: str
    fps: int
    clips: tuple[AutomaticTimelineClip, ...]
    total_duration_seconds: float
    editorial_quality_score: float
    viral_potential_score: float
    quality_band: str
    timeline_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    model_execution_enabled: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.automatic-editorial-timeline.v1":
            raise AutomaticTimelineBuilderError("unsupported automatic timeline schema")
        if not self.timeline_id.startswith("AUTOTIMELINE-"):
            raise AutomaticTimelineBuilderError("invalid automatic timeline identity")
        if not self.alignment_id.startswith("ALIGN-"):
            raise AutomaticTimelineBuilderError("invalid alignment identity")
        if not self.editorial_score_id.startswith("EDITSCORE-"):
            raise AutomaticTimelineBuilderError("invalid editorial score identity")
        if not self.title.strip():
            raise AutomaticTimelineBuilderError("timeline title is required")
        if self.aspect_ratio != "9:16" or self.resolution != "1080x1920":
            raise AutomaticTimelineBuilderError("automatic timeline must be vertical 1080x1920")
        if self.fps not in {24, 25, 30, 50, 60}:
            raise AutomaticTimelineBuilderError("unsupported timeline fps")
        if not 1 <= len(self.clips) <= 30:
            raise AutomaticTimelineBuilderError("timeline clip count is outside governed limits")
        cursor = 0.0
        for expected_order, clip in enumerate(self.clips, start=1):
            clip.validate()
            if clip.order != expected_order:
                raise AutomaticTimelineBuilderError("timeline clip order must be contiguous")
            if round(clip.timeline_start_seconds, 3) != round(cursor, 3):
                raise AutomaticTimelineBuilderError("timeline clips must be contiguous")
            cursor = clip.timeline_end_seconds
        expected_total = round(sum(item.duration_seconds for item in self.clips), 3)
        if round(self.total_duration_seconds, 3) != expected_total:
            raise AutomaticTimelineBuilderError("timeline duration is inconsistent")
        if not 3.0 <= self.total_duration_seconds <= 90.0:
            raise AutomaticTimelineBuilderError("timeline duration is outside governed limits")
        for value in (self.editorial_quality_score, self.viral_potential_score):
            if not 0.0 <= value <= 1.0:
                raise AutomaticTimelineBuilderError("timeline score must be between 0 and 1")
        if self.quality_band not in {"low", "developing", "strong", "excellent"}:
            raise AutomaticTimelineBuilderError("unsupported quality band")
        if self.timeline_state not in {"ready_for_review", "blocked"}:
            raise AutomaticTimelineBuilderError("unsupported automatic timeline state")
        if self.timeline_state == "ready_for_review" and self.blockers:
            raise AutomaticTimelineBuilderError("review-ready timeline cannot contain blockers")
        if self.timeline_state == "blocked" and not self.blockers:
            raise AutomaticTimelineBuilderError("blocked timeline requires blockers")
        if any((self.model_execution_enabled, self.network_enabled, self.acquisition_enabled, self.render_enabled, self.auto_render, self.auto_publish)):
            raise AutomaticTimelineBuilderError("0056G cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise AutomaticTimelineBuilderError("automatic timeline evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "timeline_id": self.timeline_id,
            "alignment_id": self.alignment_id,
            "editorial_score_id": self.editorial_score_id,
            "title": self.title,
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "fps": self.fps,
            "clips": [clip.to_dict() for clip in self.clips],
            "total_duration_seconds": self.total_duration_seconds,
            "editorial_quality_score": self.editorial_quality_score,
            "viral_potential_score": self.viral_potential_score,
            "quality_band": self.quality_band,
            "timeline_state": self.timeline_state,
            "blockers": list(self.blockers),
            "model_execution_enabled": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_automatic_timeline(
    *,
    title: str,
    alignment: StoryAlignmentReport,
    score: EditorialQualityReport,
    index: SemanticSceneIndex,
    fps: int = 30,
) -> AutomaticTimelinePlan:
    alignment.validate()
    score.validate()
    index.validate()
    if score.alignment_id != alignment.alignment_id:
        raise AutomaticTimelineBuilderError("score and alignment evidence do not match")
    if not title.strip():
        raise AutomaticTimelineBuilderError("timeline title is required")

    scenes = {scene.scene_id: scene for scene in index.scenes}
    clips: list[AutomaticTimelineClip] = []
    blockers = set(alignment.blockers) | set(score.blockers)
    cursor = 0.0
    for aligned in alignment.scenes:
        scene = scenes.get(aligned.scene_id)
        if scene is None:
            raise AutomaticTimelineBuilderError("aligned scene is absent from scene index")
        clip_blockers = tuple(aligned.blockers)
        blockers.update(clip_blockers)
        duration = round(scene.duration_seconds, 3)
        end = round(cursor + duration, 3)
        clips.append(
            AutomaticTimelineClip(
                order=aligned.order,
                beat_id=aligned.beat_id,
                beat_role=aligned.beat_role,
                beat_text=aligned.beat_text,
                scene_id=scene.scene_id,
                asset_id=scene.asset_id,
                provider=scene.provider,
                source_start_seconds=scene.start_seconds,
                source_end_seconds=scene.end_seconds,
                duration_seconds=duration,
                timeline_start_seconds=round(cursor, 3),
                timeline_end_seconds=end,
                transition=aligned.transition,
                match_score=aligned.match_score,
                render_allowed=aligned.render_allowed,
                rights_status=scene.rights_status,
                source_evidence_sha256=scene.evidence_sha256,
                blockers=clip_blockers,
            )
        )
        cursor = end

    total = round(cursor, 3)
    if total < 3.0:
        blockers.add("TIMELINE_TOO_SHORT")
    if total > 90.0:
        blockers.add("TIMELINE_TOO_LONG")
    if score.score_state != "scored":
        blockers.add("EDITORIAL_SCORE_BLOCKED")
    state = "blocked" if blockers else "ready_for_review"

    core = {
        "schema": "football-shorts-ai.automatic-editorial-timeline.v1",
        "alignment_id": alignment.alignment_id,
        "editorial_score_id": score.score_id,
        "title": title.strip(),
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "fps": fps,
        "clips": [clip.to_dict() for clip in clips],
        "total_duration_seconds": total,
        "editorial_quality_score": score.editorial_quality_score,
        "viral_potential_score": score.viral_potential_score,
        "quality_band": score.quality_band,
        "timeline_state": state,
        "blockers": sorted(blockers),
        "model_execution_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    timeline_id = f"AUTOTIMELINE-{provisional[:20].upper()}"
    unsigned = {**core, "timeline_id": timeline_id}
    evidence = canonical_sha256(unsigned)
    result = AutomaticTimelinePlan(
        timeline_id=timeline_id,
        evidence_sha256=evidence,
        clips=tuple(clips),
        blockers=tuple(unsigned["blockers"]),
        **{key: value for key, value in unsigned.items() if key not in {"timeline_id", "evidence_sha256", "clips", "blockers"}},
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise AutomaticTimelineBuilderError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AutomaticTimelineBuilderError("evidence must be hexadecimal") from exc


__all__ = [
    "AutomaticTimelineBuilderError",
    "AutomaticTimelineClip",
    "AutomaticTimelinePlan",
    "build_automatic_timeline",
    "canonical_sha256",
]
