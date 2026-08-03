"""FOOTBALL-SHORTS-AI-0060F — governed music, ambience and SFX mix planning.

This module only creates deterministic browser-preview mix instructions. It performs
no acquisition, generation, extraction, rendering, publication or network access.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class AudioMixError(ValueError):
    pass


SUPPORTED_KINDS = {"music", "ambience", "sfx"}
SUPPORTED_RIGHTS = {"owned", "licensed", "reference_only"}
SUPPORTED_STATES = {"mixed", "review_required", "blocked"}


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class AudioMixCue:
    cue_id: str
    kind: str
    audio_uri: str
    timeline_start_seconds: float
    timeline_end_seconds: float
    audio_start_seconds: float
    audio_end_seconds: float
    gain_db: float
    fade_in_seconds: float
    fade_out_seconds: float
    loop: bool
    duck_under_voiceover_db: float
    rights_status: str
    audio_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.cue_id.startswith("MIXCUE-"):
            raise AudioMixError("invalid cue identity")
        if self.kind not in SUPPORTED_KINDS:
            raise AudioMixError("unsupported audio kind")
        if self.rights_status not in SUPPORTED_RIGHTS:
            raise AudioMixError("unsupported rights status")
        if not 0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise AudioMixError("invalid timeline interval")
        if not 0 <= self.audio_start_seconds < self.audio_end_seconds:
            raise AudioMixError("invalid audio interval")
        if not -60 <= self.gain_db <= 12:
            raise AudioMixError("gain out of range")
        if not 0 <= self.fade_in_seconds <= 10 or not 0 <= self.fade_out_seconds <= 10:
            raise AudioMixError("fade out of range")
        if not -30 <= self.duck_under_voiceover_db <= 0:
            raise AudioMixError("ducking out of range")
        if self.rights_status == "reference_only" and self.audio_allowed:
            raise AudioMixError("reference-only audio cannot be allowed")
        if self.audio_allowed and (not self.audio_uri or self.blockers):
            raise AudioMixError("allowed audio must be complete and unblocked")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise AudioMixError("blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "cue_id": self.cue_id, "kind": self.kind, "audio_uri": self.audio_uri,
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "audio_start_seconds": round(self.audio_start_seconds, 3),
            "audio_end_seconds": round(self.audio_end_seconds, 3),
            "gain_db": round(self.gain_db, 2), "fade_in_seconds": round(self.fade_in_seconds, 3),
            "fade_out_seconds": round(self.fade_out_seconds, 3), "loop": self.loop,
            "duck_under_voiceover_db": round(self.duck_under_voiceover_db, 2),
            "rights_status": self.rights_status, "audio_allowed": self.audio_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class AudioMixTrack:
    schema: str
    mix_id: str
    timeline_id: str
    cues: tuple[AudioMixCue, ...]
    mix_state: str
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
            "schema": self.schema, "mix_id": self.mix_id, "timeline_id": self.timeline_id,
            "cues": [cue.to_dict() for cue in self.cues], "mix_state": self.mix_state,
            "blockers": list(self.blockers), "network_enabled": False,
            "generation_enabled": False, "acquisition_enabled": False,
            "extraction_enabled": False, "render_enabled": False, "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.audio-mix-track.v1":
            raise AudioMixError("unsupported mix schema")
        if not self.mix_id.startswith("AUDIOMIX-") or not self.timeline_id.startswith("TIMELINE-"):
            raise AudioMixError("invalid mix identity")
        if self.mix_state not in SUPPORTED_STATES:
            raise AudioMixError("unsupported mix state")
        for cue in self.cues:
            cue.validate()
        if self.mix_state == "mixed" and (self.blockers or not self.cues or any(not cue.audio_allowed for cue in self.cues)):
            raise AudioMixError("mixed state requires allowed cues")
        if self.mix_state != "mixed" and not self.blockers:
            raise AudioMixError("non-mixed state requires blockers")
        if any((self.network_enabled, self.generation_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise AudioMixError("0060F cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise AudioMixError("audio mix evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_audio_mix_track(*, timeline: Mapping[str, object], cue_inputs: Sequence[Mapping[str, object]]) -> AudioMixTrack:
    timeline_id = str(timeline.get("timeline_id", ""))
    blockers: set[str] = set()
    if not timeline_id.startswith("TIMELINE-") or timeline.get("composition_state") != "composed":
        blockers.add("TIMELINE_NOT_COMPOSED")
    cues: list[AudioMixCue] = []
    for raw in cue_inputs:
        cue_blockers: set[str] = set()
        rights = str(raw.get("rights_status", "reference_only"))
        uri = str(raw.get("audio_uri", ""))
        if rights == "reference_only": cue_blockers.add("AUDIO_NOT_AUTHORIZED")
        if not uri: cue_blockers.add("AUDIO_SOURCE_MISSING")
        core = {
            "kind": str(raw.get("kind", "")), "audio_uri": uri,
            "timeline_start_seconds": float(raw.get("timeline_start_seconds", 0)),
            "timeline_end_seconds": float(raw.get("timeline_end_seconds", 0)),
            "audio_start_seconds": float(raw.get("audio_start_seconds", 0)),
            "audio_end_seconds": float(raw.get("audio_end_seconds", 0)),
            "gain_db": float(raw.get("gain_db", -12)),
            "fade_in_seconds": float(raw.get("fade_in_seconds", 0)),
            "fade_out_seconds": float(raw.get("fade_out_seconds", 0)),
            "loop": bool(raw.get("loop", False)),
            "duck_under_voiceover_db": float(raw.get("duck_under_voiceover_db", -8)),
            "rights_status": rights,
            "audio_allowed": not cue_blockers,
            "blockers": tuple(sorted(cue_blockers)),
        }
        cue = AudioMixCue(cue_id=f"MIXCUE-{canonical_sha256(core)[:20].upper()}", **core)
        cue.validate(); cues.append(cue)
    if not cues: blockers.add("AUDIO_MIX_CUES_MISSING")
    if any(cue.blockers for cue in cues): blockers.add("AUDIO_MIX_REVIEW_REQUIRED")
    state = "blocked" if "TIMELINE_NOT_COMPOSED" in blockers or not cues else "review_required" if blockers else "mixed"
    core = {
        "schema": "football-shorts-ai.audio-mix-track.v1", "timeline_id": timeline_id,
        "cues": [cue.to_dict() for cue in cues], "mix_state": state,
        "blockers": sorted(blockers), "network_enabled": False,
        "generation_enabled": False, "acquisition_enabled": False,
        "extraction_enabled": False, "render_enabled": False, "auto_publish": False,
    }
    mix_id = f"AUDIOMIX-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "mix_id": mix_id}
    result = AudioMixTrack(
        schema=core["schema"], mix_id=mix_id, timeline_id=timeline_id, cues=tuple(cues),
        mix_state=state, blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate(); return result


__all__ = ["AudioMixCue", "AudioMixError", "AudioMixTrack", "build_audio_mix_track", "canonical_sha256"]
