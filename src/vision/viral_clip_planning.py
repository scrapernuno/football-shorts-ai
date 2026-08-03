"""
FOOTBALL-SHORTS-AI-0057I
VIRAL CLIP PLANNING AND EDITORIAL HANDOVER CONTRACT

Transforms governed 0057H viral-moment rankings into deterministic clip proposals.
No media is downloaded, extracted, rendered, uploaded or published.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ViralClipPlanningError(ValueError):
    """Raised when governed clip-planning evidence is invalid."""


SUPPORTED_STATES = {"planned", "review_required", "blocked"}
SUPPORTED_ROLES = {"hook", "development", "climax", "reaction", "resolution"}
SUPPORTED_RIGHTS = {"owned", "licensed", "reference_only"}


@dataclass(frozen=True)
class ViralClipProposal:
    clip_id: str
    moment_id: str
    scene_id: str
    editorial_role: str
    source_start_seconds: float
    source_end_seconds: float
    duration_seconds: float
    priority: int
    viral_score: float
    confidence: float
    rights_status: str
    render_allowed: bool
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.clip_id.startswith("VIRALCLIP-"):
            raise ViralClipPlanningError("invalid viral clip identity")
        if not self.moment_id.startswith("VIRALMOMENT-"):
            raise ViralClipPlanningError("invalid viral moment identity")
        if not self.scene_id.startswith("VSCENE-"):
            raise ViralClipPlanningError("invalid vision scene identity")
        if self.editorial_role not in SUPPORTED_ROLES:
            raise ViralClipPlanningError("unsupported editorial role")
        if not 0.0 <= self.source_start_seconds < self.source_end_seconds:
            raise ViralClipPlanningError("clip timestamps are invalid")
        expected = round(self.source_end_seconds - self.source_start_seconds, 3)
        if round(self.duration_seconds, 3) != expected:
            raise ViralClipPlanningError("clip duration is inconsistent")
        if not 0.5 <= self.duration_seconds <= 15.0:
            raise ViralClipPlanningError("clip duration is outside governed limits")
        if self.priority < 1:
            raise ViralClipPlanningError("clip priority must be positive")
        for name, value in (("viral_score", self.viral_score), ("confidence", self.confidence)):
            if not 0.0 <= value <= 1.0:
                raise ViralClipPlanningError(f"{name} must be between 0 and 1")
        if self.rights_status not in SUPPORTED_RIGHTS:
            raise ViralClipPlanningError("unsupported rights status")
        if self.render_allowed != (self.rights_status in {"owned", "licensed"} and not self.blockers):
            raise ViralClipPlanningError("render permission is inconsistent")
        if not self.evidence_ids or tuple(sorted(set(self.evidence_ids))) != self.evidence_ids:
            raise ViralClipPlanningError("clip evidence must be normalized")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ViralClipPlanningError("clip blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "clip_id": self.clip_id,
            "moment_id": self.moment_id,
            "scene_id": self.scene_id,
            "editorial_role": self.editorial_role,
            "source_start_seconds": round(self.source_start_seconds, 3),
            "source_end_seconds": round(self.source_end_seconds, 3),
            "duration_seconds": round(self.duration_seconds, 3),
            "priority": self.priority,
            "viral_score": round(self.viral_score, 4),
            "confidence": round(self.confidence, 4),
            "rights_status": self.rights_status,
            "render_allowed": self.render_allowed,
            "evidence_ids": list(self.evidence_ids),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ViralClipPlan:
    schema: str
    plan_id: str
    ranking_id: str
    asset_id: str
    rights_status: str
    clips: tuple[ViralClipProposal, ...]
    selected_hook_clip_id: str | None
    selected_climax_clip_id: str | None
    total_planned_duration_seconds: float
    planning_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.viral-clip-plan.v1":
            raise ViralClipPlanningError("unsupported viral clip plan schema")
        if not self.plan_id.startswith("CLIPPLAN-"):
            raise ViralClipPlanningError("invalid clip plan identity")
        if not self.ranking_id.startswith("VIRALRANK-"):
            raise ViralClipPlanningError("invalid ranking identity")
        if not self.asset_id.startswith("EXT-"):
            raise ViralClipPlanningError("invalid asset identity")
        if self.rights_status not in SUPPORTED_RIGHTS:
            raise ViralClipPlanningError("unsupported rights status")
        clip_ids = {item.clip_id for item in self.clips}
        if len(clip_ids) != len(self.clips):
            raise ViralClipPlanningError("clip identities must be unique")
        for expected_priority, item in enumerate(self.clips, start=1):
            item.validate()
            if item.priority != expected_priority:
                raise ViralClipPlanningError("clip priorities must be contiguous")
        if self.selected_hook_clip_id is not None and self.selected_hook_clip_id not in clip_ids:
            raise ViralClipPlanningError("selected hook clip is unknown")
        if self.selected_climax_clip_id is not None and self.selected_climax_clip_id not in clip_ids:
            raise ViralClipPlanningError("selected climax clip is unknown")
        expected_duration = round(sum(item.duration_seconds for item in self.clips), 3)
        if round(self.total_planned_duration_seconds, 3) != expected_duration:
            raise ViralClipPlanningError("planned duration is inconsistent")
        if self.planning_state not in SUPPORTED_STATES:
            raise ViralClipPlanningError("unsupported planning state")
        if self.planning_state == "planned" and (self.blockers or not self.clips):
            raise ViralClipPlanningError("planned report requires unblocked clips")
        if self.planning_state in {"review_required", "blocked"} and not self.blockers:
            raise ViralClipPlanningError("non-planned report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise ViralClipPlanningError("0057I cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ViralClipPlanningError("clip plan evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "plan_id": self.plan_id,
            "ranking_id": self.ranking_id,
            "asset_id": self.asset_id,
            "rights_status": self.rights_status,
            "clips": [item.to_dict() for item in self.clips],
            "selected_hook_clip_id": self.selected_hook_clip_id,
            "selected_climax_clip_id": self.selected_climax_clip_id,
            "total_planned_duration_seconds": self.total_planned_duration_seconds,
            "planning_state": self.planning_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_viral_clip_plan(
    *,
    ranking_report: Mapping[str, object],
    asset_id: str,
    rights_status: str,
    maximum_clips: int = 8,
    pre_roll_seconds: float = 0.35,
    post_roll_seconds: float = 0.65,
) -> ViralClipPlan:
    if not asset_id.startswith("EXT-"):
        raise ViralClipPlanningError("asset_id must start with EXT-")
    if rights_status not in SUPPORTED_RIGHTS:
        raise ViralClipPlanningError("unsupported rights status")
    if not 1 <= maximum_clips <= 20:
        raise ViralClipPlanningError("maximum_clips must be between 1 and 20")
    if not 0.0 <= pre_roll_seconds <= 3.0 or not 0.0 <= post_roll_seconds <= 3.0:
        raise ViralClipPlanningError("clip roll values are outside governed limits")

    ranking_id = _required_text(ranking_report, "ranking_id", "VIRALRANK-")
    ranking_state = str(ranking_report.get("ranking_state", "blocked"))
    candidates = [item for item in ranking_report.get("candidates", ()) if isinstance(item, Mapping)]
    ranked_ids = [str(item) for item in ranking_report.get("ranked_moment_ids", ())]
    by_id = {str(item.get("moment_id", "")): item for item in candidates}
    ordered = [by_id[item] for item in ranked_ids if item in by_id][:maximum_clips]

    blockers: set[str] = set()
    if ranking_state not in {"ranked", "review_required"}:
        blockers.add("VIRAL_RANKING_NOT_READY")
    if not ordered:
        blockers.add("VIRAL_CLIP_CANDIDATES_MISSING")
    if rights_status == "reference_only":
        blockers.add("REFERENCE_ONLY_RENDER_BLOCKED")

    clips: list[ViralClipProposal] = []
    for priority, moment in enumerate(ordered, start=1):
        start = max(0.0, float(moment.get("start_seconds", 0.0)) - pre_roll_seconds)
        end = float(moment.get("end_seconds", 0.0)) + post_roll_seconds
        duration = end - start
        if duration > 15.0:
            end = start + 15.0
            duration = 15.0
        if duration < 0.5:
            end = start + 0.5
            duration = 0.5
        moment_blockers = set(str(item) for item in moment.get("blockers", ()))
        if rights_status == "reference_only":
            moment_blockers.add("REFERENCE_ONLY_RENDER_BLOCKED")
        evidence_ids = tuple(sorted(set(str(item) for item in moment.get("evidence_ids", ()) if str(item))))
        if not evidence_ids:
            evidence_ids = (str(moment.get("moment_id", "UNKNOWN")),)
        core = {
            "moment_id": str(moment["moment_id"]),
            "scene_id": str(moment["scene_id"]),
            "editorial_role": str(moment.get("editorial_role", "development")),
            "source_start_seconds": round(start, 3),
            "source_end_seconds": round(end, 3),
            "duration_seconds": round(duration, 3),
            "priority": priority,
            "viral_score": round(float(moment.get("viral_moment_score", 0.0)), 4),
            "confidence": round(float(moment.get("confidence", 0.0)), 4),
            "rights_status": rights_status,
            "render_allowed": rights_status in {"owned", "licensed"} and not moment_blockers,
            "evidence_ids": evidence_ids,
            "blockers": tuple(sorted(moment_blockers)),
        }
        clips.append(ViralClipProposal(clip_id=f"VIRALCLIP-{canonical_sha256(core)[:20].upper()}", **core))

    if any(item.blockers for item in clips):
        blockers.add("CLIP_REVIEW_REQUIRED")
    state = "blocked" if rights_status == "reference_only" or "VIRAL_RANKING_NOT_READY" in blockers or not clips else "review_required" if blockers else "planned"
    hook_moment_id = ranking_report.get("top_hook_moment_id")
    climax_moment_id = ranking_report.get("top_climax_moment_id")
    hook_clip = next((item.clip_id for item in clips if item.moment_id == hook_moment_id), None)
    climax_clip = next((item.clip_id for item in clips if item.moment_id == climax_moment_id), None)
    total = round(sum(item.duration_seconds for item in clips), 3)
    core = {
        "schema": "football-shorts-ai.viral-clip-plan.v1",
        "ranking_id": ranking_id,
        "asset_id": asset_id,
        "rights_status": rights_status,
        "clips": [item.to_dict() for item in clips],
        "selected_hook_clip_id": hook_clip,
        "selected_climax_clip_id": climax_clip,
        "total_planned_duration_seconds": total,
        "planning_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    plan_id = f"CLIPPLAN-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "plan_id": plan_id}
    result = ViralClipPlan(
        plan_id=plan_id,
        evidence_sha256=canonical_sha256(unsigned),
        ranking_id=ranking_id,
        asset_id=asset_id,
        rights_status=rights_status,
        clips=tuple(clips),
        selected_hook_clip_id=hook_clip,
        selected_climax_clip_id=climax_clip,
        total_planned_duration_seconds=total,
        planning_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.viral-clip-plan.v1",
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _required_text(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ViralClipPlanningError(f"invalid {key}")
    return value


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ViralClipPlanningError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ViralClipPlanningError("evidence must be hexadecimal") from exc


__all__ = [
    "ViralClipPlan",
    "ViralClipPlanningError",
    "ViralClipProposal",
    "build_viral_clip_plan",
    "canonical_sha256",
]
