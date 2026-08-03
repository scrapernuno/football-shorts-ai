"""FOOTBALL-SHORTS-AI-0060D — deterministic subtitle generation.

Builds reviewable subtitle cues from a composed 0060C timeline. It performs no
network access, speech synthesis, extraction, rendering or publication.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class SubtitleGenerationError(ValueError):
    pass


@dataclass(frozen=True)
class SubtitleCue:
    cue_id: str
    timeline_clip_id: str
    start_seconds: float
    end_seconds: float
    text: str
    role: str
    position: str = "bottom"

    def validate(self) -> None:
        if not self.cue_id.startswith("SUBCUE-"):
            raise SubtitleGenerationError("invalid cue identity")
        if not self.timeline_clip_id.startswith("TLINECLIP-"):
            raise SubtitleGenerationError("invalid timeline clip identity")
        if not 0 <= self.start_seconds < self.end_seconds:
            raise SubtitleGenerationError("invalid cue timing")
        if not self.text.strip():
            raise SubtitleGenerationError("subtitle text is required")
        if len(self.text) > 180:
            raise SubtitleGenerationError("subtitle text exceeds governed limit")
        if self.position not in {"top", "middle", "bottom"}:
            raise SubtitleGenerationError("unsupported subtitle position")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "cue_id": self.cue_id,
            "timeline_clip_id": self.timeline_clip_id,
            "start_seconds": round(self.start_seconds, 3),
            "end_seconds": round(self.end_seconds, 3),
            "text": self.text,
            "role": self.role,
            "position": self.position,
        }


@dataclass(frozen=True)
class SubtitleTrack:
    schema: str
    track_id: str
    timeline_id: str
    language: str
    cues: tuple[SubtitleCue, ...]
    subtitle_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.subtitle-track.v1":
            raise SubtitleGenerationError("unsupported subtitle schema")
        if not self.track_id.startswith("SUBTRACK-"):
            raise SubtitleGenerationError("invalid subtitle track identity")
        if not self.timeline_id.startswith("TIMELINE-"):
            raise SubtitleGenerationError("invalid timeline identity")
        if self.subtitle_state not in {"generated", "review_required", "blocked"}:
            raise SubtitleGenerationError("unsupported subtitle state")
        for cue in self.cues:
            cue.validate()
        ordered = sorted(self.cues, key=lambda cue: (cue.start_seconds, cue.cue_id))
        if list(self.cues) != ordered:
            raise SubtitleGenerationError("subtitle cues must be ordered")
        for previous, current in zip(self.cues, self.cues[1:]):
            if current.start_seconds < previous.end_seconds - 0.001:
                raise SubtitleGenerationError("subtitle cues overlap")
        if self.subtitle_state == "generated" and (self.blockers or not self.cues):
            raise SubtitleGenerationError("generated subtitle track requires cues")
        if self.subtitle_state != "generated" and not self.blockers:
            raise SubtitleGenerationError("non-generated track requires blockers")
        if any((self.network_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise SubtitleGenerationError("0060D cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise SubtitleGenerationError("subtitle evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "track_id": self.track_id,
            "timeline_id": self.timeline_id,
            "language": self.language,
            "cues": [cue.to_dict() for cue in self.cues],
            "subtitle_state": self.subtitle_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_subtitle_track(*, timeline: Mapping[str, object], language: str = "pt-PT", max_words_per_cue: int = 8) -> SubtitleTrack:
    if max_words_per_cue < 1 or max_words_per_cue > 12:
        raise SubtitleGenerationError("max_words_per_cue must be between 1 and 12")
    timeline_id = str(timeline.get("timeline_id", ""))
    if not timeline_id.startswith("TIMELINE-"):
        raise SubtitleGenerationError("timeline_id is required")
    blockers: set[str] = set()
    if timeline.get("composition_state") != "composed":
        blockers.add("TIMELINE_NOT_COMPOSED")
    cues: list[SubtitleCue] = []
    for clip in timeline.get("clips", ()):
        if not isinstance(clip, Mapping):
            continue
        text = str(clip.get("script_text", "")).strip()
        if not text:
            blockers.add("SUBTITLE_TEXT_MISSING")
            continue
        start = float(clip.get("timeline_start_seconds", 0.0))
        end = float(clip.get("timeline_end_seconds", 0.0))
        words = text.split()
        chunks = [words[index:index + max_words_per_cue] for index in range(0, len(words), max_words_per_cue)]
        duration = end - start
        if duration <= 0:
            blockers.add("SUBTITLE_TIMING_INVALID")
            continue
        cursor = start
        for index, chunk in enumerate(chunks):
            chunk_end = end if index == len(chunks) - 1 else start + duration * (index + 1) / len(chunks)
            core = {
                "timeline_clip_id": str(clip.get("timeline_clip_id", "")),
                "start_seconds": round(cursor, 3),
                "end_seconds": round(chunk_end, 3),
                "text": " ".join(chunk),
                "role": str(clip.get("role", "development")),
                "position": "bottom",
            }
            cues.append(SubtitleCue(cue_id=f"SUBCUE-{canonical_sha256(core)[:20].upper()}", **core))
            cursor = chunk_end
    if not cues:
        blockers.add("SUBTITLE_CUES_MISSING")
    state = "blocked" if "TIMELINE_NOT_COMPOSED" in blockers or not cues else "review_required" if blockers else "generated"
    core = {
        "schema": "football-shorts-ai.subtitle-track.v1",
        "timeline_id": timeline_id,
        "language": language,
        "cues": [cue.to_dict() for cue in cues],
        "subtitle_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    track_id = f"SUBTRACK-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "track_id": track_id}
    result = SubtitleTrack(
        schema=core["schema"], track_id=track_id, timeline_id=timeline_id,
        language=language, cues=tuple(cues), subtitle_state=state,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


__all__ = ["SubtitleCue", "SubtitleGenerationError", "SubtitleTrack", "build_subtitle_track", "canonical_sha256"]
