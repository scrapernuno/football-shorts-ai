"""
FOOTBALL-SHORTS-AI-0054H
STORY AI AND TIMELINE ENRICHMENT INTEGRATION

Deterministically enriches a 0054F timeline with editorial story beats,
voice-over cues, captions and pacing guidance. This module creates composition
evidence only. It performs no model call, network access, media acquisition,
rendering or publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from studio.timeline_composition import TimelineComposition


class StoryTimelineEnrichmentError(ValueError):
    """Raised when story evidence or its timeline binding is invalid."""


SUPPORTED_BEAT_TYPES = {
    "hook",
    "introduction",
    "development",
    "climax",
    "ending",
    "call_to_action",
}

SUPPORTED_PACING = {"slow", "balanced", "fast", "impact"}
SUPPORTED_ENRICHMENT_STATES = {"draft", "reviewed", "ready_for_factory", "blocked"}


@dataclass(frozen=True)
class StoryBeat:
    order: int
    beat_type: str
    text: str
    start_seconds: float
    end_seconds: float
    clip_orders: tuple[int, ...]
    pacing: str
    on_screen_text: str | None = None

    def validate(self, *, timeline_duration: float, clip_count: int) -> None:
        if not isinstance(self.order, int) or isinstance(self.order, bool) or self.order < 1:
            raise StoryTimelineEnrichmentError("story beat order must be positive")
        if self.beat_type not in SUPPORTED_BEAT_TYPES:
            raise StoryTimelineEnrichmentError("unsupported story beat type")
        if not self.text.strip():
            raise StoryTimelineEnrichmentError("story beat text is required")
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise StoryTimelineEnrichmentError("story beat timestamps are invalid")
        if self.end_seconds > timeline_duration:
            raise StoryTimelineEnrichmentError("story beat exceeds timeline duration")
        if self.pacing not in SUPPORTED_PACING:
            raise StoryTimelineEnrichmentError("unsupported story pacing")
        if not self.clip_orders:
            raise StoryTimelineEnrichmentError("story beat requires clip bindings")
        if any(
            not isinstance(order, int)
            or isinstance(order, bool)
            or order < 1
            or order > clip_count
            for order in self.clip_orders
        ):
            raise StoryTimelineEnrichmentError("story beat clip binding is invalid")
        if len(set(self.clip_orders)) != len(self.clip_orders):
            raise StoryTimelineEnrichmentError("story beat clip bindings must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "order": self.order,
            "beat_type": self.beat_type,
            "text": self.text,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "clip_orders": list(self.clip_orders),
            "pacing": self.pacing,
            "on_screen_text": self.on_screen_text,
        }


@dataclass(frozen=True)
class NarrationCue:
    order: int
    text: str
    start_seconds: float
    end_seconds: float
    language: str
    emphasis: str

    def validate(self, *, timeline_duration: float) -> None:
        if not isinstance(self.order, int) or isinstance(self.order, bool) or self.order < 1:
            raise StoryTimelineEnrichmentError("narration order must be positive")
        if not self.text.strip():
            raise StoryTimelineEnrichmentError("narration text is required")
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise StoryTimelineEnrichmentError("narration timestamps are invalid")
        if self.end_seconds > timeline_duration:
            raise StoryTimelineEnrichmentError("narration exceeds timeline duration")
        if not self.language.strip():
            raise StoryTimelineEnrichmentError("narration language is required")
        if self.emphasis not in {"normal", "strong", "climax", "cta"}:
            raise StoryTimelineEnrichmentError("unsupported narration emphasis")

    def to_dict(self) -> dict[str, object]:
        return {
            "order": self.order,
            "text": self.text,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "language": self.language,
            "emphasis": self.emphasis,
        }


@dataclass(frozen=True)
class StoryTimelineEnrichment:
    schema: str
    enrichment_id: str
    timeline_id: str
    timeline_evidence_sha256: str
    title: str
    language: str
    beats: tuple[StoryBeat, ...]
    narration: tuple[NarrationCue, ...]
    captions_required: bool
    music_mood: str | None
    target_retention_seconds: float
    enrichment_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    ai_execution_enabled: bool = False
    render_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self, timeline: TimelineComposition) -> None:
        timeline.validate()
        if self.schema != "football-shorts-ai.story-timeline-enrichment.v1":
            raise StoryTimelineEnrichmentError("unsupported enrichment schema")
        if not self.enrichment_id.startswith("STORYTL-"):
            raise StoryTimelineEnrichmentError("enrichment_id must start with STORYTL-")
        if self.timeline_id != timeline.timeline_id:
            raise StoryTimelineEnrichmentError("timeline identity mismatch")
        if self.timeline_evidence_sha256 != timeline.evidence_sha256:
            raise StoryTimelineEnrichmentError("timeline evidence mismatch")
        if not self.title.strip() or not self.language.strip():
            raise StoryTimelineEnrichmentError("title and language are required")
        if not self.beats:
            raise StoryTimelineEnrichmentError("at least one story beat is required")
        orders = [beat.order for beat in self.beats]
        if orders != list(range(1, len(self.beats) + 1)):
            raise StoryTimelineEnrichmentError("story beat order must be contiguous")
        for beat in self.beats:
            beat.validate(
                timeline_duration=timeline.total_duration_seconds,
                clip_count=len(timeline.clips),
            )
        narration_orders = [cue.order for cue in self.narration]
        if narration_orders != list(range(1, len(self.narration) + 1)):
            raise StoryTimelineEnrichmentError("narration order must be contiguous")
        for cue in self.narration:
            cue.validate(timeline_duration=timeline.total_duration_seconds)
        if not 1 <= self.target_retention_seconds <= timeline.total_duration_seconds:
            raise StoryTimelineEnrichmentError("target retention is outside timeline")
        if self.enrichment_state not in SUPPORTED_ENRICHMENT_STATES:
            raise StoryTimelineEnrichmentError("unsupported enrichment state")
        if self.enrichment_state == "ready_for_factory" and self.blockers:
            raise StoryTimelineEnrichmentError("ready enrichment cannot contain blockers")
        if self.enrichment_state == "blocked" and not self.blockers:
            raise StoryTimelineEnrichmentError("blocked enrichment requires blockers")
        if self.ai_execution_enabled:
            raise StoryTimelineEnrichmentError("0054H cannot enable AI execution")
        if self.render_enabled or self.auto_render or self.auto_publish:
            raise StoryTimelineEnrichmentError("automatic production actions are forbidden")
        if not _is_sha256(self.evidence_sha256):
            raise StoryTimelineEnrichmentError("enrichment evidence must be SHA-256")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "enrichment_id": self.enrichment_id,
            "timeline_id": self.timeline_id,
            "timeline_evidence_sha256": self.timeline_evidence_sha256,
            "title": self.title,
            "language": self.language,
            "beats": [beat.to_dict() for beat in self.beats],
            "narration": [cue.to_dict() for cue in self.narration],
            "captions_required": self.captions_required,
            "music_mood": self.music_mood,
            "target_retention_seconds": self.target_retention_seconds,
            "enrichment_state": self.enrichment_state,
            "blockers": list(self.blockers),
            "evidence_sha256": self.evidence_sha256,
            "ai_execution_enabled": False,
            "render_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }


def build_story_timeline_enrichment(
    *,
    timeline: TimelineComposition,
    story: Mapping[str, object],
    language: str = "pt-PT",
    music_mood: str | None = None,
    requested_state: str = "draft",
) -> StoryTimelineEnrichment:
    """Bind supplied editorial story evidence to one deterministic timeline."""

    timeline.validate()
    if requested_state not in SUPPORTED_ENRICHMENT_STATES:
        raise StoryTimelineEnrichmentError("unsupported requested state")

    sections = _extract_sections(story)
    beat_types = tuple(name for name in SUPPORTED_BEAT_TYPES if sections.get(name))
    ordered_types = tuple(
        name
        for name in (
            "hook",
            "introduction",
            "development",
            "climax",
            "ending",
            "call_to_action",
        )
        if name in beat_types
    )
    if not ordered_types:
        raise StoryTimelineEnrichmentError("story contains no usable sections")

    beats = _allocate_beats(
        ordered_types=ordered_types,
        sections=sections,
        timeline=timeline,
    )
    narration = tuple(
        NarrationCue(
            order=index,
            text=beat.text,
            start_seconds=beat.start_seconds,
            end_seconds=beat.end_seconds,
            language=language,
            emphasis=(
                "climax"
                if beat.beat_type == "climax"
                else "cta"
                if beat.beat_type == "call_to_action"
                else "strong"
                if beat.beat_type == "hook"
                else "normal"
            ),
        )
        for index, beat in enumerate(beats, start=1)
    )

    blockers = list(timeline.blockers)
    if timeline.timeline_state == "blocked":
        blockers.append("TIMELINE_BLOCKED")
    if not all(clip.render_allowed for clip in timeline.clips):
        blockers.append("NON_RENDERABLE_CLIPS_PRESENT")
    blockers_tuple = tuple(sorted(set(blockers)))
    state = "blocked" if blockers_tuple else requested_state

    target_retention = round(
        min(
            timeline.total_duration_seconds,
            max(1.0, timeline.total_duration_seconds * 0.8),
        ),
        3,
    )
    unsigned = {
        "schema": "football-shorts-ai.story-timeline-enrichment.v1",
        "timeline_id": timeline.timeline_id,
        "timeline_evidence_sha256": timeline.evidence_sha256,
        "title": timeline.title,
        "language": language,
        "beats": [beat.to_dict() for beat in beats],
        "narration": [cue.to_dict() for cue in narration],
        "captions_required": True,
        "music_mood": music_mood,
        "target_retention_seconds": target_retention,
        "enrichment_state": state,
        "blockers": list(blockers_tuple),
        "ai_execution_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    evidence_sha256 = canonical_sha256(unsigned)
    result = StoryTimelineEnrichment(
        schema="football-shorts-ai.story-timeline-enrichment.v1",
        enrichment_id=f"STORYTL-{evidence_sha256[:20].upper()}",
        timeline_id=timeline.timeline_id,
        timeline_evidence_sha256=timeline.evidence_sha256,
        title=timeline.title,
        language=language,
        beats=beats,
        narration=narration,
        captions_required=True,
        music_mood=music_mood,
        target_retention_seconds=target_retention,
        enrichment_state=state,
        blockers=blockers_tuple,
        evidence_sha256=evidence_sha256,
        ai_execution_enabled=False,
        render_enabled=False,
        auto_render=False,
        auto_publish=False,
    )
    result.validate(timeline)
    return result


def _extract_sections(story: Mapping[str, object]) -> dict[str, str]:
    aliases: dict[str, Sequence[str]] = {
        "hook": ("hook", "top_hook"),
        "introduction": ("introduction", "intro"),
        "development": ("development", "body"),
        "climax": ("climax",),
        "ending": ("ending", "conclusion"),
        "call_to_action": ("call_to_action", "cta"),
    }
    sections: dict[str, str] = {}
    for name, candidates in aliases.items():
        for candidate in candidates:
            value = story.get(candidate)
            if isinstance(value, str) and value.strip():
                sections[name] = value.strip()
                break
    script = story.get("script")
    if isinstance(script, Mapping):
        nested = _extract_sections(script)
        for name, value in nested.items():
            sections.setdefault(name, value)
    return sections


def _allocate_beats(
    *,
    ordered_types: tuple[str, ...],
    sections: Mapping[str, str],
    timeline: TimelineComposition,
) -> tuple[StoryBeat, ...]:
    duration = timeline.total_duration_seconds
    clip_count = len(timeline.clips)
    weights = {
        "hook": 0.14,
        "introduction": 0.14,
        "development": 0.30,
        "climax": 0.20,
        "ending": 0.12,
        "call_to_action": 0.10,
    }
    total_weight = sum(weights[name] for name in ordered_types)
    cursor = 0.0
    beats: list[StoryBeat] = []
    for index, name in enumerate(ordered_types, start=1):
        if index == len(ordered_types):
            end = duration
        else:
            segment = duration * weights[name] / total_weight
            end = round(cursor + segment, 3)
        start = round(cursor, 3)
        end = round(end, 3)
        first_clip = min(clip_count, max(1, int((start / duration) * clip_count) + 1))
        last_probe = max(start, end - 0.001)
        last_clip = min(clip_count, max(first_clip, int((last_probe / duration) * clip_count) + 1))
        beats.append(
            StoryBeat(
                order=index,
                beat_type=name,
                text=sections[name],
                start_seconds=start,
                end_seconds=end,
                clip_orders=tuple(range(first_clip, last_clip + 1)),
                pacing=(
                    "impact"
                    if name in {"hook", "climax"}
                    else "fast"
                    if name == "call_to_action"
                    else "balanced"
                ),
                on_screen_text=(sections[name] if name in {"hook", "call_to_action"} else None),
            )
        )
        cursor = end
    return tuple(beats)


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
    "NarrationCue",
    "StoryBeat",
    "StoryTimelineEnrichment",
    "StoryTimelineEnrichmentError",
    "SUPPORTED_BEAT_TYPES",
    "SUPPORTED_ENRICHMENT_STATES",
    "SUPPORTED_PACING",
    "build_story_timeline_enrichment",
    "canonical_sha256",
]
