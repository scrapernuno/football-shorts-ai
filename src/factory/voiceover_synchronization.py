"""FOOTBALL-SHORTS-AI-0060E — governed voiceover synchronization.

Builds a deterministic browser-preview audio track from a composed timeline and
locally supplied, rights-cleared audio assets. It never synthesizes speech,
fetches media, renders video, or publishes content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class VoiceoverSynchronizationError(ValueError):
    pass


@dataclass(frozen=True)
class VoiceoverCue:
    cue_id: str
    timeline_clip_id: str
    timeline_start_seconds: float
    timeline_end_seconds: float
    audio_uri: str | None
    audio_start_seconds: float
    audio_end_seconds: float
    script_text: str
    role: str
    gain_db: float
    playback_rate: float
    audio_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.cue_id.startswith("VOICECUE-"):
            raise VoiceoverSynchronizationError("invalid voiceover cue identity")
        if not self.timeline_clip_id.startswith("TLINECLIP-"):
            raise VoiceoverSynchronizationError("invalid timeline clip identity")
        if not 0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise VoiceoverSynchronizationError("invalid cue timeline range")
        if not 0 <= self.audio_start_seconds <= self.audio_end_seconds:
            raise VoiceoverSynchronizationError("invalid cue audio range")
        if not 0.5 <= self.playback_rate <= 2.0:
            raise VoiceoverSynchronizationError("playback_rate out of range")
        if not -24.0 <= self.gain_db <= 12.0:
            raise VoiceoverSynchronizationError("gain_db out of range")
        if self.audio_allowed and (not self.audio_uri or self.blockers):
            raise VoiceoverSynchronizationError("allowed cue requires unblocked audio")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise VoiceoverSynchronizationError("cue blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "cue_id": self.cue_id,
            "timeline_clip_id": self.timeline_clip_id,
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "audio_uri": self.audio_uri,
            "audio_start_seconds": round(self.audio_start_seconds, 3),
            "audio_end_seconds": round(self.audio_end_seconds, 3),
            "script_text": self.script_text,
            "role": self.role,
            "gain_db": round(self.gain_db, 2),
            "playback_rate": round(self.playback_rate, 4),
            "audio_allowed": self.audio_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class VoiceoverTrack:
    schema: str
    track_id: str
    timeline_id: str
    language: str
    voice_style: str
    cues: tuple[VoiceoverCue, ...]
    synchronization_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    synthesis_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.voiceover-track.v1":
            raise VoiceoverSynchronizationError("unsupported voiceover schema")
        if not self.track_id.startswith("VOICETRACK-"):
            raise VoiceoverSynchronizationError("invalid voiceover track identity")
        if not self.timeline_id.startswith("TIMELINE-"):
            raise VoiceoverSynchronizationError("invalid timeline identity")
        if self.synchronization_state not in {"synchronized", "review_required", "blocked"}:
            raise VoiceoverSynchronizationError("unsupported synchronization state")
        for cue in self.cues:
            cue.validate()
        if self.synchronization_state == "synchronized" and (self.blockers or not self.cues):
            raise VoiceoverSynchronizationError("synchronized track requires cues")
        if self.synchronization_state != "synchronized" and not self.blockers:
            raise VoiceoverSynchronizationError("non-synchronized track requires blockers")
        if any((self.network_enabled, self.synthesis_enabled, self.acquisition_enabled,
                self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise VoiceoverSynchronizationError("0060E cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise VoiceoverSynchronizationError("voiceover evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "track_id": self.track_id,
            "timeline_id": self.timeline_id,
            "language": self.language,
            "voice_style": self.voice_style,
            "cues": [cue.to_dict() for cue in self.cues],
            "synchronization_state": self.synchronization_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "synthesis_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_voiceover_track(*, timeline: Mapping[str, object], audio_assets: Sequence[Mapping[str, object]] = (), language: str = "pt-PT", voice_style: str = "energetic") -> VoiceoverTrack:
    timeline_id = str(timeline.get("timeline_id", ""))
    if not timeline_id.startswith("TIMELINE-"):
        raise VoiceoverSynchronizationError("timeline_id is required")
    assets = {str(item.get("timeline_clip_id", "")): item for item in audio_assets}
    blockers: set[str] = set()
    if timeline.get("composition_state") != "composed":
        blockers.add("TIMELINE_NOT_COMPOSED")
    cues: list[VoiceoverCue] = []
    for clip in timeline.get("clips", ()):
        if not isinstance(clip, Mapping):
            continue
        clip_id = str(clip.get("timeline_clip_id", ""))
        asset = assets.get(clip_id, {})
        cue_blockers: set[str] = set()
        audio_uri = str(asset.get("audio_uri", "")).strip() or None
        rights = str(asset.get("rights_status", "reference_only"))
        if not audio_uri:
            cue_blockers.add("VOICEOVER_AUDIO_MISSING")
        if rights not in {"owned", "licensed"}:
            cue_blockers.add("VOICEOVER_AUDIO_NOT_AUTHORIZED")
        start = float(clip.get("timeline_start_seconds", 0.0))
        end = float(clip.get("timeline_end_seconds", 0.0))
        audio_start = float(asset.get("audio_start_seconds", 0.0))
        audio_end = float(asset.get("audio_end_seconds", max(0.0, end - start)))
        core = {
            "timeline_clip_id": clip_id,
            "timeline_start_seconds": start,
            "timeline_end_seconds": end,
            "audio_uri": audio_uri,
            "audio_start_seconds": audio_start,
            "audio_end_seconds": audio_end,
            "script_text": str(clip.get("script_text", "")),
            "role": str(clip.get("role", "development")),
            "gain_db": float(asset.get("gain_db", -3.0)),
            "playback_rate": float(asset.get("playback_rate", 1.0)),
            "audio_allowed": not cue_blockers,
            "blockers": tuple(sorted(cue_blockers)),
        }
        cues.append(VoiceoverCue(cue_id=f"VOICECUE-{canonical_sha256(core)[:20].upper()}", **core))
    if not cues:
        blockers.add("VOICEOVER_CUES_MISSING")
    if any(cue.blockers for cue in cues):
        blockers.add("VOICEOVER_REVIEW_REQUIRED")
    state = "blocked" if "TIMELINE_NOT_COMPOSED" in blockers or not cues else "review_required" if blockers else "synchronized"
    core = {
        "schema": "football-shorts-ai.voiceover-track.v1",
        "timeline_id": timeline_id,
        "language": language,
        "voice_style": voice_style,
        "cues": [cue.to_dict() for cue in cues],
        "synchronization_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "synthesis_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    track_id = f"VOICETRACK-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "track_id": track_id}
    result = VoiceoverTrack(
        schema=core["schema"], track_id=track_id, timeline_id=timeline_id,
        language=language, voice_style=voice_style, cues=tuple(cues),
        synchronization_state=state, blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


__all__ = ["VoiceoverCue", "VoiceoverTrack", "VoiceoverSynchronizationError", "build_voiceover_track", "canonical_sha256"]
