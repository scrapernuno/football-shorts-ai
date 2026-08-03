"""
FOOTBALL-SHORTS-AI-0058B
AI DIRECTOR NARRATIVE BEAT AND SCRIPT ALIGNMENT CONTRACT

Deterministic, reviewable alignment between 0058A director variants and narrative
script beats. This module performs no network access, media acquisition, model
training, extraction, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class NarrativeScriptAlignmentError(ValueError):
    """Raised when governed narrative/script alignment evidence is invalid."""


SUPPORTED_STATES = {"aligned", "review_required", "blocked"}
SUPPORTED_BEAT_ROLES = {"hook", "context", "development", "climax", "reaction", "resolution", "cta"}


@dataclass(frozen=True)
class NarrativeBeat:
    beat_id: str
    position: int
    role: str
    script_text: str
    segment_id: str
    clip_id: str
    start_seconds: float
    end_seconds: float
    narration_start_seconds: float
    narration_end_seconds: float
    alignment_score: float
    confidence: float
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.beat_id.startswith("DIRBEAT-"):
            raise NarrativeScriptAlignmentError("invalid narrative beat identity")
        if self.position < 0:
            raise NarrativeScriptAlignmentError("beat position must be non-negative")
        if self.role not in SUPPORTED_BEAT_ROLES:
            raise NarrativeScriptAlignmentError("unsupported narrative beat role")
        if not self.script_text.strip():
            raise NarrativeScriptAlignmentError("script text is required")
        if not self.segment_id.startswith("DIRSEG-"):
            raise NarrativeScriptAlignmentError("invalid director segment identity")
        if not self.clip_id.startswith("VIRALCLIP-"):
            raise NarrativeScriptAlignmentError("invalid clip identity")
        if not 0.0 <= self.start_seconds < self.end_seconds:
            raise NarrativeScriptAlignmentError("beat clip timestamps are invalid")
        if not self.start_seconds <= self.narration_start_seconds < self.narration_end_seconds <= self.end_seconds:
            raise NarrativeScriptAlignmentError("narration timing must fit inside the clip")
        for name, value in (("alignment_score", self.alignment_score), ("confidence", self.confidence)):
            if not 0.0 <= value <= 1.0:
                raise NarrativeScriptAlignmentError(f"{name} must be between 0 and 1")
        if not self.evidence_ids or tuple(sorted(set(self.evidence_ids))) != self.evidence_ids:
            raise NarrativeScriptAlignmentError("beat evidence identities must be normalized and non-empty")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise NarrativeScriptAlignmentError("beat blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "beat_id": self.beat_id,
            "position": self.position,
            "role": self.role,
            "script_text": self.script_text,
            "segment_id": self.segment_id,
            "clip_id": self.clip_id,
            "start_seconds": round(self.start_seconds, 3),
            "end_seconds": round(self.end_seconds, 3),
            "narration_start_seconds": round(self.narration_start_seconds, 3),
            "narration_end_seconds": round(self.narration_end_seconds, 3),
            "alignment_score": round(self.alignment_score, 4),
            "confidence": round(self.confidence, 4),
            "evidence_ids": list(self.evidence_ids),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class NarrativeScriptAlignmentReport:
    schema: str
    alignment_id: str
    director_report_id: str
    variant_id: str
    beats: tuple[NarrativeBeat, ...]
    total_duration_seconds: float
    average_alignment_score: float
    alignment_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.narrative-script-alignment.v1":
            raise NarrativeScriptAlignmentError("unsupported alignment schema")
        if not self.alignment_id.startswith("DIRALIGN-"):
            raise NarrativeScriptAlignmentError("invalid alignment identity")
        if not self.director_report_id.startswith("AIDIRECTOR-"):
            raise NarrativeScriptAlignmentError("invalid director report identity")
        if not self.variant_id.startswith("DIRVAR-"):
            raise NarrativeScriptAlignmentError("invalid director variant identity")
        if self.alignment_state not in SUPPORTED_STATES:
            raise NarrativeScriptAlignmentError("unsupported alignment state")
        beat_ids = {item.beat_id for item in self.beats}
        if len(beat_ids) != len(self.beats):
            raise NarrativeScriptAlignmentError("beat identities must be unique")
        for expected_position, item in enumerate(self.beats):
            item.validate()
            if item.position != expected_position:
                raise NarrativeScriptAlignmentError("beats must use contiguous narrative positions")
        expected_duration = round(sum(item.end_seconds - item.start_seconds for item in self.beats), 3)
        if round(self.total_duration_seconds, 3) != expected_duration:
            raise NarrativeScriptAlignmentError("total duration is inconsistent")
        expected_average = round(sum(item.alignment_score for item in self.beats) / len(self.beats), 4) if self.beats else 0.0
        if round(self.average_alignment_score, 4) != expected_average:
            raise NarrativeScriptAlignmentError("average alignment score is inconsistent")
        if self.alignment_state == "aligned" and (self.blockers or not self.beats):
            raise NarrativeScriptAlignmentError("aligned report requires unblocked beats")
        if self.alignment_state in {"review_required", "blocked"} and not self.blockers:
            raise NarrativeScriptAlignmentError("non-aligned report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise NarrativeScriptAlignmentError("0058B cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise NarrativeScriptAlignmentError("alignment evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "alignment_id": self.alignment_id,
            "director_report_id": self.director_report_id,
            "variant_id": self.variant_id,
            "beats": [item.to_dict() for item in self.beats],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "average_alignment_score": round(self.average_alignment_score, 4),
            "alignment_state": self.alignment_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_narrative_script_alignment(
    *,
    director_report: Mapping[str, object],
    script_beats: Sequence[Mapping[str, object]],
    variant_id: str | None = None,
    minimum_alignment_score: float = 0.65,
) -> NarrativeScriptAlignmentReport:
    if not 0.0 <= minimum_alignment_score <= 1.0:
        raise NarrativeScriptAlignmentError("minimum_alignment_score must be between 0 and 1")
    director_id = _required_id(director_report, "director_id", "AIDIRECTOR-")
    selected_variant_id = variant_id or str(director_report.get("recommended_variant_id", ""))
    if not selected_variant_id.startswith("DIRVAR-"):
        raise NarrativeScriptAlignmentError("variant_id must start with DIRVAR-")
    variants = [item for item in director_report.get("variants", ()) if isinstance(item, Mapping)]
    variant = next((item for item in variants if item.get("variant_id") == selected_variant_id), None)
    if variant is None:
        raise NarrativeScriptAlignmentError("selected director variant is unknown")

    blockers: set[str] = set()
    director_state = str(director_report.get("director_state", "blocked"))
    if director_state == "blocked":
        blockers.add("DIRECTOR_REPORT_BLOCKED")
    if bool(variant.get("render_allowed", False)) is False:
        blockers.add("DIRECTOR_VARIANT_RENDER_BLOCKED")

    segments = [item for item in variant.get("segments", ()) if isinstance(item, Mapping)]
    beats: list[NarrativeBeat] = []
    if len(script_beats) != len(segments):
        blockers.add("SCRIPT_SEGMENT_COUNT_MISMATCH")
    for position, (script, segment) in enumerate(zip(script_beats, segments)):
        role = str(script.get("role", segment.get("editorial_role", "development")))
        text = str(script.get("script_text", "")).strip()
        start = float(segment.get("start_seconds", 0.0))
        end = float(segment.get("end_seconds", 0.0))
        duration = max(0.0, end - start)
        word_count = max(1, len(text.split()))
        estimated_narration = min(duration, max(0.5, word_count / 2.7))
        narration_start = start
        narration_end = min(end, narration_start + estimated_narration)
        semantic_score = float(script.get("semantic_score", 0.75))
        timing_score = 1.0 if estimated_narration <= duration else 0.0
        role_score = 1.0 if role == str(segment.get("editorial_role", role)) else 0.55
        alignment_score = _clamp(0.50 * semantic_score + 0.30 * timing_score + 0.20 * role_score)
        confidence = _clamp(float(script.get("confidence", alignment_score)))
        beat_blockers: set[str] = set()
        if not text:
            beat_blockers.add("SCRIPT_TEXT_MISSING")
        if role not in SUPPORTED_BEAT_ROLES:
            beat_blockers.add("SCRIPT_ROLE_UNSUPPORTED")
        if alignment_score < minimum_alignment_score:
            beat_blockers.add("SCRIPT_ALIGNMENT_REVIEW_REQUIRED")
        evidence_ids = tuple(sorted({
            str(segment.get("segment_id", "")),
            str(segment.get("clip_id", "")),
            str(script.get("evidence_id", "")),
        } - {""}))
        core = {
            "position": position,
            "role": role,
            "script_text": text,
            "segment_id": str(segment.get("segment_id", "")),
            "clip_id": str(segment.get("clip_id", "")),
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "narration_start_seconds": round(narration_start, 3),
            "narration_end_seconds": round(narration_end, 3),
            "alignment_score": round(alignment_score, 4),
            "confidence": round(confidence, 4),
            "evidence_ids": evidence_ids or (str(segment.get("segment_id", "DIRSEG-MISSING")),),
            "blockers": tuple(sorted(beat_blockers)),
        }
        beat = NarrativeBeat(beat_id=f"DIRBEAT-{canonical_sha256(core)[:20].upper()}", **core)
        beats.append(beat)
        blockers.update(beat_blockers)

    if not beats:
        blockers.add("SCRIPT_ALIGNMENT_EVIDENCE_MISSING")
    state = "blocked" if "DIRECTOR_REPORT_BLOCKED" in blockers or not beats else "review_required" if blockers else "aligned"
    total = round(sum(item.end_seconds - item.start_seconds for item in beats), 3)
    average = round(sum(item.alignment_score for item in beats) / len(beats), 4) if beats else 0.0
    core = {
        "schema": "football-shorts-ai.narrative-script-alignment.v1",
        "director_report_id": director_id,
        "variant_id": selected_variant_id,
        "beats": [item.to_dict() for item in beats],
        "total_duration_seconds": total,
        "average_alignment_score": average,
        "alignment_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    alignment_id = f"DIRALIGN-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "alignment_id": alignment_id}
    result = NarrativeScriptAlignmentReport(
        alignment_id=alignment_id,
        evidence_sha256=canonical_sha256(unsigned),
        director_report_id=director_id,
        variant_id=selected_variant_id,
        beats=tuple(beats),
        total_duration_seconds=total,
        average_alignment_score=average,
        alignment_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.narrative-script-alignment.v1",
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _required_id(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise NarrativeScriptAlignmentError(f"{key} must start with {prefix}")
    return value


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise NarrativeScriptAlignmentError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise NarrativeScriptAlignmentError("evidence must be hexadecimal") from exc


__all__ = [
    "NarrativeBeat",
    "NarrativeScriptAlignmentError",
    "NarrativeScriptAlignmentReport",
    "build_narrative_script_alignment",
    "canonical_sha256",
]
